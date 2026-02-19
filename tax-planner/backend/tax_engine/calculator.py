"""
Main tax calculation engine.

Accepts a full scenario input dict and returns a complete calculated output dict.
Supports tax years 2023, 2024, 2025.
"""

from typing import Dict, Any

from .brackets import (
    calculate_ordinary_tax,
    calculate_ltcg_tax,
    get_marginal_bracket,
    get_standard_deduction,
    calculate_qbi_deduction,
    ORDINARY_BRACKETS,
    LTCG_BRACKETS,
)
from .social_security import calculate_ss_taxable, calculate_ss_taxation_pct
from .niit import calculate_niit, get_niit_threshold, calculate_distance_to_niit
from .irmaa import get_irmaa_tier, distance_to_next_irmaa_tier, get_irmaa_breakpoints
from .amt import calculate_amt
from .credits import calculate_total_credits
from .state_taxes import calculate_state_tax


def _safe_float(val: Any, default: float = 0.0) -> float:
    """Safely convert a value to float."""
    if val is None:
        return default
    try:
        return float(val)
    except (TypeError, ValueError):
        return default


def calculate_se_tax(net_se_income: float) -> Dict[str, float]:
    """
    Calculate self-employment tax.

    SE tax = 15.3% on 92.35% of net SE income.
    (12.4% Social Security on first $168,600 for 2024 + 2.9% Medicare on all)
    """
    if net_se_income <= 0:
        return {
            "se_taxable_income": 0,
            "se_tax_amount": 0,
            "se_deduction": 0,
        }

    # 92.35% of net SE income
    se_taxable = net_se_income * 0.9235

    # Social Security portion (12.4%) - capped at wage base
    ss_wage_base = 168600  # 2024
    ss_tax = min(se_taxable, ss_wage_base) * 0.124

    # Medicare portion (2.9%) - no cap
    medicare_tax = se_taxable * 0.029

    # Additional Medicare Tax (0.9%) on SE income over $200k (single) / $250k (MFJ)
    additional_medicare = 0
    if se_taxable > 200000:
        additional_medicare = (se_taxable - 200000) * 0.009

    se_tax = ss_tax + medicare_tax + additional_medicare

    # SE deduction = 50% of SE tax (deducted from gross income to get AGI)
    se_deduction = se_tax * 0.50

    return {
        "se_taxable_income": round(se_taxable, 2),
        "se_tax_amount": round(se_tax, 2),
        "se_deduction": round(se_deduction, 2),
    }


