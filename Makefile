UV ?= uv
RUN := $(UV) run

.PHONY: reset baseline tests gx dbt dashboard generate

reset:
	$(RUN) python scripts/reset_lab.py

baseline:
	$(RUN) python scripts/run_baseline.py

tests:
	$(RUN) pytest -q

gx:
	$(RUN) python gx/validate_orders.py

dbt:
	$(RUN) python scripts/sync_dbt_seeds.py
	$(RUN) dbt build --project-dir dbt_project --profiles-dir dbt_project

dashboard:
	$(RUN) streamlit run dashboard/app.py

generate:
	$(RUN) python scripts/generate_data.py --rows 600 --days 42 --seed 27
