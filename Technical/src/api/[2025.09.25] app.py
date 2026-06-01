from __future__ import annotations

import os
from typing import Optional, List

import duckdb
import pandas as pd
from fastapi import FastAPI, Query
from pydantic import BaseModel, Field


app = FastAPI(title="HMDA API")


def get_db_connection() -> duckdb.DuckDBPyConnection:
    # In-memory connections can query Parquet directly
    return duckdb.connect()


# Minimal state postal to FIPS mapping for county FIPS construction
STATE_POSTAL_TO_FIPS = {
    "AL": "01", "AK": "02", "AZ": "04", "AR": "05", "CA": "06",
    "CO": "08", "CT": "09", "DE": "10", "DC": "11", "FL": "12",
    "GA": "13", "HI": "15", "ID": "16", "IL": "17", "IN": "18",
    "IA": "19", "KS": "20", "KY": "21", "LA": "22", "ME": "23",
    "MD": "24", "MA": "25", "MI": "26", "MN": "27", "MS": "28",
    "MO": "29", "MT": "30", "NE": "31", "NV": "32", "NH": "33",
    "NJ": "34", "NM": "35", "NY": "36", "NC": "37", "ND": "38",
    "OH": "39", "OK": "40", "OR": "41", "PA": "42", "RI": "44",
    "SC": "45", "SD": "46", "TN": "47", "TX": "48", "UT": "49",
    "VT": "50", "VA": "51", "WA": "53", "WV": "54", "WI": "55",
    "WY": "56",
}


@app.get("/api/hmda/aggregate")
def hmda_aggregate(year: int = Query(..., ge=2017, le=2100),
                   county_code: Optional[str] = None,
                   lei: Optional[str] = None):
    data_dir = os.path.join("data", "hmda")
    file_path = os.path.join(data_dir, f"hmda_race_agg_{year}.parquet")
    if not os.path.exists(file_path):
        return {"error": f"File not found for year {year}"}

    con = get_db_connection()
    sql = f"""
        SELECT * FROM read_parquet('{file_path.replace("\\", "/")}')
    """
    where_clauses = []
    if county_code:
        where_clauses.append(f"county_code = '{county_code}'")
    if lei:
        where_clauses.append(f"lei = '{lei}'")
    if where_clauses:
        sql += " WHERE " + " AND ".join(where_clauses)

    df: pd.DataFrame = con.execute(sql).fetchdf()
    return {"rows": df.to_dict(orient="records"), "count": len(df)}


@app.get("/api/hmda/years")
def hmda_years() -> List[int]:
    data_dir = os.path.join("data", "hmda")
    if not os.path.exists(data_dir):
        return []
    years: List[int] = []
    for name in os.listdir(data_dir):
        if name.startswith("hmda_race_agg_") and name.endswith(".parquet"):
            try:
                year = int(name.split("hmda_race_agg_")[1].split(".")[0])
                years.append(year)
            except Exception:
                continue
    return sorted(years)


def _find_column(df: pd.DataFrame, candidates: List[str]) -> Optional[str]:
    lower_map = {c.lower(): c for c in df.columns}
    for cand in candidates:
        if cand.lower() in lower_map:
            return lower_map[cand.lower()]
    return None


@app.get("/api/census/ffiec")
def census_ffiec(year: int = Query(..., ge=1990, le=2100),
                 state_fips: Optional[str] = None,
                 county_fips: Optional[str] = None,
                 limit: int = Query(1000, ge=1, le=20000)):
    data_dir = os.path.join("data", "census")
    file_path = os.path.join(data_dir, f"census_data_{year}.parquet")
    if not os.path.exists(file_path):
        return {"error": f"File not found for year {year}"}

    con = get_db_connection()
    base_sql = f"""
        SELECT * FROM read_parquet('{file_path.replace("\\", "/")}')
    """
    df = con.execute(base_sql + " LIMIT 1").fetchdf()
    # detect FIPS columns across versions
    state_col = _find_column(df, ["FIPS State Code", "State", "state", "state_code"]) or ""
    county_col = _find_column(df, ["FIPS County Code", "County", "county", "county_code"]) or ""

    where = []
    if state_fips and state_col:
        where.append(f""""{state_col}" = '{state_fips}'""")
    if county_fips and county_col:
        where.append(f""""{county_col}" = '{county_fips}'""")

    sql = base_sql
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += f" LIMIT {int(limit)}"

    out_df: pd.DataFrame = con.execute(sql).fetchdf()
    return {
        "meta": {
            "state_col": state_col,
            "county_col": county_col,
            "year": year,
            "returned": len(out_df)
        },
        "rows": out_df.to_dict(orient="records")
    }


