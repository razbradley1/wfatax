"""Tax Report and Explainer API routes."""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.orm import Session
from pydantic import BaseModel

from ..database import get_db
from ..models import Scenario, Household, TaxReturn, Settings
from ..tax_engine.calculator import calculate_tax
from ..tax_engine.niit import get_niit_threshold
from ..tax_engine.irmaa import get_irmaa_breakpoints

router = APIRouter(prefix="/api/reports", tags=["reports"])


def _get_setting(db: Session, key: str, default: str = "") -> str:
    setting = db.query(Settings).filter(Settings.key == key).first()
    return setting.value if setting else default


def generate_observations(outputs: dict, inputs: dict) -> list:
    """Generate plain-English observations from tax calculation outputs."""
    obs = []
    filing_status = outputs.get("filing_status", "single")
    tax_year = outputs.get("tax_year", 2024)

    # Capital loss carryforward
    cf = outputs.get("capital_loss_carryforward_remaining", 0)
    if cf > 0:
        obs.append({
            "type": "capital_loss",
            "severity": "info",
            "text": f"Client has ${cf:,.0f} of capital loss carryforward available for future years.",
        })

    # NIIT proximity
    niit_dist = outputs.get("thresholds", {}).get("niit_distance", 0)
    if 0 < niit_dist < 50000:
        obs.append({
            "type": "niit",
            "severity": "warning",
            "text": f"Client is ${niit_dist:,.0f} below the NIIT threshold. Additional investment income may trigger the 3.8% surtax.",
        })
    elif niit_dist < 0:
        niit_amount = outputs.get("niit", 0)
        obs.append({
            "type": "niit",
            "severity": "alert",
            "text": f"Client is subject to NIIT. Current NIIT amount: ${niit_amount:,.0f}.",
        })

    # Roth conversion opportunity
    marginal = outputs.get("marginal_bracket", 0)
    if marginal <= 0.22:
        agi = outputs.get("agi", 0)
        obs.append({
            "type": "roth",
            "severity": "opportunity",
            "text": f"Client is in the {marginal*100:.0f}% bracket — this may be a good Roth conversion opportunity zone.",
        })

    # LTCG 0% bracket room
    ltcg_room = outputs.get("thresholds", {}).get("ltcg_room_in_0pct", 0)
    if ltcg_room > 0:
        obs.append({
            "type": "ltcg",
            "severity": "opportunity",
            "text": f"Client is in the 0% LTCG bracket with ${ltcg_room:,.0f} of room before the 15% rate begins.",
        })

    # IRMAA
    irmaa = outputs.get("irmaa", {})
    irmaa_dist = outputs.get("irmaa_distance_to_next_tier")
    if irmaa.get("tier", 0) > 0:
        surcharge = irmaa.get("annual_total_surcharge", 0)
        obs.append({
            "type": "irmaa",
            "severity": "alert",
            "text": f"Client is subject to IRMAA (Tier {irmaa['tier']}). Annual Medicare surcharge: ${surcharge:,.0f}.",
        })
    elif irmaa_dist and irmaa_dist.get("distance", 0) < 30000:
        obs.append({
            "type": "irmaa",
            "severity": "warning",
            "text": f"Client is within ${irmaa_dist['distance']:,.0f} of the next IRMAA tier. Additional income may trigger Medicare surcharges.",
        })

    # Social Security taxation
    ss_pct = outputs.get("social_security_taxation_pct", 0)
    ss_total = outputs.get("social_security_total", 0)
    if ss_total > 0 and ss_pct > 0:
        obs.append({
            "type": "social_security",
            "severity": "info",
            "text": f"Social Security is {ss_pct:.0f}% taxable. {'Income reduction strategies could reduce the taxable portion.' if ss_pct >= 50 else ''}",
        })

    # QBI deduction
    qbi = outputs.get("qbi_deduction", 0)
    if qbi > 0:
        obs.append({
            "type": "qbi",
            "severity": "info",
            "text": f"QBI deduction is ${qbi:,.0f}. Check if optimization opportunities exist (e.g., increasing W-2 wages for the W-2/UBIA test).",
        })

    # Estimated tax payments
    estimated = outputs.get("estimated_tax_payments", 0)
    if estimated > 0:
        total_tax = outputs.get("total_tax", 0)
        withholding = outputs.get("federal_withholding", 0)
        if withholding + estimated < total_tax * 0.9:
            obs.append({
                "type": "estimated_payments",
                "severity": "warning",
                "text": "Client paid estimated taxes. Total payments may be below the safe harbor threshold — check for underpayment penalty risk.",
            })

    # Deduction comparison
    std = outputs.get("standard_deduction", 0)
    itemized = outputs.get("total_itemized_deduction", 0)
    deduction_type = outputs.get("deduction_type", "standard")
    advantage = outputs.get("deduction_advantage", 0)
    if deduction_type == "standard" and itemized > 0:
        obs.append({
            "type": "deduction",
            "severity": "info",
            "text": f"Standard deduction (${std:,.0f}) exceeds itemized deductions (${itemized:,.0f}) by ${advantage:,.0f}. Consider bunching strategy for charitable contributions.",
        })

    return obs


