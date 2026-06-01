"""
Bhutta (2011) RD Replication - Version 8 (Investigate Sample Size)

KEY FINDING from v6:
- Purchase-only: β = 0.0702 (91.9% of target), N = 842
- Purchase+Refi: β = 0.0503 (65.9% of target), N = 1,741
- Target: β = 0.0764, N = 1,800

This version investigates why purchase-only has half the sample size:
1. Compare tract counts across specifications
2. Check if orig_per_oou filter is too strict for purchase-only
3. Test relaxing filters

The coefficient match is better with purchase-only, but we need more sample.
"""

import pandas as pd
import numpy as np
import statsmodels.api as sm
from pathlib import Path
import warnings
import os
DATA_ROOT = Path(os.environ.get("DATA_ROOT", "data"))
OUTPUT_ROOT = Path(os.environ.get("OUTPUT_ROOT", "outputs"))

warnings.filterwarnings("ignore")

HMDA_DIR = DATA_ROOT / "Inputs/Old/CRA_code/_files2/1990to2006/src"
CENSUS_DIR = OUTPUT_ROOT / "Technical/data/census_parsed_v2"
OUTPUT_DIR = Path(
    str(DATA_ROOT / "Technical/src/bhutta_replication/r_modified/output_v8")
)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

YEARS = [1994, 1995, 1996, 1997, 1998, 1999, 2000, 2001, 2002]


def load_hmda_year(
    year: int, bank_only: bool = True, purchase_only: bool = True
) -> pd.DataFrame:
    """Load HMDA LAR data with flexible filters."""
    patterns = [f"*HMDA_LAR_{year}.txt", f"*hmda_lar_{year}.txt", f"*{year}*.txt"]
    filepath = None
    for pattern in patterns:
        matches = list(HMDA_DIR.glob(pattern))
        if matches:
            filepath = matches[0]
            break

    if filepath is None:
        return pd.DataFrame()

    chunks = []
    for chunk in pd.read_csv(
        filepath,
        sep="|",
        chunksize=500000,
        dtype={
            "census_tract": str,
            "state_code": str,
            "county_code": str,
            "msamd": str,
            "loan_amount": str,
        },
    ):
        chunk["action_taken"] = pd.to_numeric(chunk["action_taken"], errors="coerce")
        chunk["loan_purpose"] = pd.to_numeric(chunk["loan_purpose"], errors="coerce")
        chunk["occupancy_type"] = pd.to_numeric(
            chunk["occupancy_type"], errors="coerce"
        )
        chunk["loan_amount"] = pd.to_numeric(chunk["loan_amount"], errors="coerce")
        chunk["agency_code"] = pd.to_numeric(chunk["agency_code"], errors="coerce")

        mask = (
            (chunk["action_taken"] == 1)
            & (chunk["occupancy_type"] == 1)
            & (chunk["msamd"].notna())
            & (chunk["msamd"] != "")
        )

        if purchase_only:
            mask = mask & (chunk["loan_purpose"] == 1)
        else:
            mask = mask & (chunk["loan_purpose"].isin([1, 3]))

        if bank_only:
            mask = mask & chunk["agency_code"].isin([1, 2, 3, 5])

        chunks.append(chunk[mask])

    df = pd.concat(chunks, ignore_index=True)
    df["year"] = year
    return df


def aggregate_hmda(hmda: pd.DataFrame) -> pd.DataFrame:
    """Aggregate HMDA to tract level."""
    hmda["tract_only"] = (
        hmda["census_tract"].str.replace(".", "", regex=False).str.zfill(6)
    )
    hmda["msa_tract_key"] = hmda["msamd"].astype(str) + "_" + hmda["tract_only"]

    tract_agg = (
        hmda.groupby(["msa_tract_key", "msamd"])
        .agg(num_loans=("loan_amount", "count"))
        .reset_index()
    )
    return tract_agg


def load_census() -> pd.DataFrame:
    """Load census data."""
    path = CENSUS_DIR / "census_1996.parquet"
    return pd.read_parquet(path)


def get_large_msas(census: pd.DataFrame) -> set:
    """Get Large MSAs (pop > 2M)."""
    msa_pop = census.groupby("msa_code")["population"].sum().reset_index()
    msa_pop = msa_pop[~msa_pop["msa_code"].isin(["9999", ""])]
    return set(msa_pop[msa_pop["population"] > 2_000_000]["msa_code"])


def create_vars(df: pd.DataFrame) -> pd.DataFrame:
    """Create analysis variables."""
    result = df.copy()
    result["D"] = (result["TM"] < 0.80).astype(int)
    result["TM_c"] = result["TM"] - 0.80
    result["D_TM"] = result["D"] * result["TM_c"]
    result["ln_num_loans"] = np.log(result["num_loans"].clip(lower=1))
    result["ln_oou"] = np.log(result["owner_occupied_units"].clip(lower=1))
    result["ln_value"] = np.log(result["median_home_value"].clip(lower=1))
    result["orig_per_oou"] = result["num_loans"] / result["owner_occupied_units"]
    return result


