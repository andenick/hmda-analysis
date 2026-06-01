from __future__ import annotations

import os
from typing import Optional, List

import duckdb
import yaml


def load_yaml_config(config_path: str) -> dict:
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def enrich_segments_with_census(year: int, config_path: str = "python_project.yaml", limit: Optional[int] = None) -> str:
    cfg = load_yaml_config(config_path)
    seg_path = os.path.join(cfg["outputs"]["data_dir"], "hmda", "segments", f"segments_{year}.parquet")
    cen_path = os.path.join(cfg["outputs"]["data_dir"], "census", f"census_data_{year}.parquet")
    if not os.path.exists(seg_path):
        raise FileNotFoundError(seg_path)
    if not os.path.exists(cen_path):
        raise FileNotFoundError(cen_path)

    con = duckdb.connect()
    # Detect census FIPS columns
    probe = con.execute(f"SELECT * FROM read_parquet('{cen_path.replace('\\\\','/')}') LIMIT 1").fetchdf()
    # pick plausible columns
    state_col = None
    county_col = None
    for cand in ["FIPS State Code", "State", "state"]:
        if cand in probe.columns:
            state_col = cand
            break
    for cand in ["FIPS County Code", "County", "county"]:
        if cand in probe.columns:
            county_col = cand
            break
    if not state_col or not county_col:
        state_col = state_col or "State"
        county_col = county_col or "County"

    # Create county_fips in census view
    sql = f"""
        WITH cen AS (
          SELECT *,
                 LPAD(CAST("{state_col}" AS VARCHAR), 2, '0') || LPAD(CAST("{county_col}" AS VARCHAR), 3, '0') AS county_fips
          FROM read_parquet('{cen_path.replace('\\\\','/')}')
        ), seg AS (
          SELECT * FROM read_parquet('{seg_path.replace('\\\\','/')}')
        )
        SELECT s.*, c.Year AS census_year, c.MSA_MD AS census_msa_md
        FROM seg s
        LEFT JOIN cen c USING(county_fips)
        {f'LIMIT {int(limit)}' if limit else ''}
    """
    out = con.execute(sql).fetchdf()
    out_dir = os.path.join(cfg["outputs"]["data_dir"], "hmda", "enriched")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, f"segments_with_census_{year}.parquet")
    con.execute(f"COPY (SELECT * FROM out) TO '{out_path.replace('\\\\','/')}' (FORMAT PARQUET)")
    return out_path


