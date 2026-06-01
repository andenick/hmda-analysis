from __future__ import annotations

import os
from typing import Dict, List, Optional

import pandas as pd
import yaml


def load_yaml_config(config_path: str) -> dict:
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def read_raw(year: int, cfg: dict, nrows: Optional[int] = None) -> pd.DataFrame:
    hmda_src = cfg["raw_paths"]["hmda_src"]
    lar_path = os.path.join(hmda_src, f"{year}_public_lar_csv.csv")
    pp_path = os.path.join(hmda_src, f"{year}_public_panel_csv.csv")
    # select minimal needed columns
    usecols = cfg["processing"]["hmda_select_cols"]
    lar = pd.read_csv(lar_path, dtype=object, nrows=nrows, usecols=usecols)
    pp = pd.read_csv(pp_path, dtype=object, nrows=nrows)
    df = pd.merge(lar, pp, how="left", on=["lei", "activity_year"], suffixes=("", "_pp"))
    # Apply R-like filters
    df = df[df["action_taken"].isin(["1", "6"]) & (df["loan_purpose"] != "4")]
    df = df[~df["state_code"].isin(["PR", "VI", "AS"])].copy()
    county_num = pd.to_numeric(df["county_code"], errors="coerce")
    df = df[~(county_num >= 57000).fillna(False)]
    return df


def add_flags(df: pd.DataFrame) -> pd.DataFrame:
    to_num = lambda s: pd.to_numeric(s, errors="coerce")
    out = df.copy()
    out["income_num"] = to_num(out["income"])  # thousands
    out["msa_med_fam_inc"] = to_num(out["ffiec_msa_md_median_family_income"])  # dollars
    out["tract_to_msa_income_percentage_num"] = to_num(out["tract_to_msa_income_percentage"])  # percent
    out["All"] = True
    out["BILow"] = out["income_num"] < (0.5 * out["msa_med_fam_inc"] / 1000.0)
    out["BIMod"] = (~out["BILow"]) & (out["income_num"] < (0.8 * out["msa_med_fam_inc"] / 1000.0))
    out["TILow"] = out["tract_to_msa_income_percentage_num"] < 50
    out["TIMod"] = (~out["TILow"]) & (out["tract_to_msa_income_percentage_num"] < 80)
    # Race recode
    def recode_race(v: str) -> str:
        v = (v or "").strip()
        if v == "White":
            return "White"
        if v in ("Native Hawaiian or Other Pacific Islander", "American Indian or Alaska Native"):
            return "Indigenous"
        if v in ("Race Not Available", "Free Form Text Only"):
            return "NotAvail"
        if v == "Asian":
            return "Asian"
        if v == "Black or African American":
            return "Black"
        if v in ("Joint", "2 or more minority races"):
            return "Other"
        return v
    out["race2"] = out["derived_race"].astype(str).map(recode_race)
    return out


def aggregate_subset(df: pd.DataFrame, mask_col: Optional[str]) -> pd.DataFrame:
    to_num = lambda s: pd.to_numeric(s, errors="coerce").fillna(0)
    df = df if mask_col is None else df[df[mask_col]]
    df = df.copy()
    # Use numeric action_taken to avoid any hidden string formatting issues
    df["action_taken_num"] = pd.to_numeric(df["action_taken"], errors="coerce")
    df["is_orig"] = df["action_taken_num"] == 1
    df["is_purch"] = df["action_taken_num"] == 6
    df["loan_amount_num"] = to_num(df["loan_amount"])  # thousands
    grp = (
        df.groupby(["activity_year", "county_code", "lei", "race2"], dropna=False)
          .agg(
              HL_Loan_Orig=("action_taken_num", lambda x: (x == 1).sum()),
              HL_Loan_Purch=("action_taken_num", lambda x: (x == 6).sum()),
              HL_Amt_Orig=("loan_amount_num", lambda x: x[df.loc[x.index, "is_orig"]].sum()),
              HL_Amt_Purch=("loan_amount_num", lambda x: x[df.loc[x.index, "is_purch"]].sum()),
              state_code=("state_code", "first"),
              agency_code=("agency_code", "first"),
              respondent_rssd=("respondent_rssd", "first"),
              respondent_name=("respondent_name", "first"),
              assets=("assets", "first"),
              other_lender_code=("other_lender_code", "first"),
          )
          .reset_index()
    )
    wide = grp.pivot_table(
        index=["activity_year", "county_code", "lei", "state_code", "agency_code", "respondent_rssd", "respondent_name", "assets", "other_lender_code"],
        columns="race2",
        values=["HL_Loan_Orig", "HL_Loan_Purch", "HL_Amt_Orig", "HL_Amt_Purch"],
        fill_value=0,
        aggfunc="sum",
    )
    wide.columns = [f"{a}_{b}" for a, b in wide.columns.to_flat_index()]
    wide = wide.reset_index()
    return wide


