"""Tests for the tax calculation engine."""

import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from tax_engine.calculator import calculate_tax, calculate_range, find_rate_spike
from tax_engine.brackets import (
    calculate_ordinary_tax,
    calculate_ltcg_tax,
    get_marginal_bracket,
    get_standard_deduction,
    calculate_qbi_deduction,
)
from tax_engine.social_security import calculate_ss_taxable
from tax_engine.niit import calculate_niit
from tax_engine.irmaa import get_irmaa_tier
from tax_engine.amt import calculate_amt
from tax_engine.credits import calculate_child_tax_credit
from tax_engine.state_taxes import calculate_state_tax


class TestOrdinaryTax:
    """Test ordinary income tax bracket calculations."""

    def test_single_filer_100k_wages_2024(self):
        """Single filer with $100k wages, 2024."""
        # $100k wages - $14,600 standard deduction = $85,400 taxable
        taxable = 100000 - 14600
        tax = calculate_ordinary_tax(taxable, 2024, "single")
        # 10% on first $11,600 = $1,160
        # 12% on $11,601-$47,150 = $4,266
        # 22% on $47,151-$85,400 = $8,415
        expected = 1160 + (47150 - 11600) * 0.12 + (85400 - 47150) * 0.22
        assert abs(tax - expected) < 1.0

    def test_mfj_200k_wages_2024(self):
        """MFJ with $200k wages, 2024."""
        taxable = 200000 - 29200
        tax = calculate_ordinary_tax(taxable, 2024, "mfj")
        # 10% on $23,200 = $2,320
        # 12% on $23,201-$94,300 = $8,532
        # 22% on $94,301-$170,800 = $16,830
        expected = 23200 * 0.10 + (94300 - 23200) * 0.12 + (170800 - 94300) * 0.22
        assert abs(tax - expected) < 1.0

    def test_zero_income(self):
        tax = calculate_ordinary_tax(0, 2024, "single")
        assert tax == 0.0

    def test_negative_income(self):
        tax = calculate_ordinary_tax(-5000, 2024, "single")
        assert tax == 0.0

    def test_high_income_single_2024(self):
        """Single filer with $1M taxable income."""
        tax = calculate_ordinary_tax(1000000, 2024, "single")
        assert tax > 300000  # Should be significant

    def test_hoh_brackets_2024(self):
        """Head of Household, 2024."""
        taxable = 50000
        tax = calculate_ordinary_tax(taxable, 2024, "hoh")
        expected = 16550 * 0.10 + (50000 - 16550) * 0.12
        assert abs(tax - expected) < 1.0


class TestLTCGTax:
    """Test long-term capital gains tax."""

    def test_0pct_bracket_single_2024(self):
        """LTCG within 0% bracket."""
        # Single, $30k ordinary + $10k LTCG = $40k total, under $47,025
        tax = calculate_ltcg_tax(30000, 10000, 2024, "single")
        assert tax == 0.0

    def test_15pct_bracket_single_2024(self):
        """LTCG in 15% bracket."""
        # Single, $50k ordinary + $50k LTCG
        tax = calculate_ltcg_tax(50000, 50000, 2024, "single")
        # 0% up to $47,025 => already past with ordinary
        # All LTCG at 15%
        assert abs(tax - 50000 * 0.15) < 1.0

    def test_straddle_0_15_bracket(self):
        """LTCG straddles the 0%/15% boundary."""
        # Single, $40k ordinary + $20k LTCG
        tax = calculate_ltcg_tax(40000, 20000, 2024, "single")
        # 0% on $47,025 - $40,000 = $7,025
        # 15% on remaining $12,975
        expected = 0 + 12975 * 0.15
        assert abs(tax - expected) < 1.0


class TestStandardDeduction:
    def test_single_2024(self):
        assert get_standard_deduction(2024, "single") == 14600

    def test_mfj_2024(self):
        assert get_standard_deduction(2024, "mfj") == 29200

    def test_single_65_plus_2024(self):
        sd = get_standard_deduction(2024, "single", age_65_primary=True)
        assert sd == 14600 + 1950

    def test_mfj_both_65_2024(self):
        sd = get_standard_deduction(2024, "mfj", age_65_primary=True, age_65_secondary=True)
        assert sd == 29200 + 1550 * 2