def calculate_tax(inputs: Dict[str, Any]) -> Dict[str, Any]:
    """
    Master tax calculation function.

    Accepts a dict of all income/deduction inputs and returns
    a complete dict of calculated tax outputs.

    Input keys (all optional, default to 0):
        tax_year: int (2023-2025, default 2024)
        filing_status: str (single, mfj, mfs, hoh, qw)

        # Income
        wages_salaries: float
        interest_income_taxable: float
        interest_income_exempt: float
        qualified_dividends: float
        ordinary_dividends: float
        ira_distributions_total: float
        ira_distributions_taxable: float
        pension_annuity_total: float
        pension_annuity_taxable: float
        social_security_total: float
        social_security_taxable: float (if provided, overrides calc)
        capital_gain_loss: float (net, can be negative)
        st_gains_losses: float
        lt_gains_losses: float
        other_income: float
        business_income: float (net from Schedule C)
        rental_income: float (net from Schedule E)
        k1_income: float (net from K-1s)

        # Adjustments
        se_health_insurance_deduction: float
        ira_deduction: float
        student_loan_interest: float
        other_adjustments: float

        # Deductions
        use_itemized: bool
        medical_expenses: float
        state_local_taxes: float (SALT - capped at $10,000)
        mortgage_interest: float
        charitable_contributions: float
        other_itemized: float

        # QBI
        qbi_eligible_income: float
        w2_wages_for_qbi: float
        ubia_for_qbi: float

        # Credits
        num_qualifying_children: int
        dependent_care_expenses: float
        num_care_qualifying: int
        retirement_contributions_for_credit: float
        education_credits: float
        other_credits: float

        # Other taxes
        additional_medicare_tax_wages: float (for W-2 wages over threshold)

        # Payments
        federal_withholding: float
        estimated_tax_payments: float
        other_payments: float

        # Personal
        age_primary: int
        age_secondary: int (for MFJ)
        blind_primary: bool
        blind_secondary: bool

        # State
        state: str (two-letter code)
        state_adjustment: float

        # AMT
        iso_spread: float
        other_amt_adjustments: float
        tax_exempt_interest_private_activity: float

        # Carry forwards
        capital_loss_carryforward: float (from prior year, positive number)
        passive_activity_loss_carryforward: float
    """
    # Extract inputs with defaults
    tax_year = int(inputs.get("tax_year", 2024))
    if tax_year not in (2023, 2024, 2025):
        tax_year = 2024

    filing_status = inputs.get("filing_status", "single").lower()
    if filing_status not in ("single", "mfj", "mfs", "hoh", "qw"):
        filing_status = "single"

    # ---- INCOME ----
    wages = _safe_float(inputs.get("wages_salaries"))
    interest_taxable = _safe_float(inputs.get("interest_income_taxable"))
    interest_exempt = _safe_float(inputs.get("interest_income_exempt"))
    qualified_divs = _safe_float(inputs.get("qualified_dividends"))
    ordinary_divs = _safe_float(inputs.get("ordinary_dividends"))
    # Ordinary dividends includes qualified dividends
    non_qualified_divs = max(ordinary_divs - qualified_divs, 0)

    ira_total = _safe_float(inputs.get("ira_distributions_total"))
    ira_taxable = _safe_float(inputs.get("ira_distributions_taxable"))
    pension_total = _safe_float(inputs.get("pension_annuity_total"))
    pension_taxable = _safe_float(inputs.get("pension_annuity_taxable"))

    ss_total = _safe_float(inputs.get("social_security_total"))

    st_gains = _safe_float(inputs.get("st_gains_losses"))
    lt_gains = _safe_float(inputs.get("lt_gains_losses"))
    capital_gain_loss = _safe_float(inputs.get("capital_gain_loss"))
    # If component gains provided, use them; otherwise use net
    if st_gains != 0 or lt_gains != 0:
        net_capital = st_gains + lt_gains
    else:
        net_capital = capital_gain_loss

    # Apply capital loss carryforward
    capital_loss_cf = _safe_float(inputs.get("capital_loss_carryforward"))
    if capital_loss_cf > 0 and net_capital > 0:
        net_capital = net_capital  # Carryforward already factored in by user
    elif capital_loss_cf > 0:
        # net_capital is already negative or zero, carryforward makes it more negative
        pass

    # Capital loss limitation: max $3,000 deduction ($1,500 MFS) per year
    capital_loss_limit = 1500 if filing_status == "mfs" else 3000
    if net_capital < -capital_loss_limit:
        remaining_loss_cf = abs(net_capital) - capital_loss_limit
        capital_applied = -capital_loss_limit
    else:
        remaining_loss_cf = 0
        capital_applied = net_capital

    other_income = _safe_float(inputs.get("other_income"))
    business_income = _safe_float(inputs.get("business_income"))
    rental_income = _safe_float(inputs.get("rental_income"))
    k1_income = _safe_float(inputs.get("k1_income"))

    # ---- SELF-EMPLOYMENT TAX ----
    net_se_income = business_income  # Simplified: Schedule C net profit
    se_result = calculate_se_tax(max(net_se_income, 0))

    # ---- SOCIAL SECURITY TAXATION ----
    # Calculate total income before SS to determine provisional income
    income_before_ss = (
        wages + interest_taxable + ordinary_divs + ira_taxable +
        pension_taxable + capital_applied + other_income +
        business_income + rental_income + k1_income
    )

    # Check if user provided pre-calculated SS taxable
    ss_taxable_override = inputs.get("social_security_taxable")
    if ss_taxable_override is not None and _safe_float(ss_taxable_override) > 0:
        ss_taxable = _safe_float(ss_taxable_override)
    else:
        ss_taxable = calculate_ss_taxable(
            ss_total, income_before_ss, interest_exempt, filing_status
        )

    ss_taxation_pct = 0
    if ss_total > 0:
        ss_taxation_pct = round((ss_taxable / ss_total) * 100, 1)

    # ---- TOTAL INCOME ----
    total_income = (
        wages + interest_taxable + ordinary_divs +
        ira_taxable + pension_taxable + ss_taxable +
        capital_applied + other_income +
        business_income + rental_income + k1_income
    )

    # ---- ADJUSTMENTS TO INCOME ----
    se_deduction = se_result["se_deduction"]
    se_health = _safe_float(inputs.get("se_health_insurance_deduction"))
    ira_deduction = _safe_float(inputs.get("ira_deduction"))
    student_loan = _safe_float(inputs.get("student_loan_interest"))
    other_adj = _safe_float(inputs.get("other_adjustments"))

    total_adjustments = se_deduction + se_health + ira_deduction + student_loan + other_adj

    # ---- AGI ----
    agi = total_income - total_adjustments

    # ---- DEDUCTIONS ----
    age_primary = int(inputs.get("age_primary", 0))
    age_secondary = int(inputs.get("age_secondary", 0))
    age_65_primary = age_primary >= 65
    age_65_secondary = age_secondary >= 65
    blind_primary = bool(inputs.get("blind_primary", False))
    blind_secondary = bool(inputs.get("blind_secondary", False))

    standard_deduction = get_standard_deduction(
        tax_year, filing_status,
        age_65_primary, age_65_secondary,
        blind_primary, blind_secondary,
    )

    # Itemized deductions
    medical = _safe_float(inputs.get("medical_expenses"))
    # Medical: only amount exceeding 7.5% of AGI
    medical_deductible = max(medical - (agi * 0.075), 0)

    salt = _safe_float(inputs.get("state_local_taxes"))
    salt_capped = min(salt, 10000)  # SALT cap
    if filing_status == "mfs":
        salt_capped = min(salt, 5000)

    mortgage = _safe_float(inputs.get("mortgage_interest"))
    charitable = _safe_float(inputs.get("charitable_contributions"))
    other_itemized = _safe_float(inputs.get("other_itemized"))

    total_itemized = medical_deductible + salt_capped + mortgage + charitable + other_itemized

    # Determine which deduction to use
    use_itemized = inputs.get("use_itemized")
    if use_itemized is None:
        # Auto-select whichever is larger
        use_itemized = total_itemized > standard_deduction
    else:
        use_itemized = bool(use_itemized)

    deduction_used = total_itemized if use_itemized else standard_deduction
    deduction_type = "itemized" if use_itemized else "standard"

    # ---- QBI DEDUCTION ----
    qbi_eligible = _safe_float(inputs.get("qbi_eligible_income"))
    if qbi_eligible == 0 and business_income > 0:
        qbi_eligible = business_income  # Default: business income is QBI-eligible

    taxable_before_qbi = agi - deduction_used
    w2_wages_qbi = _safe_float(inputs.get("w2_wages_for_qbi"))
    ubia_qbi = _safe_float(inputs.get("ubia_for_qbi"))

    qbi_deduction = calculate_qbi_deduction(
        qbi_eligible, taxable_before_qbi, tax_year, filing_status,
        w2_wages_qbi, ubia_qbi,
    )

    # ---- TAXABLE INCOME ----
    taxable_income = max(agi - deduction_used - qbi_deduction, 0)

    # ---- INCOME TAX CALCULATION ----
    # Separate ordinary income from preferential rate income
    # LTCG + qualified dividends get preferential rates
    preferential_income = 0
    if lt_gains > 0:
        preferential_income += lt_gains
    elif capital_applied > 0 and lt_gains == 0 and st_gains == 0:
        # If only net capital gain provided and positive, treat as LTCG
        preferential_income += capital_applied
    preferential_income += qualified_divs

    ordinary_taxable = max(taxable_income - preferential_income, 0)

    # Tax on ordinary income
    ordinary_tax = calculate_ordinary_tax(ordinary_taxable, tax_year, filing_status)

    # Tax on LTCG/qualified dividends
    ltcg_tax = calculate_ltcg_tax(ordinary_taxable, preferential_income, tax_year, filing_status)

    # Total income tax before credits
    income_tax = ordinary_tax + ltcg_tax

    # ---- AMT ----
    amt_result = calculate_amt(
        taxable_income=taxable_income,
        filing_status=filing_status,
        tax_year=tax_year,
        regular_tax=income_tax,
        state_local_tax_deduction=salt_capped if use_itemized else 0,
        iso_spread=_safe_float(inputs.get("iso_spread")),
        other_amt_adjustments=_safe_float(inputs.get("other_amt_adjustments")),
        tax_exempt_interest_private_activity=_safe_float(
            inputs.get("tax_exempt_interest_private_activity")
        ),
    )

    # Tax after AMT
    tax_after_amt = income_tax + amt_result["amt"]

    # ---- CREDITS ----
    credits_result = calculate_total_credits(inputs, agi, filing_status, tax_year)
    total_credits = credits_result["total_credits"]

    # Credits reduce tax but not below zero (non-refundable)
    tax_after_credits = max(tax_after_amt - total_credits, 0)

    # ---- OTHER TAXES ----
    se_tax = se_result["se_tax_amount"]

    # Net Investment Income Tax (NIIT)
    # NII = interest + dividends + capital gains + rental + other passive
    nii = (
        interest_taxable + ordinary_divs +
        max(capital_applied, 0) + max(rental_income, 0) +
        max(k1_income, 0)  # Simplified: treat K-1 income as investment
    )
    niit = calculate_niit(agi, nii, filing_status)

    # Additional Medicare Tax on wages over $200k/$250k
    add_medicare_wages = _safe_float(inputs.get("additional_medicare_tax_wages", wages))
    additional_medicare = 0
    medicare_threshold = 250000 if filing_status == "mfj" else 200000
    if add_medicare_wages > medicare_threshold:
        additional_medicare = round((add_medicare_wages - medicare_threshold) * 0.009, 2)

    # ---- TOTAL TAX ----
    total_other_taxes = se_tax + niit + additional_medicare
    total_tax = round(tax_after_credits + total_other_taxes, 2)

    # ---- PAYMENTS AND REFUND ----
    withholding = _safe_float(inputs.get("federal_withholding"))
    estimated = _safe_float(inputs.get("estimated_tax_payments"))
    other_payments = _safe_float(inputs.get("other_payments"))
    total_payments = withholding + estimated + other_payments

    refund_or_owed = round(total_payments - total_tax, 2)

    # ---- EFFECTIVE AND MARGINAL RATES ----
    effective_rate = 0
    if total_income > 0:
        effective_rate = round((total_tax / total_income) * 100, 1)

    marginal_bracket = get_marginal_bracket(taxable_income, tax_year, filing_status)

    # Effective tax on next $1,000
    next_1000_inputs = inputs.copy()
    next_1000_inputs["wages_salaries"] = wages + 1000
    # Quick marginal calculation
    taxable_plus = taxable_income + 1000
    tax_on_next = calculate_ordinary_tax(taxable_plus, tax_year, filing_status) - ordinary_tax
    # Add potential NIIT on next $1000
    niit_next = calculate_niit(agi + 1000, nii + 1000, filing_status)
    effective_next_1000 = round(tax_on_next + (niit_next - niit), 2)

    # ---- MAGI CALCULATIONS ----
    # Various MAGI definitions (simplified - mostly equal to AGI)
    magi_general = agi  # Most MAGI = AGI + certain deductions added back
    magi_roth = agi  # Roth IRA MAGI
    magi_ira = agi  # IRA deductibility MAGI
    magi_aca = agi + interest_exempt  # ACA MAGI includes tax-exempt interest
    magi_niit = agi
    magi_irmaa = agi + interest_exempt  # IRMAA MAGI includes tax-exempt interest

    # ---- IRMAA ----
    irmaa = get_irmaa_tier(magi_irmaa, tax_year, filing_status)
    irmaa_distance = distance_to_next_irmaa_tier(magi_irmaa, tax_year, filing_status)

    # ---- MAGI THRESHOLDS ----
    niit_threshold = get_niit_threshold(filing_status)
    niit_distance = calculate_distance_to_niit(agi, filing_status)

    # Roth IRA phaseout ranges
    roth_phaseout = {
        2023: {"single": (138000, 153000), "mfj": (218000, 228000)},
        2024: {"single": (146000, 161000), "mfj": (230000, 240000)},
        2025: {"single": (150000, 165000), "mfj": (236000, 246000)},
    }
    rp = roth_phaseout.get(tax_year, roth_phaseout[2025])
    roth_range = rp.get(filing_status, rp.get("single", (150000, 165000)))

    # IRA deductibility phaseout (if covered by employer plan)
    ira_phaseout = {
        2023: {"single": (73000, 83000), "mfj": (116000, 136000)},
        2024: {"single": (77000, 87000), "mfj": (123000, 143000)},
        2025: {"single": (79000, 89000), "mfj": (126000, 146000)},
    }
    ip = ira_phaseout.get(tax_year, ira_phaseout[2025])
    ira_range = ip.get(filing_status, ip.get("single", (79000, 89000)))

    # ---- STATE TAX ----
    state = inputs.get("state", "")
    state_result = None
    if state:
        state_adj = _safe_float(inputs.get("state_adjustment"))
        state_result = calculate_state_tax(
            taxable_income, filing_status, state, state_adj, ss_taxable
        )

    # ---- LTCG BRACKET INFO ----
    ltcg_brackets = LTCG_BRACKETS[tax_year][filing_status]
    ltcg_0_ceiling = ltcg_brackets[0][0]
    ltcg_room_in_0pct = max(ltcg_0_ceiling - taxable_income, 0)

    # ---- BUILD OUTPUT ----
    output = {
        "tax_year": tax_year,
        "filing_status": filing_status,

        # Income
        "wages_salaries": round(wages, 2),
        "interest_income_taxable": round(interest_taxable, 2),
        "interest_income_exempt": round(interest_exempt, 2),
        "qualified_dividends": round(qualified_divs, 2),
        "ordinary_dividends": round(ordinary_divs, 2),
        "ira_distributions_total": round(ira_total, 2),
        "ira_distributions_taxable": round(ira_taxable, 2),
        "pension_annuity_total": round(pension_total, 2),
        "pension_annuity_taxable": round(pension_taxable, 2),
        "social_security_total": round(ss_total, 2),
        "social_security_taxable": round(ss_taxable, 2),
        "social_security_taxation_pct": ss_taxation_pct,
        "capital_gain_loss_net": round(capital_applied, 2),
        "st_gains_losses": round(st_gains, 2),
        "lt_gains_losses": round(lt_gains, 2),
        "capital_loss_carryforward_remaining": round(remaining_loss_cf, 2),
        "other_income": round(other_income, 2),
        "business_income": round(business_income, 2),
        "rental_income": round(rental_income, 2),
        "k1_income": round(k1_income, 2),
        "total_income": round(total_income, 2),

        # Adjustments
        "se_deduction": round(se_deduction, 2),
        "total_adjustments": round(total_adjustments, 2),

        # AGI
        "agi": round(agi, 2),

        # Deductions
        "standard_deduction": round(standard_deduction, 2),
        "total_itemized_deduction": round(total_itemized, 2),
        "itemized_breakdown": {
            "medical_deductible": round(medical_deductible, 2),
            "salt_capped": round(salt_capped, 2),
            "mortgage_interest": round(mortgage, 2),
            "charitable": round(charitable, 2),
            "other": round(other_itemized, 2),
        },
        "deduction_used": round(deduction_used, 2),
        "deduction_type": deduction_type,
        "deduction_advantage": round(abs(total_itemized - standard_deduction), 2),
        "qbi_deduction": round(qbi_deduction, 2),
        "qbi_eligible_income": round(qbi_eligible, 2),

        # Taxable income
        "taxable_income": round(taxable_income, 2),
        "ordinary_taxable_income": round(ordinary_taxable, 2),
        "preferential_income": round(preferential_income, 2),

        # Tax calculation
        "ordinary_tax": round(ordinary_tax, 2),
        "ltcg_tax": round(ltcg_tax, 2),
        "income_tax": round(income_tax, 2),

        # AMT
        "amt": amt_result,

        # Credits
        "credits": credits_result,
        "total_credits": round(total_credits, 2),
        "tax_after_credits": round(tax_after_credits, 2),

        # Other taxes
        "se_tax": round(se_tax, 2),
        "se_details": se_result,
        "niit": round(niit, 2),
        "net_investment_income": round(nii, 2),
        "additional_medicare_tax": round(additional_medicare, 2),
        "total_other_taxes": round(total_other_taxes, 2),

        # Total tax
        "total_tax": total_tax,

        # Payments
        "federal_withholding": round(withholding, 2),
        "estimated_tax_payments": round(estimated, 2),
        "total_payments": round(total_payments, 2),
        "refund_or_owed": refund_or_owed,

        # Rates
        "effective_rate": effective_rate,
        "marginal_bracket": marginal_bracket,
        "marginal_bracket_pct": round(marginal_bracket * 100, 1),
        "effective_tax_on_next_1000": effective_next_1000,

        # MAGI thresholds
        "magi": round(magi_general, 2),
        "magi_roth": round(magi_roth, 2),
        "magi_ira": round(magi_ira, 2),
        "magi_aca": round(magi_aca, 2),
        "magi_niit": round(magi_niit, 2),
        "magi_irmaa": round(magi_irmaa, 2),

        "thresholds": {
            "niit_threshold": niit_threshold,
            "niit_distance": round(niit_distance, 2),
            "roth_ira_phaseout_start": roth_range[0],
            "roth_ira_phaseout_end": roth_range[1],
            "ira_deductibility_phaseout_start": ira_range[0],
            "ira_deductibility_phaseout_end": ira_range[1],
            "ss_50pct_threshold": 25000 if filing_status != "mfj" else 32000,
            "ss_85pct_threshold": 34000 if filing_status != "mfj" else 44000,
            "ltcg_0pct_ceiling": ltcg_0_ceiling,
            "ltcg_room_in_0pct": round(ltcg_room_in_0pct, 2),
        },

        # IRMAA
        "irmaa": irmaa,
        "irmaa_distance_to_next_tier": irmaa_distance,

        # State tax
        "state_tax": state_result,

        # Bracket details for visualization
        "bracket_details": _get_bracket_details(
            ordinary_taxable, preferential_income, tax_year, filing_status
        ),
    }

    return output


