"""Coordinate Reference System transformations — NAD27→NAD83, UTM projection, projected distance.

Supports hardening the spatial engine against mixed-datum points in Montana public records.
"""

import math

# ---------------------------------------------------------------------------
# NAD27 ↔ NAD83 datum shift (Molodensky simplified)
# Standard CONUS parameters for NAD27 (Clarke 1866) → NAD83 (GRS80)
# ---------------------------------------------------------------------------

# Clarke 1866 ellipsoid (NAD27)
NAD27_A = 6378206.4  # semi-major axis (m)
NAD27_F = 1.0 / 294.9786982  # flattening

# GRS80 ellipsoid (NAD83 / WGS84)
NAD83_A = 6378137.0  # semi-major axis (m)
NAD83_F = 1.0 / 298.257222101  # flattening

# Molodensky shifts (meters) for CONUS NAD27→NAD83
# ΔX = -8m, ΔY = +160m, ΔZ = +176m (average CONUS)
_DX = -8.0
_DY = 160.0
_DZ = 176.0

# ---------------------------------------------------------------------------
# UTM Zone 13N constants (Montana State Plane / UTM Zone 13)
# Central meridian: 105°W (zone 13 = -105 + 0 for West)
# ---------------------------------------------------------------------------
UTM_A = 6378137.0  # WGS84 semi-major (m)
UTM_F = 1.0 / 298.257223563  # WGS84 flattening
UTM_K0 = 0.9996  # scale factor
UTM_E = math.sqrt(2 * UTM_F - UTM_F**2)  # eccentricity


def _deg_to_rad(deg: float) -> float:
    return deg * math.pi / 180.0


def _rad_to_deg(rad: float) -> float:
    return rad * 180.0 / math.pi


def _clarke66_to_grs80(
    lat: float, lon: float, h: float = 0.0
) -> tuple[float, float, float]:
    """Molodensky transform from Clarke 1866 (NAD27) to GRS80/WGS84 (NAD83).

    Returns (lat_deg, lon_deg, h_meters) in WGS84.
    """
    phi = _deg_to_rad(lat)
    lam = _deg_to_rad(lon)

    # Clarke 1866 first eccentricity
    e2_nad27 = 2 * NAD27_F - NAD27_F**2
    2 * NAD83_F - NAD83_F**2

    # Prime vertical radius of curvature
    sin_phi = math.sin(phi)
    cos_phi = math.cos(phi)
    Rn_nad27 = NAD27_A / math.sqrt(1 - e2_nad27 * sin_phi**2)

    # Molodensky (abridged)
    da = NAD83_A - NAD27_A
    df = NAD83_F - NAD27_F

    dlat_rad = (
        -_DX * sin_phi * cos_phi
        - _DY * sin_phi * cos_phi * math.sin(lam)
        + _DZ * cos_phi * cos_phi
        + da * (Rn_nad27 * e2_nad27 * sin_phi * cos_phi) / NAD27_A
        + df
        * (Rn_nad27 * (1 / (1 - e2_nad27 * sin_phi**2)) + Rn_nad27)
        * sin_phi
        * cos_phi
    ) / (Rn_nad27 + h)

    dlon_rad = (-_DX * math.sin(lam) + _DY * math.cos(lam)) / ((Rn_nad27 + h) * cos_phi)

    lat_wgs84 = _rad_to_deg(phi + dlat_rad)
    lon_wgs84 = _rad_to_deg(lam + dlon_rad)

    return lat_wgs84, lon_wgs84, h


def infer_datum_row(spud_date: str | None) -> str:
    """Infer the likely coordinate datum from spud date.

    Pre-1990 → likely NAD27 (Clarke 1866)
    1990+ → likely NAD83/WGS84
    Unknown → assume WGS84
    """
    if spud_date is None:
        return "wgs84_assumed"
    try:
        year = int(spud_date[:4])
        return "nad27" if year < 1990 else "nad83_wgs84"
    except (ValueError, TypeError, IndexError):
        return "wgs84_assumed"


def nad27_to_nad83(lat: float, lon: float) -> tuple[float, float]:
    """Convert NAD27 (Clarke 1866) lat/lon to NAD83/WGS84 lat/lon."""
    lat83, lon83, _ = _clarke66_to_grs80(lat, lon)
    return lat83, lon83