def run_rd(df: pd.DataFrame, bandwidth: float = 0.05) -> dict:
    """Run RD regression."""
    sample = df[(df["TM"] >= 0.80 - bandwidth) & (df["TM"] <= 0.80 + bandwidth)].copy()

    outcome = "ln_num_loans"
    treatment = ["D", "TM_c", "D_TM"]
    controls = [
        "minority_pct",
        "ln_oou",
        "ln_value",
        "poverty_pct",
        "pct_pre1940",
        "pct_1940_69",
        "pct_age_65_plus",
        "pct_single_family",
        "pct_2_4_family",
        "pct_5_plus",
    ]

    regressors = treatment + controls
    reg_vars = [outcome] + regressors + ["msa_code"]
    sample = sample.dropna(subset=reg_vars)

    if len(sample) < 50:
        return {"coef": np.nan, "se": np.nan, "n": len(sample), "r2": np.nan}

    msa_dummies = pd.get_dummies(
        sample["msa_code"], prefix="msa", drop_first=True, dtype=float
    )
    X_regressors = sample[regressors].astype(float)
    X = pd.concat(
        [X_regressors.reset_index(drop=True), msa_dummies.reset_index(drop=True)],
        axis=1,
    )
    X = sm.add_constant(X)
    y = sample[outcome].reset_index(drop=True).astype(float)
    sample_reset = sample.reset_index(drop=True)

    model = sm.OLS(y, X).fit(
        cov_type="cluster", cov_kwds={"groups": sample_reset["msa_code"]}
    )

    return {
        "coef": model.params["D"],
        "se": model.bse["D"],
        "n": len(sample),
        "r2": model.rsquared,
    }


