"""Net Investment Income Tax (NIIT) - IRC Section 1411."""

from .brackets import SINGLE, MFJ, MFS, HOH, QW

# NIIT rate
NIIT_RATE = 0.038

# MAGI thresholds for NIIT (these are NOT indexed for inflation)
NIIT_THRESHOLDS = {
    SINGLE: 200000,
    HOH: 200000,
    MFJ: 250000,
    MFS: 125000,
    QW: 250000,
}


def calculate_niit(
    magi: float,
    net_investment_income: float,
    filing_status: str,
) -> float:
    """
    Calculate Net Investment Income Tax.

    NIIT is 3.8% on the lesser of:
    1. Net investment income, OR
    2. MAGI in excess of the threshold

    Net investment income includes: interest, dividends, capital gains,
    rental/royalty income, passive activity income, annuities.
    Does NOT include wages, SE income, SS benefits, tax-exempt interest.
    """
    if net_investment_income <= 0:
        return 0.0

    threshold = NIIT_THRESHOLDS[filing_status]
    magi_excess = magi - threshold

    if magi_excess <= 0:
        return 0.0

    taxable_base = min(net_investment_income, magi_excess)
    return round(taxable_base * NIIT_RATE, 2)


def get_niit_threshold(filing_status: str) -> float:
    """Return the NIIT MAGI threshold for the filing status."""
    return NIIT_THRESHOLDS[filing_status]


def calculate_distance_to_niit(magi: float, filing_status: str) -> float:
    """Return how far below (positive) or above (negative) the NIIT threshold."""
    threshold = NIIT_THRESHOLDS[filing_status]
    return threshold - magi
