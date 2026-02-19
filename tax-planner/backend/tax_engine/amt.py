"""Alternative Minimum Tax (AMT) calculation."""

from .brackets import SINGLE, MFJ, MFS, HOH, QW

# AMT exemption amounts
AMT_EXEMPTION = {
    2023: {
        SINGLE: 81300,
        MFJ: 126500,
        MFS: 63250,
        HOH: 81300,
        QW: 126500,
    },
    2024: {
        SINGLE: 85700,
        MFJ: 133300,
        MFS: 66650,
        HOH: 85700,
        QW: 133300,
    },
    2025: {
        SINGLE: 88100,
        MFJ: 137000,
        MFS: 68500,
        HOH: 88100,
        QW: 137000,
    },
}

# AMT exemption phaseout threshold (exemption reduced by 25% of AMTI over this)
AMT_PHASEOUT_START = {
    2023: {
        SINGLE: 578150,
        MFJ: 1156300,
        MFS: 578150,
        HOH: 578150,
        QW: 1156300,
    },
    2024: {
        SINGLE: 609350,
        MFJ: 1218700,
        MFS: 609350,
        HOH: 609350,
        QW: 1218700,
    },
    2025: {
        SINGLE: 626350,
        MFJ: 1252700,
        MFS: 626350,
        HOH: 626350,
        QW: 1252700,
    },
}

# AMT rates
AMT_RATE_LOW = 0.26
AMT_RATE_HIGH = 0.28
AMT_RATE_THRESHOLD = {
    2023: {SINGLE: 220700, MFJ: 220700, MFS: 110350, HOH: 220700, QW: 220700},
    2024: {SINGLE: 232600, MFJ: 232600, MFS: 116300, HOH: 232600, QW: 232600},
    2025: {SINGLE: 239100, MFJ: 239100, MFS: 119550, HOH: 239100, QW: 239100},
}


def calculate_amt(
    taxable_income: float,
    filing_status: str,
    tax_year: int,
    regular_tax: float,
    # AMT preference items / adjustments
    state_local_tax_deduction: float = 0,
    misc_itemized_above_2pct: float = 0,
    iso_spread: float = 0,
    other_amt_adjustments: float = 0,
    tax_exempt_interest_private_activity: float = 0,
) -> dict:
    """
    Calculate Alternative Minimum Tax.

    Returns dict with AMTI, tentative minimum tax, and AMT owed.
    """
    year_data = lambda d: d.get(tax_year, d[2025])

    # Step 1: Calculate AMTI (Alternative Minimum Taxable Income)
    amti = taxable_income

    # Add back preference items
    amti += state_local_tax_deduction  # SALT deduction added back
    amti += misc_itemized_above_2pct
    amti += iso_spread
    amti += other_amt_adjustments
    amti += tax_exempt_interest_private_activity

    if amti <= 0:
        return {
            "amti": 0,
            "amt_exemption": 0,
            "tentative_minimum_tax": 0,
            "amt": 0,
        }

    # Step 2: Calculate AMT exemption
    exemption = year_data(AMT_EXEMPTION)[filing_status]
    phaseout_start = year_data(AMT_PHASEOUT_START)[filing_status]

    if amti > phaseout_start:
        reduction = (amti - phaseout_start) * 0.25
        exemption = max(exemption - reduction, 0)

    # Step 3: Calculate AMT base
    amt_base = max(amti - exemption, 0)

    # Step 4: Apply AMT rates
    rate_threshold = year_data(AMT_RATE_THRESHOLD)[filing_status]

    if amt_base <= rate_threshold:
        tentative_min_tax = amt_base * AMT_RATE_LOW
    else:
        tentative_min_tax = (rate_threshold * AMT_RATE_LOW) + (
            (amt_base - rate_threshold) * AMT_RATE_HIGH
        )

    # Step 5: AMT = max(tentative minimum tax - regular tax, 0)
    amt = max(round(tentative_min_tax - regular_tax, 2), 0)

    return {
        "amti": round(amti, 2),
        "amt_exemption": round(exemption, 2),
        "tentative_minimum_tax": round(tentative_min_tax, 2),
        "amt": amt,
    }