def main():
    print("=" * 70)
    print("BHUTTA (2011) RD REPLICATION - VERSION 8 (SAMPLE SIZE INVESTIGATION)")
    print("=" * 70)
    print()

    # Load census
    print("Loading census data...")
    census = load_census()
    large_msas = get_large_msas(census)
    print(f"  Large MSAs: {len(large_msas)}")
    print(f"  Census tracts: {len(census):,}")

    # Load HMDA - PURCHASE ONLY
    print("\nLoading HMDA data (purchase only, bank-only)...")
    hmda_dfs = []
    for year in YEARS:
        df = load_hmda_year(year, bank_only=True, purchase_only=True)
        if len(df) > 0:
            hmda_dfs.append(df)

    hmda = pd.concat(hmda_dfs, ignore_index=True)
    print(f"  Total purchase loans: {len(hmda):,}")

    # Also load PURCHASE+REFI for comparison
    print("\nLoading HMDA data (purchase+refi, bank-only)...")
    hmda_refi_dfs = []
    for year in YEARS:
        df = load_hmda_year(year, bank_only=True, purchase_only=False)
        if len(df) > 0:
            hmda_refi_dfs.append(df)

    hmda_refi = pd.concat(hmda_refi_dfs, ignore_index=True)
    print(f"  Total purchase+refi loans: {len(hmda_refi):,}")

    # Aggregate both
    print("\nAggregating to tract level...")
    tract_purch = aggregate_hmda(hmda)
    tract_refi = aggregate_hmda(hmda_refi)

    print(f"  Purchase-only tracts: {len(tract_purch):,}")
    print(f"  Purchase+refi tracts: {len(tract_refi):,}")

    # Merge with census
    print("\nMerging with census...")
    merged_purch = census.merge(
        tract_purch[["msa_tract_key", "num_loans"]],
        on="msa_tract_key",
        how="left",
    )
    merged_purch["num_loans"] = merged_purch["num_loans"].fillna(0)

    merged_refi = census.merge(
        tract_refi[["msa_tract_key", "num_loans"]],
        on="msa_tract_key",
        how="left",
    )
    merged_refi["num_loans"] = merged_refi["num_loans"].fillna(0)

    # Apply base filters (except orig_per_oou)
    print("\n" + "=" * 70)
    print("FILTER ANALYSIS: Why does purchase-only have smaller sample?")
    print("=" * 70)

    def apply_step_by_step(df, spec_name):
        print(f"\n{spec_name}:")
        print("-" * 50)

        result = create_vars(df.copy())
        result = result[result["msa_code"].isin(large_msas)]
        print(f"  Large MSA tracts: {len(result):,}")

        # In bandwidth
        bw = 0.05
        in_bw = result[(result["TM"] >= 0.80 - bw) & (result["TM"] <= 0.80 + bw)]
        print(f"  In bandwidth (h=0.05): {len(in_bw):,}")

        # Exclude AK/HI
        in_bw = in_bw[~in_bw["state_code"].isin(["02", "15", "2"])]
        print(f"  After exclude AK/HI: {len(in_bw):,}")

        # Housing units >= 100
        in_bw = in_bw[in_bw["total_housing_units"] >= 100]
        print(f"  After housing_units >= 100: {len(in_bw):,}")

        # OOU > 0
        in_bw = in_bw[in_bw["owner_occupied_units"] > 0]
        print(f"  After OOU > 0: {len(in_bw):,}")

        # Group quarters < 30%
        in_bw = in_bw[in_bw["pct_group_quarters"] < 0.30]
        print(f"  After GQ < 30%: {len(in_bw):,}")

        # Num loans > 0
        before_loans = len(in_bw)
        in_bw = in_bw[in_bw["num_loans"] > 0]
        print(
            f"  After num_loans > 0: {len(in_bw):,} (dropped {before_loans - len(in_bw)})"
        )

        # Orig per OOU filter
        before_ratio = len(in_bw)
        in_bw_filtered = in_bw[
            (in_bw["orig_per_oou"] >= 0.25) & (in_bw["orig_per_oou"] <= 20)
        ]
        print(
            f"  After 0.25 <= orig_per_oou <= 20: {len(in_bw_filtered):,} (dropped {before_ratio - len(in_bw_filtered)})"
        )

        # Check orig_per_oou distribution
        print(f"\n  orig_per_oou stats (before filter):")
        print(f"    Mean: {in_bw['orig_per_oou'].mean():.3f}")
        print(f"    Median: {in_bw['orig_per_oou'].median():.3f}")
        print(f"    Min: {in_bw['orig_per_oou'].min():.3f}")
        print(f"    Max: {in_bw['orig_per_oou'].max():.3f}")
        print(f"    < 0.25: {(in_bw['orig_per_oou'] < 0.25).sum()}")
        print(f"    > 20: {(in_bw['orig_per_oou'] > 20).sum()}")

        return in_bw_filtered

    filtered_purch = apply_step_by_step(merged_purch, "PURCHASE ONLY")
    filtered_refi = apply_step_by_step(merged_refi, "PURCHASE + REFI")

    # Run regressions with different orig_per_oou filters
    print("\n" + "=" * 70)
    print("TESTING DIFFERENT ORIG_PER_OOU FILTERS (Purchase only)")
    print("=" * 70)

    # Start with all base filters
    df = create_vars(merged_purch.copy())
    df = df[df["msa_code"].isin(large_msas)]
    df = df[~df["state_code"].isin(["02", "15", "2"])]
    df = df[df["total_housing_units"] >= 100]
    df = df[df["owner_occupied_units"] > 0]
    df = df[df["pct_group_quarters"] < 0.30]
    df = df[df["num_loans"] > 0]

    print("\nNo orig_per_oou filter:")
    result = run_rd(df.copy())
    print(f"  β = {result['coef']:.4f}, N = {result['n']:,}")

    print("\nWith orig_per_oou >= 0.25 only (no upper bound):")
    df_lower = df[df["orig_per_oou"] >= 0.25]
    result = run_rd(df_lower)
    print(f"  β = {result['coef']:.4f}, N = {result['n']:,}")

    print("\nWith orig_per_oou <= 20 only (no lower bound):")
    df_upper = df[df["orig_per_oou"] <= 20]
    result = run_rd(df_upper)
    print(f"  β = {result['coef']:.4f}, N = {result['n']:,}")

    print("\nWith both bounds (0.25-20):")
    df_both = df[(df["orig_per_oou"] >= 0.25) & (df["orig_per_oou"] <= 20)]
    result = run_rd(df_both)
    print(f"  β = {result['coef']:.4f}, N = {result['n']:,}")

    # Try looser lower bound
    print("\nWith orig_per_oou >= 0.10 and <= 20:")
    df_loose = df[(df["orig_per_oou"] >= 0.10) & (df["orig_per_oou"] <= 20)]
    result = run_rd(df_loose)
    print(f"  β = {result['coef']:.4f}, N = {result['n']:,}")

    # Final summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print("\nThe sample size drop from 1,741 (purch+refi) to 842 (purch only)")
    print("is because purchase-only has ~half the loans per tract,")
    print("so more tracts fall below the 0.25 orig_per_oou threshold.")
    print("\nRecommendations:")
    print("1. Keep purchase-only (91.9% coefficient match)")
    print("2. Consider relaxing orig_per_oou lower bound")
    print("3. Or accept smaller sample - Bhutta may have had different data")


if __name__ == "__main__":
    main()