@router.get("/tax-report/{scenario_id}")
def get_tax_report(scenario_id: int, db: Session = Depends(get_db)):
    """Generate a complete tax report for a scenario."""
    scenario = db.query(Scenario).filter(Scenario.id == scenario_id).first()
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")

    household = db.query(Household).filter(Household.id == scenario.household_id).first()
    outputs = scenario.calculated_outputs or {}

    # Income breakdown for charts
    income_breakdown = []
    income_fields = [
        ("Wages & Salaries", "wages_salaries"),
        ("Business Income", "business_income"),
        ("Capital Gains", "capital_gain_loss_net"),
        ("Interest & Dividends", None),  # Combined
        ("Retirement Distributions", None),  # Combined
        ("Social Security", "social_security_taxable"),
        ("Rental Income", "rental_income"),
        ("Other Income", "other_income"),
    ]

    for label, field in income_fields:
        if field:
            val = outputs.get(field, 0)
        elif label == "Interest & Dividends":
            val = outputs.get("interest_income_taxable", 0) + outputs.get("ordinary_dividends", 0)
        elif label == "Retirement Distributions":
            val = outputs.get("ira_distributions_taxable", 0) + outputs.get("pension_annuity_taxable", 0)
        else:
            val = 0

        if val and val > 0:
            income_breakdown.append({"label": label, "value": round(val, 2)})

    # MAGI thresholds table
    thresholds = outputs.get("thresholds", {})
    filing_status = outputs.get("filing_status", "single")
    magi = outputs.get("magi", 0)

    magi_table = [
        {
            "name": "IRA Deductibility Phaseout",
            "start": thresholds.get("ira_deductibility_phaseout_start"),
            "end": thresholds.get("ira_deductibility_phaseout_end"),
            "client_magi": magi,
            "status": "below" if magi < thresholds.get("ira_deductibility_phaseout_start", 0) else
                      "in_range" if magi < thresholds.get("ira_deductibility_phaseout_end", 0) else "above",
        },
        {
            "name": "Roth IRA Contribution Phaseout",
            "start": thresholds.get("roth_ira_phaseout_start"),
            "end": thresholds.get("roth_ira_phaseout_end"),
            "client_magi": magi,
            "status": "below" if magi < thresholds.get("roth_ira_phaseout_start", 0) else
                      "in_range" if magi < thresholds.get("roth_ira_phaseout_end", 0) else "above",
        },
        {
            "name": "NIIT Threshold",
            "start": thresholds.get("niit_threshold"),
            "end": None,
            "client_magi": magi,
            "status": "below" if thresholds.get("niit_distance", 0) > 0 else "above",
        },
        {
            "name": "SS 50% Taxation Threshold",
            "start": thresholds.get("ss_50pct_threshold"),
            "end": thresholds.get("ss_85pct_threshold"),
            "client_magi": magi,
            "note": "Based on provisional income",
        },
    ]

    # IRMAA breakpoints
    irmaa_breakpoints = get_irmaa_breakpoints(
        outputs.get("tax_year", 2024), filing_status
    )

    observations = generate_observations(outputs, scenario.inputs)

    advisor_name = _get_setting(db, "advisor_name", "Financial Advisor")
    firm_name = _get_setting(db, "firm_name", "")

    return {
        "household": {
            "name": household.name,
            "primary_name": household.primary_name,
            "filing_status": household.filing_status,
        },
        "scenario": {
            "id": scenario.id,
            "name": scenario.name,
            "tax_year": scenario.tax_year,
        },
        "summary": {
            "filing_status": outputs.get("filing_status"),
            "tax_year": outputs.get("tax_year"),
            "total_income": outputs.get("total_income"),
            "agi": outputs.get("agi"),
            "taxable_income": outputs.get("taxable_income"),
            "total_tax": outputs.get("total_tax"),
            "effective_rate": outputs.get("effective_rate"),
            "marginal_bracket_pct": outputs.get("marginal_bracket_pct"),
            "refund_or_owed": outputs.get("refund_or_owed"),
        },
        "income_breakdown": income_breakdown,
        "bracket_details": outputs.get("bracket_details", []),
        "magi_thresholds": magi_table,
        "irmaa_breakpoints": irmaa_breakpoints,
        "deductions": {
            "standard_deduction": outputs.get("standard_deduction"),
            "total_itemized": outputs.get("total_itemized_deduction"),
            "deduction_type": outputs.get("deduction_type"),
            "deduction_used": outputs.get("deduction_used"),
            "deduction_advantage": outputs.get("deduction_advantage"),
            "itemized_breakdown": outputs.get("itemized_breakdown"),
            "qbi_deduction": outputs.get("qbi_deduction"),
        },
        "capital_gains": {
            "st_gains_losses": outputs.get("st_gains_losses"),
            "lt_gains_losses": outputs.get("lt_gains_losses"),
            "net_capital": outputs.get("capital_gain_loss_net"),
            "carryforward": outputs.get("capital_loss_carryforward_remaining"),
            "ltcg_tax": outputs.get("ltcg_tax"),
            "ltcg_0pct_room": thresholds.get("ltcg_room_in_0pct"),
        },
        "irmaa": outputs.get("irmaa"),
        "observations": observations,
        "advisor_name": advisor_name,
        "firm_name": firm_name,
    }


