"""Flowback dynamics — load recovery efficiency and solids ingress."""


def load_recovery_pct(
    load_fluid_recovered_bbls: float, fluid_pumped_bbls: float
) -> float | None:
    """Percent of pumped fracturing fluid returned before stabilization."""
    if fluid_pumped_bbls is None or fluid_pumped_bbls <= 0:
        return None
    return round(load_fluid_recovered_bbls / fluid_pumped_bbls * 100.0, 1)


def assess_load_recovery(recovery_pct: float | None) -> dict:
    """Classify load recovery efficiency."""
    if recovery_pct is None:
        return {
            "risk": "UNKNOWN",
            "message": "No recovery data — cannot assess load recovery",
        }
    if recovery_pct < 15:
        return {
            "risk": "HIGH",
            "message": (
                f"Load recovery {recovery_pct:.0f}% < 15% — fluid trapped in un-energized "
                "fracture network or under-pressured matrix with high capillary end effects"
            ),
        }
    if recovery_pct < 20:
        return {
            "risk": "MODERATE",
            "message": f"Load recovery {recovery_pct:.0f}% in 15–20% marginal range",
        }
    return {
        "risk": "LOW",
        "message": f"Load recovery {recovery_pct:.0f}% within acceptable range",
    }


def classify_proppant_flowback(solids_flowback: list[dict]) -> list[dict]:
    """Classify proppant flowback events (poor closure / resin / overflush).

    solids_flowback: list of dicts with 'volume_bbls' and 'mesh_size'.
    Returns categorized risks.
    """
    results = []
    for s in solids_flowback:
        vol = s.get("volume_bbls") or 0
        mesh = s.get("mesh_size") or ""
        risk = "LOW"
        if vol > 5:
            risk = "HIGH"
        elif vol > 1:
            risk = "MODERATE"
        results.append(
            {
                "volume_bbls": vol,
                "mesh_size": mesh,
                "risk": risk,
                "note": (
                    "Excessive proppant flowback — poor closure stress or inadequate resin curing"
                    if risk == "HIGH"
                    else "Minor proppant flowback"
                ),
            }
        )
    return results
