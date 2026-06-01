"""
Bhutta (2011) RD Replication - Full Python Implementation

This script replicates the Bhutta (2011) CRA analysis using the CORRECT specification:
- NO central city filter
- Total housing units >= 100
- MSA fixed effects
- Clustered standard errors

Compares results to:
1. Original R code (with central city filter): β = -0.088
2. Bhutta (2011) paper target: β = +0.0764***
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

# ============================================================
# CONFIGURATION
# ============================================================

HMDA_DIR = DATA_ROOT / "Inputs/Old/CRA_code/_files2/1990to2006/src"
CENSUS_DIR = OUTPUT_ROOT / "Technical/data/census_bhutta"
OUTPUT_DIR = Path(
    str(DATA_ROOT / "Technical/src/bhutta_replication/r_modified/output")
)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Years to process (Bhutta uses 1994-2002)
YEARS = [1994, 1995, 1996, 1997, 1998, 1999, 2000, 2001, 2002]

# Bhutta targets
BHUTTA_TARGETS = {
    "large_h05_linear": {"coef": 0.0764, "se": 0.0274, "n": 1800},
    "large_h30_cubic": {"coef": 0.0613, "se": 0.0393, "n": 8000},
}

# R code results (central city filter)
R_CODE_RESULTS = {
    "large_h05_linear": {"coef": -0.088, "se": 0.086, "n": 6493},
    "large_h30_cubic": {"coef": 0.029, "se": 0.046, "n": 32772},
}


def load_hmda_year(year: int) -> pd.DataFrame:
    """Load and filter HMDA LAR data for a single year."""
    # Find the file
    patterns = [f"*HMDA_LAR_{year}.txt", f"*hmda_lar_{year}.txt"]
    filepath = None
    for pattern in patterns:
        matches = list(HMDA_DIR.glob(pattern))
        if matches:
            filepath = matches[0]
            break

    if filepath is None:
        print(f"  Warning: No file found for year {year}")
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
            "loan_amount": str,  # Read as string, convert later
        },
    ):
        # Convert numeric columns
        chunk["action_taken"] = pd.to_numeric(chunk["action_taken"], errors="coerce")
        chunk["loan_purpose"] = pd.to_numeric(chunk["loan_purpose"], errors="coerce")
        chunk["occupancy_type"] = pd.to_numeric(
            chunk["occupancy_type"], errors="coerce"
        )
        chunk["loan_amount"] = pd.to_numeric(chunk["loan_amount"], errors="coerce")

        # Bhutta filters: originated, home purchase/refi, owner-occupied, in MSA
        filtered = chunk[
            (chunk["action_taken"] == 1)
            & (chunk["loan_purpose"].isin([1, 3]))
            & (chunk["occupancy_type"] == 1)
            & (chunk["msamd"].notna())
            & (chunk["msamd"] != "")
        ]
        chunks.append(filtered)

    df = pd.concat(chunks, ignore_index=True)
    df["year"] = year
    return df


def aggregate_hmda_to_tract(hmda: pd.DataFrame) -> pd.DataFrame:
    """Aggregate HMDA to tract-year level."""
    hmda["tract_only"] = (
        hmda["census_tract"].str.replace(".", "", regex=False).str.zfill(6)
    )
    hmda["msa_tract_key"] = hmda["msamd"].astype(str) + "_" + hmda["tract_only"]

    tract_agg = (
        hmda.groupby(["msa_tract_key", "msamd", "year"])
        .agg(
            num_loans=("loan_amount", "count"),
            total_loan_amount=("loan_amount", "sum"),
        )
        .reset_index()
    )

    return tract_agg


def load_census_year(year: int) -> pd.DataFrame:
    """Load census data for a single year.

    For 1994-1995, use 1996 census as proxy (all from 1990 Census base).
    """
    # Map 1994-1995 to 1996 census file
    census_year = year if year >= 1996 else 1996
    path = CENSUS_DIR / f"census_{census_year}.parquet"

    if not path.exists():
        print(f"  Warning: No census file for year {year} (tried {census_year})")
        return pd.DataFrame()

    df = pd.read_parquet(path)
    df["year"] = year  # Use actual HMDA year for merging
    df["tract_in_msa"] = df["tract"].astype(str).str.zfill(6)
    df["msa_tract_key"] = df["msa_code"].astype(str) + "_" + df["tract_in_msa"]

    return df


def apply_bhutta_filters(df: pd.DataFrame, central_city: bool = False) -> pd.DataFrame:
    """
    Apply Bhutta (2011) sample restrictions.

    Args:
        df: Merged HMDA+Census data
        central_city: If True, apply central city filter (original R spec)
                     If False, use all MSA tracts (Bhutta spec)
    """
    result = df.copy()

    # Exclude Alaska and Hawaii
    result = result[~result["state_code"].isin(["02", "15", 2, 15])]

    # Housing unit filter
    if central_city:
        # Original R code: owner-occupied >= 100
        result = result[result["owner_occupied_units"] >= 100]
    else:
        # Bhutta spec: total housing >= 100
        result = result[result["total_housing_units"] >= 100]

    # Central city filter (only if specified)
    if central_city:
        result = result[result["central_city_flag"] == "1"]

    return result


def create_analysis_vars(df: pd.DataFrame) -> pd.DataFrame:
    """Create variables for RD analysis."""
    result = df.copy()

    # Treatment indicator (TM < 0.80)
    result["D"] = (result["TM"] < 0.80).astype(int)

    # Centered running variable
    result["TM_c"] = result["TM"] - 0.80

    # Interaction for local linear RD
    result["D_TM"] = result["D"] * result["TM_c"]

    # Log outcome
    result["ln_num_loans"] = np.log(result["num_loans"].clip(lower=1))

    # Control variables
    result["ln_oou"] = np.log(result["owner_occupied_units"].clip(lower=1))
    result["ln_value"] = result["ln_median_home_value"]
    result["pct_pre1940"] = result["housing_pre1940"] / result["total_housing_units"]
    result["pct_1940_69"] = result["housing_1940_1969"] / result["total_housing_units"]

    # GSE goal indicator
    result["d_gse"] = (result["TM"] <= 0.90).astype(int)

    return result


def run_rd_regression(
    df: pd.DataFrame,
    bandwidth: float,
    controls: bool = True,
    msa_fe: bool = True,
    cubic: bool = False,
) -> dict:
    """
    Run RD regression with specified options.

    Args:
        df: Analysis data
        bandwidth: Bandwidth around 0.80 cutoff
        controls: Include control variables
        msa_fe: Include MSA fixed effects (via demeaning)
        cubic: Use cubic polynomial (for wide bandwidth)

    Returns:
        Dictionary with regression results
    """
    # Apply bandwidth filter
    sample = df[(df["TM"] >= 0.80 - bandwidth) & (df["TM"] <= 0.80 + bandwidth)].copy()

    # Define variables
    outcome = "ln_num_loans"
    treatment = ["D", "TM_c", "D_TM"]
    control_vars = ["minority_pct", "ln_oou", "ln_value", "pct_pre1940", "pct_1940_69"]

    if bandwidth >= 0.20:
        control_vars.append("d_gse")

    if cubic:
        sample["TM_c2"] = sample["TM_c"] ** 2
        sample["TM_c3"] = sample["TM_c"] ** 3
        sample["D_TM_c2"] = sample["D"] * sample["TM_c2"]
        sample["D_TM_c3"] = sample["D"] * sample["TM_c3"]
        treatment = ["D", "TM_c", "TM_c2", "TM_c3", "D_TM", "D_TM_c2", "D_TM_c3"]

    # Build regressor list
    regressors = treatment.copy()
    if controls:
        regressors.extend(control_vars)

    # Drop NAs
    reg_vars = [outcome] + regressors + ["msa_code"]
    reg_sample = sample.dropna(subset=reg_vars)

    if len(reg_sample) < 100:
        return {"error": "Insufficient observations"}

    # Apply MSA fixed effects via demeaning
    if msa_fe:
        for col in [outcome] + regressors:
            reg_sample[col + "_dm"] = reg_sample.groupby("msa_code")[col].transform(
                lambda x: x - x.mean()
            )

        X = reg_sample[[r + "_dm" for r in regressors]]
        y = reg_sample[outcome + "_dm"]
    else:
        X = sm.add_constant(reg_sample[regressors])
        y = reg_sample[outcome]

    # Run regression with MSA-clustered standard errors (matches R code)
    model_cluster = sm.OLS(y, X).fit(
        cov_type="cluster", cov_kwds={"groups": reg_sample["msa_code"]}
    )

    # Also compute HC1 robust SEs (may better match Bhutta's reported SEs)
    model_hc1 = sm.OLS(y, X).fit(cov_type="HC1")

    # Extract treatment effect
    d_col = "D_dm" if msa_fe else "D"

    return {
        "coef": model_cluster.params[d_col],
        "se": model_cluster.bse[d_col],
        "se_hc1": model_hc1.bse[d_col],  # HC1 robust SE
        "t_stat": model_cluster.tvalues[d_col],
        "p_value": model_cluster.pvalues[d_col],
        "n": len(reg_sample),
        "n_clusters": reg_sample["msa_code"].nunique(),
        "r2": model_cluster.rsquared,
        "model": model_cluster,
    }


def main():
    """Run full Bhutta replication analysis."""
    print("=" * 70)
    print("BHUTTA (2011) RD REPLICATION - FULL ANALYSIS")
    print("=" * 70)
    print()

    # ===== STEP 1: Load HMDA Data =====
    print("Step 1: Loading HMDA LAR data...")
    hmda_dfs = []
    for year in YEARS:
        print(f"  Processing {year}...", end=" ")
        df = load_hmda_year(year)
        if len(df) > 0:
            hmda_dfs.append(df)
            print(f"{len(df):,} loans")
        else:
            print("skipped")

    hmda_all = pd.concat(hmda_dfs, ignore_index=True)
    print(f"  Total HMDA loans: {len(hmda_all):,}")

    # Aggregate to tract-year
    print("  Aggregating to tract-year level...")
    tract_agg = aggregate_hmda_to_tract(hmda_all)
    print(f"  Unique tract-years: {len(tract_agg):,}")

    # ===== STEP 2: Load Census Data =====
    print("\nStep 2: Loading census data...")
    census_dfs = []
    for year in YEARS:
        df = load_census_year(year)
        if len(df) > 0:
            census_dfs.append(df)

    census_all = pd.concat(census_dfs, ignore_index=True)
    print(f"  Total census tracts: {len(census_all):,}")

    # ===== STEP 3: Merge =====
    print("\nStep 3: Merging HMDA and census...")
    merged = census_all.merge(
        tract_agg[["msa_tract_key", "year", "num_loans", "total_loan_amount"]],
        on=["msa_tract_key", "year"],
        how="left",
    )
    merged["num_loans"] = merged["num_loans"].fillna(0)
    print(f"  Merged observations: {len(merged):,}")
    print(
        f"  With loans: {(merged['num_loans'] > 0).sum():,} ({(merged['num_loans'] > 0).mean()*100:.1f}%)"
    )

    # ===== STEP 4: Apply Filters and Create Variables =====
    print("\nStep 4: Applying filters...")

    # Bhutta specification (NO central city)
    bhutta_sample = apply_bhutta_filters(merged, central_city=False)
    print(f"  Bhutta spec (all MSA): {len(bhutta_sample):,}")

    # Original R specification (WITH central city)
    r_sample = apply_bhutta_filters(merged, central_city=True)
    print(f"  R code spec (central city): {len(r_sample):,}")

    diff_pct = (len(bhutta_sample) - len(r_sample)) / len(bhutta_sample) * 100
    print(f"  Central city filter removes: {diff_pct:.1f}%")

    # Create analysis variables
    bhutta_sample = create_analysis_vars(bhutta_sample)
    r_sample = create_analysis_vars(r_sample)

    # ===== STEP 4b: Add Large MSA Filter =====
    # Calculate MSA total population (sum of tract populations)
    msa_pop = merged.groupby("msa_code")["population"].sum().reset_index()
    msa_pop.columns = ["msa_code", "msa_total_pop"]
    msa_pop = msa_pop.sort_values("msa_total_pop", ascending=False)

    # Exclude MSA 9999 (catch-all code for non-metro)
    msa_pop = msa_pop[msa_pop["msa_code"] != "9999"]

    # Large MSA definition from R code: 1990 population > 2,000,000
    # (R code uses: `1990_population` > 2000000 ~ "Large")
    large_msas = set(msa_pop[msa_pop["msa_total_pop"] > 2000000]["msa_code"])
    top5_msas = set(msa_pop.head(5)["msa_code"])
    print(f"  Large MSAs (pop > 2M, R code definition): {len(large_msas)}")
    print(f"  Top 5 MSAs by population: {top5_msas}")

    # Create Large MSA samples
    bhutta_large = bhutta_sample[bhutta_sample["msa_code"].isin(large_msas)].copy()
    bhutta_top5 = bhutta_sample[bhutta_sample["msa_code"].isin(top5_msas)].copy()
    r_large = r_sample[r_sample["msa_code"].isin(large_msas)].copy()
    print(f"  Bhutta spec + Large MSA (>2M): {len(bhutta_large):,}")
    print(f"  Bhutta spec + Top 5 MSA: {len(bhutta_top5):,}")

    # ===== STEP 5: Run Regressions =====
    print("\n" + "=" * 70)
    print("RD REGRESSION RESULTS")
    print("=" * 70)

    results = {}

    # Bhutta specification - ALL MSAs
    print("\n----- BHUTTA SPECIFICATION (NO central city filter) -----")

    print("\n[1] All MSAs, h=0.05, Linear, with controls, MSA FE:")
    res = run_rd_regression(
        bhutta_sample, bandwidth=0.05, controls=True, msa_fe=True, cubic=False
    )
    results["bhutta_all_h05"] = res
    if "error" not in res:
        print(
            f"    D coefficient: {res['coef']:.4f} (SE_cluster: {res['se']:.4f}, SE_hc1: {res['se_hc1']:.4f})"
        )
        print(f"    T-statistic:   {res['t_stat']:.2f}")
        print(f"    N:             {res['n']:,}")

    # Bhutta specification - LARGE MSAs only (this should match Bhutta!)
    print("\n----- BHUTTA SPECIFICATION + LARGE MSA FILTER -----")

    print("\n[1b] Large MSAs only, h=0.05, Linear, with controls, MSA FE:")
    res = run_rd_regression(
        bhutta_large, bandwidth=0.05, controls=True, msa_fe=True, cubic=False
    )
    results["bhutta_large_h05"] = res
    if "error" not in res:
        print(
            f"    D coefficient: {res['coef']:.4f} (SE_cluster: {res['se']:.4f}, SE_hc1: {res['se_hc1']:.4f})"
        )
        print(f"    T-statistic:   {res['t_stat']:.2f}")
        print(f"    N:             {res['n']:,}")

    print("\n[2b] Large MSAs only, h=0.30, Cubic, with controls, MSA FE:")
    res = run_rd_regression(
        bhutta_large, bandwidth=0.30, controls=True, msa_fe=True, cubic=True
    )
    results["bhutta_large_h30"] = res
    if "error" not in res:
        print(f"    D coefficient: {res['coef']:.4f} (SE: {res['se']:.4f})")
        print(f"    T-statistic:   {res['t_stat']:.2f}")
        print(f"    N:             {res['n']:,}")

    # TOP 5 MSAs - this should best match Bhutta's "Large MSA" results
    print("\n----- TOP 5 MSA SPECIFICATION (closest to Bhutta) -----")

    for bw in [0.05, 0.04, 0.03, 0.02]:
        print(f"\n[Top5] h={bw}, Linear, with controls, MSA FE:")
        res = run_rd_regression(
            bhutta_top5, bandwidth=bw, controls=True, msa_fe=True, cubic=False
        )
        results[f"top5_h{int(bw*100):02d}"] = res
        if "error" not in res:
            print(f"    D coefficient: {res['coef']:.4f} (SE: {res['se']:.4f})")
            print(f"    T-statistic:   {res['t_stat']:.2f}")
            print(f"    N:             {res['n']:,}")

    print("\n[2] All MSAs, h=0.30, Cubic, with controls, MSA FE:")
    res = run_rd_regression(
        bhutta_sample, bandwidth=0.30, controls=True, msa_fe=True, cubic=True
    )
    results["bhutta_all_h30"] = res
    if "error" not in res:
        print(f"    D coefficient: {res['coef']:.4f} (SE: {res['se']:.4f})")
        print(f"    T-statistic:   {res['t_stat']:.2f}")
        print(f"    N:             {res['n']:,}")

    # Original R specification regressions
    print("\n----- ORIGINAL R SPECIFICATION (WITH central city filter) -----")

    print("\n[3] Central city, h=0.05, Linear, with controls, MSA FE:")
    res = run_rd_regression(
        r_sample, bandwidth=0.05, controls=True, msa_fe=True, cubic=False
    )
    results["r_code_h05"] = res
    if "error" not in res:
        print(f"    D coefficient: {res['coef']:.4f} (SE: {res['se']:.4f})")
        print(f"    T-statistic:   {res['t_stat']:.2f}")
        print(f"    N:             {res['n']:,}")

    print("\n[4] Central city, h=0.30, Cubic, with controls, MSA FE:")
    res = run_rd_regression(
        r_sample, bandwidth=0.30, controls=True, msa_fe=True, cubic=True
    )
    results["r_code_h30"] = res
    if "error" not in res:
        print(f"    D coefficient: {res['coef']:.4f} (SE: {res['se']:.4f})")
        print(f"    T-statistic:   {res['t_stat']:.2f}")
        print(f"    N:             {res['n']:,}")

    # ===== STEP 6: Comparison Summary =====
    print("\n" + "=" * 70)
    print("COMPARISON SUMMARY")
    print("=" * 70)

    print(
        "\n{:<30} {:>12} {:>12} {:>12}".format(
            "Specification", "Coefficient", "Std Error", "N"
        )
    )
    print("-" * 70)

    # Bhutta paper targets
    print(
        "{:<30} {:>12.4f} {:>12} {:>12}".format(
            "Bhutta (2011) h=0.05 target", 0.0764, "(0.0274)", "~1,800"
        )
    )
    print(
        "{:<30} {:>12.4f} {:>12} {:>12}".format(
            "Bhutta (2011) h=0.30 target", 0.0613, "(0.0393)", "~8,000"
        )
    )
    print("-" * 70)

    # Our results
    if "bhutta_all_h05" in results and "error" not in results["bhutta_all_h05"]:
        r = results["bhutta_all_h05"]
        print(
            "{:<30} {:>12.4f} {:>12} {:>12,}".format(
                "Python Bhutta spec h=0.05", r["coef"], f"({r['se']:.4f})", r["n"]
            )
        )

    if "bhutta_all_h30" in results and "error" not in results["bhutta_all_h30"]:
        r = results["bhutta_all_h30"]
        print(
            "{:<30} {:>12.4f} {:>12} {:>12,}".format(
                "Python Bhutta spec h=0.30", r["coef"], f"({r['se']:.4f})", r["n"]
            )
        )

    print("-" * 70)

    # R code results
    print(
        "{:<30} {:>12.4f} {:>12} {:>12}".format(
            "Original R code h=0.05", -0.088, "(0.086)", "6,493"
        )
    )

    if "r_code_h05" in results and "error" not in results["r_code_h05"]:
        r = results["r_code_h05"]
        print(
            "{:<30} {:>12.4f} {:>12} {:>12,}".format(
                "Python R spec h=0.05", r["coef"], f"({r['se']:.4f})", r["n"]
            )
        )

    # ===== STEP 7: Key Findings =====
    print("\n" + "=" * 70)
    print("KEY FINDINGS")
    print("=" * 70)

    if "bhutta_all_h05" in results and "error" not in results["bhutta_all_h05"]:
        bhutta_coef = results["bhutta_all_h05"]["coef"]
        r_reported = -0.088

        print(f"\n1. SIGN CHECK:")
        print(f"   Original R code (central city):     {r_reported:+.4f} (NEGATIVE)")
        print(
            f"   Python Bhutta spec (all MSA):       {bhutta_coef:+.4f} ({'POSITIVE' if bhutta_coef > 0 else 'NEGATIVE'})"
        )
        print(f"   Bhutta (2011) target:               +0.0764 (POSITIVE)")

        if bhutta_coef > 0:
            print(f"\n   [OK] SIGN REVERSAL CONFIRMED!")
            print(f"   Removing central city filter fixes the sign.")
        else:
            print(
                f"\n   [WARNING] Sign still negative - may need additional specification fixes"
            )

    # Large MSA results
    if "bhutta_large_h05" in results and "error" not in results["bhutta_large_h05"]:
        large_coef = results["bhutta_large_h05"]["coef"]
        large_n = results["bhutta_large_h05"]["n"]
        print(f"\n3. LARGE MSA FILTER (pop > 1M):")
        print(f"   Coefficient:                        {large_coef:+.4f}")
        print(f"   Sample size:                        {large_n:,}")
        print(f"   Target (Bhutta):                    +0.0764, N~1,800")
        print(f"   Still too large sample - may need narrower filter.")

    print("\n2. CENTRAL CITY FILTER IMPACT:")
    print(f"   Tracts with central city filter:    {len(r_sample):,}")
    print(f"   Tracts without (Bhutta spec):       {len(bhutta_sample):,}")
    print(f"   Percent removed by filter:          {diff_pct:.1f}%")

    # Save results
    print("\n" + "=" * 70)
    results_df = pd.DataFrame(
        [
            {
                "spec": "Bhutta (2011) target h=0.05",
                "coef": 0.0764,
                "se": 0.0274,
                "n": 1800,
                "source": "paper",
            },
            {
                "spec": "Original R code h=0.05",
                "coef": -0.088,
                "se": 0.086,
                "n": 6493,
                "source": "r_output",
            },
        ]
    )

    for name, res in results.items():
        if "error" not in res:
            results_df = pd.concat(
                [
                    results_df,
                    pd.DataFrame(
                        [
                            {
                                "spec": f"Python {name}",
                                "coef": res["coef"],
                                "se": res["se"],
                                "n": res["n"],
                                "source": "python",
                            }
                        ]
                    ),
                ],
                ignore_index=True,
            )

    results_df.to_csv(OUTPUT_DIR / "regression_comparison.csv", index=False)
    print(f"Results saved to: {OUTPUT_DIR / 'regression_comparison.csv'}")

    return results


if __name__ == "__main__":
    results = main()