@router.get("/explainer/tax/{scenario_id}")
def get_tax_explainer(scenario_id: int, db: Session = Depends(get_db)):
    """Generate line-by-line tax return explainer."""
    scenario = db.query(Scenario).filter(Scenario.id == scenario_id).first()
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")

    outputs = scenario.calculated_outputs or {}
    household = db.query(Household).filter(Household.id == scenario.household_id).first()

    lines = []

    # Build explainer sections
    if outputs.get("wages_salaries", 0) > 0:
        lines.append({
            "line": "Line 1a",
            "label": "Wages, Salaries, Tips",
            "amount": outputs["wages_salaries"],
            "explanation": f"This represents your total employment income reported on W-2 forms. Your wages of ${outputs['wages_salaries']:,.0f} are subject to federal income tax, Social Security tax (6.2%), and Medicare tax (1.45%).",
        })

    if outputs.get("interest_income_taxable", 0) > 0:
        lines.append({
            "line": "Line 2b",
            "label": "Taxable Interest",
            "amount": outputs["interest_income_taxable"],
            "explanation": f"Interest income of ${outputs['interest_income_taxable']:,.0f} from bank accounts, CDs, and bonds is included in your taxable income.",
        })

    if outputs.get("interest_income_exempt", 0) > 0:
        lines.append({
            "line": "Line 2a",
            "label": "Tax-Exempt Interest",
            "amount": outputs["interest_income_exempt"],
            "explanation": f"Tax-exempt interest of ${outputs['interest_income_exempt']:,.0f} (typically from municipal bonds) is not subject to federal income tax but may affect other calculations like Social Security taxation and IRMAA.",
        })

    if outputs.get("ordinary_dividends", 0) > 0:
        lines.append({
            "line": "Line 3b",
            "label": "Ordinary Dividends",
            "amount": outputs["ordinary_dividends"],
            "explanation": f"Total dividend income of ${outputs['ordinary_dividends']:,.0f}. Of this, ${outputs.get('qualified_dividends', 0):,.0f} qualifies for preferential long-term capital gains rates (0%/15%/20%) rather than ordinary income rates.",
        })

    if outputs.get("ira_distributions_taxable", 0) > 0:
        lines.append({
            "line": "Line 4b",
            "label": "Taxable IRA Distributions",
            "amount": outputs["ira_distributions_taxable"],
            "explanation": f"Taxable IRA distributions of ${outputs['ira_distributions_taxable']:,.0f}. Because your original contributions were pre-tax (traditional IRA), the withdrawal amount is subject to federal income tax.",
        })

    if outputs.get("pension_annuity_taxable", 0) > 0:
        lines.append({
            "line": "Line 5b",
            "label": "Taxable Pensions and Annuities",
            "amount": outputs["pension_annuity_taxable"],
            "explanation": f"Taxable pension/annuity income of ${outputs['pension_annuity_taxable']:,.0f}.",
        })

    if outputs.get("social_security_total", 0) > 0:
        lines.append({
            "line": "Line 6a/6b",
            "label": "Social Security Benefits",
            "amount": outputs["social_security_total"],
            "explanation": f"Total Social Security benefits: ${outputs['social_security_total']:,.0f}. Of this, ${outputs.get('social_security_taxable', 0):,.0f} ({outputs.get('social_security_taxation_pct', 0):.0f}%) is taxable based on your provisional income level.",
        })

    if outputs.get("capital_gain_loss_net", 0) != 0:
        val = outputs["capital_gain_loss_net"]
        lines.append({
            "line": "Line 7",
            "label": "Capital Gain or Loss",
            "amount": val,
            "explanation": f"Net capital {'gain' if val > 0 else 'loss'} of ${abs(val):,.0f}. {'Long-term gains are taxed at preferential rates.' if val > 0 else 'Capital losses are limited to $3,000 per year against ordinary income. Unused losses carry forward.'}",
        })

    if outputs.get("business_income", 0) != 0:
        lines.append({
            "line": "Schedule C",
            "label": "Business Income/Loss",
            "amount": outputs["business_income"],
            "explanation": f"Net business {'income' if outputs['business_income'] > 0 else 'loss'} of ${abs(outputs['business_income']):,.0f} from self-employment. This is subject to self-employment tax (15.3%) in addition to income tax.",
        })

    # AGI
    lines.append({
        "line": "Line 11",
        "label": "Adjusted Gross Income (AGI)",
        "amount": outputs.get("agi", 0),
        "explanation": f"Your AGI of ${outputs.get('agi', 0):,.0f} is your total income minus adjustments (such as the SE tax deduction). AGI is the key figure used to determine eligibility for many deductions, credits, and tax thresholds.",
    })

    # Deduction
    lines.append({
        "line": "Line 12",
        "label": f"{'Standard' if outputs.get('deduction_type') == 'standard' else 'Itemized'} Deduction",
        "amount": outputs.get("deduction_used", 0),
        "explanation": f"You {'took' if outputs.get('deduction_type') == 'standard' else 'itemized'} the {'standard' if outputs.get('deduction_type') == 'standard' else 'itemized'} deduction of ${outputs.get('deduction_used', 0):,.0f}. {'The standard deduction was more beneficial by ${}'.format('{:,.0f}'.format(outputs.get('deduction_advantage', 0))) + '.' if outputs.get('deduction_type') == 'standard' and outputs.get('deduction_advantage', 0) > 0 else ''}",
    })

    # Taxable income
    lines.append({
        "line": "Line 15",
        "label": "Taxable Income",
        "amount": outputs.get("taxable_income", 0),
        "explanation": f"Your taxable income of ${outputs.get('taxable_income', 0):,.0f} is what's actually subject to income tax after subtracting your deduction and any QBI deduction.",
    })

    # Total tax
    lines.append({
        "line": "Line 24",
        "label": "Total Tax",
        "amount": outputs.get("total_tax", 0),
        "explanation": f"Your total federal tax liability is ${outputs.get('total_tax', 0):,.0f}, which includes income tax, self-employment tax, NIIT, and any additional Medicare tax. Your effective tax rate is {outputs.get('effective_rate', 0):.1f}% and your marginal bracket is {outputs.get('marginal_bracket_pct', 0):.0f}%.",
    })

    return {
        "household_name": household.name,
        "tax_year": scenario.tax_year,
        "scenario_name": scenario.name,
        "lines": lines,
    }


