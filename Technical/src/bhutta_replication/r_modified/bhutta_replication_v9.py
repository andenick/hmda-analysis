"""
Bhutta (2011) RD Replication - Version 9 (Annualized Origination Rate)

HYPOTHESIS: Bhutta's orig_per_oou filter may be ANNUAL, not 9-year aggregate.

Our current approach:
- Total originations 1994-2002 / OOU = 0.41 mean for purchase-only
- Filter 0.25-20 drops most tracts

Bhutta approach (hypothesized):
- Annual originations per OOU (average across years)
- Annual rate of ~0.04-0.05 is typical (4-5% of housing stock turns over annually)

Testing:
1. Use annual average originations / OOU
2. Different filter thresholds for annual data
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
    str(DATA_ROOT / "Technical/src/bhutta_replication/r_modified/output_v9")
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
    result["orig_per_oou_total"] = result["num_loans"] / result["owner_occupied_units"]
    # Annualized rate (9 years of data)
    result["orig_per_oou_annual"] = result["orig_per_oou_total"] / 9
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
    print("BHUTTA (2011) RD REPLICATION - VERSION 9 (ANNUALIZED ORIG RATE)")
    print("=" * 70)
    print()

    # Load census
    print("Loading census data...")
    census = load_census()
    large_msas = get_large_msas(census)
    print(f"  Large MSAs: {len(large_msas)}")

    # Load HMDA - PURCHASE ONLY
    print("\nLoading HMDA data (purchase only, bank-only)...")
    hmda_dfs = []
    for year in YEARS:
        df = load_hmda_year(year, bank_only=True, purchase_only=True)
        if len(df) > 0:
            hmda_dfs.append(df)

    hmda = pd.concat(hmda_dfs, ignore_index=True)
    print(f"  Total purchase loans: {len(hmda):,}")

    # Aggregate
    tract_agg = aggregate_hmda(hmda)

    # Merge with census
    merged = census.merge(
        tract_agg[["msa_tract_key", "num_loans"]],
        on="msa_tract_key",
        how="left",
    )
    merged["num_loans"] = merged["num_loans"].fillna(0)

    # Create variables
    df = create_vars(merged.copy())
    df = df[df["msa_code"].isin(large_msas)]

    # Apply base filters
    df = df[~df["state_code"].isin(["02", "15", "2"])]
    df = df[df["total_housing_units"] >= 100]
    df = df[df["owner_occupied_units"] > 0]
    df = df[df["pct_group_quarters"] < 0.30]
    df = df[df["num_loans"] > 0]

    print("\n" + "=" * 70)
    print("ANNUALIZED ORIGINATION RATE ANALYSIS")
    print("=" * 70)

    # Check the distribution of annualized rates
    in_bw = df[(df["TM"] >= 0.75) & (df["TM"] <= 0.85)]
    print(f"\nTracts in bandwidth (before filter): {len(in_bw):,}")
    print(f"\nANNUAL origination rate stats (per OOU per year):")
    print(f"  Mean: {in_bw['orig_per_oou_annual'].mean():.4f}")
    print(f"  Median: {in_bw['orig_per_oou_annual'].median():.4f}")
    print(f"  Min: {in_bw['orig_per_oou_annual'].min():.4f}")
    print(f"  Max: {in_bw['orig_per_oou_annual'].max():.4f}")
    print(f"  25th percentile: {in_bw['orig_per_oou_annual'].quantile(0.25):.4f}")
    print(f"  75th percentile: {in_bw['orig_per_oou_annual'].quantile(0.75):.4f}")

    print(f"\n9-YEAR TOTAL origination rate stats (per OOU over 9 years):")
    print(f"  Mean: {in_bw['orig_per_oou_total'].mean():.4f}")
    print(f"  Median: {in_bw['orig_per_oou_total'].median():.4f}")

    # Test different filter thresholds
    print("\n" + "=" * 70)
    print("TESTING DIFFERENT ANNUAL RATE FILTERS")
    print("=" * 70)

    # Using annual rate
    thresholds = [
        (0, 100, "No filter"),
        (0.01, 100, "Annual >= 0.01 (1%)"),
        (0.02, 100, "Annual >= 0.02 (2%)"),
        (0.03, 100, "Annual >= 0.03 (3%)"),
        (0.04, 100, "Annual >= 0.04 (4%)"),
        (0.05, 100, "Annual >= 0.05 (5%)"),
    ]

    results = []
    for lower, upper, name in thresholds:
        filtered = df[
            (df["orig_per_oou_annual"] >= lower) & (df["orig_per_oou_annual"] <= upper)
        ]
        result = run_rd(filtered)
        print(f"\n{name}:")
        print(f"  β = {result['coef']:.4f}, N = {result['n']:,}")
        results.append({"filter": name, **result})

    # Also test the 9-year total filter that we've been using
    print("\n" + "=" * 70)
    print("COMPARISON: 9-YEAR TOTAL vs ANNUAL FILTER")
    print("=" * 70)

    print("\n9-year total >= 0.25 (current filter):")
    filtered = df[df["orig_per_oou_total"] >= 0.25]
    result = run_rd(filtered)
    print(f"  β = {result['coef']:.4f}, N = {result['n']:,}")

    # 0.25 / 9 = 0.0278 per year
    print(f"\nEquivalent annual rate = 0.25 / 9 = {0.25/9:.4f}")
    print("\nAnnual >= 0.028 (equivalent to 9-year total >= 0.25):")
    filtered = df[df["orig_per_oou_annual"] >= 0.028]
    result = run_rd(filtered)
    print(f"  β = {result['coef']:.4f}, N = {result['n']:,}")

    # Find the threshold that gives N ~ 1800
    print("\n" + "=" * 70)
    print("FINDING THRESHOLD FOR N ~ 1,800")
    print("=" * 70)

    for thresh in np.arange(0.000, 0.035, 0.002):
        filtered = df[df["orig_per_oou_annual"] >= thresh]
        sample = filtered[(filtered["TM"] >= 0.75) & (filtered["TM"] <= 0.85)]
        if 1700 <= len(sample) <= 1900:
            result = run_rd(filtered)
            print(
                f"  Annual >= {thresh:.3f}: N = {result['n']:,}, β = {result['coef']:.4f}"
            )


if __name__ == "__main__":
    main()
