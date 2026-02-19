"""State income tax calculations.

Implements basic state income tax for:
California, New York, Texas (none), Florida (none), Illinois, New Jersey,
Pennsylvania, Ohio, Georgia, North Carolina, Arizona, Colorado, Washington (none).
"""

from typing import Optional


def _apply_brackets(income: float, brackets: list) -> float:
    """Apply progressive tax brackets."""
    if income <= 0:
        return 0.0
    tax = 0.0
    prev = 0.0
    for upper, rate in brackets:
        if income <= prev:
            break
        bracket_income = min(income, upper) - prev
        if bracket_income > 0:
            tax += bracket_income * rate
        prev = upper
    return round(tax, 2)


# ---- State implementations ----

def _california_tax(taxable_income: float, filing_status: str) -> float:
    """California income tax (2024 rates)."""
    if filing_status in ("mfj", "qw"):
        brackets = [
            (20824, 0.01), (49368, 0.02), (77918, 0.04),
            (108162, 0.06), (136700, 0.08), (698274, 0.093),
            (837922, 0.103), (1000000, 0.113), (float("inf"), 0.123),
        ]
        std_ded = 10726
    else:  # single, mfs, hoh
        brackets = [
            (10412, 0.01), (24684, 0.02), (38959, 0.04),
            (54081, 0.06), (68350, 0.08), (349137, 0.093),
            (418961, 0.103), (698271, 0.113), (float("inf"), 0.123),
        ]
        std_ded = 5363
        if filing_status == "hoh":
            std_ded = 10726

    income = max(taxable_income - std_ded, 0)
    tax = _apply_brackets(income, brackets)

    # Mental Health Services Tax: 1% on income over $1M
    if taxable_income > 1000000:
        tax += (taxable_income - 1000000) * 0.01

    return round(tax, 2)


def _new_york_tax(taxable_income: float, filing_status: str) -> float:
    """New York state income tax (2024 rates)."""
    if filing_status in ("mfj", "qw"):
        brackets = [
            (17150, 0.04), (23600, 0.045), (27900, 0.0525),
            (161550, 0.0585), (323200, 0.0625), (2155350, 0.0685),
            (5000000, 0.0965), (25000000, 0.103), (float("inf"), 0.109),
        ]
        std_ded = 16050
    else:
        brackets = [
            (8500, 0.04), (11700, 0.045), (13900, 0.0525),
            (80650, 0.0585), (215400, 0.0625), (1077550, 0.0685),
            (5000000, 0.0965), (25000000, 0.103), (float("inf"), 0.109),
        ]
        std_ded = 8000
        if filing_status == "hoh":
            std_ded = 11200

    income = max(taxable_income - std_ded, 0)
    return _apply_brackets(income, brackets)


def _illinois_tax(taxable_income: float, filing_status: str) -> float:
    """Illinois income tax - flat rate."""
    return round(max(taxable_income, 0) * 0.0495, 2)


def _new_jersey_tax(taxable_income: float, filing_status: str) -> float:
    """New Jersey income tax (2024 rates)."""
    if filing_status in ("mfj", "qw"):
        brackets = [
            (20000, 0.014), (35000, 0.0175), (40000, 0.035),
            (75000, 0.05525), (150000, 0.0637), (500000, 0.0897),
            (1000000, 0.1075), (float("inf"), 0.1075),
        ]
    else:
        brackets = [
            (20000, 0.014), (35000, 0.0175), (40000, 0.035),
            (75000, 0.05525), (500000, 0.0637), (1000000, 0.0897),
            (float("inf"), 0.1075),
        ]
    return _apply_brackets(taxable_income, brackets)


def _pennsylvania_tax(taxable_income: float, filing_status: str) -> float:
    """Pennsylvania income tax - flat rate."""
    return round(max(taxable_income, 0) * 0.0307, 2)


def _ohio_tax(taxable_income: float, filing_status: str) -> float:
    """Ohio income tax (2024 rates)."""
    brackets = [
        (26050, 0.0),  # 0% on first $26,050
        (46100, 0.02765),
        (92150, 0.03226),
        (115300, 0.03688),
        (float("inf"), 0.0399),
    ]
    return _apply_brackets(taxable_income, brackets)


def _georgia_tax(taxable_income: float, filing_status: str) -> float:
    """Georgia income tax (2024 rates) - moving to flat tax."""
    if filing_status in ("mfj", "qw"):
        brackets = [
            (1000, 0.01), (3000, 0.02), (5000, 0.03),
            (7000, 0.04), (10000, 0.05), (float("inf"), 0.055),
        ]
        std_ded = 12000
    else:
        brackets = [
            (750, 0.01), (2250, 0.02), (3750, 0.03),
            (5250, 0.04), (7000, 0.05), (float("inf"), 0.055),
        ]
        std_ded = 5400
        if filing_status == "hoh":
            std_ded = 7100

    income = max(taxable_income - std_ded, 0)
    return _apply_brackets(income, brackets)


