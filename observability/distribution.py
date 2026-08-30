from __future__ import annotations

from typing import Any, Iterable

import numpy as np


def detect_distribution_shift(
    current_values: Iterable[float],
    baseline_values: Iterable[float],
    *,
    ratio_threshold: float = 3.0,
) -> dict[str, Any]:
    """Two-sample Kolmogorov-Smirnov detector without a SciPy dependency.

    ``score`` is normalized by the approximate 5% critical value, so values at
    or above 1 indicate drift. A mean-ratio guard remains useful for tiny
    samples where an empirical CDF test has little power.
    """
    cur = np.asarray(list(current_values), dtype=float)
    base = np.asarray(list(baseline_values), dtype=float)
    cur = cur[np.isfinite(cur)]
    base = base[np.isfinite(base)]
    if cur.size == 0 or base.size == 0:
        return {"is_anomaly": False, "score": 0.0, "method": "ks+mean_ratio", "reason": "empty_input"}
    cur_mean = float(np.mean(cur))
    base_mean = float(np.mean(base))
    if base_mean == 0:
        mean_ratio = float("inf") if cur_mean != 0 else 1.0
    else:
        mean_ratio = max(abs(cur_mean / base_mean), abs(base_mean / cur_mean)) if cur_mean != 0 else float("inf")

    support = np.sort(np.unique(np.concatenate([cur, base])))
    cur_cdf = np.searchsorted(np.sort(cur), support, side="right") / cur.size
    base_cdf = np.searchsorted(np.sort(base), support, side="right") / base.size
    ks_distance = float(np.max(np.abs(cur_cdf - base_cdf)))
    critical = 1.36 * float(np.sqrt((cur.size + base.size) / (cur.size * base.size)))
    normalized_ks = ks_distance / critical if critical else 0.0
    is_anomaly = normalized_ks >= 1.0 or mean_ratio >= ratio_threshold
    score = max(normalized_ks, mean_ratio / ratio_threshold)
    return {
        "is_anomaly": bool(is_anomaly),
        "score": float(score),
        "method": "ks+mean_ratio",
        "reason": (
            f"ks_distance={ks_distance:.4f}, ks_critical={critical:.4f}, "
            f"mean_ratio={mean_ratio:.4f}, ratio_threshold={ratio_threshold:.4f}; "
            f"baseline_mean={base_mean:.3f}, current_mean={cur_mean:.3f}"
        ),
    }
