from __future__ import annotations

import os
from typing import List, Optional

import pandas as pd
import yaml


def load_yaml_config(config_path: str) -> dict:
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def read_hmda_year(year: int, config: dict, nrows: Optional[int] = None) -> pd.DataFrame:
    hmda_src = config["raw_paths"]["hmda_src"]
    lar_path = os.path.join(hmda_src, f"{year}_public_lar_csv.csv")
    pp_path = os.path.join(hmda_src, f"{year}_public_panel_csv.csv")

    usecols = config["processing"]["hmda_select_cols"]
    lar = pd.read_csv(lar_path, usecols=usecols, dtype=object, nrows=nrows)
    panel = pd.read_csv(pp_path, dtype=object, nrows=nrows)

    # drop pp fields per R code (we simply keep needed ones by inner join keys)
    merged = pd.merge(lar, panel, how="left", on=["lei", "activity_year"], suffixes=("", "_pp"))

    # Filter per R logic
    merged = merged[merged["action_taken"].isin(["1", "6"]) & (merged["loan_purpose"] != "4")]
    # Safe numeric comparison for county_code
    county_num = pd.to_numeric(merged["county_code"], errors="coerce")
    merged = merged[~merged["state_code"].isin(["PR", "VI", "AS"]) & ~((county_num >= 57000).fillna(False))]

    # Indicators
    # ensure numerics safely cast
    def to_num(s: pd.Series) -> pd.Series:
        return pd.to_numeric(s, errors="coerce")

    merged["income_num"] = to_num(merged["income"])  # income is $ thousands in HMDA
    merged["msa_med_fam_inc"] = to_num(merged["ffiec_msa_md_median_family_income"])  # dollars
    merged["tract_to_msa_income_percentage_num"] = to_num(merged["tract_to_msa_income_percentage"])  # percent

    merged["All"] = True
    merged["BILow"] = merged["income_num"] < (0.5 * merged["msa_med_fam_inc"] / 1000.0)
    merged["BIMod"] = (~merged["BILow"]) & (merged["income_num"] < (0.8 * merged["msa_med_fam_inc"] / 1000.0))
    merged["TILow"] = merged["tract_to_msa_income_percentage_num"] < 50
    merged["TIMod"] = (~merged["TILow"]) & (merged["tract_to_msa_income_percentage_num"] < 80)

    # Race recode
    def recode_race(val: str) -> str:
        v = (val or "").strip()
        if v == "White":
            return "White"
        if v in ["Native Hawaiian or Other Pacific Islander", "American Indian or Alaska Native"]:
            return "Indigenous"
        if v in ["Race Not Available", "Free Form Text Only"]:
            return "NotAvail"
        if v == "Asian":
            return "Asian"
        if v == "Black or African American":
            return "Black"
        if v in ["Joint", "2 or more minority races"]:
            return "Other"
        return v

    merged["derived_race_2"] = merged["derived_race"].astype(str).map(recode_race)

    return merged


def aggregate_by_race(df: pd.DataFrame) -> pd.DataFrame:
    # Convert fields for incfilt-like sums
    def to_num(s: pd.Series) -> pd.Series:
        return pd.to_numeric(s, errors="coerce").fillna(0)

    df["loan_amount_num"] = to_num(df["loan_amount"])  # HMDA in thousands
    df["action_taken_num"] = to_num(df["action_taken"])  # 1 orig, 6 purchase

    # group and compute sums
    grp = (
        df.groupby(["activity_year", "county_code", "lei", "derived_race_2"], dropna=False)
        .agg(
            HL_Loan_Orig=("action_taken_num", lambda x: (x == 1).sum()),
            HL_Loan_Purch=("action_taken_num", lambda x: (x == 6).sum()),
            HL_Amt_Orig=("loan_amount_num", lambda x: df.loc[x.index, "action_taken_num"].where(df.loc[x.index, "action_taken_num"] == 1, 0).mul(x.notna()).sum()),
            HL_Amt_Purch=("loan_amount_num", lambda x: df.loc[x.index, "action_taken_num"].where(df.loc[x.index, "action_taken_num"] == 6, 0).mul(x.notna()).sum()),
            state_code=("state_code", "first"),
        )
        .reset_index()
    )

    # pivot wide
    wide = grp.pivot_table(
        index=["activity_year", "county_code", "lei"],
        columns="derived_race_2",
        values=["HL_Loan_Orig", "HL_Loan_Purch", "HL_Amt_Orig", "HL_Amt_Purch"],
        fill_value=0,
        aggfunc="sum",
    )
    wide.columns = [f"{a}_{b}" for a, b in wide.columns.to_flat_index()]
    wide = wide.reset_index().sort_values(["county_code"])  # match R ordering intent
    return wide


def process_hmda(years: List[int] | None = None, config_path: str = "python_project.yaml", nrows: Optional[int] = None) -> List[str]:
    cfg = load_yaml_config(config_path)
    years = years or list(cfg["processing"]["hmda_years"])

    out_dir = os.path.join(cfg["outputs"]["data_dir"], "hmda")
    os.makedirs(out_dir, exist_ok=True)

    written: List[str] = []
    for yr in years:
        df = read_hmda_year(yr, cfg, nrows=nrows)
        if cfg["processing"].get("subset_state"):
            state = cfg["processing"]["subset_state"]
            df = df[df["state_code"] == state]

        wide = aggregate_by_race(df)
        out_path = os.path.join(out_dir, f"hmda_race_agg_{yr}.parquet")
        wide.to_parquet(out_path, index=False)
        written.append(out_path)
    return written