@app.get("/api/census/years")
def census_years() -> List[int]:
    data_dir = os.path.join("data", "census")
    if not os.path.exists(data_dir):
        return []
    years: List[int] = []
    for name in os.listdir(data_dir):
        if name.startswith("census_data_") and name.endswith(".parquet"):
            try:
                year = int(name.split("census_data_")[1].split(".")[0])
                years.append(year)
            except Exception:
                continue
    return sorted(years)


@app.get("/api/hmda/segments")
def hmda_segments(year: int = Query(..., ge=2017, le=2100),
                  limit: int = Query(1000, ge=1, le=50000)):
    file_path = os.path.join("data", "hmda", "segments", f"segments_{year}.parquet")
    if not os.path.exists(file_path):
        return {"error": f"Segments not found for {year}"}
    con = get_db_connection()
    sql = f"SELECT * FROM read_parquet('{file_path.replace('\\\\','/')}') LIMIT {int(limit)}"
    df = con.execute(sql).fetchdf()
    return {"rows": df.to_dict(orient="records"), "count": len(df)}


@app.get("/api/hmda/metrics")
def hmda_metrics(year: int = Query(..., ge=2017, le=2100),
                 type: str = Query("approval", pattern="^(approval|denials|hhi_county|hhi_msa)$"),
                 limit: int = Query(1000, ge=1, le=50000)):
    fname = {
        "approval": f"metrics_approval_{year}.parquet",
        "denials": f"metrics_denials_{year}.parquet",
        "hhi_county": f"metrics_hhi_county_{year}.parquet",
        "hhi_msa": f"metrics_hhi_msa_{year}.parquet",
    }[type]
    file_path = os.path.join("data", "hmda", "metrics", fname)
    if not os.path.exists(file_path):
        return {"error": f"Metrics not found for {year} ({type})"}
    con = get_db_connection()
    sql = f"SELECT * FROM read_parquet('{file_path.replace('\\\\','/')}') LIMIT {int(limit)}"
    df = con.execute(sql).fetchdf()
    return {"rows": df.to_dict(orient="records"), "count": len(df)}


class CrossTabRequest(BaseModel):
    year: int = Field(..., ge=2017, le=2100)
    group_by: list[str] = Field(..., description="Dimensions to group by from segments columns")
    metrics: list[str] = Field(default_factory=lambda: ["applications", "originations", "purchases", "orig_amount_total", "purch_amount_total"])  # segments metrics set
    limit: int = Field(default=10000, ge=1, le=100000)


@app.post("/api/hmda/segments/crosstab")
def hmda_segments_crosstab(body: CrossTabRequest):
    file_path = os.path.join("data", "hmda", "segments", f"segments_{body.year}.parquet")
    if not os.path.exists(file_path):
        return {"error": f"Segments not found for {body.year}"}
    con = get_db_connection()
    cols = ", ".join([f'"{c}"' for c in body.group_by])
    mets = ", ".join([f'SUM("{m}") AS "{m}"' for m in body.metrics])
    sql = f"""
        SELECT {cols}, {mets}
        FROM read_parquet('{file_path.replace('\\\\','/')}')
        GROUP BY {cols}
        LIMIT {int(body.limit)}
    """
    df = con.execute(sql).fetchdf()
    return {"rows": df.to_dict(orient="records"), "count": len(df)}


