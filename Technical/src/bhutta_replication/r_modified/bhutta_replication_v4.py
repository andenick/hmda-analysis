"""
Bhutta (2011) RD Replication - Version 4 (Full Controls + Group Quarters Filter)

Key improvements over v3:
1. Uses extended census data with ALL Bhutta controls
2. Adds group quarters filter (< 30% population)
3. Includes all 12+ control variables from Bhutta's specification
4. Better matches Bhutta's exact sample construction

Target: β = +0.0764*** (SE 0.0274), N = 1,800 for Large MSAs at h=0.05
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
CENSUS_DIR = Path(
    str(OUTPUT_ROOT / "Technical/data/census_parsed_v2")
)  # Extended variables
OUTPUT_DIR = Path(
    str(DATA_ROOT / "Technical/src/bhutta_replication/r_modified/output_v4")
)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Years to process (Bhutta uses 1994-2002)
YEARS = [1994, 1995, 1996, 1997, 1998, 1999, 2000, 2001, 2002]

# Bhutta targets from Table 2
BHUTTA_TARGETS = {
    "all_msas_h05": {"coef": 0.0337, "se": 0.0187, "n": 4708},
    "small_msas_h05": {"coef": -0.0045, "se": 0.0348, "n": 1266},
    "medium_msas_h05": {"coef": 0.0114, "se": 0.0299, "n": 1642},
    "large_msas_h05": {"coef": 0.0764, "se": 0.0274, "n": 1800},  # PRIMARY TARGET
    "large_msas_h30": {"coef": 0.0729, "se": 0.0158, "n": 9551},
}


def load_hmda_year(year: int) -> pd.DataFrame:
    """Load and filter HMDA LAR data for a single year."""
    patterns = [f"*HMDA_LAR_{year}.txt", f"*hmda_lar_{year}.txt", f"*{year}*.txt"]
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
            "loan_amount": str,
        },
    ):
        # Convert numeric columns
        chunk["action_taken"] = pd.to_numeric(chunk["action_taken"], errors="coerce")
        chunk["loan_purpose"] = pd.to_numeric(chunk["loan_purpose"], errors="coerce")
        chunk["occupancy_type"] = pd.to_numeric(
            chunk["occupancy_type"], errors="coerce"
        )
        chunk["loan_amount"] = pd.to_numeric(chunk["loan_amount"], errors="coerce")
        chunk["agency_code"] = pd.to_numeric(chunk["agency_code"], errors="coerce")

        # Bhutta filters: originated, home purchase/refi, owner-occupied, in MSA
        # CRITICAL: Bank loans only (agency 1=OCC, 2=FRS, 3=FDIC, 5=OTS)
        filtered = chunk[
            (chunk["action_taken"] == 1)
            & (chunk["loan_purpose"].isin([1, 3]))
            & (chunk["occupancy_type"] == 1)
            & (chunk["msamd"].notna())
            & (chunk["msamd"] != "")
            & (chunk["agency_code"].isin([1, 2, 3, 5]))  # BANKS ONLY
        ]
        chunks.append(filtered)

    df = pd.concat(chunks, ignore_index=True)
    df["year"] = year
    return df


def aggregate_hmda_to_tract_period(hmda: pd.DataFrame) -> pd.DataFrame:
    """
    Aggregate HMDA to TRACT-LEVEL (sum over entire 1994-2002 period).

    This matches Bhutta's specification where N = number of tracts, not tract-years.
    """
    hmda["tract_only"] = (
        hmda["census_tract"].str.replace(".", "", regex=False).str.zfill(6)
    )
    hmda["msa_tract_key"] = hmda["msamd"].astype(str) + "_" + hmda["tract_only"]

    # Aggregate to tract-level (sum over all years)
    tract_agg = (
        hmda.groupby(["msa_tract_key", "msamd"])
        .agg(
            num_loans=("loan_amount", "count"),  # Total originations 1994-2002
            total_loan_amount=("loan_amount", "sum"),
            years_with_data=("year", "nunique"),
        )
        .reset_index()
    )

    return tract_agg


def load_census_1996() -> pd.DataFrame:
    """
    Load base census characteristics from extended FFIEC data.

    Uses 1996 as base (1990 Census tract characteristics, same as Bhutta).
    """
    path = CENSUS_DIR / "census_1996.parquet"
    if not path.exists():
        raise FileNotFoundError(f"Census file not found: {path}")

    df = pd.read_parquet(path)
    print(f"  Loaded census: {len(df):,} tracts")
    print(f"  Mean OOU: {df['owner_occupied_units'].mean():.1f}")
    print(f"  Mean % age 65+: {df['pct_age_65_plus'].mean()*100:.1f}%")
    print(f"  Mean % single-family: {df['pct_single_family'].mean()*100:.1f}%")
    print(f"  Mean % group quarters: {df['pct_group_quarters'].mean()*100:.1f}%")

    return df


def get_msa_size_categories(census: pd.DataFrame) -> dict:
    """
    Categorize MSAs by 1990 population.

    From Bhutta (2011):
    - Small: < 500,000
    - Medium: 500,000 to 2,000,000
    - Large: > 2,000,000 (23 MSAs)
    """
    # Sum population by MSA
    msa_pop = census.groupby("msa_code")["population"].sum().reset_index()
    msa_pop.columns = ["msa_code", "msa_pop"]

    # Exclude 9999 (non-metro catch-all)
    msa_pop = msa_pop[msa_pop["msa_code"] != "9999"]
    msa_pop = msa_pop[msa_pop["msa_code"] != ""]

    # Categorize
    small_msas = set(msa_pop[msa_pop["msa_pop"] < 500_000]["msa_code"])
    medium_msas = set(
        msa_pop[(msa_pop["msa_pop"] >= 500_000) & (msa_pop["msa_pop"] <= 2_000_000)][
            "msa_code"
        ]
    )
    large_msas = set(msa_pop[msa_pop["msa_pop"] > 2_000_000]["msa_code"])

    print(
        f"  MSA categories: Small={len(small_msas)}, Medium={len(medium_msas)}, Large={len(large_msas)}"
    )

    return {
        "small": small_msas,
        "medium": medium_msas,
        "large": large_msas,
        "msa_pop": msa_pop.set_index("msa_code")["msa_pop"].to_dict(),
    }


def apply_bhutta_filters(df: pd.DataFrame) -> pd.DataFrame:
    """
    Apply Bhutta (2011) sample restrictions from Section 4.1.

    From the paper:
    "I drop tracts that had fewer than 100 housing units (in 1990),
     zero (specified) owner-occupied units, more than 30 percent of
     the population in group quarters, and either fewer than .25 or
     more than 20 originations per (1990) owner-occupied unit over
     the entire 1994-2002 period."
    """
    result = df.copy()
    n_start = len(result)

    # 1. Exclude Alaska (02) and Hawaii (15) - implied by urban focus
    result = result[~result["state_code"].isin(["02", "15", "2"])]
    print(
        f"    After AK/HI exclusion: {len(result):,} ({len(result)/n_start*100:.1f}%)"
    )

    # 2. Housing units >= 100
    result = result[result["total_housing_units"] >= 100]
    print(f"    After housing >= 100: {len(result):,} ({len(result)/n_start*100:.1f}%)")

    # 3. Owner-occupied units > 0
    result = result[result["owner_occupied_units"] > 0]
    print(f"    After OOU > 0: {len(result):,} ({len(result)/n_start*100:.1f}%)")

    # 4. Group quarters < 30% (NEW in v4!)
    result = result[result["pct_group_quarters"] < 0.30]
    print(
        f"    After group quarters < 30%: {len(result):,} ({len(result)/n_start*100:.1f}%)"
    )

    # 5. Require some lending activity
    result = result[result["num_loans"] > 0]
    print(f"    After loans > 0: {len(result):,} ({len(result)/n_start*100:.1f}%)")

    # 6. Originations per OOU filter: 0.25 to 20 (over entire 1994-2002 period)
    result["orig_per_oou"] = result["num_loans"] / result["owner_occupied_units"]
    result = result[(result["orig_per_oou"] >= 0.25) & (result["orig_per_oou"] <= 20)]
    print(
        f"    After orig/OOU [0.25, 20]: {len(result):,} ({len(result)/n_start*100:.1f}%)"
    )

    return result


def create_analysis_vars(df: pd.DataFrame) -> pd.DataFrame:
    """Create variables for RD analysis with ALL Bhutta controls."""
    result = df.copy()

    # Treatment indicator (TM < 0.80)
    result["D"] = (result["TM"] < 0.80).astype(int)

    # Centered running variable
    result["TM_c"] = result["TM"] - 0.80

    # Interaction for local linear RD
    result["D_TM"] = result["D"] * result["TM_c"]

    # Log outcome (total originations 1994-2002)
    result["ln_num_loans"] = np.log(result["num_loans"].clip(lower=1))

    # ===== FULL BHUTTA CONTROL VARIABLES =====

    # 1. Minority percentage (already in data)
    # result['minority_pct'] - already present

    # 2. Log owner-occupied units
    result["ln_oou"] = np.log(result["owner_occupied_units"].clip(lower=1))

    # 3. Log median housing value
    result["ln_value"] = np.log(result["median_home_value"].clip(lower=1))

    # 4. Poverty rate (already in data as poverty_pct)
    # result['poverty_pct'] - already present

    # 5. % housing built pre-1940 (already computed in census)
    # result['pct_pre1940'] - already present

    # 6. % housing built 1940-69 (already computed in census)
    # result['pct_1940_69'] - already present

    # 7. % age 65+ (NEW in v4!)
    # result['pct_age_65_plus'] - already present

    # 8. % single-family (NEW in v4!)
    # result['pct_single_family'] - already present

    # 9. % 2-4 family (NEW in v4!)
    # result['pct_2_4_family'] - already present

    # 10. % 5+ family (NEW in v4!)
    # result['pct_5_plus'] - already present

    return result


def run_rd_regression(
    df: pd.DataFrame,
    bandwidth: float,
    controls: bool = True,
    msa_fe: bool = True,
    cubic: bool = False,
    use_extended_controls: bool = True,
) -> dict:
    """
    Run RD regression matching Bhutta's specification.

    Key: Uses tract-level data (not tract-year), MSA-clustered SEs.
    """
    # Apply bandwidth filter
    sample = df[(df["TM"] >= 0.80 - bandwidth) & (df["TM"] <= 0.80 + bandwidth)].copy()

    # Define variables
    outcome = "ln_num_loans"
    treatment = ["D", "TM_c", "D_TM"]

    # Control variables - EXTENDED for v4
    if use_extended_controls:
        control_vars = [
            "minority_pct",  # 1. % minority
            "ln_oou",  # 2. Log owner-occupied units
            "ln_value",  # 3. Log median value
            "poverty_pct",  # 4. Poverty rate
            "pct_pre1940",  # 5. % pre-1940
            "pct_1940_69",  # 6. % 1940-69
            "pct_age_65_plus",  # 7. % age 65+ (NEW)
            "pct_single_family",  # 8. % single-family (NEW)
            "pct_2_4_family",  # 9. % 2-4 family (NEW)
            "pct_5_plus",  # 10. % 5+ family (NEW)
        ]
    else:
        # Basic controls (like v3)
        control_vars = [
            "minority_pct",
            "ln_oou",
            "ln_value",
            "pct_pre1940",
            "pct_1940_69",
        ]

    # Add GSE goal indicator for wide bandwidth (Bhutta footnote)
    if bandwidth >= 0.20:
        sample["d_gse"] = (sample["TM"] <= 0.90).astype(int)
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

    if len(reg_sample) < 50:
        return {"error": "Insufficient observations", "n": len(reg_sample)}

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

    # Run regression with MSA-clustered standard errors
    model = sm.OLS(y, X).fit(
        cov_type="cluster", cov_kwds={"groups": reg_sample["msa_code"]}
    )

    # Extract treatment effect
    d_col = "D_dm" if msa_fe else "D"

    return {
        "coef": model.params[d_col],
        "se": model.bse[d_col],
        "t_stat": model.tvalues[d_col],
        "p_value": model.pvalues[d_col],
        "n": len(reg_sample),
        "n_clusters": reg_sample["msa_code"].nunique(),
        "r2": model.rsquared,
    }


def main():
    """Run improved Bhutta replication analysis with all controls."""
    print("=" * 70)
    print("BHUTTA (2011) RD REPLICATION - VERSION 4 (FULL CONTROLS)")
    print("=" * 70)
    print()

    # ===== STEP 1: Load HMDA Data =====
    print("Step 1: Loading HMDA LAR data (1994-2002)...")
    hmda_dfs = []
    for year in YEARS:
        print(f"  {year}...", end=" ")
        df = load_hmda_year(year)
        if len(df) > 0:
            hmda_dfs.append(df)
            print(f"{len(df):,} loans")
        else:
            print("skipped")

    hmda_all = pd.concat(hmda_dfs, ignore_index=True)
    print(f"  Total HMDA loans: {len(hmda_all):,}")

    # Aggregate to TRACT-LEVEL (not tract-year)
    print("\nStep 2: Aggregating to tract-level (sum 1994-2002)...")
    tract_agg = aggregate_hmda_to_tract_period(hmda_all)
    print(f"  Unique tracts with loans: {len(tract_agg):,}")

    # ===== STEP 3: Load Census =====
    print("\nStep 3: Loading census data (extended FFIEC 1996)...")
    census = load_census_1996()

    # Get MSA size categories
    msa_cats = get_msa_size_categories(census)

    # ===== STEP 4: Merge =====
    print("\nStep 4: Merging HMDA and census...")
    merged = census.merge(
        tract_agg[
            ["msa_tract_key", "num_loans", "total_loan_amount", "years_with_data"]
        ],
        on="msa_tract_key",
        how="left",
    )
    merged["num_loans"] = merged["num_loans"].fillna(0)
    print(f"  Merged tracts: {len(merged):,}")
    print(f"  Tracts with loans: {(merged['num_loans'] > 0).sum():,}")

    # ===== STEP 5: Apply Filters =====
    print("\nStep 5: Applying Bhutta sample restrictions (WITH GROUP QUARTERS)...")
    filtered = apply_bhutta_filters(merged)
    print(f"  Final sample: {len(filtered):,}")

    # ===== STEP 6: Create Analysis Variables =====
    print("\nStep 6: Creating analysis variables with FULL controls...")
    analysis = create_analysis_vars(filtered)

    # ===== STEP 7: Run RD Regressions =====
    print("\nStep 7: Running RD regressions for Large MSAs...")

    # Filter to Large MSAs
    large_msas_df = analysis[analysis["msa_code"].isin(msa_cats["large"])]
    print(f"  Large MSAs sample size: {len(large_msas_df):,}")

    # Run for h=0.05 (PRIMARY TARGET)
    print("\n  Running h=0.05 (Primary Specification)...")
    result_h05 = run_rd_regression(
        large_msas_df, bandwidth=0.05, use_extended_controls=True
    )

    # Also test with basic controls for comparison
    result_h05_basic = run_rd_regression(
        large_msas_df, bandwidth=0.05, use_extended_controls=False
    )

    # Run for h=0.30 (Secondary)
    print("  Running h=0.30...")
    result_h30 = run_rd_regression(
        large_msas_df, bandwidth=0.30, cubic=True, use_extended_controls=True
    )

    # ===== STEP 8: Print Results =====
    print("\n" + "=" * 70)
    print("RESULTS COMPARISON")
    print("=" * 70)

    target_h05 = BHUTTA_TARGETS["large_msas_h05"]
    target_h30 = BHUTTA_TARGETS["large_msas_h30"]

    print("\nLarge MSAs, h=0.05 (PRIMARY TARGET):")
    print("-" * 50)
    print(f"  {'':20} {'Our Result':>12} {'Bhutta Target':>14}")
    print(
        f"  {'Coefficient:':20} {result_h05['coef']:>12.4f} {target_h05['coef']:>14.4f}"
    )
    print(
        f"  {'Standard Error:':20} {result_h05['se']:>12.4f} {target_h05['se']:>14.4f}"
    )
    print(f"  {'N (tracts):':20} {result_h05['n']:>12,} {target_h05['n']:>14,}")
    print(f"  {'R-squared:':20} {result_h05['r2']:>12.4f} {'~0.869':>14}")
    print(f"  {'N Clusters:':20} {result_h05['n_clusters']:>12}")

    coef_ratio = result_h05["coef"] / target_h05["coef"] * 100
    n_ratio = result_h05["n"] / target_h05["n"] * 100
    print(f"\n  Coefficient match: {coef_ratio:.1f}% of target")
    print(f"  Sample size match: {n_ratio:.1f}% of target")

    print("\n\nComparison: Extended vs Basic Controls (h=0.05):")
    print("-" * 50)
    print(f"  {'':20} {'Extended':>12} {'Basic':>12}")
    print(
        f"  {'Coefficient:':20} {result_h05['coef']:>12.4f} {result_h05_basic['coef']:>12.4f}"
    )
    print(
        f"  {'Standard Error:':20} {result_h05['se']:>12.4f} {result_h05_basic['se']:>12.4f}"
    )
    print(
        f"  {'R-squared:':20} {result_h05['r2']:>12.4f} {result_h05_basic['r2']:>12.4f}"
    )

    print("\n\nLarge MSAs, h=0.30 (Secondary):")
    print("-" * 50)
    print(f"  {'':20} {'Our Result':>12} {'Bhutta Target':>14}")
    print(
        f"  {'Coefficient:':20} {result_h30['coef']:>12.4f} {target_h30['coef']:>14.4f}"
    )
    print(
        f"  {'Standard Error:':20} {result_h30['se']:>12.4f} {target_h30['se']:>14.4f}"
    )
    print(f"  {'N (tracts):':20} {result_h30['n']:>12,} {target_h30['n']:>14,}")

    # ===== STEP 9: Save Results =====
    results_summary = pd.DataFrame(
        [
            {
                "specification": "large_msas_h05_extended",
                "our_coef": result_h05["coef"],
                "our_se": result_h05["se"],
                "target_coef": target_h05["coef"],
                "target_se": target_h05["se"],
                "our_n": result_h05["n"],
                "target_n": target_h05["n"],
                "r2": result_h05["r2"],
                "coef_match_pct": coef_ratio,
            },
            {
                "specification": "large_msas_h05_basic",
                "our_coef": result_h05_basic["coef"],
                "our_se": result_h05_basic["se"],
                "target_coef": target_h05["coef"],
                "target_se": target_h05["se"],
                "our_n": result_h05_basic["n"],
                "target_n": target_h05["n"],
                "r2": result_h05_basic["r2"],
                "coef_match_pct": result_h05_basic["coef"] / target_h05["coef"] * 100,
            },
            {
                "specification": "large_msas_h30",
                "our_coef": result_h30["coef"],
                "our_se": result_h30["se"],
                "target_coef": target_h30["coef"],
                "target_se": target_h30["se"],
                "our_n": result_h30["n"],
                "target_n": target_h30["n"],
                "r2": result_h30["r2"],
                "coef_match_pct": result_h30["coef"] / target_h30["coef"] * 100,
            },
        ]
    )

    results_path = OUTPUT_DIR / "replication_results_v4.csv"
    results_summary.to_csv(results_path, index=False)
    print(f"\n\nResults saved to: {results_path}")

    print("\n" + "=" * 70)
    print("REPLICATION COMPLETE - VERSION 4")
    print("=" * 70)


if __name__ == "__main__":
    main()
