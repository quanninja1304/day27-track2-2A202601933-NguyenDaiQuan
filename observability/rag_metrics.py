from __future__ import annotations

from typing import Any, Iterable

import numpy as np

from observability.anomaly import zscore_detector
from observability.distribution import detect_distribution_shift


def approximate_token_lengths(texts: Iterable[str]) -> list[int]:
    # Deliberately simple proxy; no tokenizer/model download needed.
    return [len(str(t).split()) for t in texts]


def detect_text_length_shift(
    current_texts: Iterable[str],
    baseline_batch_means: Iterable[float],
    *,
    threshold: float = 3.0,
) -> dict[str, Any]:
    lengths = approximate_token_lengths(current_texts)
    current_mean = float(np.mean(lengths)) if lengths else 0.0
    result = zscore_detector(current_mean, baseline_batch_means, threshold=threshold)
    result["metric"] = "mean_text_length"
    result["current_mean"] = current_mean
    return result


def detect_embedding_norm_shift(
    current_norms: Iterable[float], baseline_norms: Iterable[float]
) -> dict[str, Any]:
    """Detect changes in precomputed embedding norms without loading a model."""
    current = list(current_norms)
    baseline = list(baseline_norms)
    if not current or not baseline:
        return {"is_anomaly": False, "score": 0.0, "method": "embedding_norm", "reason": "empty_input"}
    distribution = detect_distribution_shift(current, baseline, ratio_threshold=1.5)
    mean_signal = zscore_detector(float(np.mean(current)), baseline, threshold=3.0)
    use_mean = mean_signal["is_anomaly"] and mean_signal["score"] >= distribution["score"]
    chosen = mean_signal if use_mean else distribution
    return {
        "is_anomaly": bool(distribution["is_anomaly"] or mean_signal["is_anomaly"]),
        "score": float(max(distribution["score"], mean_signal["score"])),
        "method": "embedding_norm:zscore" if use_mean else "embedding_norm:ks",
        "reason": chosen["reason"],
        "current_mean": float(np.mean(current)),
        "baseline_mean": float(np.mean(baseline)),
    }