class TestMarginalBracket:
    def test_single_22pct(self):
        rate = get_marginal_bracket(60000, 2024, "single")
        assert rate == 0.22

    def test_single_12pct(self):
        rate = get_marginal_bracket(20000, 2024, "single")
        assert rate == 0.12

    def test_mfj_24pct(self):
        rate = get_marginal_bracket(250000, 2024, "mfj")
        assert rate == 0.24


class TestSocialSecurity:
    def test_no_ss(self):
        result = calculate_ss_taxable(0, 50000, 0, "single")
        assert result == 0.0

    def test_below_threshold_single(self):
        """Single with low income — SS not taxable."""
        result = calculate_ss_taxable(20000, 10000, 0, "single")
        # Provisional = $10,000 + $10,000 (50% SS) = $20,000 < $25,000
        assert result == 0.0

    def test_50pct_tier_single(self):
        """Single in the 50% tier."""
        # Provisional = $20,000 + $10,000 = $30,000
        result = calculate_ss_taxable(20000, 20000, 0, "single")
        # Excess over $25k = $5,000, 50% = $2,500
        assert abs(result - 2500) < 1.0

    def test_85pct_tier_single(self):
        """Single with high income — up to 85% taxable."""
        result = calculate_ss_taxable(30000, 80000, 0, "single")
        # Provisional = $80,000 + $15,000 = $95,000
        # 50% tier: ($34,000 - $25,000) * 0.50 = $4,500
        # 85% tier: ($95,000 - $34,000) * 0.85 = $51,850
        # Total = $56,350, capped at 85% of $30,000 = $25,500
        assert abs(result - 25500) < 1.0

    def test_mfj_thresholds(self):
        """MFJ with SS below threshold."""
        result = calculate_ss_taxable(24000, 15000, 0, "mfj")
        # Provisional = $15,000 + $12,000 = $27,000 < $32,000
        assert result == 0.0


class TestNIIT:
    def test_below_threshold(self):
        niit = calculate_niit(180000, 50000, "single")
        assert niit == 0.0

    def test_above_threshold_single(self):
        """Single with $250k MAGI and $80k NII."""
        niit = calculate_niit(250000, 80000, "single")
        # Excess = $50k, NII = $80k, lesser = $50k
        expected = 50000 * 0.038
        assert abs(niit - expected) < 1.0

    def test_mfj_threshold(self):
        niit = calculate_niit(240000, 50000, "mfj")
        assert niit == 0.0

    def test_nii_less_than_excess(self):
        """NII is less than MAGI excess."""
        niit = calculate_niit(300000, 20000, "single")
        # Excess = $100k, NII = $20k, lesser = $20k
        expected = 20000 * 0.038
        assert abs(niit - expected) < 1.0


class TestIRMAA:
    def test_tier_0_single(self):
        result = get_irmaa_tier(90000, 2025, "single")
        assert result["tier"] == 0
        assert result["annual_total_surcharge"] == 0

    def test_tier_1_single(self):
        result = get_irmaa_tier(120000, 2025, "single")
        assert result["tier"] == 1
        assert result["annual_total_surcharge"] > 0

    def test_tier_0_mfj(self):
        result = get_irmaa_tier(200000, 2025, "mfj")
        assert result["tier"] == 0


class TestAMT:
    def test_no_amt(self):
        result = calculate_amt(
            taxable_income=100000,
            filing_status="single",
            tax_year=2024,
            regular_tax=15000,
        )
        assert result["amt"] == 0

    def test_amt_with_iso(self):
        """AMT triggered by ISO spread."""
        result = calculate_amt(
            taxable_income=200000,
            filing_status="single",
            tax_year=2024,
            regular_tax=35000,
            iso_spread=300000,
        )
        assert result["amti"] > 200000
        # May or may not trigger AMT depending on exemption


class TestCredits:
    def test_ctc_basic(self):
        credit = calculate_child_tax_credit(2, 100000, "mfj", 2024)
        assert credit == 4000  # $2,000 x 2

    def test_ctc_phaseout(self):
        credit = calculate_child_tax_credit(1, 450000, "mfj", 2024)
        # $450k - $400k = $50k excess, $50k/1000 = 50 units, 50 * $50 = $2,500 reduction
        # $2,000 - $2,500 = $0 (floored)
        assert credit == 0

    def test_ctc_no_children(self):
        credit = calculate_child_tax_credit(0, 100000, "single", 2024)
        assert credit == 0