@router.get("/explainer/roth/{scenario_id}")
def get_roth_explainer(scenario_id: int, db: Session = Depends(get_db)):
    """Generate Roth conversion explainer specific to client situation."""
    scenario = db.query(Scenario).filter(Scenario.id == scenario_id).first()
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")

    outputs = scenario.calculated_outputs or {}
    household = db.query(Household).filter(Household.id == scenario.household_id).first()

    marginal = outputs.get("marginal_bracket_pct", 0)
    agi = outputs.get("agi", 0)
    taxable = outputs.get("taxable_income", 0)

    return {
        "household_name": household.name,
        "tax_year": scenario.tax_year,
        "title": "Roth Conversion Analysis",
        "sections": [
            {
                "heading": "What Is a Roth Conversion?",
                "content": "A Roth conversion moves money from a pre-tax retirement account (Traditional IRA, 401(k)) to a Roth IRA. The converted amount is added to your taxable income in the year of conversion, but all future growth and qualified withdrawals from the Roth are tax-free.",
            },
            {
                "heading": "Your Current Tax Situation",
                "content": f"You are currently in the {marginal:.0f}% marginal tax bracket with AGI of ${agi:,.0f} and taxable income of ${taxable:,.0f}. {'This relatively low bracket makes it an attractive time to consider Roth conversions — you would pay tax at a lower rate now to avoid potentially higher rates in the future.' if marginal <= 24 else 'Your current bracket is relatively high. Roth conversions may still be beneficial if you expect to be in an even higher bracket in retirement or want to reduce future RMDs.'}",
            },
            {
                "heading": "Key Benefits",
                "content": "1. Tax-free growth and withdrawals in retirement\n2. No Required Minimum Distributions (RMDs) for Roth IRAs\n3. Tax diversification — having both pre-tax and Roth accounts gives flexibility\n4. Estate planning: Roth IRAs pass to beneficiaries tax-free\n5. May reduce future IRMAA Medicare surcharges by lowering RMDs",
            },
            {
                "heading": "Considerations",
                "content": "1. The conversion amount is taxable income — plan the amount carefully\n2. Converting too much could push you into a higher bracket, trigger NIIT, or increase IRMAA\n3. You need to have cash outside the IRA to pay the tax (don't use IRA funds to pay)\n4. The 5-year rule: converted amounts have a 5-year waiting period for penalty-free withdrawal if under 59½\n5. Consider converting over multiple years to stay within a target bracket",
            },
            {
                "heading": "IRMAA Impact",
                "content": f"IRMAA uses your MAGI from 2 years prior. Converting now will affect your Medicare premiums in 2 years. {'You are currently not subject to IRMAA surcharges.' if outputs.get('irmaa', {}).get('tier', 0) == 0 else f'You are currently at IRMAA Tier {outputs.get(\"irmaa\", {}).get(\"tier\", 0)}.'}",
            },
        ],
    }