def append_suffix(df: pd.DataFrame, suffix: str) -> pd.DataFrame:
    out = df.copy()
    rename_map: Dict[str, str] = {}
    for c in out.columns:
        if c.startswith("HL_"):
            rename_map[c] = f"{c}_{suffix}"
    out = out.rename(columns=rename_map)
    return out


def select_metric_cols(df: pd.DataFrame, keys: List[str]) -> pd.DataFrame:
    metric_cols = [c for c in df.columns if c.startswith("HL_")]
    return df[keys + metric_cols].copy()


def compute_totals(df: pd.DataFrame) -> pd.DataFrame:
    # Row sums across race columns by metric & suffix
    out = df.copy()
    def sum_cols(prefix: str, suffix: str) -> pd.Series:
        cols = [c for c in out.columns if c.startswith(prefix) and c.endswith(f"_{suffix}") and ("_Total_" not in c)]
        return out[cols].sum(axis=1)
    for metric in ("HL_Loan_Orig", "HL_Loan_Purch", "HL_Amt_Orig", "HL_Amt_Purch"):
        for suffix in ("All", "BILow", "BIMod", "TILow", "TIMod"):
            out[f"{metric}_Total_{suffix}"] = sum_cols(metric, suffix)
    return out


def compute_percentages(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    # Generate percentages for loan amount origination share by race (All) to match R explicit section
    races = ["Asian", "Black", "White", "Indigenous", "Other", "NotAvail"]
    for race in races:
        base = f"HL_Amt_Orig_{race}_All"
        total = "HL_Amt_Orig_Total_All"
        if base in out.columns and total in out.columns:
            out[f"{base}_Pct"] = out[base] / out[total].replace(0, pd.NA)
    return out


def rename_final_id_cols(df: pd.DataFrame) -> pd.DataFrame:
    out = df.rename(columns={
        "respondent_rssd": "id_rssd",
        "lei": "hmda_lender_id",
        "respondent_name": "inst_name",
        "county_code": "fips",
    })
    return out


def filter_banks(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    # bank filter: other_lender_code == 0, agency_code in {1,2,3,9}, exclude credit unions under code 9
    out = out[(out["other_lender_code"].astype(str) == "0") & (out["agency_code"].astype(str).isin(["1", "2", "3", "9"]))]
    out = out[~((out["agency_code"].astype(str) == "9") & (out["inst_name"].astype(str).str.lower().str.contains("credit union", na=False)))]
    return out


def write_csv(df: pd.DataFrame, path: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    df.to_csv(path, index=False)


def replicate_year(year: int, config_path: str = "python_project.yaml", nrows: Optional[int] = None) -> Dict[str, str]:
    cfg = load_yaml_config(config_path)
    out_dir = os.path.join(cfg["outputs"]["data_dir"], "r_replication")

    raw = read_raw(year, cfg, nrows=nrows)
    raw = add_flags(raw)

    # Build All and income subsets
    all_df = append_suffix(aggregate_subset(raw, None), "All")
    bilow_df = append_suffix(aggregate_subset(raw, "BILow"), "BILow")
    bimod_df = append_suffix(aggregate_subset(raw, "BIMod"), "BIMod")
    tilow_df = append_suffix(aggregate_subset(raw, "TILow"), "TILow")
    timod_df = append_suffix(aggregate_subset(raw, "TIMod"), "TIMod")

    # step2: left join aggregated subsets onto the unique base of (activity_year, county_code, lei)
    base_cols = [
        "activity_year", "county_code", "lei", "state_code", "agency_code",
        "respondent_rssd", "respondent_name", "assets", "other_lender_code",
    ]
    # Create unique base by (activity_year, county_code, lei) - this matches R behavior
    base_df = raw[base_cols].drop_duplicates(subset=["activity_year", "county_code", "lei"]).copy()
    merge_keys = ["activity_year", "county_code", "lei"]
    all_m = select_metric_cols(all_df, merge_keys)
    bilow_m = select_metric_cols(bilow_df, merge_keys)
    bimod_m = select_metric_cols(bimod_df, merge_keys)
    tilow_m = select_metric_cols(tilow_df, merge_keys)
    timod_m = select_metric_cols(timod_df, merge_keys)
    step2 = (base_df
             .merge(all_m, on=merge_keys, how="left")
             .merge(bilow_m, on=merge_keys, how="left")
             .merge(bimod_m, on=merge_keys, how="left")
             .merge(tilow_m, on=merge_keys, how="left")
             .merge(timod_m, on=merge_keys, how="left"))
    p_step2 = os.path.join(out_dir, f"{year}_lar_race_step2.csv")
    write_csv(step2, p_step2)

    # step3: totals
    step3 = compute_totals(step2)
    p_step3 = os.path.join(out_dir, f"{year}_lar_race_step3.csv")
    write_csv(step3, p_step3)

    # step4: percentages
    step4 = compute_percentages(step3)
    p_step4 = os.path.join(out_dir, f"{year}_lar_race_step4.csv")
    write_csv(step4, p_step4)

    # step5: rename id columns
    step5 = rename_final_id_cols(step4)
    p_step5 = os.path.join(out_dir, f"{year}_lar_race_step5.csv")
    write_csv(step5, p_step5)

    # step6: bank filters + also save unfiltered
    p_step6 = os.path.join(out_dir, f"{year}_lar_race_step6.csv")
    write_csv(step5, p_step6)
    step6 = step5  # naming for subsequent steps
    step6_banks = filter_banks(step5)
    p_step6b = os.path.join(out_dir, f"{year}_lar_race_step6_banks.csv")
    write_csv(step6_banks, p_step6b)

    # step7: County-level totals and percentages
    step7 = compute_county_totals_and_pcts(step6)
    p_step7 = os.path.join(out_dir, f"{year}_lar_race_step7.csv")
    write_csv(step7, p_step7)

    # step8: Adjust FIPS and add State/County names from FIPS mapping file if available
    step8 = add_fips_and_names(step7)
    p_step8 = os.path.join(out_dir, f"{year}_lar_race_step8.csv")
    write_csv(step8, p_step8)

    # step9: Final cleanup and formatting (remove rows with missing key data)
    step9 = final_cleanup(step8)
    p_step9 = os.path.join(out_dir, f"{year}_lar_race_step9.csv")
    write_csv(step9, p_step9)

    return {
        "step2": p_step2,
        "step3": p_step3,
        "step4": p_step4,
        "step5": p_step5,
        "step6": p_step6,
        "step6_banks": p_step6b,
        "step7": p_step7,
        "step8": p_step8,
        "step9": p_step9,
    }


def compute_county_totals_and_pcts(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    # Ensure fips exists
    if "fips" not in out.columns:
        out["fips"] = out["county_code"].astype(str)

    prefixes = ["HL_Amt_Orig_", "HL_Loan_Orig_"]
    income_suffixes = ["All", "BILow", "BIMod", "TILow", "TIMod"]

    for prefix in prefixes:
        # All numeric metric columns that match prefix and not percentage
        cols = [c for c in out.columns if c.startswith(prefix) and not c.endswith("_Pct")]
        if not cols:
            continue
        # county totals
        grp = out.groupby("fips")[cols].sum(min_count=1).reset_index()
        # rename with County_
        rename_map = {c: f"County_{c}" for c in cols}
        grp = grp.rename(columns=rename_map)
        out = out.merge(grp, on="fips", how="left")
        # compute percentages per (race, income) relative to County_Total_income
        for inc in income_suffixes:
            total_col = f"County_{prefix}Total_{inc}"
            if total_col not in out.columns:
                continue
            for c in cols:
                if c.endswith(f"_{inc}") and not c.endswith("Total_" + inc):
                    county_c = f"County_{c}"
                    pct_col = f"{county_c}_Pct"
                    denom = out[total_col].replace(0, pd.NA)
                    out[pct_col] = out[county_c] / denom
    return out


def add_fips_and_names(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    # zero-pad to 5 chars
    out["fips"] = out["fips"].astype(str).str.zfill(5)
    # Try to map names from US_FIPS_Codes.xls if present
    fips_xls = os.path.join("Old", "CRA_code", "US_FIPS_Codes.xls")
    if os.path.exists(fips_xls):
        try:
            ref = pd.read_excel(fips_xls, dtype=object)
            cols = [c for c in ref.columns]
            # detect columns
            def pick(cands):
                for c in cols:
                    lc = str(c).lower()
                    for cand in cands:
                        if cand in lc:
                            return c
                return None
            stc = pick(["statefp", "state fips", "state code", "statefp" ])
            ctc = pick(["countyfp", "county fips", "county code", "countyfp"])
            namec = pick(["name", "countyname", "county name"])
            if stc is not None and ctc is not None and namec is not None:
                ref["fips"] = ref[stc].astype(str).str.zfill(2) + ref[ctc].astype(str).str.zfill(3)
                # split name into State and County if possible, otherwise assign full name to County
                ref = ref[["fips", namec]].drop_duplicates()
                ref = ref.rename(columns={namec: "County"})
                out = out.merge(ref, on="fips", how="left")
        except Exception:
            pass
    return out


def final_cleanup(df: pd.DataFrame) -> pd.DataFrame:
    """Final cleanup step - remove rows with missing key data and format consistently."""
    out = df.copy()

    # Remove rows with missing key identifiers (similar to what R step9 appears to do)
    initial_rows = len(out)

    # Remove rows where key fields are missing
    out = out.dropna(subset=['fips', 'hmda_lender_id'])

    # Remove rows with invalid fips (too short after processing)
    out = out[out['fips'].astype(str).str.len() >= 5]

    final_rows = len(out)
    print(f"Final cleanup: {initial_rows} -> {final_rows} rows ({initial_rows - final_rows} removed)")

    return out