class TestStateTax:
    def test_no_income_tax_states(self):
        for state in ["TX", "FL", "WA"]:
            result = calculate_state_tax(100000, "single", state)
            assert result["state_tax"] == 0.0

    def test_california_tax(self):
        result = calculate_state_tax(100000, "single", "CA")
        assert result["state_tax"] > 0

    def test_illinois_flat(self):
        result = calculate_state_tax(100000, "single", "IL")
        expected = 100000 * 0.0495
        assert abs(result["state_tax"] - expected) < 1.0

    def test_unsupported_state(self):
        result = calculate_state_tax(100000, "single", "ZZ", state_adjustment=5000)
        assert result["state_tax"] == 5000


class TestQBIDeduction:
    def test_basic_qbi(self):
        """QBI deduction below phaseout."""
        qbi = calculate_qbi_deduction(
            qbi_eligible_income=100000,
            taxable_income_before_qbi=100000,
            tax_year=2024,
            filing_status="single",
        )
        assert qbi == 20000  # 20% of $100k

    def test_qbi_phaseout(self):
        """QBI in phaseout range."""
        qbi = calculate_qbi_deduction(
            qbi_eligible_income=100000,
            taxable_income_before_qbi=220000,
            tax_year=2024,
            filing_status="single",
        )
        assert qbi < 20000  # Should be reduced

    def test_no_qbi(self):
        qbi = calculate_qbi_deduction(0, 100000, 2024, "single")
        assert qbi == 0