@router.get("/explainer/qcd/{scenario_id}")
def get_qcd_explainer(scenario_id: int, db: Session = Depends(get_db)):
    """Generate QCD (Qualified Charitable Distribution) explainer."""
    scenario = db.query(Scenario).filter(Scenario.id == scenario_id).first()
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")

    outputs = scenario.calculated_outputs or {}
    household = db.query(Household).filter(Household.id == scenario.household_id).first()

    return {
        "household_name": household.name,
        "tax_year": scenario.tax_year,
        "title": "Qualified Charitable Distributions (QCD)",
        "sections": [
            {
                "heading": "What Is a QCD?",
                "content": "A Qualified Charitable Distribution is a direct transfer from your IRA to a qualified charity. The distribution is excluded from your taxable income, making it one of the most tax-efficient ways to give to charity.",
            },
            {
                "heading": "Eligibility",
                "content": "You must be age 70½ or older at the time of the distribution. The distribution must be made directly from the IRA custodian to the charity (not to you first). Only traditional IRAs and inherited IRAs qualify — Roth IRAs, SEP IRAs, and SIMPLE IRAs generally do not.",
            },
            {
                "heading": "Annual Limit",
                "content": "The annual QCD limit is $105,000 per person for 2024 (indexed for inflation). For married couples, each spouse can do up to $105,000 from their own IRA.",
            },
            {
                "heading": "Tax Benefit vs. Regular Charitable Donation",
                "content": f"With your current situation:\n- A regular charitable donation requires itemizing to get a deduction (your {'itemized' if outputs.get('deduction_type') == 'itemized' else 'standard'} deduction is ${outputs.get('deduction_used', 0):,.0f})\n- A QCD reduces your AGI directly, which can:\n  • Reduce Social Security taxation (currently {outputs.get('social_security_taxation_pct', 0):.0f}% taxable)\n  • Help avoid IRMAA surcharges\n  • Reduce NIIT exposure\n  • Keep you eligible for other income-tested benefits",
            },
            {
                "heading": "RMD Satisfaction",
                "content": "QCDs can count toward your Required Minimum Distribution. This means you can satisfy your RMD while excluding that income from taxation — a significant benefit.",
            },
        ],
    }


