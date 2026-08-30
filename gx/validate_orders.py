#!/usr/bin/env python3
"""Production-shaped GX validation flow for the orders batch."""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

try:
    import great_expectations as gx
    from great_expectations.checkpoint import ValidationAction
except ImportError as exc:
    raise SystemExit("Run `uv sync --python 3.13` before the GX workflow.") from exc

from src.contract_validator import failed_issues, load_contract, validate_now


class LocalSeverityAction(ValidationAction):
    """Fast local Checkpoint Action that records the highest failed severity."""

    type: Literal["local_severity"] = "local_severity"

    def run(self, checkpoint_result: object, action_context: object | None = None) -> dict:
        severity = self._get_max_severity_failure_from_checkpoint_result(checkpoint_result)
        return {"max_failed_severity": severity.name.lower() if severity else None}


def build_checkpoint(context: object) -> object:
    """Create the Suite → ValidationDefinition → Checkpoint graph."""
    data_source = context.data_sources.add_pandas("orders_pandas")
    asset = data_source.add_dataframe_asset(name="orders_dataframe")
    batch_definition = asset.add_batch_definition_whole_dataframe("whole_orders")

    suite = context.suites.add(gx.ExpectationSuite(name="orders_contract_suite"))
    expectations = [
        gx.expectations.ExpectColumnValuesToNotBeNull(column="order_id", severity="critical"),
        gx.expectations.ExpectColumnValuesToBeUnique(column="order_id", severity="critical"),
        gx.expectations.ExpectColumnValuesToNotBeNull(column="customer_id", severity="critical"),
        gx.expectations.ExpectColumnValuesToNotBeNull(column="amount", severity="critical"),
        gx.expectations.ExpectColumnValuesToBeBetween(column="amount", min_value=0, severity="critical"),
        gx.expectations.ExpectColumnValuesToBeInSet(
            column="currency", value_set=["USD", "VND"], severity="critical"
        ),
        gx.expectations.ExpectColumnValuesToBeInSet(
            column="status",
            value_set=["pending", "completed", "refunded", "cancelled"],
            severity="warning",
        ),
    ]
    for expectation in expectations:
        suite.add_expectation(expectation)

    definition = context.validation_definitions.add(
        gx.ValidationDefinition(
            name="orders_validation_definition",
            data=batch_definition,
            suite=suite,
        )
    )
    checkpoint = gx.Checkpoint(
        name="orders_checkpoint",
        validation_definitions=[definition],
        actions=[LocalSeverityAction(name="classify_contract_failure")],
        result_format={"result_format": "SUMMARY"},
    )
    return context.checkpoints.add(checkpoint)


def main() -> int:
    df = pd.read_csv(ROOT / "data" / "incoming" / "orders.csv")
    context = gx.get_context(mode="ephemeral")
    checkpoint = build_checkpoint(context)
    checkpoint_result = checkpoint.run(batch_parameters={"dataframe": df})

    contract = load_contract(ROOT / "contracts" / "orders_contract.yaml")
    failures = failed_issues(validate_now(df, contract))
    critical = [failure for failure in failures if failure["severity"] == "critical"]
    action = "block_and_quarantine" if critical else ("warn" if failures else "proceed")

    evidence = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "gx_success": bool(checkpoint_result.success),
        "action": action,
        "failed_checks": failures,
    }
    report_path = ROOT / "reports" / "gx_latest.json"
    report_path.write_text(json.dumps(evidence, indent=2), encoding="utf-8")

    if critical:
        quarantine = ROOT / "reports" / "quarantine"
        quarantine.mkdir(parents=True, exist_ok=True)
        df.to_csv(quarantine / "orders_rejected.csv", index=False)

    print(f"GX checkpoint success : {checkpoint_result.success}")
    print(f"Severity action       : {action}")
    print(f"Evidence              : {report_path.relative_to(ROOT)}")
    return 0 if not critical else 1


if __name__ == "__main__":
    raise SystemExit(main())