def to_utm13n(lat_wgs84: float, lon_wgs84: float) -> tuple[float, float]:
    """Convert WGS84 lat/lon to UTM Zone 13N (meters).

    Returns (easting_m, northing_m).
    """
    phi = _deg_to_rad(lat_wgs84)
    lam = _deg_to_rad(lon_wgs84)

    # UTM parameters
    e2 = 2 * UTM_F - UTM_F**2  # first eccentricity²
    e_prime2 = e2 / (1 - e2)  # second eccentricity²

    # Central meridian of Zone 13 = 105°W = -105° longitude
    lon0 = _deg_to_rad(-105.0)
    dlam = lam - lon0

    # Meridian distance
    n = UTM_F / (2 - UTM_F)
    a0 = 1 + (n**2) / 4 + (n**4) / 64
    a2 = 3 / 2 * (n - n**3 / 8)
    a4 = 15 / 16 * (n**2 - n**4 / 4)
    a6 = 35 * n**3 / 48
    a8 = 315 * n**4 / 512

    # Meridian arc
    s = (
        UTM_A
        * (1 - e2)
        * (
            a0 * phi
            - a2 * math.sin(2 * phi) / 2
            + a4 * math.sin(4 * phi) / 4
            - a6 * math.sin(6 * phi) / 6
            + a8 * math.sin(8 * phi) / 8
        )
    )

    # Projection equations
    sin_phi = math.sin(phi)
    cos_phi = math.cos(phi)
    tan_phi = math.tan(phi)

    t = tan_phi**2
    c = e_prime2 * cos_phi**2
    a = dlam * cos_phi
    a2_val = a * a

    nu = UTM_A / math.sqrt(1 - e2 * sin_phi**2)

    # Easting
    easting = (
        UTM_K0
        * nu
        * (
            a
            + (1 - t + c) * a2_val * a / 6
            + (5 - 18 * t + t**2 + 72 * c - 58 * e_prime2) * a2_val * a2_val * a / 120
        )
    )

    # Northing
    northing = UTM_K0 * (
        s
        + nu
        * tan_phi
        * (
            a2_val / 2
            + (5 - t + 9 * c + 4 * c**2) * a2_val * a2_val / 24
            + (61 - 58 * t + t**2 + 600 * c - 330 * e_prime2)
            * a2_val
            * a2_val
            * a2_val
            / 720
        )
    )

    # 500,000 m false easting, 0 m false northing (Northern hemisphere)
    easting += 500000.0
    if northing < 0:
        northing += 10000000.0  # Southern hemisphere

    return easting, northing


def projected_distance(
    lat1: float,
    lon1: float,
    lat2: float,
    lon2: float,
    datum1: str = "wgs84_assumed",
    datum2: str = "wgs84_assumed",
) -> tuple[float, str]:
    """Compute projected 2D distance between two points with datum handling.

    Returns (distance_m, method) where method describes the projection used.
    Points are normalized to WGS84, projected to UTM Zone 13N, then Euclidean.
    """
    # Normalize to WGS84
    lat1_wgs, lon1_wgs = _to_wgs84(lat1, lon1, datum1)
    lat2_wgs, lon2_wgs = _to_wgs84(lat2, lon2, datum2)

    # Project to UTM Zone 13N
    e1, n1 = to_utm13n(lat1_wgs, lon1_wgs)
    e2, n2 = to_utm13n(lat2_wgs, lon2_wgs)

    # Euclidean distance
    de = e2 - e1
    dn = n2 - n1
    dist_m = math.sqrt(de * de + dn * dn)

    method = "utm13n_projected"
    if datum1 != datum2:
        method += "_mixed_datum"
    return dist_m, method


def _to_wgs84(lat: float, lon: float, datum: str) -> tuple[float, float]:
    """Convert a point to WGS84 lat/lon based on its datum tag."""
    if datum in ("nad27", "NAD27"):
        return nad27_to_nad83(lat, lon)
    # NAD83 and WGS84 are effectively equivalent for our purposes
    return lat, lon


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Haversine distance in meters (spherical Earth). Kept as fallback."""
    R = 6371000.0
    dphi = _deg_to_rad(lat2 - lat1)
    dlambda = _deg_to_rad(lon2 - lon1)
    a = (
        math.sin(dphi / 2) ** 2
        + math.cos(_deg_to_rad(lat1))
        * math.cos(_deg_to_rad(lat2))
        * math.sin(dlambda / 2) ** 2
    )
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
