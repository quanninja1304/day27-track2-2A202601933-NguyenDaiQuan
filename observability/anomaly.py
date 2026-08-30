"""Anomaly detection starter.

Z-score is deliberately the default baseline. Students should improve `auto`
mode for seasonality/outliers rather than deleting the simple implementation.
"""
from __future__ import annotations

from typing import Any, Iterable

import numpy as np


def _finite_values(history: Iterable[float]) -> np.ndarray:
    values = np.asarray(list(history), dtype=float)
    return values[np.isfinite(values)]


def zscore_detector(current: float, history: Iterable[float], threshold: float = 3.0) -> dict[str, Any]:
    values = _finite_values(history)
    if values.size < 3:
        return {"is_anomaly": False, "score": 0.0, "method": "zscore", "reason": "insufficient_history"}
    mean = float(np.mean(values))
    std = float(np.std(values))
    if std == 0:
        score = float("inf") if float(current) != mean else 0.0
    else:
        score = abs(float(current) - mean) / std
    return {
        "is_anomaly": bool(score > threshold),
        "score": float(score),
        "method": "zscore",
        "reason": f"mean={mean:.3f}, std={std:.3f}, threshold={threshold}",
    }


def mad_detector(current: float, history: Iterable[float], threshold: float = 3.5) -> dict[str, Any]:
    """Robust modified-z detector, including a deterministic zero-MAD case."""
    values = _finite_values(history)
    if values.size < 5:
        return {"is_anomaly": False, "score": 0.0, "method": "mad", "reason": "insufficient_history"}
    median = float(np.median(values))
    mad = float(np.median(np.abs(values - median)))
    if mad == 0:
        score = float("inf") if float(current) != median else 0.0
        return {
            "is_anomaly": bool(score > threshold),
            "score": score,
            "method": "mad",
            "reason": f"median={median:.3f}, mad=0, threshold={threshold}",
        }
    modified_z = 0.6745 * abs(float(current) - median) / mad
    return {
        "is_anomaly": bool(modified_z > threshold),
        "score": float(modified_z),
        "method": "mad",
        "reason": f"median={median:.3f}, mad={mad:.3f}, threshold={threshold}",
    }


def detect_anomaly(
    current: float,
    history: Iterable[float],
    *,
    method: str = "auto",
    threshold: float = 3.0,
    context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Stable lab API.

    Auto mode prefers a same-segment baseline and robust MAD statistics. A
    known event suppresses paging while retaining a scored observability event.
    """
    if method == "mad":
        return mad_detector(current, history)
    if method == "zscore":
        return zscore_detector(current, history, threshold=threshold)
    if method == "auto":
        context = context or {}
        segment = context.get("same_segment_history")
        selected = list(segment) if segment is not None else list(history)
        selected = _finite_values(selected).tolist()
        used_segment = segment is not None and len(selected) >= 3
        if segment is not None and not used_segment:
            selected = _finite_values(history).tolist()
        detector = "mad" if len(selected) >= 5 else "zscore"
        result = mad_detector(current, selected) if detector == "mad" else zscore_detector(current, selected, threshold=threshold)
        result["method"] = f"auto:{'same_segment:' if used_segment else ''}{detector}"
        result["reason"] += f"; metric={context.get('metric_name', 'unknown')}"
        if context.get("day_of_week") is not None:
            result["reason"] += f"; day_of_week={context['day_of_week']}"
        if context.get("known_event"):
            result["raw_is_anomaly"] = result["is_anomaly"]
            result["is_anomaly"] = False
            result["reason"] += f"; suppressed_known_event={context['known_event']}"
        return result
    raise ValueError(f"Unsupported method: {method}")