def _get_bracket_details(
    ordinary_taxable: float,
    preferential_income: float,
    tax_year: int,
    filing_status: str,
) -> list:
    """Generate bracket fill details for visualization."""
    brackets = ORDINARY_BRACKETS[tax_year][filing_status]
    details = []
    prev = 0.0
    remaining_ordinary = max(ordinary_taxable, 0)
    remaining_pref = max(preferential_income, 0)

    for upper, rate in brackets:
        bracket_size = upper - prev if upper != float("inf") else None
        ordinary_in_bracket = 0
        pref_in_bracket = 0

        if remaining_ordinary > 0 and bracket_size is not None:
            ordinary_in_bracket = min(remaining_ordinary, upper - prev)
            remaining_ordinary -= ordinary_in_bracket
        elif remaining_ordinary > 0:
            ordinary_in_bracket = remaining_ordinary
            remaining_ordinary = 0

        details.append({
            "bracket_bottom": prev,
            "bracket_top": upper if upper != float("inf") else None,
            "rate": rate,
            "rate_pct": round(rate * 100, 1),
            "ordinary_income_in_bracket": round(ordinary_in_bracket, 2),
            "bracket_size": bracket_size,
            "fill_pct": round(
                (ordinary_in_bracket / bracket_size * 100) if bracket_size else 0, 1
            ),
        })
        prev = upper

    return details


