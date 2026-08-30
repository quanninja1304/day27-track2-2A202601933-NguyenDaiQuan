from __future__ import annotations

from typing import Any


def calculate_slo(target: float, bad_events: int, total_events: int) -> dict[str, Any]:
    if not 0 < target < 1:
        raise ValueError("target must be between 0 and 1 (exclusive)")
    if bad_events < 0 or total_events < 0 or bad_events > total_events:
        raise ValueError("invalid event counts")
    allowed_bad_rate = 1.0 - target
    if total_events == 0:
        return {
            "target": target,
            "actual_bad_rate": 0.0,
            "allowed_bad_rate": allowed_bad_rate,
            "burn_rate": 0.0,
            "remaining_error_budget_fraction": 1.0,
            "breached": False,
        }
    actual_bad_rate = bad_events / total_events
    burn_rate = actual_bad_rate / allowed_bad_rate
    consumed_fraction = min(1.0, actual_bad_rate / allowed_bad_rate)
    return {
        "target": target,
        "actual_bad_rate": actual_bad_rate,
        "allowed_bad_rate": allowed_bad_rate,
        "burn_rate": burn_rate,
        "remaining_error_budget_fraction": max(0.0, 1.0 - consumed_fraction),
        "breached": bool(actual_bad_rate > allowed_bad_rate),
    }


def evaluate_multiwindow_burn(
    *,
    short_window_burn: float,
    long_window_burn: float,
    policy: str = "google_sre",
) -> dict[str, Any]:
    """Evaluate paired burn windows and reject short transient spikes.

    The thresholds mirror the useful shape of the Google SRE policy: both a
    fast and a sustained signal must agree before paging.
    """
    if short_window_burn < 0 or long_window_burn < 0:
        raise ValueError("burn rates must be non-negative")
    if short_window_burn >= 14.4 and long_window_burn >= 6.0:
        page, severity, reason = True, "critical", "sustained_fast_burn"
    elif short_window_burn >= 6.0 and long_window_burn >= 3.0:
        page, severity, reason = True, "warning", "sustained_elevated_burn"
    elif short_window_burn >= 6.0:
        page, severity, reason = False, "info", "transient_short_window_spike"
    else:
        page, severity, reason = False, "info", "within_burn_policy"
    return {
        "page": page,
        "severity": severity,
        "reason": reason,
        "policy": policy,
        "short_window_burn": short_window_burn,
        "long_window_burn": long_window_burn,
    }
