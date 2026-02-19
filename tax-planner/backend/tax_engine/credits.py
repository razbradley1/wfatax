"""Tax credits calculations."""

from .brackets import SINGLE, MFJ, MFS, HOH, QW


# Child Tax Credit parameters
CTC_AMOUNT = {
    2023: 2000,
    2024: 2000,
    2025: 2000,
}

CTC_PHASEOUT_START = {
    SINGLE: 200000,
    HOH: 200000,
    MFJ: 400000,
    MFS: 200000,
    QW: 400000,
}

CTC_PHASEOUT_RATE = 0.05  # $50 reduction per $1,000 over threshold


def calculate_child_tax_credit(
    num_qualifying_children: int,
    agi: float,
    filing_status: str,
    tax_year: int,
) -> float:
    """
    Calculate Child Tax Credit.
    $2,000 per qualifying child under 17.
    Phaseout: reduced by $50 per $1,000 (or fraction) of AGI over threshold.
    """
    if num_qualifying_children <= 0:
        return 0.0

    credit_per_child = CTC_AMOUNT.get(tax_year, 2000)
    total_credit = credit_per_child * num_qualifying_children

    threshold = CTC_PHASEOUT_START[filing_status]
    if agi > threshold:
        excess = agi - threshold
        # Round up to nearest $1,000
        reduction_units = -(-int(excess) // 1000)  # ceiling division
        reduction = reduction_units * 50
        total_credit = max(total_credit - reduction, 0)

    return round(total_credit, 2)


# Child and Dependent Care Credit
CARE_CREDIT_MAX_EXPENSES = {
    1: 3000,  # one qualifying individual
    2: 6000,  # two or more
}

CARE_CREDIT_RATES = [
    # (AGI threshold, credit percentage)
    (15000, 0.35),
    (17000, 0.34),
    (19000, 0.33),
    (21000, 0.32),
    (23000, 0.31),
    (25000, 0.30),
    (27000, 0.29),
    (29000, 0.28),
    (31000, 0.27),
    (33000, 0.26),
    (35000, 0.25),
    (37000, 0.24),
    (39000, 0.23),
    (41000, 0.22),
    (43000, 0.21),
    (float("inf"), 0.20),
]


def calculate_care_credit(
    qualifying_expenses: float,
    num_qualifying_individuals: int,
    agi: float,
) -> float:
    """Calculate Child and Dependent Care Credit."""
    if qualifying_expenses <= 0 or num_qualifying_individuals <= 0:
        return 0.0

    max_expenses = CARE_CREDIT_MAX_EXPENSES.get(
        min(num_qualifying_individuals, 2), 6000
    )
    eligible_expenses = min(qualifying_expenses, max_expenses)

    # Determine credit rate based on AGI
    rate = 0.20
    for threshold, r in CARE_CREDIT_RATES:
        if agi <= threshold:
            rate = r
            break

    return round(eligible_expenses * rate, 2)


# Saver's Credit (Retirement Savings Contributions Credit)
SAVERS_CREDIT_THRESHOLDS = {
    2023: {
        SINGLE: [(21750, 0.50), (23750, 0.20), (36500, 0.10)],
        MFJ: [(43500, 0.50), (47500, 0.20), (73000, 0.10)],
        HOH: [(32625, 0.50), (35625, 0.20), (54750, 0.10)],
    },
    2024: {
        SINGLE: [(23000, 0.50), (25000, 0.20), (38250, 0.10)],
        MFJ: [(46000, 0.50), (50000, 0.20), (76500, 0.10)],
        HOH: [(34500, 0.50), (37500, 0.20), (57375, 0.10)],
    },
    2025: {
        SINGLE: [(23750, 0.50), (25750, 0.20), (39500, 0.10)],
        MFJ: [(47500, 0.50), (51500, 0.20), (79000, 0.10)],
        HOH: [(35625, 0.50), (38625, 0.20), (59250, 0.10)],
    },
}


def calculate_savers_credit(
    retirement_contributions: float,
    agi: float,
    filing_status: str,
    tax_year: int,
) -> float:
    """
    Calculate Retirement Savings Contributions Credit (Saver's Credit).
    Max contribution eligible: $2,000 per person ($4,000 MFJ).
    """
    if retirement_contributions <= 0:
        return 0.0

    max_contrib = 4000 if filing_status == MFJ else 2000
    eligible = min(retirement_contributions, max_contrib)

    thresholds = SAVERS_CREDIT_THRESHOLDS.get(tax_year, SAVERS_CREDIT_THRESHOLDS[2025])
    status_key = filing_status
    if status_key not in thresholds:
        status_key = SINGLE  # MFS and QW use single thresholds

    for threshold, rate in thresholds[status_key]:
        if agi <= threshold:
            return round(eligible * rate, 2)

    return 0.0  # AGI exceeds all thresholds


def calculate_total_credits(
    inputs: dict,
    agi: float,
    filing_status: str,
    tax_year: int,
) -> dict:
    """Calculate all applicable credits and return breakdown."""
    credits = {}

    # Child Tax Credit
    num_children = inputs.get("num_qualifying_children", 0)
    credits["child_tax_credit"] = calculate_child_tax_credit(
        num_children, agi, filing_status, tax_year
    )

    # Child and Dependent Care Credit
    care_expenses = inputs.get("dependent_care_expenses", 0)
    care_individuals = inputs.get("num_care_qualifying", 0)
    credits["care_credit"] = calculate_care_credit(
        care_expenses, care_individuals, agi
    )

    # Saver's Credit
    retirement_contribs = inputs.get("retirement_contributions_for_credit", 0)
    credits["savers_credit"] = calculate_savers_credit(
        retirement_contribs, agi, filing_status, tax_year
    )

    # Education credits (simplified - manual entry)
    credits["education_credits"] = inputs.get("education_credits", 0)

    # Other credits (manual override)
    credits["other_credits"] = inputs.get("other_credits", 0)

    credits["total_credits"] = round(sum(credits.values()), 2)

    return credits