class TestCalculateTax:
    """Integration tests for the full calculate_tax function."""

    def test_simple_single_wages(self):
        """Single filer with just wages."""
        result = calculate_tax({
            "tax_year": 2024,
            "filing_status": "single",
            "wages_salaries": 75000,
        })
        assert result["agi"] == 75000
        assert result["taxable_income"] == 75000 - 14600
        assert result["total_tax"] > 0
        assert result["effective_rate"] > 0
        assert result["marginal_bracket"] == 0.22

    def test_mfj_with_multiple_income(self):
        """MFJ with wages, dividends, and capital gains."""
        result = calculate_tax({
            "tax_year": 2024,
            "filing_status": "mfj",
            "wages_salaries": 150000,
            "qualified_dividends": 10000,
            "ordinary_dividends": 15000,
            "lt_gains_losses": 20000,
        })
        assert result["agi"] == 150000 + 15000 + 20000
        assert result["qualified_dividends"] == 10000
        assert result["total_tax"] > 0
        assert result["ltcg_tax"] >= 0

    def test_self_employment(self):
        """Single filer with business income."""
        result = calculate_tax({
            "tax_year": 2024,
            "filing_status": "single",
            "business_income": 100000,
        })
        assert result["se_tax"] > 0
        assert result["se_details"]["se_deduction"] > 0
        assert result["total_adjustments"] > 0  # SE deduction

    def test_social_security_recipient(self):
        """Retiree with SS and pension."""
        result = calculate_tax({
            "tax_year": 2024,
            "filing_status": "mfj",
            "social_security_total": 36000,
            "pension_annuity_taxable": 50000,
            "interest_income_taxable": 5000,
        })
        assert result["social_security_taxable"] > 0
        assert result["social_security_taxable"] <= 36000 * 0.85

    def test_itemized_deductions(self):
        """Filer with high itemized deductions."""
        result = calculate_tax({
            "tax_year": 2024,
            "filing_status": "mfj",
            "wages_salaries": 200000,
            "use_itemized": True,
            "state_local_taxes": 15000,  # SALT capped at $10k
            "mortgage_interest": 20000,
            "charitable_contributions": 10000,
        })
        assert result["deduction_type"] == "itemized"
        assert result["itemized_breakdown"]["salt_capped"] == 10000
        assert result["deduction_used"] == 10000 + 20000 + 10000  # SALT + mortgage + charity

    def test_capital_loss_limitation(self):
        """Capital loss limited to $3,000."""
        result = calculate_tax({
            "tax_year": 2024,
            "filing_status": "single",
            "wages_salaries": 80000,
            "st_gains_losses": -15000,
        })
        assert result["capital_gain_loss_net"] == -3000
        assert result["capital_loss_carryforward_remaining"] == 12000

    def test_niit_trigger(self):
        """High income triggers NIIT."""
        result = calculate_tax({
            "tax_year": 2024,
            "filing_status": "single",
            "wages_salaries": 180000,
            "interest_income_taxable": 30000,
            "lt_gains_losses": 40000,
        })
        assert result["niit"] > 0

    def test_no_income(self):
        """Edge case: no income."""
        result = calculate_tax({
            "tax_year": 2024,
            "filing_status": "single",
        })
        assert result["total_tax"] == 0
        assert result["agi"] == 0

    def test_refund_calculation(self):
        """Withholding exceeds tax = refund."""
        result = calculate_tax({
            "tax_year": 2024,
            "filing_status": "single",
            "wages_salaries": 50000,
            "federal_withholding": 15000,
        })
        assert result["refund_or_owed"] > 0  # Should get a refund

    def test_amount_owed(self):
        """Underpayment = amount owed."""
        result = calculate_tax({
            "tax_year": 2024,
            "filing_status": "single",
            "wages_salaries": 200000,
            "federal_withholding": 10000,
        })
        assert result["refund_or_owed"] < 0  # Owes money

    def test_magi_thresholds_present(self):
        """Verify MAGI thresholds are in output."""
        result = calculate_tax({
            "tax_year": 2024,
            "filing_status": "single",
            "wages_salaries": 100000,
        })
        assert "thresholds" in result
        assert "niit_threshold" in result["thresholds"]
        assert "roth_ira_phaseout_start" in result["thresholds"]
        assert "ltcg_0pct_ceiling" in result["thresholds"]

    def test_bracket_details_present(self):
        """Verify bracket details for visualization."""
        result = calculate_tax({
            "tax_year": 2024,
            "filing_status": "single",
            "wages_salaries": 100000,
        })
        assert "bracket_details" in result
        assert len(result["bracket_details"]) == 7  # 7 brackets

    def test_state_tax(self):
        """State tax included when state provided."""
        result = calculate_tax({
            "tax_year": 2024,
            "filing_status": "single",
            "wages_salaries": 100000,
            "state": "CA",
        })
        assert result["state_tax"] is not None
        assert result["state_tax"]["state_tax"] > 0

    def test_2023_tax_year(self):
        result = calculate_tax({
            "tax_year": 2023,
            "filing_status": "single",
            "wages_salaries": 100000,
        })
        assert result["tax_year"] == 2023
        assert result["taxable_income"] == 100000 - 13850

    def test_2025_tax_year(self):
        result = calculate_tax({
            "tax_year": 2025,
            "filing_status": "single",
            "wages_salaries": 100000,
        })
        assert result["tax_year"] == 2025
        assert result["taxable_income"] == 100000 - 15000

    def test_child_tax_credit(self):
        """CTC reduces tax."""
        result = calculate_tax({
            "tax_year": 2024,
            "filing_status": "mfj",
            "wages_salaries": 120000,
            "num_qualifying_children": 2,
        })
        assert result["credits"]["child_tax_credit"] == 4000

    def test_irmaa_output(self):
        """IRMAA tier info in output."""
        result = calculate_tax({
            "tax_year": 2025,
            "filing_status": "single",
            "wages_salaries": 150000,
        })
        assert "irmaa" in result
        assert "tier" in result["irmaa"]


class TestRangeCalc:
    def test_basic_range(self):
        base = {
            "tax_year": 2024,
            "filing_status": "single",
            "wages_salaries": 50000,
        }
        points = calculate_range(base, "wages_salaries", 0, 50000, 10000)
        assert len(points) == 6  # 0, 10k, 20k, 30k, 40k, 50k
        # Tax should increase with income
        assert points[-1]["total_tax"] > points[0]["total_tax"]


class TestFindRateSpike:
    def test_find_spike(self):
        base = {
            "tax_year": 2024,
            "filing_status": "single",
            "wages_salaries": 180000,
        }
        result = find_rate_spike(base, "wages_salaries", max_additional=100000)
        assert "safe_additional_income" in result
        assert "message" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
