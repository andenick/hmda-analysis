"""
Bhutta (2011) RD Replication - Version 7 (Purchase Only + Bandwidth Tests)

KEY FINDING from v6: Purchase-only gives β = 0.0702 (91.9% of target)
BUT sample size N = 842 is too small (target = 1,800)

This version tests:
1. Purchase-only with different bandwidths to increase sample
2. Purchase-only with less restrictive sample filters
3. Check if the N discrepancy is from group quarters filter

Target: β = +0.0764, SE = 0.0274, N = 1,800
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
    str(DATA_ROOT / "Technical/src/bhutta_replication/r_modified/output_v7")
)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

YEARS = [1994, 1995, 1996, 1997, 1998, 1999, 2000, 2001, 2002]

BHUTTA_TARGETS = {
    "large_msas_h05": {"coef": 0.0764, "se": 0.0274, "n": 1800},
}


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

        # Base filters
        mask = (
            (chunk["action_taken"] == 1)
            & (chunk["occupancy_type"] == 1)
            & (chunk["msamd"].notna())
            & (chunk["msamd"] != "")
        )

        # Loan purpose filter
        if purchase_only:
            mask = mask & (chunk["loan_purpose"] == 1)  # Home purchase only
        else:
            mask = mask & (chunk["loan_purpose"].isin([1, 3]))  # Purchase + Refi

        # Agency filter (banks only vs all lenders)
        if bank_only:
            mask = mask & chunk["agency_code"].isin([1, 2, 3, 5])

        filtered = chunk[mask][
            ["state_code", "county_code", "census_tract", "msamd", "loan_amount"]
        ].copy()
        filtered["year"] = year
        chunks.append(filtered)

    return pd.concat(chunks, ignore_index=True) if chunks else pd.DataFrame()


def load_census_year(year: int) -> pd.DataFrame:
    """Load census data for a year."""
    filepath = CENSUS_DIR / f"census_{year}.parquet"
    if filepath.exists():
        df = pd.read_parquet(filepath)
        # Standardize column names to match v5/v6 expectations
        rename_map = {
            "msa_code": "msamd",
            "minority_pct": "tract_minority_pct",
            "population": "total_pop",
            "pct_age_65_plus": "pct_age65plus",
            "pct_2_4_family": "pct_2_4_units",
            "pct_5_plus": "pct_5plus_units",
        }
        df = df.rename(columns=rename_map)
        # Create tract_fips
        df["state_code"] = df["state_code"].astype(str).str.zfill(2)
        df["county_code"] = df["county_code"].astype(str).str.zfill(3)
        df["tract"] = df["tract"].astype(str).str.zfill(7)
        df["tract_fips"] = df["state_code"] + df["county_code"] + df["tract"]
        return df
    return pd.DataFrame()


def create_fips(df: pd.DataFrame) -> pd.DataFrame:
    """Create tract FIPS code."""
    df = df.copy()
    df["state_code"] = df["state_code"].str.zfill(2)
    df["county_code"] = df["county_code"].str.zfill(3)
    df["census_tract"] = df["census_tract"].str.zfill(7)
    df["tract_fips"] = df["state_code"] + df["county_code"] + df["census_tract"]
    return df


def run_rd_regression(
    data: pd.DataFrame,
    bandwidth: float = 0.05,
    threshold: float = 0.80,
    use_explicit_fe: bool = True,
) -> dict:
    """Run RD regression with MSA fixed effects."""
    df = data.copy()

    # Create running variable centered at threshold
    df["tm_centered"] = df["tract_minority_pct"] - threshold

    # Filter to bandwidth
    df = df[np.abs(df["tm_centered"]) <= bandwidth]

    if len(df) < 50:
        return {"coef": np.nan, "se": np.nan, "n": len(df), "r2": np.nan}

    # Treatment indicator
    df["D"] = (df["tm_centered"] < 0).astype(int)

    # Control variables
    controls = [
        "tract_minority_pct",
        "ln_oou",
        "ln_median_value",
        "pct_pre1940",
        "pct_1940_69",
        "pct_age65plus",
        "pct_single_family",
        "pct_2_4_units",
        "pct_5plus_units",
    ]

    available_controls = [
        c for c in controls if c in df.columns and df[c].notna().sum() > 0
    ]

    # Build design matrix
    if use_explicit_fe:
        # Explicit MSA dummies
        msa_dummies = pd.get_dummies(df["msamd"], prefix="msa", drop_first=True)
        X = pd.concat(
            [
                df[["D", "tm_centered"] + available_controls].reset_index(drop=True),
                msa_dummies.reset_index(drop=True),
            ],
            axis=1,
        )
    else:
        X = df[["D", "tm_centered"] + available_controls]

    X = sm.add_constant(X)
    y = df["ln_total_loans"]

    # Remove any remaining NaNs
    valid = X.notna().all(axis=1) & y.notna()
    X = X[valid]
    y = y[valid]

    if len(y) < 50:
        return {"coef": np.nan, "se": np.nan, "n": len(y), "r2": np.nan}

    # OLS with MSA-clustered standard errors
    model = sm.OLS(y, X)
    clusters = df.loc[valid.values, "msamd"]
    results = model.fit(cov_type="cluster", cov_kwds={"groups": clusters})

    return {
        "coef": results.params.get("D", np.nan),
        "se": results.bse.get("D", np.nan),
        "n": int(results.nobs),
        "r2": results.rsquared,
    }


def main():
    print("=" * 70)
    print("BHUTTA (2011) RD REPLICATION - VERSION 7 (PURCHASE ONLY FOCUS)")
    print("=" * 70)

    # Load census data and identify Large MSAs
    print("\nLoading census data...")
    census_frames = []
    for year in YEARS:
        cdf = load_census_year(year)
        if not cdf.empty:
            cdf["year"] = year
            census_frames.append(cdf)

    census = pd.concat(census_frames, ignore_index=True)

    # Large MSAs = 500,000+ population
    msa_pop = census.groupby("msamd")["total_pop"].sum()
    large_msas = set(msa_pop[msa_pop >= 500000].index)
    print(f"  Large MSAs: {len(large_msas)}")

    # Load HMDA data - HOME PURCHASE ONLY
    print("\nLoading HMDA data (home purchase only, bank-only)...")
    hmda_frames = []
    for year in YEARS:
        print(f"  Loading {year}...", end=" ", flush=True)
        df = load_hmda_year(year, bank_only=True, purchase_only=True)
        if not df.empty:
            hmda_frames.append(df)
            print(f"{len(df):,} loans")
        else:
            print("no data")

    hmda = pd.concat(hmda_frames, ignore_index=True)
    print(f"  Total loans: {len(hmda):,}")

    # Create tract identifiers
    hmda = create_fips(hmda)

    # Aggregate to tract level
    tract_loans = (
        hmda.groupby(["tract_fips", "msamd"])
        .agg(
            total_loans=("loan_amount", "size"),
            total_amount=("loan_amount", "sum"),
        )
        .reset_index()
    )

    print(f"  Total unique tracts: {len(tract_loans):,}")

    # Merge with census (average across years for tract characteristics)
    census_avg = (
        census.groupby("tract_fips")
        .agg(
            {
                "tract_minority_pct": "mean",
                "owner_occupied_units": "mean",
                "median_home_value": "mean",
                "pct_pre1940": "mean",
                "pct_1940_69": "mean",
                "pct_age65plus": "mean",
                "pct_single_family": "mean",
                "pct_2_4_units": "mean",
                "pct_5plus_units": "mean",
                "pct_group_quarters": "mean",
            }
        )
        .reset_index()
    )

    merged = tract_loans.merge(census_avg, on="tract_fips", how="inner")

    # Add derived variables
    merged["ln_total_loans"] = np.log(merged["total_loans"].clip(lower=1))
    merged["ln_oou"] = np.log(merged["owner_occupied_units"].clip(lower=1))
    merged["ln_median_value"] = np.log(merged["median_home_value"].clip(lower=1))

    # Filter to Large MSAs
    merged_large = merged[merged["msamd"].isin(large_msas)]
    print(f"  Large MSA tracts: {len(merged_large):,}")

    # Test different configurations
    print("\n" + "=" * 70)
    print("TESTING DIFFERENT SPECIFICATIONS")
    print("=" * 70)

    results = []

    # Test 1: No group quarters filter
    print("\n1. Purchase only, NO group quarters filter")
    print("-" * 50)
    result = run_rd_regression(merged_large, bandwidth=0.05)
    print(f"   β = {result['coef']:.4f}, N = {result['n']:,}, R² = {result['r2']:.4f}")
    results.append({"spec": "Purchase, no GQ filter", **result})

    # Test 2: With group quarters filter
    print("\n2. Purchase only, WITH group quarters filter (<30%)")
    print("-" * 50)
    merged_gq = merged_large[merged_large["pct_group_quarters"] < 0.30]
    result = run_rd_regression(merged_gq, bandwidth=0.05)
    print(f"   β = {result['coef']:.4f}, N = {result['n']:,}, R² = {result['r2']:.4f}")
    results.append({"spec": "Purchase, GQ<30%", **result})

    # Test 3: Wider bandwidths with no GQ filter
    print("\n3. Different bandwidths (no GQ filter)")
    print("-" * 50)
    for bw in [0.05, 0.10, 0.15, 0.20]:
        result = run_rd_regression(merged_large, bandwidth=bw)
        print(f"   h={bw:.2f}: β = {result['coef']:.4f}, N = {result['n']:,}")
        results.append({"spec": f"Purchase, h={bw}", **result})

    # Test 4: Check if the sample size issue is from empty tracts
    print("\n4. Checking sample in bandwidth (h=0.05)")
    print("-" * 50)
    in_bw = merged_large[np.abs(merged_large["tract_minority_pct"] - 0.80) <= 0.05]
    print(f"   Tracts in bandwidth: {len(in_bw):,}")
    print(f"   Tracts with loans > 0: {len(in_bw[in_bw['total_loans'] > 0]):,}")
    print(f"   Mean loans per tract: {in_bw['total_loans'].mean():.1f}")

    # Test 5: Year-specific sample counts
    print("\n5. Checking sample by bandwidth around threshold")
    print("-" * 50)
    for bw in [0.03, 0.05, 0.07, 0.10]:
        in_bw = merged_large[np.abs(merged_large["tract_minority_pct"] - 0.80) <= bw]
        below = len(in_bw[in_bw["tract_minority_pct"] < 0.80])
        above = len(in_bw[in_bw["tract_minority_pct"] >= 0.80])
        print(f"   h={bw:.2f}: Total={len(in_bw):,} (below={below}, above={above})")

    # Test 6: Minimum loans filter
    print("\n6. Testing with minimum loan thresholds")
    print("-" * 50)
    for min_loans in [1, 10, 50, 100]:
        filtered = merged_large[merged_large["total_loans"] >= min_loans]
        result = run_rd_regression(filtered, bandwidth=0.05)
        print(
            f"   min_loans>={min_loans}: β = {result['coef']:.4f}, N = {result['n']:,}"
        )

    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY: KEY RESULTS")
    print("=" * 70)

    print("\nBest result from v6: Purchase only gave β = 0.0702 (91.9% of target)")
    print(f"Target: β = 0.0764, N = 1,800")

    print("\nThis version's results:")
    for r in results[:4]:
        match_pct = (r["coef"] / 0.0764) * 100 if r["coef"] else 0
        print(
            f"  {r['spec']}: β = {r['coef']:.4f}, N = {r['n']:,}, Match = {match_pct:.1f}%"
        )

    # Save results
    results_df = pd.DataFrame(results)
    results_df.to_csv(OUTPUT_DIR / "bandwidth_tests.csv", index=False)
    print(f"\nResults saved to: {OUTPUT_DIR / 'bandwidth_tests.csv'}")


if __name__ == "__main__":
    main()
