"""Directional survey analysis — dogleg severity, tortuosity, landed position."""

import math


def compute_dls(
    inc1: float,
    az1: float,
    inc2: float,
    az2: float,
    delta_md_ft: float,
) -> float | None:
    """Compute Dogleg Severity in deg/100ft from two survey stations.

    DLS = arccos[cos(inc1)cos(inc2) + sin(inc1)sin(inc2)cos(az2−az1)] × 100/ΔMD
    """
    if delta_md_ft is None or delta_md_ft <= 0:
        return None
    inc1_r, inc2_r = math.radians(inc1), math.radians(inc2)
    az1_r, az2_r = math.radians(az1), math.radians(az2)
    cos_angle = math.cos(inc1_r) * math.cos(inc2_r) + math.sin(inc1_r) * math.sin(
        inc2_r
    ) * math.cos(az2_r - az1_r)
    cos_angle = max(-1.0, min(1.0, cos_angle))
    dogleg_rad = math.acos(cos_angle)
    return round(math.degrees(dogleg_rad) * 100.0 / delta_md_ft, 2)


def enrich_survey_with_dls(points: list[dict]) -> list[dict]:
    """Compute DLS for each station and annotate points in-place (new list)."""
    if not points:
        return []
    out = []
    prev = None
    for p in points:
        item = dict(p)
        if prev is not None:
            dls = compute_dls(
                prev["inclination_deg"],
                prev["azimuth_deg"],
                p["inclination_deg"],
                p["azimuth_deg"],
                p["md_ft"] - prev["md_ft"],
            )
            item["dls_deg_per_100ft"] = dls
        else:
            item["dls_deg_per_100ft"] = 0.0
        out.append(item)
        prev = item
    return out


def find_tortuosity_hotspots(
    survey_points: list[dict],
    threshold_dls: float = 3.0,
) -> list[dict]:
    """Flag lateral sections with DLS above threshold (micro-tortuosity).

    Returns hotspot entries with md and dls. Only flags points in the lateral
    (identified by inclination ≥ 70°, typical horizontal wells).
    """
    hotspots = []
    for p in survey_points:
        dls = p.get("dls_deg_per_100ft")
        inc = p.get("inclination_deg", 0)
        if dls is not None and dls > threshold_dls and inc >= 70:
            hotspots.append(
                {
                    "md_ft": p.get("md_ft"),
                    "tvd_ft": p.get("tvd_ft"),
                    "dls_deg_per_100ft": dls,
                    "note": (
                        f"High localized DLS {dls:.1f}°/100ft in lateral — "
                        "tubing wear / rod part / liner hang-up risk"
                    ),
                }
            )
    return hotspots


def max_dls_in_lateral(survey_points: list[dict]) -> float | None:
    """Maximum DLS within the lateral section."""
    lateral = [
        p["dls_deg_per_100ft"]
        for p in survey_points
        if p.get("inclination_deg", 0) >= 70 and p.get("dls_deg_per_100ft") is not None
    ]
    return max(lateral) if lateral else None


def check_landed_position(
    lateral_survey: list[dict],
    formation_tops: list[dict],
) -> dict | None:
    """Verify lateral landed position vs formation marker tops.

    Returns dict with landing assessment, or None if insufficient data.
    """
    if not lateral_survey or not formation_tops:
        return None
    # Use the average TVD of the lateral section
    lateral_tvds = [p["tvd_ft"] for p in lateral_survey if p.get("tvd_ft") is not None]
    if not lateral_tvds:
        return None
    avg_lateral_tvd = sum(lateral_tvds) / len(lateral_tvds)

    # Find target formation (deepest top with a bottom reference)
    # If we only have tops, use the deepest top as proxy target top
    target = max(formation_tops, key=lambda t: t.get("tvd_ft", 0) or 0)
    target_top_tvd = target.get("tvd_ft")

    if not target_top_tvd:
        return None

    # Assumption: lateral should sit within ~150ft below the target formation top
    # (typical lateral thickness/landing window)
    offset = avg_lateral_tvd - target_top_tvd
    if abs(offset) <= 150:
        assessment = "IN_ZONE"
        note = f"Lateral avg TVD {avg_lateral_tvd:.0f} ft within ~150 ft of {target.get('formation_name')} top ({target_top_tvd:.0f} ft)"
    elif offset > 150:
        assessment = "BELOW_TARGET"
        note = f"Lateral avg TVD {avg_lateral_tvd:.0f} ft is {offset:.0f} ft below target top — possible breach into water-bearing interval"
    else:
        assessment = "ABOVE_TARGET"
        note = f"Lateral avg TVD {avg_lateral_tvd:.0f} ft is above target — possible bounding shale"

    return {
        "avg_lateral_tvd_ft": round(avg_lateral_tvd, 1),
        "target_formation": target.get("formation_name"),
        "target_top_tvd_ft": target_top_tvd,
        "assessment": assessment,
        "note": note,
    }
