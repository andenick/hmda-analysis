# Data Manifest — HMDA Analysis

This repository ships **no data**. All inputs are **public** and must be downloaded
separately, then placed under your `DATA_ROOT` (see the project README). Outputs are
written under `OUTPUT_ROOT`.

## Required public sources

### 1. HMDA Loan/Application Register (LAR)
- **What:** loan-level mortgage application/origination records.
- **Modern (2007–present):** CFPB HMDA Data Browser and bulk files
  - https://ffiec.cfpb.gov/data-browser/
  - https://ffiec.cfpb.gov/data-publication/snapshot-national-loan-level-dataset
- **Historical (pre-2007):** FFIEC HMDA archives
  - https://www.ffiec.gov/hmda/hmdaproducts.htm

### 2. FFIEC Census flat files
- **What:** tract-level census/demographic flat files used to enrich and segment LAR records.
- **Source:** FFIEC Census & Demographic data
  - https://www.ffiec.gov/censusapp.htm
  - https://www.ffiec.gov/hmda/censusproducts.htm
- The parsers in `Technical/src/census/` expect the FFIEC flat-file guides
  (`_flatFileGuide2`) and `src/` flat files; the schema XLSX guides live under
  `Inputs/Old/Python Stuff/schemas/`.

### 3. Census tract boundaries / TIGER (for boundary corrections)
- **What:** tract geometries and relationship files across vintages, used by the
  tract-boundary correction/validation modules.
- **Source:** U.S. Census Bureau TIGER/Line
  - https://www.census.gov/geographies/mapping-files/time-series/geo/tiger-line-file.html
  - Tract relationship files: https://www.census.gov/geographies/reference-files/time-series/geo/relationship-files.html

## Expected layout under `DATA_ROOT`

The loaders reference these relative paths (originating from the project's internal
organization — recreate the parts you need):

```
DATA_ROOT/
  Inputs/Old/CRA_code/_files2/1990to2006/src/        # historical HMDA LAR flat files
  Inputs/Old/CRA_code/_files2/flatFiles/src/         # FFIEC census flat files
  Inputs/Old/CRA_code/_files2/flatFiles/_flatFileGuide2/   # FFIEC flat-file guides
  Inputs/Old/Python Stuff/schemas/                   # schema XLSX guides
```

Outputs (parsed census, processed HMDA, analysis results) are written under `OUTPUT_ROOT`
(e.g. `Outputs/census_csv/`, `Technical/data/census_parsed_v2/`).

## Notes
- HMDA and FFIEC Census data are released for public use; verify the FFIEC/CFPB terms for
  the specific vintages you download.
- File names, year coverage, and column schemas change across vintages — consult the FFIEC
  file specifications for the years you use.