def _north_carolina_tax(taxable_income: float, filing_status: str) -> float:
    """North Carolina income tax - flat rate (2024)."""
    if filing_status in ("mfj", "qw"):
        std_ded = 25500
    elif filing_status == "hoh":
        std_ded = 19125
    else:
        std_ded = 12750

    income = max(taxable_income - std_ded, 0)
    return round(income * 0.045, 2)


def _arizona_tax(taxable_income: float, filing_status: str) -> float:
    """Arizona income tax - flat rate (2024)."""
    if filing_status in ("mfj", "qw"):
        std_ded = 29200
    elif filing_status == "hoh":
        std_ded = 21900
    else:
        std_ded = 14600

    income = max(taxable_income - std_ded, 0)
    return round(income * 0.025, 2)


def _colorado_tax(taxable_income: float, filing_status: str) -> float:
    """Colorado income tax - flat rate (2024). Based on federal taxable income."""
    return round(max(taxable_income, 0) * 0.044, 2)


# State calculation registry
STATE_CALCULATORS = {
    "CA": _california_tax,
    "NY": _new_york_tax,
    "TX": lambda ti, fs: 0.0,  # No income tax
    "FL": lambda ti, fs: 0.0,  # No income tax
    "WA": lambda ti, fs: 0.0,  # No income tax
    "IL": _illinois_tax,
    "NJ": _new_jersey_tax,
    "PA": _pennsylvania_tax,
    "OH": _ohio_tax,
    "GA": _georgia_tax,
    "NC": _north_carolina_tax,
    "AZ": _arizona_tax,
    "CO": _colorado_tax,
}

# States with no income tax
NO_INCOME_TAX_STATES = {"TX", "FL", "WA", "NV", "WY", "AK", "SD", "TN", "NH"}

# States where Social Security is exempt
SS_EXEMPT_STATES = {
    "CA", "NY", "TX", "FL", "WA", "IL", "NJ", "PA", "OH", "GA", "NC", "AZ",
    # Most states exempt SS
}


def calculate_state_tax(
    federal_taxable_income: float,
    filing_status: str,
    state: str,
    state_adjustment: float = 0,
    social_security_income: float = 0,
) -> dict:
    """
    Calculate state income tax.

    Args:
        federal_taxable_income: Federal taxable income (used as base for most states)
        filing_status: Filing status
        state: Two-letter state code
        state_adjustment: Manual adjustment for states not fully implemented
        social_security_income: SS income (some states exempt this)

    Returns dict with state tax info.
    """
    state = state.upper()

    if state in NO_INCOME_TAX_STATES and state not in STATE_CALCULATORS:
        return {
            "state": state,
            "state_tax": 0.0,
            "effective_state_rate": 0.0,
            "has_income_tax": False,
            "note": "No state income tax",
        }

    calculator = STATE_CALCULATORS.get(state)
    if calculator is None:
        # State not implemented - use manual adjustment
        return {
            "state": state,
            "state_tax": round(state_adjustment, 2),
            "effective_state_rate": 0.0,
            "has_income_tax": True,
            "note": f"State {state} not fully implemented. Using manual adjustment.",
        }

    # Adjust taxable income for state-specific exemptions
    adjusted_income = federal_taxable_income

    # Remove SS income for states that exempt it
    if state in SS_EXEMPT_STATES and social_security_income > 0:
        adjusted_income -= social_security_income

    adjusted_income += state_adjustment

    tax = calculator(adjusted_income, filing_status)

    effective_rate = 0.0
    if federal_taxable_income > 0:
        effective_rate = round((tax / federal_taxable_income) * 100, 2)

    return {
        "state": state,
        "state_tax": tax,
        "effective_state_rate": effective_rate,
        "has_income_tax": state not in NO_INCOME_TAX_STATES,
        "note": None,
    }


def get_supported_states() -> list:
    """Return list of supported states with their tax type."""
    states = []
    for code in sorted(STATE_CALCULATORS.keys()):
        if code in NO_INCOME_TAX_STATES:
            tax_type = "none"
        elif code in ("IL", "PA", "NC", "AZ", "CO"):
            tax_type = "flat"
        else:
            tax_type = "progressive"
        states.append({"code": code, "tax_type": tax_type})
    return states
