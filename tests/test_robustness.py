from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

from student_api import (
    column_downstream,
    detect_distribution,
    detect_metric,
    multiwindow_burn,
    rag_embedding_shift,
    validate_orders,
)
from src.contract_validator import load_contract, validate_dataframe

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts" / "orders_contract.yaml"


def order_frame(updated_at: datetime | None = None) -> pd.DataFrame:
    updated = updated_at or datetime.now(timezone.utc)
    frame = pd.DataFrame(
        [
            {
                "order_id": 1,
                "customer_id": "C1",
                "amount": 10.0,
                "currency": "USD",
                "status": "completed",
                "created_at": updated - timedelta(minutes=5),
                "updated_at": updated,
            }
        ]
    )
    frame.attrs["reference_time"] = datetime.now(timezone.utc)
    return frame


def failures(frame: pd.DataFrame) -> list[dict]:
    return [result for result in validate_orders(frame, CONTRACT) if not result["passed"]]


def test_type_drift_and_unparseable_range_are_detected() -> None:
    frame = order_frame()
    frame["amount"] = frame["amount"].astype(object)
    frame.loc[0, "amount"] = "ten"
    checks = failures(frame)
    assert any(result["check"] == "type" and result["column"] == "amount" for result in checks)
    assert any(result["check"] == "range" and result["column"] == "amount" for result in checks)


def test_live_freshness_and_action_are_enforced() -> None:
    frame = order_frame(datetime.now(timezone.utc) - timedelta(hours=2))
    checks = failures(frame)
    freshness = next(result for result in checks if result["check"] == "freshness")
    assert freshness["severity"] == "warning"
    assert freshness["action"] == "warn"


def test_auto_uses_same_weekday_and_suppresses_known_event() -> None:
    weekday = [245, 255, 250, 248, 252, 251, 249]
    assert detect_metric(
        250,
        [600] * 20,
        method="auto",
        context={"day_of_week": 5, "same_segment_history": weekday},
    )["is_anomaly"] is False
    suppressed = detect_metric(
        50,
        weekday,
        method="auto",
        context={"known_event": "planned_maintenance"},
    )
    assert suppressed["is_anomaly"] is False
    assert suppressed["raw_is_anomaly"] is True


def test_zero_mad_change_is_anomaly() -> None:
    assert detect_metric(1, [10] * 7, method="mad")["is_anomaly"] is True


def test_distribution_shape_shift_with_similar_mean() -> None:
    baseline = [0.0] * 50 + [10.0] * 50
    current = [4.9] * 50 + [5.1] * 50
    assert detect_distribution(current, baseline)["is_anomaly"] is True


def test_multiwindow_requires_sustained_burn() -> None:
    assert multiwindow_burn(15.0, 7.0)["page"] is True
    assert multiwindow_burn(15.0, 1.0)["page"] is False


def test_column_lineage_is_transitive_and_cycle_safe() -> None:
    graph = {"a.x": ["b.x"], "b.x": ["c.x"], "c.x": ["a.x"]}
    assert column_downstream(graph, "a.x") == ["b.x", "c.x"]


def test_embedding_norm_shift() -> None:
    baseline = [0.98, 1.0, 1.01, 0.99, 1.02, 1.0, 0.97]
    assert rag_embedding_shift([2.0, 2.1, 1.9, 2.05], baseline)["is_anomaly"] is True


def test_stale_kb_fault_violates_freshness_contract() -> None:
    now = datetime.now(timezone.utc)
    docs = [
        {
            "doc_id": "refund",
            "version": 1,
            "effective_at": now - timedelta(days=1),
            "published_at": now - timedelta(hours=3),
            "source_uri": "policy/refund.pdf",
            "content": "Refund policy content long enough for the contract.",
        }
    ]
    issues = validate_dataframe(
        pd.DataFrame(docs),
        load_contract(ROOT / "contracts" / "kb_contract.yaml"),
        reference_time=now,
    )
    assert any(issue["check"] == "freshness" and not issue["passed"] for issue in issues)
