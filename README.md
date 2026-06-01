# HMDA Analysis

Code and methodology for analyzing **Home Mortgage Disclosure Act (HMDA)** loan-level
data and FFIEC Census data: mortgage-lending patterns, geographic disparities,
tract-boundary corrections across vintages, longitudinal time-series, systemic-bank
analysis, and a Python replication of published R methodologies (incl. a
Bhutta-style replication).

This is a **code-only** release. The underlying HMDA LAR and Census corpora (hundreds of
GB) are **not** included — see [`data/MANIFEST.md`](data/MANIFEST.md) for the public
sources and download links.

## Repository layout

- `Technical/src/` — analysis library
  - `hmda/`, `census/` — loaders / parsers for HMDA LAR and FFIEC Census flat files
  - `analysis/` — disparity, geographic-aggregation, longitudinal, multi-scope analyses
  - `bhutta_replication/` — Python port of the R replication (multiple iterations + diagnostics)
  - `validation/`, `quality/` — tract-boundary correction/validation and data-quality monitors
  - `api/` — Flask / Streamlit / FastAPI dashboards
- `Technical/scripts/` — CLI entry points
- `streamlit_dashboard.py`, `update_dashboard_data.py` — dashboard app + data refresh
- `comprehensive_*.py`, `hmda_master_workflow.py` — top-level orchestration

## Setup

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### Data location (required)

The code reads inputs from `DATA_ROOT` and writes outputs to `OUTPUT_ROOT`, both set via
environment variables (defaults: `./data` and `./outputs`). Point them at where you have
downloaded the HMDA / Census data (see [`data/MANIFEST.md`](data/MANIFEST.md)):

```bash
export DATA_ROOT=/path/to/your/hmda-and-census-data
export OUTPUT_ROOT=/path/to/where/outputs/should/go
```

```powershell
$env:DATA_ROOT = "D:\path\to\data"
$env:OUTPUT_ROOT = "D:\path\to\outputs"
```

Inside `DATA_ROOT`, the loaders expect the original sub-layout (e.g.
`Inputs/Old/CRA_code/...`, `Inputs/Old/Python Stuff/schemas/...`); `data/MANIFEST.md`
documents which public files populate each path. Copy `.env.example` to `.env` and edit if
you prefer a dotenv file.

### Run

```bash
# Census flat-file parser
python "Technical/src/census/census_full_parser.py"

# Bhutta-style replication (latest)
python Technical/src/bhutta_replication/r_modified/bhutta_replication_FINAL.py

# Dashboard
streamlit run streamlit_dashboard.py
```

## API keys — bring your own

The analysis pipeline runs on **local files** and needs no API keys. The dashboards
expose only operational settings (see `.env.example`): `SECRET_KEY` (generate your own
with `python -c "import secrets; print(secrets.token_hex(32))"`), host/port, CORS, and
optional `GOOGLE_ANALYTICS_ID` / `SENTRY_DSN`. None are required to run the analysis code.

## Data

HMDA and FFIEC Census data are **public**. This repository ships **no data**. Download the
required inputs yourself per [`data/MANIFEST.md`](data/MANIFEST.md) and set `DATA_ROOT`.

## License

No license is granted (all rights reserved) unless one is added later.
