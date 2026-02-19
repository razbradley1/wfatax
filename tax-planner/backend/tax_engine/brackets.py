"""Federal income tax brackets and standard deductions by year and filing status."""

from typing import Dict, List, Tuple

# Filing status constants
SINGLE = "single"
MFJ = "mfj"
MFS = "mfs"
HOH = "hoh"
QW = "qw"

# Standard deductions by year and filing status
STANDARD_DEDUCTIONS: Dict[int, Dict[str, float]] = {
    2023: {
        SINGLE: 13850,
        MFJ: 27700,
        MFS: 13850,
        HOH: 20800,
        QW: 27700,
    },
    2024: {
        SINGLE: 14600,
        MFJ: 29200,
        MFS: 14600,
        HOH: 21900,
        QW: 29200,
    },
    2025: {
        SINGLE: 15000,
        MFJ: 30000,
        MFS: 15000,
        HOH: 22500,
        QW: 30000,
    },
}

# Additional standard deduction for age 65+ or blind (per person)
ADDITIONAL_STD_DEDUCTION: Dict[int, Dict[str, float]] = {
    2023: {
        SINGLE: 1850,
        MFJ: 1500,
        MFS: 1500,
        HOH: 1850,
        QW: 1500,
    },
    2024: {
        SINGLE: 1950,
        MFJ: 1550,
        MFS: 1550,
        HOH: 1950,
        QW: 1550,
    },
    2025: {
        SINGLE: 2000,
        MFJ: 1600,
        MFS: 1600,
        HOH: 2000,
        QW: 1600,
    },
}

# Ordinary income tax brackets: list of (upper_bound, rate)
# The last bracket has no upper bound (represented as float('inf'))
ORDINARY_BRACKETS: Dict[int, Dict[str, List[Tuple[float, float]]]] = {
    2023: {
        SINGLE: [
            (11000, 0.10),
            (44725, 0.12),
            (95375, 0.22),
            (182100, 0.24),
            (231250, 0.32),
            (578125, 0.35),
            (float("inf"), 0.37),
        ],
        MFJ: [
            (22000, 0.10),
            (89450, 0.12),
            (190750, 0.22),
            (364200, 0.24),
            (462500, 0.32),
            (693750, 0.35),
            (float("inf"), 0.37),
        ],
        MFS: [
            (11000, 0.10),
            (44725, 0.12),
            (95375, 0.22),
            (182100, 0.24),
            (231250, 0.32),
            (346875, 0.35),
            (float("inf"), 0.37),
        ],
        HOH: [
            (15700, 0.10),
            (59850, 0.12),
            (95350, 0.22),
            (182100, 0.24),
            (231250, 0.32),
            (578100, 0.35),
            (float("inf"), 0.37),
        ],
        QW: [
            (22000, 0.10),
            (89450, 0.12),
            (190750, 0.22),
            (364200, 0.24),
            (462500, 0.32),
            (693750, 0.35),
            (float("inf"), 0.37),
        ],
    },
    2024: {
        SINGLE: [
            (11600, 0.10),
            (47150, 0.12),
            (100525, 0.22),
            (191950, 0.24),
            (243725, 0.32),
            (609350, 0.35),
            (float("inf"), 0.37),
        ],
        MFJ: [
            (23200, 0.10),
            (94300, 0.12),
            (201050, 0.22),
            (383900, 0.24),
            (487450, 0.32),
            (731200, 0.35),
            (float("inf"), 0.37),
        ],
        MFS: [
            (11600, 0.10),
            (47150, 0.12),
            (100525, 0.22),
            (191950, 0.24),
            (243725, 0.32),
            (365600, 0.35),
            (float("inf"), 0.37),
        ],
        HOH: [
            (16550, 0.10),
            (63100, 0.12),
            (100500, 0.22),
            (191950, 0.24),
            (243700, 0.32),
            (609350, 0.35),
            (float("inf"), 0.37),
        ],
        QW: [
            (23200, 0.10),
            (94300, 0.12),
            (201050, 0.22),
            (383900, 0.24),
            (487450, 0.32),
            (731200, 0.35),
            (float("inf"), 0.37),
        ],
    },
    2025: {
        SINGLE: [
            (11925, 0.10),
            (48475, 0.12),
            (103350, 0.22),
            (197300, 0.24),
            (250525, 0.32),
            (626350, 0.35),
            (float("inf"), 0.37),
        ],
        MFJ: [
            (23850, 0.10),
            (96950, 0.12),
            (206700, 0.22),
            (394600, 0.24),
            (501050, 0.32),
            (751600, 0.35),
            (float("inf"), 0.37),
        ],
        MFS: [
            (11925, 0.10),
            (48475, 0.12),
            (103350, 0.22),
            (197300, 0.24),
            (250525, 0.32),
            (375800, 0.35),
            (float("inf"), 0.37),
        ],
        HOH: [
            (17000, 0.10),
            (64850, 0.12),
            (103350, 0.22),
            (197300, 0.24),
            (250500, 0.32),
            (626350, 0.35),
            (float("inf"), 0.37),
        ],
        QW: [
            (23850, 0.10),
            (96950, 0.12),
            (206700, 0.22),
            (394600, 0.24),
            (501050, 0.32),
            (751600, 0.35),
            (float("inf"), 0.37),
        ],
    },
}