@router.get("/explainer/daf/{scenario_id}")
def get_daf_explainer(scenario_id: int, db: Session = Depends(get_db)):
    """Generate Donor Advised Fund explainer."""
    scenario = db.query(Scenario).filter(Scenario.id == scenario_id).first()
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")

    outputs = scenario.calculated_outputs or {}
    household = db.query(Household).filter(Household.id == scenario.household_id).first()

    std_ded = outputs.get("standard_deduction", 0)

    return {
        "household_name": household.name,
        "tax_year": scenario.tax_year,
        "title": "Donor Advised Funds (DAF)",
        "sections": [
            {
                "heading": "What Is a Donor Advised Fund?",
                "content": "A Donor Advised Fund is a charitable giving vehicle that allows you to make a tax-deductible contribution now, invest the funds for growth, and distribute grants to charities over time.",
            },
            {
                "heading": "The Bunching Strategy",
                "content": f"Your standard deduction is ${std_ded:,.0f}. If your annual charitable giving plus other itemized deductions don't exceed this amount, you lose the tax benefit of giving. The bunching strategy concentrates multiple years of giving into a single year via a DAF contribution, allowing you to itemize in that year and take the standard deduction in other years.",
            },
            {
                "heading": "Example",
                "content": f"If you normally give $10,000/year to charity:\n- Over 3 years with standard deduction: $0 charitable tax benefit (if other itemized < ${std_ded:,.0f})\n- Bunch 3 years into 1 via DAF ($30,000): Itemize in year 1, standard deduction in years 2-3\n- You still distribute $10,000/year from the DAF to your charities\n- The DAF contribution grows tax-free while awaiting distribution",
            },
            {
                "heading": "Appreciated Securities",
                "content": "Contributing appreciated stocks or funds to a DAF provides a double tax benefit:\n1. You get a deduction for the full fair market value\n2. You avoid paying capital gains tax on the appreciation\nThis is especially valuable for clients with large unrealized gains.",
            },
            {
                "heading": "Key Rules",
                "content": "- Contributions are irrevocable (you can't get the money back)\n- You can recommend grants to qualified 501(c)(3) charities\n- Deduction limited to 60% of AGI for cash, 30% for appreciated assets\n- No minimum distribution requirement (unlike private foundations)\n- Investment growth is tax-free inside the DAF",
            },
        ],
    }
