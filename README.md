# Lab 27 — Data Reliability Game Day

**Chủ đề:** Data Observability, Data Contracts, dbt Testing, Anomaly Detection, Lineage, SLO và Incident Response  
**Thời lượng gợi ý:** 120 phút  
**Hình thức:** nhóm 2–4 học viên  
**Chi phí:** $0 — chạy local  
**AI coding agent:** được phép và khuyến khích, nhưng phải verify output.

## 1. Scenario

Bạn là **Data/AI Reliability Team** của một công ty e-commerce. Pipeline vẫn báo `SUCCESS`, nhưng CEO thấy revenue giảm bất thường và Support Agent trả policy refund cũ.

Mục tiêu của nhóm:

> **Detect → Triage → Find Root Cause → Determine Blast Radius → Mitigate → Verify Recovery**

Kiến trúc lab:

```text
orders/customers ----------------------+
                                       |
                                       v
                                Data contracts
                                       |
                                       v
                                  dbt models
                                       |
                         +-------------+-------------+
                         |                           |
                         v                           v
                fct_daily_revenue              CEO dashboard

kb_documents -> validation -> active KB -> RAG/Support Agent

Across the pipeline: metrics -> anomaly -> lineage -> SLO -> incident response
```

## 2. Quick start

Yêu cầu: **Python 3.10–3.13**. Docker không bắt buộc.

Repo dùng **uv** để khóa dependency và tự chọn Python tương thích:

```bash
uv sync --python 3.13
uv run python scripts/reset_lab.py
uv run python scripts/run_baseline.py
uv run pytest -q
```

Nếu máy có GNU Make, các lệnh tương đương là `make reset`, `make baseline`
và `make tests`; Makefile cũng gọi qua `uv run`.

Chạy dbt:

```bash
uv run python scripts/sync_dbt_seeds.py
uv run dbt build --project-dir dbt_project --profiles-dir dbt_project
```

Chạy Great Expectations example:

```bash
uv run python gx/validate_orders.py
```

Dashboard:

```bash
uv run streamlit run dashboard/app.py
```

## 3. Starter code đã có gì?

- Bộ **synthetic sample data** đi kèm, không cần tải dataset ngoài.
- Script tạo lại data lớn hơn: `scripts/generate_data.py`.
- Data contract YAML và validator Python cơ bản.
- Great Expectations example nhỏ để học viên mở rộng thành Suite/Checkpoint/Actions.
- dbt project chạy trên DuckDB, có staging + mart + public tests.
- Z-score anomaly detector cơ bản.
- SLO/error-budget calculator cơ bản.
- Dataset-level lineage graph + BFS downstream traversal.
- Streamlit dashboard tối giản.
- 3 public fault scenarios để tập điều tra.
- 10 public tests để kiểm tra stable interface.

**Trạng thái submission:** các phần nâng cao đã được triển khai và kiểm chứng:
type/freshness contract, severity actions, GX Checkpoint/quarantine, dbt unit
test, MAD/seasonality, distribution drift, transitive column lineage,
multi-window burn rate và RAG embedding drift. Evidence nằm tại
`docs/SOLUTION.md` và `reports/`.

## 4. Public fault scenarios

```bash
uv run python scripts/inject_fault.py duplicate_pk
uv run python scripts/inject_fault.py volume_drop
uv run python scripts/inject_fault.py stale_kb
```

Sau mỗi scenario:

```bash
make baseline
```

Reset về trạng thái khỏe:

```bash
make reset
```

## 5. Những phần cần hoàn thiện

Xem chi tiết trong `docs/LAB_GUIDE.md`.

Các hạng mục đã hoàn thiện:

- `src/contract_validator.py`: type checking, freshness, severity/action.
- `gx/validate_orders.py`: Suite/ValidationDefinition/Checkpoint/custom Action.
- `dbt_project/`: singular data tests và native unit test cho join/SCD.
- `observability/anomaly.py`: robust MAD baseline và seasonal context.
- `observability/distribution.py`: KS distribution drift và mean guard.
- `observability/slo.py`: multi-window burn-rate policy.
- `observability/lineage.py`: transitive dataset/column lineage.
- `observability/rag_metrics.py`: text-length và embedding-norm drift.
- `reports/incident_report.md`: incident report hoàn chỉnh.

## 6. Hidden evaluation

Bộ hidden evaluation gồm **20 test cases khó** không nằm trong ZIP học viên. Giảng viên chạy riêng để đánh giá robustness.

Hidden test sẽ gọi stable interface trong `student_api.py`. Nếu refactor code, vẫn cần giữ interface mô tả trong `docs/STUDENT_API.md`.

## 7. Dùng AI coding agent

Có thể dùng Claude Code, Cursor, Codex, ChatGPT, Gemini CLI hoặc agent khác.

Mỗi thay đổi quan trọng cần có:

1. Hypothesis của học viên.
2. Agent proposal.
3. Test/evidence.
4. Quyết định accept/reject/revise.

Ghi ngắn gọn vào `reports/agent_log.md`.

## 8. Tài liệu học tiếp

- Great Expectations Core: https://docs.greatexpectations.io/
- dbt data tests: https://docs.getdbt.com/docs/build/data-tests
- dbt unit tests: https://docs.getdbt.com/docs/build/unit-tests
- OpenLineage: https://openlineage.io/
- Google SRE Workbook — Alerting on SLOs: https://sre.google/workbook/alerting-on-slos/
- Soda Core: https://docs.soda.io/
- Elementary OSS: https://github.com/elementary-data/elementary

---

**Rule quan trọng nhất:** pipeline `SUCCESS` không có nghĩa data đúng.