# Long-term capital gains / qualified dividends brackets
LTCG_BRACKETS: Dict[int, Dict[str, List[Tuple[float, float]]]] = {
    2023: {
        SINGLE: [
            (44625, 0.00),
            (492300, 0.15),
            (float("inf"), 0.20),
        ],
        MFJ: [
            (89250, 0.00),
            (553850, 0.15),
            (float("inf"), 0.20),
        ],
        MFS: [
            (44625, 0.00),
            (276900, 0.15),
            (float("inf"), 0.20),
        ],
        HOH: [
            (59750, 0.00),
            (523050, 0.15),
            (float("inf"), 0.20),
        ],
        QW: [
            (89250, 0.00),
            (553850, 0.15),
            (float("inf"), 0.20),
        ],
    },
    2024: {
        SINGLE: [
            (47025, 0.00),
            (518900, 0.15),
            (float("inf"), 0.20),
        ],
        MFJ: [
            (94050, 0.00),
            (583750, 0.15),
            (float("inf"), 0.20),
        ],
        MFS: [
            (47025, 0.00),
            (291850, 0.15),
            (float("inf"), 0.20),
        ],
        HOH: [
            (63000, 0.00),
            (551350, 0.15),
            (float("inf"), 0.20),
        ],
        QW: [
            (94050, 0.00),
            (583750, 0.15),
            (float("inf"), 0.20),
        ],
    },
    2025: {
        SINGLE: [
            (48350, 0.00),
            (533400, 0.15),
            (float("inf"), 0.20),
        ],
        MFJ: [
            (96700, 0.00),
            (600050, 0.15),
            (float("inf"), 0.20),
        ],
        MFS: [
            (48350, 0.00),
            (300000, 0.15),
            (float("inf"), 0.20),
        ],
        HOH: [
            (64750, 0.00),
            (566700, 0.15),
            (float("inf"), 0.20),
        ],
        QW: [
            (96700, 0.00),
            (600050, 0.15),
            (float("inf"), 0.20),
        ],
    },
}

# QBI deduction phaseout thresholds
QBI_THRESHOLDS: Dict[int, Dict[str, Tuple[float, float]]] = {
    # (start of phaseout, end of phaseout = start + $50k single / $100k MFJ)
    2023: {
        SINGLE: (182100, 232100),
        MFJ: (364200, 464200),
        MFS: (182100, 232100),
        HOH: (182100, 232100),
        QW: (364200, 464200),
    },
    2024: {
        SINGLE: (191950, 241950),
        MFJ: (383900, 483900),
        MFS: (191950, 241950),
        HOH: (191950, 241950),
        QW: (383900, 483900),
    },
    2025: {
        SINGLE: (197300, 247300),
        MFJ: (394600, 494600),
        MFS: (197300, 247300),
        HOH: (197300, 247300),
        QW: (394600, 494600),
    },
}


