"""IRMAA (Income-Related Monthly Adjustment Amount) for Medicare Parts B and D."""

from typing import Dict, List, Tuple, Optional

from .brackets import SINGLE, MFJ, MFS, HOH, QW

# IRMAA tiers: (magi_threshold, monthly_part_b_surcharge, monthly_part_d_surcharge)
# 2025 values (based on 2023 MAGI with 2-year lookback)
# Standard Part B premium for 2025: $185.00/month
IRMAA_TIERS: Dict[int, Dict[str, List[Tuple[float, float, float]]]] = {
    2023: {
        # Based on 2021 MAGI
        SINGLE: [
            (97000, 0, 0),        # Tier 0: no surcharge
            (123000, 65.90, 12.20),   # Tier 1
            (153000, 164.80, 31.50),  # Tier 2
            (183000, 263.70, 50.70),  # Tier 3
            (500000, 362.60, 70.00),  # Tier 4
            (float("inf"), 395.60, 76.40),  # Tier 5
        ],
        MFJ: [
            (194000, 0, 0),
            (246000, 65.90, 12.20),
            (306000, 164.80, 31.50),
            (366000, 263.70, 50.70),
            (750000, 362.60, 70.00),
            (float("inf"), 395.60, 76.40),
        ],
    },
    2024: {
        SINGLE: [
            (103000, 0, 0),
            (129000, 69.90, 12.90),
            (161000, 174.70, 33.30),
            (193000, 279.50, 53.80),
            (500000, 384.30, 74.20),
            (float("inf"), 418.50, 81.00),
        ],
        MFJ: [
            (206000, 0, 0),
            (258000, 69.90, 12.90),
            (322000, 174.70, 33.30),
            (386000, 279.50, 53.80),
            (750000, 384.30, 74.20),
            (float("inf"), 418.50, 81.00),
        ],
    },
    2025: {
        SINGLE: [
            (106000, 0, 0),
            (133000, 74.00, 13.70),
            (167000, 185.00, 35.30),
            (200000, 295.90, 57.00),
            (500000, 406.90, 78.60),
            (float("inf"), 443.90, 85.80),
        ],
        MFJ: [
            (212000, 0, 0),
            (266000, 74.00, 13.70),
            (334000, 185.00, 35.30),
            (400000, 295.90, 57.00),
            (750000, 406.90, 78.60),
            (float("inf"), 443.90, 85.80),
        ],
    },
}

# Map HOH and QW to use SINGLE thresholds, MFS uses SINGLE thresholds
for year in IRMAA_TIERS:
    if SINGLE in IRMAA_TIERS[year]:
        IRMAA_TIERS[year][HOH] = IRMAA_TIERS[year][SINGLE]
        IRMAA_TIERS[year][QW] = IRMAA_TIERS[year][SINGLE]  # QW typically uses MFJ but after death year uses single
        IRMAA_TIERS[year][MFS] = IRMAA_TIERS[year][SINGLE]


def get_irmaa_tier(
    magi: float,
    tax_year: int,
    filing_status: str,
) -> dict:
    """
    Determine IRMAA tier and annual surcharge.

    Note: IRMAA uses MAGI from 2 years prior. The tax_year parameter
    should be the IRMAA assessment year, and magi should be from 2 years before.

    Returns dict with tier info.
    """
    tiers = IRMAA_TIERS.get(tax_year, IRMAA_TIERS[2025])

    # Use MFJ tiers for QW in most cases
    status_key = filing_status
    if status_key not in tiers:
        status_key = SINGLE

    tier_list = tiers[status_key]

    for i, (threshold, part_b_monthly, part_d_monthly) in enumerate(tier_list):
        if magi <= threshold:
            annual_part_b = round(part_b_monthly * 12, 2)
            annual_part_d = round(part_d_monthly * 12, 2)
            return {
                "tier": i,
                "magi_threshold": threshold,
                "monthly_part_b_surcharge": part_b_monthly,
                "monthly_part_d_surcharge": part_d_monthly,
                "annual_part_b_surcharge": annual_part_b,
                "annual_part_d_surcharge": annual_part_d,
                "annual_total_surcharge": round(annual_part_b + annual_part_d, 2),
            }

    # Should not reach here due to inf threshold, but just in case
    last = tier_list[-1]
    return {
        "tier": len(tier_list) - 1,
        "magi_threshold": last[0],
        "monthly_part_b_surcharge": last[1],
        "monthly_part_d_surcharge": last[2],
        "annual_part_b_surcharge": round(last[1] * 12, 2),
        "annual_part_d_surcharge": round(last[2] * 12, 2),
        "annual_total_surcharge": round((last[1] + last[2]) * 12, 2),
    }


def get_irmaa_breakpoints(tax_year: int, filing_status: str) -> List[dict]:
    """Return all IRMAA breakpoints for the given year and filing status."""
    tiers = IRMAA_TIERS.get(tax_year, IRMAA_TIERS[2025])
    status_key = filing_status if filing_status in tiers else SINGLE
    tier_list = tiers[status_key]

    result = []
    for i, (threshold, part_b, part_d) in enumerate(tier_list):
        if threshold == float("inf"):
            continue
        result.append({
            "tier": i,
            "magi_threshold": threshold,
            "monthly_part_b_surcharge": part_b,
            "monthly_part_d_surcharge": part_d,
            "annual_total_surcharge": round((part_b + part_d) * 12, 2),
        })
    return result


def distance_to_next_irmaa_tier(
    magi: float,
    tax_year: int,
    filing_status: str,
) -> Optional[dict]:
    """Calculate distance to the next IRMAA tier threshold."""
    tiers = IRMAA_TIERS.get(tax_year, IRMAA_TIERS[2025])
    status_key = filing_status if filing_status in tiers else SINGLE
    tier_list = tiers[status_key]

    for i, (threshold, part_b, part_d) in enumerate(tier_list):
        if magi <= threshold and threshold != float("inf"):
            # Find the next tier
            if i + 1 < len(tier_list):
                next_threshold = tier_list[i + 1][0] if tier_list[i + 1][0] != float("inf") else tier_list[i][0]
                return {
                    "current_tier": i,
                    "next_tier": i + 1,
                    "next_threshold": threshold + 1,  # crossing the current threshold puts you in next tier
                    "distance": round(threshold - magi, 2),
                    "next_annual_surcharge": round((tier_list[i + 1][1] + tier_list[i + 1][2]) * 12, 2) if i + 1 < len(tier_list) else 0,
                }
            break

    return None
