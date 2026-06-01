from __future__ import annotations

import os
from typing import Optional, List, Dict

import pandas as pd
import yaml


def load_yaml_config(config_path: str) -> dict:
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _read_raw_hmda(year: int, cfg: dict, nrows: Optional[int]) -> pd.DataFrame:
    hmda_src = cfg["raw_paths"]["hmda_src"]
    lar_path = os.path.join(hmda_src, f"{year}_public_lar_csv.csv")
    pp_path = os.path.join(hmda_src, f"{year}_public_panel_csv.csv")
    lar = pd.read_csv(lar_path, dtype=object, nrows=nrows)
    pp = pd.read_csv(pp_path, dtype=object, nrows=nrows)
    df = pd.merge(lar, pp, how="left", on=["lei", "activity_year"], suffixes=("", "_pp"))
    return df


def _lender_type(row: pd.Series) -> str:
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


def _add_basic_features(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["lender_type_segment"] = out.apply(_lender_type, axis=1)

    purpose_map = {
        "1": "Home purchase",
        "2": "Home improvement",
        "31": "Refinance",
        "32": "Cash-out refinance",
    }
    out["loan_purpose_segment"] = out["loan_purpose"].map(purpose_map).fillna("Other purpose")

    # numeric helpers
    to_num = lambda s: pd.to_numeric(s, errors="coerce")
    out["loan_amount_num"] = to_num(out.get("loan_amount"))

    # action flags
    out["is_app"] = True
    out["is_orig"] = (out["action_taken"] == "1")
    out["is_purch"] = (out["action_taken"] == "6")
    out["is_denied"] = (out["action_taken"] == "3")
    return out


def compute_approval_denial_metrics(df: pd.DataFrame) -> pd.DataFrame:
    dims = [
        "state_code",
        "county_code",
        "derived_msa_md",
        "lender_type_segment",
        "loan_purpose_segment",
    ]

    # aggregate
    grouped = (
        df.groupby(dims, dropna=False, observed=True)
          .agg(
              applications=("is_app", "sum"),
              originations=("is_orig", "sum"),
              purchases=("is_purch", "sum"),
              denials=("is_denied", "sum"),
              orig_amount_total=("loan_amount_num", lambda x: x[df.loc[x.index, "is_orig"].astype(bool)].sum()),
          )
          .reset_index()
    )
    # rates
    denom = grouped["applications"].replace(0, pd.NA)
    grouped["approval_rate"] = grouped["originations"] / denom
    grouped["denial_rate"] = grouped["denials"] / denom
    return grouped


def compute_denial_reason_distribution(df: pd.DataFrame) -> pd.DataFrame:
    # melt denial reasons
    cols = [c for c in ["denial_reason_1", "denial_reason_2", "denial_reason_3", "denial_reason_4"] if c in df.columns]
    if not cols:
        return pd.DataFrame()
    base_dims = ["state_code", "county_code", "derived_msa_md", "lender_type_segment", "loan_purpose_segment"]
    melted = df.loc[df["is_denied"]].melt(
        id_vars=base_dims,
        value_vars=cols,
        var_name="denial_reason_order",
        value_name="denial_reason"
    )
    melted = melted.dropna(subset=["denial_reason"]).copy()
    dist = (
        melted.groupby(base_dims + ["denial_reason"], dropna=False, observed=True)
              .size()
              .reset_index(name="count")
    )
    return dist


def compute_hhi(df: pd.DataFrame, geo: str, purpose_split: bool = True) -> pd.DataFrame:
    # HHI over lei shares of originations per geography-year-(purpose)
    dims = [geo]
    if purpose_split:
        dims.append("loan_purpose_segment")
    # originations per lei
    per_lei = (
        df[df["is_orig"]]
          .groupby(["activity_year"] + dims + ["lei"], dropna=False, observed=True)
          .size()
          .reset_index(name="orig_count")
    )
    # total per geo
    totals = (
        per_lei.groupby(["activity_year"] + dims, dropna=False, observed=True)
               .agg(total=("orig_count", "sum"))
               .reset_index()
    )
    merged = per_lei.merge(totals, on=["activity_year"] + dims, how="left")
    merged["share"] = merged["orig_count"] / merged["total"].replace(0, pd.NA)
    # HHI = sum(share^2)
    hhi = (
        merged.groupby(["activity_year"] + dims, dropna=False, observed=True)
              .agg(hhi=("share", lambda s: (s.fillna(0) ** 2).sum()))
              .reset_index()
    )
    hhi["hhi_10k"] = (hhi["hhi"] * 10000).round(0)
    return hhi


def build_metrics(year: int, config_path: str = "python_project.yaml", nrows: Optional[int] = None) -> Dict[str, str]:
    cfg = load_yaml_config(config_path)
    df = _read_raw_hmda(year, cfg, nrows)
    df = _add_basic_features(df)

    out_dir = os.path.join(cfg["outputs"]["data_dir"], "hmda", "metrics")
    os.makedirs(out_dir, exist_ok=True)

    # Approval/Denial metrics
    appr = compute_approval_denial_metrics(df)
    appr_path = os.path.join(out_dir, f"metrics_approval_{year}.parquet")
    appr.to_parquet(appr_path, index=False)

    # Denial reasons distribution
    denial_dist = compute_denial_reason_distribution(df)
    denial_path = os.path.join(out_dir, f"metrics_denials_{year}.parquet")
    if not denial_dist.empty:
        denial_dist.to_parquet(denial_path, index=False)
    else:
        denial_path = ""

    # HHI at county and MSA
    hhi_cty = compute_hhi(df, geo="county_code", purpose_split=True)
    hhi_cty_path = os.path.join(out_dir, f"metrics_hhi_county_{year}.parquet")
    hhi_cty.to_parquet(hhi_cty_path, index=False)

    hhi_msa = compute_hhi(df, geo="derived_msa_md", purpose_split=True)
    hhi_msa_path = os.path.join(out_dir, f"metrics_hhi_msa_{year}.parquet")
    hhi_msa.to_parquet(hhi_msa_path, index=False)

    return {
        "approval": appr_path,
        "denials": denial_path,
        "hhi_county": hhi_cty_path,
        "hhi_msa": hhi_msa_path,
    }