def get_standard_deduction(
    tax_year: int,
    filing_status: str,
    age_65_primary: bool = False,
    age_65_secondary: bool = False,
    blind_primary: bool = False,
    blind_secondary: bool = False,
) -> float:
    """Calculate total standard deduction including additional amounts for age/blindness."""
    base = STANDARD_DEDUCTIONS[tax_year][filing_status]
    additional = ADDITIONAL_STD_DEDUCTION[tax_year][filing_status]

    extra_count = 0
    if age_65_primary:
        extra_count += 1
    if blind_primary:
        extra_count += 1
    if filing_status in (MFJ, QW):
        if age_65_secondary:
            extra_count += 1
        if blind_secondary:
            extra_count += 1

    return base + (additional * extra_count)


def calculate_ordinary_tax(taxable_income: float, tax_year: int, filing_status: str) -> float:
    """Calculate ordinary income tax using bracket tables."""
    if taxable_income <= 0:
        return 0.0

    brackets = ORDINARY_BRACKETS[tax_year][filing_status]
    tax = 0.0
    prev_bound = 0.0

    for upper_bound, rate in brackets:
        if taxable_income <= prev_bound:
            break
        bracket_income = min(taxable_income, upper_bound) - prev_bound
        if bracket_income > 0:
            tax += bracket_income * rate
        prev_bound = upper_bound

    return round(tax, 2)


def calculate_ltcg_tax(
    ordinary_taxable_income: float,
    ltcg_income: float,
    tax_year: int,
    filing_status: str,
) -> float:
    """
    Calculate tax on long-term capital gains and qualified dividends.
    LTCG brackets are applied based on total taxable income (ordinary + LTCG stacked on top).
    """
    if ltcg_income <= 0:
        return 0.0

    brackets = LTCG_BRACKETS[tax_year][filing_status]
    tax = 0.0
    # LTCG stacks on top of ordinary income
    base = max(ordinary_taxable_income, 0)
    remaining = ltcg_income

    for upper_bound, rate in brackets:
        if remaining <= 0:
            break
        if base >= upper_bound:
            continue
        # Amount of LTCG that falls in this bracket
        space_in_bracket = upper_bound - base
        taxable_in_bracket = min(remaining, space_in_bracket)
        tax += taxable_in_bracket * rate
        remaining -= taxable_in_bracket
        base += taxable_in_bracket

    return round(tax, 2)


def get_marginal_bracket(taxable_income: float, tax_year: int, filing_status: str) -> float:
    """Return the marginal ordinary income tax rate for the given taxable income."""
    if taxable_income <= 0:
        return 0.10

    brackets = ORDINARY_BRACKETS[tax_year][filing_status]
    prev_bound = 0.0
    for upper_bound, rate in brackets:
        if taxable_income <= upper_bound:
            return rate
        prev_bound = upper_bound

    return brackets[-1][1]


def calculate_qbi_deduction(
    qbi_eligible_income: float,
    taxable_income_before_qbi: float,
    tax_year: int,
    filing_status: str,
    w2_wages: float = 0,
    ubia: float = 0,
) -> float:
    """
    Calculate Qualified Business Income deduction (Section 199A).
    Simplified: 20% of QBI, subject to phaseout above threshold.
    """
    if qbi_eligible_income <= 0:
        return 0.0

    thresholds = QBI_THRESHOLDS[tax_year][filing_status]
    start, end = thresholds

    base_deduction = qbi_eligible_income * 0.20

    if taxable_income_before_qbi <= start:
        # Full deduction
        deduction = base_deduction
    elif taxable_income_before_qbi >= end:
        # Fully phased out — limited to greater of W-2/UBIA test
        w2_limit = max(w2_wages * 0.50, w2_wages * 0.25 + ubia * 0.025)
        deduction = min(base_deduction, w2_limit)
    else:
        # Partial phaseout
        phase_pct = (taxable_income_before_qbi - start) / (end - start)
        w2_limit = max(w2_wages * 0.50, w2_wages * 0.25 + ubia * 0.025)
        reduction = (base_deduction - w2_limit) * phase_pct
        deduction = max(base_deduction - reduction, 0)

    # QBI deduction cannot exceed 20% of taxable income (before QBI deduction)
    max_deduction = max(taxable_income_before_qbi, 0) * 0.20
    return round(min(deduction, max_deduction), 2)