def calculate_range(
    base_inputs: Dict[str, Any],
    income_type: str,
    start_amount: float,
    end_amount: float,
    step: float = 1000,
) -> list:
    """
    Calculate effective marginal rate across a range of income values.

    Used for the Range Calc visualization tool.
    Returns list of data points for charting.
    """
    points = []
    prev_tax = None

    amount = start_amount
    while amount <= end_amount:
        test_inputs = base_inputs.copy()
        current_val = _safe_float(test_inputs.get(income_type, 0))
        test_inputs[income_type] = current_val + amount

        result = calculate_tax(test_inputs)
        total_tax = result["total_tax"]

        marginal_rate = 0
        if prev_tax is not None and step > 0:
            marginal_rate = round(((total_tax - prev_tax) / step) * 100, 2)

        points.append({
            "additional_income": round(amount, 2),
            "total_income": result["total_income"],
            "agi": result["agi"],
            "taxable_income": result["taxable_income"],
            "total_tax": total_tax,
            "effective_rate": result["effective_rate"],
            "marginal_rate": marginal_rate,
            "marginal_bracket": result["marginal_bracket_pct"],
            "niit": result["niit"],
            "irmaa_tier": result["irmaa"]["tier"],
            "irmaa_surcharge": result["irmaa"]["annual_total_surcharge"],
            "se_tax": result["se_tax"],
            "ss_taxable_pct": result["social_security_taxation_pct"],
        })

        prev_tax = total_tax
        amount += step

    return points


