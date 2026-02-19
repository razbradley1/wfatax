"""Social Security benefit taxation calculation."""

from .brackets import SINGLE, MFJ, MFS, HOH, QW


# Provisional income thresholds for SS taxation
# (base_threshold_50pct, base_threshold_85pct)
SS_THRESHOLDS = {
    SINGLE: (25000, 34000),
    HOH: (25000, 34000),
    MFJ: (32000, 44000),
    MFS: (0, 0),  # MFS who lived with spouse: all SS is potentially taxable
    QW: (32000, 44000),
}


def calculate_ss_taxable(
    social_security_total: float,
    agi_without_ss: float,
    tax_exempt_interest: float,
    filing_status: str,
) -> float:
    """
    Calculate the taxable portion of Social Security benefits.

    Uses the provisional income formula:
    Provisional Income = AGI (without SS) + tax-exempt interest + 50% of SS benefits

    Then apply 50%/85% thresholds by filing status.
    """
    if social_security_total <= 0:
        return 0.0

    half_ss = social_security_total * 0.50
    provisional_income = agi_without_ss + tax_exempt_interest + half_ss

    thresh_50, thresh_85 = SS_THRESHOLDS[filing_status]

    # MFS who lived with spouse: up to 85% is taxable from $0
    if filing_status == MFS and thresh_50 == 0:
        taxable = min(social_security_total * 0.85, provisional_income * 0.85)
        return round(max(taxable, 0), 2)

    if provisional_income <= thresh_50:
        return 0.0

    # Amount taxable under 50% tier
    excess_50 = min(provisional_income - thresh_50, thresh_85 - thresh_50)
    taxable_50 = excess_50 * 0.50

    # Amount taxable under 85% tier
    if provisional_income > thresh_85:
        excess_85 = provisional_income - thresh_85
        taxable_85 = excess_85 * 0.85
    else:
        taxable_85 = 0.0

    taxable = taxable_50 + taxable_85

    # Cannot exceed 85% of total benefits
    max_taxable = social_security_total * 0.85
    return round(min(taxable, max_taxable), 2)


def calculate_ss_taxation_pct(
    social_security_total: float,
    agi_without_ss: float,
    tax_exempt_interest: float,
    filing_status: str,
) -> float:
    """Return the percentage of SS benefits that are taxable (0-85%)."""
    if social_security_total <= 0:
        return 0.0
    taxable = calculate_ss_taxable(
        social_security_total, agi_without_ss, tax_exempt_interest, filing_status
    )
    return round((taxable / social_security_total) * 100, 1)
