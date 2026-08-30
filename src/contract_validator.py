"""Simple contract validator used as the starter baseline.

The implementation intentionally covers only common deterministic checks.
Students are expected to extend it with:
- stronger type validation/coercion rules,
- freshness checks,
- cross-field/cross-table assertions,
- severity-aware actions (block/quarantine/warn),
- richer observability metadata.
"""
from __future__ import annotations

import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import yaml


def _issue(
    check: str,
    *,
    column: str | None,
    severity: str,
    passed: bool,
    details: str,
    action: str | None = None,
) -> dict[str, Any]:
    resolved_action = action or {
        "critical": "block",
        "warning": "warn",
        "info": "observe",
    }.get(severity, "warn")
    return {
        "check": check,
        "column": column,
        "severity": severity,
        "passed": bool(passed),
        "details": details,
        "action": resolved_action,
    }


def load_contract(path: str | Path) -> dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _type_failure_mask(series: pd.Series, declared_type: str) -> pd.Series:
    """Return a mask for non-null values that cannot honor a contract type."""
    non_null = series.notna()
    kind = declared_type.lower()
    if kind in {"integer", "int"}:
        numeric = pd.to_numeric(series, errors="coerce")
        return non_null & (
            numeric.isna()
            | ~numeric.map(
                lambda value: bool(
                    pd.notna(value) and math.isfinite(float(value)) and float(value).is_integer()
                )
            )
        )
    if kind in {"number", "numeric", "float"}:
        numeric = pd.to_numeric(series, errors="coerce")
        return non_null & (
            numeric.isna()
            | ~numeric.map(lambda value: bool(pd.notna(value) and math.isfinite(float(value))))
        )
    if kind in {"datetime", "timestamp"}:
        return non_null & pd.to_datetime(series, utc=True, errors="coerce").isna()
    if kind in {"boolean", "bool"}:
        accepted = {True, False, 0, 1, "0", "1", "true", "false", "True", "False"}
        return non_null & ~series.isin(accepted)
    if kind in {"string", "str"}:
        return non_null & ~series.map(lambda value: isinstance(value, str))
    return pd.Series(False, index=series.index)


def validate_dataframe(
    df: pd.DataFrame,
    contract: dict[str, Any],
    *,
    reference_time: datetime | pd.Timestamp | None = None,
) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    columns = contract.get("columns", contract.get("fields", {}))

    for column, rules in columns.items():
        severity = rules.get("severity", "warning")
        required = bool(rules.get("required", False))

        if column not in df.columns:
            if required:
                issues.append(
                    _issue(
                        "required_column",
                        column=column,
                        severity=severity,
                        passed=False,
                        details=f"Missing required column: {column}",
                    )
                )
            continue

        series = df[column]

        if required:
            null_count = int(series.isna().sum())
            issues.append(
                _issue(
                    "not_null",
                    column=column,
                    severity=severity,
                    passed=(null_count == 0),
                    details=f"null_count={null_count}",
                )
            )

        declared_type = rules.get("type")
        if declared_type:
            invalid_count = int(_type_failure_mask(series, str(declared_type)).sum())
            issues.append(
                _issue(
                    "type",
                    column=column,
                    severity=severity,
                    passed=(invalid_count == 0),
                    details=f"declared_type={declared_type}; invalid_count={invalid_count}",
                )
            )

        if rules.get("unique"):
            duplicate_count = int(series.duplicated(keep=False).sum())
            issues.append(
                _issue(
                    "unique",
                    column=column,
                    severity=severity,
                    passed=(duplicate_count == 0),
                    details=f"duplicate_rows={duplicate_count}",
                )
            )

        accepted = rules.get("accepted_values")
        if accepted is not None:
            invalid_mask = series.notna() & ~series.isin(accepted)
            invalid_count = int(invalid_mask.sum())
            issues.append(
                _issue(
                    "accepted_values",
                    column=column,
                    severity=severity,
                    passed=(invalid_count == 0),
                    details=f"invalid_count={invalid_count}; accepted={accepted}",
                )
            )

        # Starter numeric range support. Type validation is intentionally minimal.
        if "min" in rules or "max" in rules:
            numeric = pd.to_numeric(series, errors="coerce")
            invalid = series.notna() & numeric.isna()
            if "min" in rules:
                invalid |= numeric < rules["min"]
            if "max" in rules:
                invalid |= numeric > rules["max"]
            invalid_count = int(invalid.fillna(False).sum())
            issues.append(
                _issue(
                    "range",
                    column=column,
                    severity=severity,
                    passed=(invalid_count == 0),
                    details=f"invalid_count={invalid_count}",
                )
            )

        if "min_length" in rules:
            invalid = series.notna() & series.map(lambda value: len(str(value)) < int(rules["min_length"]))
            invalid_count = int(invalid.sum())
            issues.append(
                _issue(
                    "min_length",
                    column=column,
                    severity=severity,
                    passed=(invalid_count == 0),
                    details=f"invalid_count={invalid_count}; min_length={rules['min_length']}",
                )
            )

    freshness = contract.get("freshness")
    # Unit-test fixtures and historical snapshots are deterministic when no
    # reference is supplied. Production callers explicitly supply their clock.
    if freshness and reference_time is not None:
        column = freshness.get("column")
        severity = freshness.get("severity", "warning")
        max_delay = float(freshness["max_delay_minutes"])
        if column not in df.columns:
            issues.append(
                _issue(
                    "freshness",
                    column=column,
                    severity=severity,
                    passed=False,
                    details=f"Freshness column is missing: {column}",
                )
            )
        else:
            parsed = pd.to_datetime(df[column], utc=True, errors="coerce")
            latest = parsed.max()
            now = pd.Timestamp(reference_time)
            now = now.tz_localize("UTC") if now.tzinfo is None else now.tz_convert("UTC")
            age_minutes = float("inf") if pd.isna(latest) else (now - latest).total_seconds() / 60.0
            passed = bool(pd.notna(latest) and -5.0 <= age_minutes <= max_delay)
            issues.append(
                _issue(
                    "freshness",
                    column=column,
                    severity=severity,
                    passed=passed,
                    details=f"age_minutes={age_minutes:.3f}; max_delay_minutes={max_delay:.3f}",
                )
            )

    return issues


def validate_now(df: pd.DataFrame, contract: dict[str, Any]) -> list[dict[str, Any]]:
    """Validate a live batch, including wall-clock freshness."""
    return validate_dataframe(df, contract, reference_time=datetime.now(timezone.utc))


def failed_issues(issues: list[dict[str, Any]], min_severity: str | None = None) -> list[dict[str, Any]]:
    failed = [i for i in issues if not i.get("passed", False)]
    if min_severity is None:
        return failed
    order = {"info": 0, "warning": 1, "critical": 2}
    threshold = order[min_severity]
    return [i for i in failed if order.get(i.get("severity", "warning"), 1) >= threshold]