def find_rate_spike(
    base_inputs: Dict[str, Any],
    income_type: str,
    max_additional: float = 500000,
    step: float = 500,
) -> dict:
    """
    Find the point where effective marginal rate spikes significantly.

    Used for the "Find Tax-Efficient Income Limit" tool.
    Detects bracket changes, NIIT onset, IRMAA tier crossings, etc.
    """
    prev_result = calculate_tax(base_inputs)
    prev_tax = prev_result["total_tax"]
    prev_marginal = prev_result["marginal_bracket"]
    prev_irmaa = prev_result["irmaa"]["tier"]
    prev_niit = prev_result["niit"]

    spikes = []
    amount = step

    while amount <= max_additional:
        test_inputs = base_inputs.copy()
        current_val = _safe_float(test_inputs.get(income_type, 0))
        test_inputs[income_type] = current_val + amount

        result = calculate_tax(test_inputs)
        total_tax = result["total_tax"]
        marginal_rate = ((total_tax - prev_tax) / step) * 100

        # Detect spikes
        spike_reasons = []

        if result["marginal_bracket"] > prev_marginal:
            spike_reasons.append(
                f"Bracket change: {prev_marginal*100:.0f}% → {result['marginal_bracket']*100:.0f}%"
            )

        if result["niit"] > 0 and prev_niit == 0:
            spike_reasons.append("NIIT onset (3.8%)")

        if result["irmaa"]["tier"] > prev_irmaa:
            spike_reasons.append(
                f"IRMAA tier change: {prev_irmaa} → {result['irmaa']['tier']}"
            )

        if spike_reasons:
            spikes.append({
                "additional_income": round(amount, 2),
                "marginal_rate_before": round(
                    ((prev_tax - calculate_tax(
                        {**base_inputs, income_type: current_val + amount - 2*step}
                    )["total_tax"]) / step) * 100 if amount > step else 0, 2
                ),
                "marginal_rate_after": round(marginal_rate, 2),
                "reasons": spike_reasons,
                "total_tax_at_spike": total_tax,
                "total_income_at_spike": result["total_income"],
            })

        prev_tax = total_tax
        prev_marginal = result["marginal_bracket"]
        prev_irmaa = result["irmaa"]["tier"]
        prev_niit = result["niit"]
        amount += step

    # Return the first (most relevant) spike
    safe_amount = spikes[0]["additional_income"] - step if spikes else max_additional

    return {
        "safe_additional_income": round(safe_amount, 2),
        "income_type": income_type,
        "spikes": spikes[:5],  # Top 5 spikes
        "message": (
            f"You can add ${safe_amount:,.0f} of {income_type} before "
            f"hitting the next rate spike"
            if spikes else
            f"No significant rate spikes found up to ${max_additional:,.0f} additional income"
        ),
    }
