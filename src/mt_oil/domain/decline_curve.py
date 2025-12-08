import numpy as np
from scipy.optimize import curve_fit
from typing import Dict


def arps_decline(t: np.ndarray, qi: float, di: float, b: float) -> np.ndarray:
    """
    Standard Arps Decline Curve.
    q(t) = qi / (1 + b * di * t)^(1/b)
    """
    # handle b=0 case (exponential)
    if np.isclose(b, 0):
        return qi * np.exp(-di * t)
    return qi / np.power((1 + b * di * t), (1 / b))


def modified_arps_decline(
    t: np.ndarray, qi: float, di: float, b: float, d_lim: float = 0.06
) -> np.ndarray:
    """
    Modified Arps Decline. Switches to exponential decline when the decline rate reaches d_lim.
    """
    # Simply using Arps for now as a base.
    # True implementation requires calculating the switch point t_star.

    # Calculate current decline rate at time t: D(t) = Di / (1 + b * Di * t)
    # We want to find t where D(t) = d_lim

    # if b=0, decline is constant di.
    if np.isclose(b, 0):
        return qi * np.exp(-di * t)

    # If initial decline is less than limit, just use exponential (or arps, but effectively low decline)
    if di < d_lim:
        return arps_decline(t, qi, di, b)

    t_switch = (di / d_lim - 1) / (b * di)

    # q_switch at time t_switch
    q_switch = qi / np.power((1 + b * di * t_switch), (1 / b))

    # Arrays
    q = np.zeros_like(t, dtype=float)

    mask_hyp = t <= t_switch
    mask_exp = t > t_switch

    # Hyperbolic part
    q[mask_hyp] = arps_decline(t[mask_hyp], qi, di, b)

    # Exponential part
    # q(t) = q_switch * exp(-d_lim * (t - t_switch))
    q[mask_exp] = q_switch * np.exp(-d_lim * (t[mask_exp] - t_switch))

    return q


def duong_decline(t: np.ndarray, qi: float, a: float, m: float) -> np.ndarray:
    """
    Duong Decline for Unconventional Reservoirs.
    q(t) = qi * t^(-m) * exp(a / (1-m) * (t^(1-m) - 1))

    Simplified form often used: q(t) = q1 * t^(-m) * exp( a * (t^(1-m)-1)/(1-m) )
    Here we treat qi as the intercept parameter roughly.
    Note: Duong is usually for cumulative, but rate form exists.
    Common rate form: q = qi * t^-m * exp( a/(1-m) * (t^(1-m) - 1))
    """
    # Prevent division by zero or negative power issues
    t_safe = np.where(t < 1, 1, t)

    if np.isclose(m, 1):
        return qi * np.power(t_safe, -1.0)  # Harmonic-ish limit

    term1 = np.power(t_safe, -m)
    term2 = np.exp((a / (1 - m)) * (np.power(t_safe, 1 - m) - 1))

    return qi * term1 * term2


def fit_best_decline(
    time_months: np.ndarray, production: np.ndarray, method: str = "auto"
) -> Dict:
    """
    Fits decline curves to production data and returns the parameters of the best fit.

    Args:
        time_months: Array of time in months.
        production: Array of production rates.
        method: 'arps', 'modified_arps', 'duong', or 'auto'

    Returns:
        Dictionary containing 'method', 'parameters', 'score' (mse).
    """
    best_fit = {"method": None, "score": float("inf"), "params": []}

    # initial guesses
    qi_guess = np.max(production) if len(production) > 0 else 1000
    di_guess = 0.5
    b_guess = 1.2  # Typically > 1 for shale

    # 1. Arps / Modified Arps
    if method in ["arps", "modified_arps", "auto"]:
        try:
            # Bounds: qi > 0, 0 < di < 5, 0 <= b <= 2.5 (relaxed max b for shale)
            popt, _ = curve_fit(
                arps_decline,
                time_months,
                production,
                p0=[qi_guess, di_guess, b_guess],
                bounds=([0, 0, 0], [np.inf, 10, 3]),
                maxfev=2000,
            )

            # Predict
            pred = arps_decline(time_months, *popt)
            mse = np.mean((production - pred) ** 2)

            if mse < best_fit["score"]:
                best_fit = {
                    "method": "arps",
                    "score": mse,
                    "params": {"qi": popt[0], "di": popt[1], "b": popt[2]},
                    "prediction": pred,  # for debug/plot
                }
        except Exception:
            pass  # Fit failed

    # 2. Duong
    if method in ["duong", "auto"]:
        try:
            # qi, a, m
            # Duong params are sensitive.
            # m typically 1.1 to 1.3 for shale logic slightly different,
            # standard Duong m is slope on log-log q/Gp plot.
            # Let's try basic bounds.
            popt, _ = curve_fit(
                duong_decline,
                time_months,
                production,
                p0=[qi_guess, 1.0, 1.1],
                bounds=([0, 0, 0.5], [np.inf, 10, 2.0]),
                maxfev=2000,
            )

            pred = duong_decline(time_months, *popt)
            mse = np.mean((production - pred) ** 2)

            if mse < best_fit["score"]:
                best_fit = {
                    "method": "duong",
                    "score": mse,
                    "params": {"qi": popt[0], "a": popt[1], "m": popt[2]},
                    "prediction": pred,
                }
        except Exception:
            pass

    return best_fit
