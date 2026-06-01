"""
Bhutta (2011) RD Replication - VERSION 11 (100% Match Attempt)

This version implements ALL methodological fixes identified from detailed
analysis of Bhutta's original paper:

KEY CHANGES FROM v10 (FINAL):
1. ORIGINATION RATE FILTER: Bhutta's exact filter (0.25-20 per OOU over 9 years)
   instead of annual >= 2%
2. CONTROL VARIABLES: Exact match to Table 1:
   - pct_black and pct_hispanic SEPARATELY (not combined minority_pct)
   - pct_mobile_homes (was missing)
   - pct_built_1980_89 (was missing)
   - ln_total_hu (per footnote 20)
   - REMOVED poverty_pct (not in Bhutta's specification)
3. LOAN TYPES: Tests BOTH specifications:
   - Spec A: All loans (purchase + refinance + home improvement) per Table 2 note
   - Spec B: Purchase only (current approach that gave 99.4%)

TARGETS (Table 2, Row 4 - Large MSAs, h=0.05, Linear):
- Coefficient: 0.0764
- SE: 0.0274
- N: 1,800
- R²: 0.869

Uses v3 census data with all new variables.
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

# Directories
HMDA_DIR = DATA_ROOT / "Inputs/Old/CRA_code/_files2/1990to2006/src"
CENSUS_DIR = OUTPUT_ROOT / "Technical/data/census_parsed_v3"
OUTPUT_DIR = Path(
    str(DATA_ROOT / "Technical/src/bhutta_replication/r_modified/output_v11")
)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

YEARS = [1994, 1995, 1996, 1997, 1998, 1999, 2000, 2001, 2002]

BHUTTA_TARGETS = {
    "large_msas_h05": {"coef": 0.0764, "se": 0.0274, "n": 1800, "r2": 0.869},
}


def load_hmda_year(year: int, loan_types: str = "all") -> pd.DataFrame:
    """
    Load HMDA LAR data with specified loan type filter.

    Args:
        year: Year of data
        loan_types: "all" for purchase+refi+improvement, "purchase" for purchase only
    """
    patterns = [f"*HMDA_LAR_{year}.txt"]
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
            "respondent_id": str,
        },
        low_memory=False,
    ):
        chunk["action_taken"] = pd.to_numeric(chunk["action_taken"], errors="coerce")
        chunk["loan_purpose"] = pd.to_numeric(chunk["loan_purpose"], errors="coerce")
        chunk["occupancy_type"] = pd.to_numeric(
            chunk["occupancy_type"], errors="coerce"
        )
        chunk["loan_amount"] = pd.to_numeric(chunk["loan_amount"], errors="coerce")
        chunk["agency_code"] = pd.to_numeric(chunk["agency_code"], errors="coerce")

        # Base Bhutta specification filters
        mask = (
            (chunk["action_taken"] == 1)  # Originated loans
            & (chunk["occupancy_type"] == 1)  # Owner-occupied
            & (chunk["msamd"].notna())  # In an MSA
            & (chunk["msamd"] != "")
            & (chunk["agency_code"].isin([1, 2, 3, 5]))  # CRA-covered banks only
        )

        # Loan type filter
        if loan_types == "purchase":
            mask = mask & (chunk["loan_purpose"] == 1)
        elif loan_types == "all":
            # Home purchase (1) + refinance (3) + home improvement (2)
            # Note: In 1990s HMDA, loan_purpose codes are: 1=purchase, 2=improvement, 3=refi
            mask = mask & (chunk["loan_purpose"].isin([1, 2, 3]))
        else:
            raise ValueError(f"Unknown loan_types: {loan_types}")

        chunks.append(chunk[mask])

    df = pd.concat(chunks, ignore_index=True)
    df["year"] = year
    return df


def aggregate_hmda(hmda: pd.DataFrame) -> pd.DataFrame:
    """Aggregate HMDA to tract level (sum over 1994-2002)."""
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
    """Load census data (1996 as reference year for tract characteristics)."""
    path = CENSUS_DIR / "census_1996.parquet"
    return pd.read_parquet(path)


def get_large_msas(census: pd.DataFrame) -> set:
    """Get Large MSAs (pop > 2M) per Bhutta definition."""
    msa_pop = census.groupby("msa_code")["population"].sum().reset_index()
    msa_pop = msa_pop[~msa_pop["msa_code"].isin(["9999", ""])]
    return set(msa_pop[msa_pop["population"] > 2_000_000]["msa_code"])


def apply_bhutta_filters(
    df: pd.DataFrame, use_bhutta_exact_filter: bool = True
) -> pd.DataFrame:
    """
    Apply Bhutta (2011) sample restrictions.

    From paper p. 461:
    "I drop tracts that had fewer than 100 housing units (in 1990), zero (specified)
    owner-occupied units, more than 30 percent of the population in group quarters,
    and either fewer than .25 or more than 20 originations per (1990) owner-occupied
    unit over the entire 1994-2002 period."
    """
    result = df.copy()

    print(f"  Starting tracts: {len(result):,}")

    # Exclude Alaska and Hawaii
    result = result[~result["state_code"].isin(["02", "15", "2"])]
    print(f"  After excluding AK/HI: {len(result):,}")

    # Total housing units >= 100
    result = result[result["total_housing_units"] >= 100]
    print(f"  After HU >= 100: {len(result):,}")

    # Owner-occupied units > 0
    result = result[result["owner_occupied_units"] > 0]
    print(f"  After OOU > 0: {len(result):,}")

    # Group quarters < 30% of population
    result = result[result["pct_group_quarters"] < 0.30]
    print(f"  After GQ < 30%: {len(result):,}")

    # Must have positive loans
    result = result[result["num_loans"] > 0]
    print(f"  After num_loans > 0: {len(result):,}")

    # Origination rate filter
    result["orig_per_oou_total"] = result["num_loans"] / result["owner_occupied_units"]

    if use_bhutta_exact_filter:
        # BHUTTA'S EXACT FILTER: 0.25-20 originations per OOU over 9 years
        result = result[
            (result["orig_per_oou_total"] >= 0.25)
            & (result["orig_per_oou_total"] <= 20)
        ]
        print(f"  After Bhutta filter (0.25-20 per OOU): {len(result):,}")
    else:
        # Previous filter: Annual origination rate >= 2%
        result["orig_per_oou_annual"] = result["orig_per_oou_total"] / 9
        result = result[result["orig_per_oou_annual"] >= 0.02]
        print(f"  After annual >= 2% filter: {len(result):,}")

    return result


def create_rd_vars(df: pd.DataFrame) -> pd.DataFrame:
    """Create RD regression variables with Bhutta-exact controls."""
    result = df.copy()

    # Treatment indicator: D = 1 if TM < 80%
    result["D"] = (result["TM"] < 0.80).astype(int)

    # Running variable centered at threshold
    result["TM_c"] = result["TM"] - 0.80

    # Interaction for local linear
    result["D_TM"] = result["D"] * result["TM_c"]

    # Outcome: log total originations
    result["ln_num_loans"] = np.log(result["num_loans"].clip(lower=1))

    # Log controls (per Bhutta footnote 20)
    result["ln_total_hu"] = np.log(result["total_housing_units"].clip(lower=1))
    result["ln_oou"] = np.log(result["owner_occupied_units"].clip(lower=1))
    result["ln_value"] = np.log(result["median_home_value"].clip(lower=1))

    return result


def run_rd_regression(df: pd.DataFrame, bandwidth: float = 0.05) -> dict:
    """
    Run RD regression with MSA fixed effects and clustered SEs.

    Uses Bhutta Table 1 exact control variables:
    - ln(Housing units), ln(Owner-occupied units), ln(Median home value)
    - % Detached, % Multifamily, % Mobile homes
    - % Built 1980-89, % Built 1940-69, % Built before 1940
    - % Black, % Hispanic, % Age > 65
    """

    # Restrict to bandwidth
    sample = df[(df["TM"] >= 0.80 - bandwidth) & (df["TM"] <= 0.80 + bandwidth)].copy()

    # Outcome
    outcome = "ln_num_loans"

    # Regressors: treatment, running variable, interaction
    treatment_vars = ["D", "TM_c", "D_TM"]

    # Control variables - EXACT match to Bhutta Table 1 + footnote 20
    controls = [
        # Log transforms (footnote 20)
        "ln_total_hu",  # Log housing units
        "ln_oou",  # Log owner-occupied units
        "ln_value",  # Log median home value
        # Property type (Table 1)
        "pct_detached",  # % Detached (single-family detached)
        "pct_multifamily",  # % Multifamily buildings
        "pct_mobile_homes",  # % Mobile homes
        # Housing age (Table 1)
        "pct_built_1980_89",  # % Built in 1980-89
        "pct_1940_69",  # % Built in 1940-69
        "pct_pre1940",  # % Built before 1940
        # Demographics (Table 1)
        "pct_black",  # % Black
        "pct_hispanic",  # % Hispanic
        "pct_age_65_plus",  # % Age > 65
    ]

    regressors = treatment_vars + controls
    reg_vars = [outcome] + regressors + ["msa_code"]

    # Drop missing
    sample = sample.dropna(subset=reg_vars)

    if len(sample) < 50:
        return {"error": "Insufficient observations", "n": len(sample)}

    # Create MSA fixed effect dummies
    msa_dummies = pd.get_dummies(
        sample["msa_code"], prefix="msa", drop_first=True, dtype=float
    )

    # Build design matrix
    X_regressors = sample[regressors].astype(float)
    X = pd.concat(
        [X_regressors.reset_index(drop=True), msa_dummies.reset_index(drop=True)],
        axis=1,
    )
    X = sm.add_constant(X)

    y = sample[outcome].reset_index(drop=True).astype(float)
    sample_reset = sample.reset_index(drop=True)

    # OLS with MSA-clustered standard errors
    model = sm.OLS(y, X).fit(
        cov_type="cluster", cov_kwds={"groups": sample_reset["msa_code"]}
    )

    return {
        "coef": model.params["D"],
        "se": model.bse["D"],
        "t_stat": model.tvalues["D"],
        "p_value": model.pvalues["D"],
        "n": int(model.nobs),
        "n_clusters": sample["msa_code"].nunique(),
        "r2": model.rsquared,
    }


def run_specification(loan_types: str, spec_name: str):
    """Run a complete specification and return results."""
    print(f"\n{'='*70}")
    print(f"SPECIFICATION: {spec_name}")
    print(f"Loan Types: {loan_types}")
    print(f"{'='*70}")

    # Load census data
    print("\nStep 1: Loading census data (v3 with Bhutta-exact variables)...")
    census = load_census()
    large_msas = get_large_msas(census)
    print(f"  Census tracts: {len(census):,}")
    print(f"  Large MSAs (pop > 2M): {len(large_msas)}")

    # Load HMDA data
    print(f"\nStep 2: Loading HMDA data (1994-2002), loan_types={loan_types}...")
    hmda_dfs = []
    for year in YEARS:
        df = load_hmda_year(year, loan_types=loan_types)
        if len(df) > 0:
            print(f"    {year}: {len(df):,} loans")
            hmda_dfs.append(df)

    hmda = pd.concat(hmda_dfs, ignore_index=True)
    print(f"  Total: {len(hmda):,} loans")

    # Aggregate to tract level
    print("\nStep 3: Aggregating to tract level...")
    tract_agg = aggregate_hmda(hmda)
    print(f"  Unique tracts: {len(tract_agg):,}")

    # Merge with census
    print("\nStep 4: Merging with census characteristics...")
    merged = census.merge(
        tract_agg[["msa_tract_key", "num_loans"]],
        on="msa_tract_key",
        how="left",
    )
    merged["num_loans"] = merged["num_loans"].fillna(0)

    # Filter to Large MSAs
    large_msa_df = merged[merged["msa_code"].isin(large_msas)]
    print(f"  Tracts in Large MSAs: {len(large_msa_df):,}")

    # Apply Bhutta filters with EXACT origination rate filter
    print("\nStep 5: Applying Bhutta (2011) sample restrictions...")
    filtered = apply_bhutta_filters(large_msa_df, use_bhutta_exact_filter=True)

    # Create RD variables
    analysis_df = create_rd_vars(filtered)

    # Summary of sample near threshold
    in_bw = analysis_df[(analysis_df["TM"] >= 0.75) & (analysis_df["TM"] <= 0.85)]
    print(f"\nSample in bandwidth (0.75-0.85):")
    print(f"  Total tracts: {len(in_bw):,}")
    print(f"  Below threshold (D=1): {(in_bw['D'] == 1).sum():,}")
    print(f"  Above threshold (D=0): {(in_bw['D'] == 0).sum():,}")

    # Run RD regression
    print(f"\n{'='*70}")
    print(f"REGRESSION RESULTS: Large MSAs, h=0.05, {spec_name}")
    print(f"{'='*70}")

    result = run_rd_regression(analysis_df, bandwidth=0.05)

    if "error" in result:
        print(f"ERROR: {result['error']}")
        return None

    target = BHUTTA_TARGETS["large_msas_h05"]
    coef_match = (result["coef"] / target["coef"]) * 100
    n_match = (result["n"] / target["n"]) * 100
    r2_match = (result["r2"] / target["r2"]) * 100

    print(f"\n{'Statistic':<20} {'Our Result':>15} {'Bhutta (2011)':>15} {'Match':>10}")
    print("-" * 65)
    print(
        f"{'Coefficient (D)':<20} {result['coef']:>15.4f} {target['coef']:>15.4f} {coef_match:>9.1f}%"
    )
    print(f"{'Standard Error':<20} {result['se']:>15.4f} {target['se']:>15.4f}")
    print(
        f"{'Sample Size (N)':<20} {result['n']:>15,} {target['n']:>15,} {n_match:>9.1f}%"
    )
    print(
        f"{'R-squared':<20} {result['r2']:>15.4f} {target['r2']:>15.4f} {r2_match:>9.1f}%"
    )
    print(f"{'MSA Clusters':<20} {result['n_clusters']:>15}")
    print(f"{'t-statistic':<20} {result['t_stat']:>15.2f}")
    print(f"{'p-value':<20} {result['p_value']:>15.4f}")

    return {
        "spec_name": spec_name,
        "loan_types": loan_types,
        **result,
        "target_coef": target["coef"],
        "target_se": target["se"],
        "target_n": target["n"],
        "target_r2": target["r2"],
        "coef_match_pct": coef_match,
        "n_match_pct": n_match,
        "r2_match_pct": r2_match,
    }


def main():
    print("=" * 70)
    print("BHUTTA (2011) RD REPLICATION - VERSION 11")
    print("100% MATCH ATTEMPT")
    print("=" * 70)
    print()
    print("KEY CHANGES FROM v10:")
    print("  1. Origination filter: Bhutta exact (0.25-20/OOU) vs annual>=2%")
    print("  2. Controls: pct_black, pct_hispanic separate; pct_mobile_homes,")
    print("               pct_built_1980_89 added; poverty_pct removed")
    print("  3. Added ln_total_hu per footnote 20")
    print("  4. Testing BOTH loan type specifications")
    print()

    results = []

    # Spec A: All loan types (per Table 2 note)
    result_a = run_specification("all", "Spec A: All Loans (Purchase+Refi+Improvement)")
    if result_a:
        results.append(result_a)

    # Spec B: Purchase only (what worked before)
    result_b = run_specification("purchase", "Spec B: Purchase Only")
    if result_b:
        results.append(result_b)

    # Summary comparison
    print("\n" + "=" * 70)
    print("SPECIFICATION COMPARISON")
    print("=" * 70)
    print()
    print(f"{'Specification':<45} {'Coef':>10} {'Match%':>8} {'N':>8} {'R²':>8}")
    print("-" * 85)
    print(
        f"{'Bhutta (2011) Target':<45} {0.0764:>10.4f} {'100.0%':>8} {1800:>8} {0.869:>8.3f}"
    )
    print("-" * 85)

    for r in results:
        sig = (
            "***"
            if r["p_value"] < 0.01
            else ("**" if r["p_value"] < 0.05 else ("*" if r["p_value"] < 0.10 else ""))
        )
        print(
            f"{r['spec_name']:<45} {r['coef']:>10.4f}{sig} {r['coef_match_pct']:>7.1f}% {r['n']:>8,} {r['r2']:>8.3f}"
        )

    # Identify best match
    if results:
        best = max(results, key=lambda x: x["coef_match_pct"])
        print()
        print(f"BEST MATCH: {best['spec_name']}")
        print(
            f"  Coefficient: {best['coef']:.4f} ({best['coef_match_pct']:.1f}% of target)"
        )
        print(f"  Sample Size: {best['n']:,} ({best['n_match_pct']:.1f}% of target)")
        print(f"  R²: {best['r2']:.4f} ({best['r2_match_pct']:.1f}% of target)")

    # Save results
    if results:
        results_df = pd.DataFrame(results)
        results_df.to_csv(OUTPUT_DIR / "v11_comparison_results.csv", index=False)
        print(f"\nResults saved to: {OUTPUT_DIR / 'v11_comparison_results.csv'}")


if __name__ == "__main__":
    main()
