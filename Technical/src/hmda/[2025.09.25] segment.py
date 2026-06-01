from __future__ import annotations

import os
from typing import List, Optional

import pandas as pd
import yaml


def load_yaml_config(config_path: str) -> dict:
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_hmda_year_raw(year: int, cfg: dict, nrows: Optional[int] = None) -> pd.DataFrame:
    hmda_src = cfg["raw_paths"]["hmda_src"]
    lar_path = os.path.join(hmda_src, f"{year}_public_lar_csv.csv")
    pp_path = os.path.join(hmda_src, f"{year}_public_panel_csv.csv")

    lar = pd.read_csv(lar_path, dtype=object, nrows=nrows)
    panel = pd.read_csv(pp_path, dtype=object, nrows=nrows)
    merged = pd.merge(lar, panel, how="left", on=["lei", "activity_year"], suffixes=("", "_pp"))
    return merged


def derive_segments(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()

    # Lender type segments based on agency_code, RSSD presence, and other_lender_code
    def lender_type(row) -> str:
        agency = str(row.get("agency_code", "")).strip()
        other = str(row.get("other_lender_code", "")).strip()
        parent = str(row.get("topholder_name", "") or row.get("parent_name", "")).strip()
        if agency == "1":
            return "OCC-regulated bank"
        if agency == "2":
            return "FED-reserve bank"
        if agency == "3":
            return "FDIC bank"
        if agency == "5":
            return "NCUA credit union"
        if other == "1":
            return "Mortgage company"
        if parent:
            return "Affiliated (holding company)"
        return "Other lender"

    out["lender_type_segment"] = out.apply(lender_type, axis=1)

    # Loan purpose segment
    purpose_map = {
        "1": "Home purchase",
        "2": "Home improvement",
        "31": "Refinance",
        "32": "Cash-out refinance",
    }
    out["loan_purpose_segment"] = out["loan_purpose"].map(purpose_map).fillna("Other purpose")

    # Pricing/terms segments
    def to_num(s: pd.Series) -> pd.Series:
        return pd.to_numeric(s, errors="coerce")

    out["int_rate"] = to_num(out.get("interest_rate"))
    out["dti_num"] = to_num(out.get("debt_to_income_ratio"))
    out["cltv_num"] = to_num(out.get("combined_loan_to_value_ratio"))
    out["loan_amt_num"] = to_num(out.get("loan_amount"))
    out["prop_val_num"] = to_num(out.get("property_value"))

    # Buckets
    out["dti_bucket"] = pd.cut(out["dti_num"], bins=[-1, 20, 30, 36, 43, 50, 60, 1000], labels=["<=20", "20-30", "30-36", "36-43", "43-50", "50-60", ">60"])  # classic underwriting steps
    out["cltv_bucket"] = pd.cut(out["cltv_num"], bins=[-1, 80, 90, 97, 105, 200], labels=["<=80", "80-90", "90-97", "97-105", ">105"]) 
    out["rate_bucket"] = pd.cut(out["int_rate"], bins=[-1, 3, 4, 5, 6, 8, 100], labels=["<=3", "3-4", "4-5", "5-6", "6-8", ">8"]) 
    out["loan_size_bucket"] = pd.cut(out["loan_amt_num"], bins=[-1, 100, 250, 417, 647, 766, 1000, 100000], labels=["<=100k", "100-250k", "250-417k", "417-647k", "647-766k", "766k-1m", ">1m"]) 

    # Borrower income relative to MSA
    out["income_num"] = to_num(out.get("income"))
    out["msa_med_fam_inc"] = to_num(out.get("ffiec_msa_md_median_family_income"))
    denom = out["msa_med_fam_inc"].replace(0, pd.NA)
    ratio = (out["income_num"] * 1000.0) / denom * 100.0
    out["borrower_income_to_msa_pct"] = pd.to_numeric(ratio, errors="coerce")
    out["borrower_income_bucket"] = pd.cut(
        out["borrower_income_to_msa_pct"].astype(float),
        bins=[-1, 50, 80, 100, 120, 2000],
        labels=["<=50% MSA", "50-80%", "80-100%", "100-120%", ">120%"],
    )

    # Race and sex directly from derived variables
    out["race_segment"] = out.get("derived_race")
    out["sex_segment"] = out.get("derived_sex")

    # Age buckets (if available)
    out["applicant_age_num"] = to_num(out.get("applicant_age"))
    out["age_bucket"] = pd.cut(out["applicant_age_num"], bins=[-1, 24, 34, 44, 54, 64, 74, 200], labels=["<=24", "25-34", "35-44", "45-54", "55-64", "65-74", "75+"])

    return out


def summarize_segments(df: pd.DataFrame) -> pd.DataFrame:
    # Key metrics by lender and borrower segments
    key_dims = [
        "lender_type_segment",
        "loan_purpose_segment",
        "dti_bucket",
        "cltv_bucket",
        "rate_bucket",
        "loan_size_bucket",
        "borrower_income_bucket",
        "race_segment",
        "sex_segment",
        "age_bucket",
        "state_code",
        "county_code",
    ]

    def to_num(s: pd.Series) -> pd.Series:
        return pd.to_numeric(s, errors="coerce").fillna(0)

    df["is_orig"] = (df["action_taken"] == "1")
    df["is_purch"] = (df["action_taken"] == "6")

    df["loan_amount_num"] = to_num(df.get("loan_amount"))

    # Avoid cartesian product expansion by using observed=True and precomputed masks
    df["is_orig_int"] = df["is_orig"].astype(int)
    df["is_purch_int"] = df["is_purch"].astype(int)
    df["orig_amount_num"] = df["loan_amount_num"] * df["is_orig_int"]
    df["purch_amount_num"] = df["loan_amount_num"] * df["is_purch_int"]

    grouped = (
        df.groupby(key_dims, dropna=False, observed=True)
          .agg(
              applications=("lei", "count"),
              originations=("is_orig_int", "sum"),
              purchases=("is_purch_int", "sum"),
              orig_amount_total=("orig_amount_num", "sum"),
              purch_amount_total=("purch_amount_num", "sum"),
          )
          .reset_index()
    )
    return grouped


def segment_hmda(year: int, config_path: str = "python_project.yaml", nrows: Optional[int] = None) -> str:
    cfg = load_yaml_config(config_path)
    df = load_hmda_year_raw(year, cfg, nrows=nrows)
    df = derive_segments(df)
    summary = summarize_segments(df)
    # Add county FIPS if possible (state postal -> FIPS + county_code)
    state_map = {
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
    def mk_county_fips(row):
        st = str(row.get("state_code", "")).strip()
        c = str(row.get("county_code", "")).strip().zfill(3)
        stf = state_map.get(st)
        if stf and c and c != "nan":
            return f"{stf}{c}"
        return None
    try:
        summary["county_fips"] = summary.apply(mk_county_fips, axis=1)
    except Exception:
        pass
    out_dir = os.path.join(cfg["outputs"]["data_dir"], "hmda", "segments")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, f"segments_{year}.parquet")
    summary.to_parquet(out_path, index=False)
    return out_path


