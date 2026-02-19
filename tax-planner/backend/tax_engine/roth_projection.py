"""Multi-year Roth Conversion projection tool."""

from typing import List, Dict, Optional
from .calculator import calculate_tax


def project_roth_conversions(
    current_age: int,
    retirement_age: int,
    target_end_age: int,
    pretax_balance: float,
    roth_balance: float,
    taxable_balance: float,
    annual_return: float,  # e.g., 0.07 for 7%
    expected_retirement_income: float,  # annual income in retirement (SS, pension, etc.)
    filing_status: str,
    target_bracket_rate: float,  # e.g., 0.22 for 22% bracket
    tax_year: int = 2025,
    annual_contribution_pretax: float = 0,
    annual_contribution_roth: float = 0,
    rmd_start_age: int = 73,
) -> Dict:
    """
    Project multi-year Roth conversion strategy.

    Models year-by-year optimal Roth conversion amounts that fill up to
    the target bracket, comparing with a no-conversion baseline.

    Returns projection table and summary statistics.
    """
    # RMD distribution periods (simplified - Uniform Lifetime Table)
    RMD_TABLE = {
        73: 26.5, 74: 25.5, 75: 24.6, 76: 23.7, 77: 22.9,
        78: 22.0, 79: 21.1, 80: 20.2, 81: 19.4, 82: 18.5,
        83: 17.7, 84: 16.8, 85: 16.0, 86: 15.2, 87: 14.4,
        88: 13.7, 89: 12.9, 90: 12.2, 91: 11.5, 92: 10.8,
        93: 10.1, 94: 9.5, 95: 8.9, 96: 8.4, 97: 7.8,
        98: 7.3, 99: 6.8, 100: 6.4,
    }

    def get_rmd_factor(age: int) -> float:
        if age < 73:
            return 0
        if age > 100:
            return 5.0
        return RMD_TABLE.get(age, 6.4)

    def find_conversion_amount(
        other_income: float,
        fs: str,
        target_rate: float,
    ) -> float:
        """Binary search for conversion amount that fills to target bracket."""
        from .brackets import ORDINARY_BRACKETS, STANDARD_DEDUCTIONS

        brackets = ORDINARY_BRACKETS.get(tax_year, ORDINARY_BRACKETS[2025])
        std_ded = STANDARD_DEDUCTIONS.get(tax_year, STANDARD_DEDUCTIONS[2025])

        bracket_list = brackets[fs]
        deduction = std_ded[fs]

        # Find the top of the target bracket
        target_top = 0
        for upper, rate in bracket_list:
            if rate == target_rate:
                target_top = upper
                break
            if rate > target_rate:
                # Target rate not found exactly, use previous bracket top
                break
            target_top = upper

        if target_top == 0:
            # Use first bracket above target rate
            for upper, rate in bracket_list:
                if rate >= target_rate:
                    target_top = upper
                    break

        # Taxable income = income - deduction
        # We want taxable_income to reach target_top
        target_total_income = target_top + deduction
        conversion = max(target_total_income - other_income, 0)
        return round(conversion, 2)

    # Run two scenarios: with conversion and without
    years = []
    cumulative_tax_with = 0
    cumulative_tax_without = 0

    pretax_with = pretax_balance
    roth_with = roth_balance
    pretax_without = pretax_balance
    roth_without = roth_balance

    for year_offset in range(target_end_age - current_age + 1):
        age = current_age + year_offset
        year = tax_year + year_offset
        is_retired = age >= retirement_age

        # Income for the year
        if is_retired:
            base_income = expected_retirement_income
        else:
            base_income = expected_retirement_income  # simplification

        # RMDs (from pre-tax balance)
        rmd_with = 0
        rmd_without = 0
        rmd_factor = get_rmd_factor(age)
        if rmd_factor > 0:
            rmd_with = pretax_with / rmd_factor if pretax_with > 0 else 0
            rmd_without = pretax_without / rmd_factor if pretax_without > 0 else 0

        # Conversion amount (only in pre-retirement or early retirement years)
        conversion = 0
        if age < rmd_start_age:  # Convert before RMDs start
            total_income_before_conversion = base_income + rmd_with
            conversion = find_conversion_amount(
                total_income_before_conversion, filing_status, target_bracket_rate
            )
            conversion = min(conversion, pretax_with)  # Can't convert more than available

        # Tax calculations - with conversion
        income_with = base_income + rmd_with + conversion
        tax_result_with = calculate_tax({
            "tax_year": min(year, 2025),  # Use latest available year params
            "filing_status": filing_status,
            "wages_salaries": base_income if not is_retired else 0,
            "pension_annuity_taxable": (base_income if is_retired else 0) + rmd_with,
            "ira_distributions_taxable": conversion,
        })
        tax_with = tax_result_with.get("total_tax", 0)
        cumulative_tax_with += tax_with

        # Tax calculations - without conversion
        income_without = base_income + rmd_without
        tax_result_without = calculate_tax({
            "tax_year": min(year, 2025),
            "filing_status": filing_status,
            "wages_salaries": base_income if not is_retired else 0,
            "pension_annuity_taxable": (base_income if is_retired else 0) + rmd_without,
        })
        tax_without = tax_result_without.get("total_tax", 0)
        cumulative_tax_without += tax_without

        # Grow balances
        # With conversion: move conversion from pretax to roth
        pretax_with = (pretax_with - rmd_with - conversion) * (1 + annual_return)
        roth_with = roth_with * (1 + annual_return)
        if not is_retired:
            pretax_with += annual_contribution_pretax
            roth_with += annual_contribution_roth + conversion

        # Without conversion
        pretax_without = (pretax_without - rmd_without) * (1 + annual_return)
        roth_without = roth_without * (1 + annual_return)
        if not is_retired:
            pretax_without += annual_contribution_pretax
            roth_without += annual_contribution_roth

        years.append({
            "year": year,
            "age": age,
            "pretax_balance_with_conversion": round(pretax_with, 2),
            "roth_balance_with_conversion": round(roth_with, 2),
            "pretax_balance_no_conversion": round(pretax_without, 2),
            "roth_balance_no_conversion": round(roth_without, 2),
            "conversion_amount": round(conversion, 2),
            "rmd_with_conversion": round(rmd_with, 2),
            "rmd_no_conversion": round(rmd_without, 2),
            "tax_cost_conversion": round(tax_with, 2),
            "tax_no_conversion": round(tax_without, 2),
            "cumulative_tax_with": round(cumulative_tax_with, 2),
            "cumulative_tax_without": round(cumulative_tax_without, 2),
        })

    # Find break-even year
    break_even_year = None
    for yr in years:
        if yr["cumulative_tax_with"] < yr["cumulative_tax_without"]:
            break_even_year = yr["year"]
            break

    total_savings = round(cumulative_tax_without - cumulative_tax_with, 2)

    return {
        "projection": years,
        "summary": {
            "total_tax_with_conversion": round(cumulative_tax_with, 2),
            "total_tax_without_conversion": round(cumulative_tax_without, 2),
            "total_tax_savings": total_savings,
            "break_even_year": break_even_year,
            "final_pretax_with": years[-1]["pretax_balance_with_conversion"] if years else 0,
            "final_roth_with": years[-1]["roth_balance_with_conversion"] if years else 0,
            "final_pretax_without": years[-1]["pretax_balance_no_conversion"] if years else 0,
            "final_roth_without": years[-1]["roth_balance_no_conversion"] if years else 0,
        },
    }
