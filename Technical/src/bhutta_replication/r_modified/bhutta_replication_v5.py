"""
Bhutta (2011) RD Replication - Version 5 (Explicit MSA Fixed Effects)

Key improvement: Uses explicit MSA dummies instead of demeaning.

The low R² in v3/v4 (0.58 vs Bhutta's 0.87) suggests the demeaning approach
may not be equivalent to explicit MSA fixed effects. This version tests
explicit MSA dummy variables.

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
CENSUS_DIR = OUTPUT_ROOT / "Technical/data/census_parsed_v2"
OUTPUT_DIR = Path(
    str(DATA_ROOT / "Technical/src/bhutta_replication/r_modified/output_v5")
)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

YEARS = [1994, 1995, 1996, 1997, 1998, 1999, 2000, 2001, 2002]

BHUTTA_TARGETS = {
    "large_msas_h05": {"coef": 0.0764, "se": 0.0274, "n": 1800},
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

        filtered = chunk[
            (chunk["action_taken"] == 1)
            & (chunk["loan_purpose"].isin([1, 3]))
            & (chunk["occupancy_type"] == 1)
            & (chunk["msamd"].notna())
            & (chunk["msamd"] != "")
            & (chunk["agency_code"].isin([1, 2, 3, 5]))
        ]
        chunks.append(filtered)

    df = pd.concat(chunks, ignore_index=True)
    df["year"] = year
    return df


def aggregate_hmda_to_tract_period(hmda: pd.DataFrame) -> pd.DataFrame:
    """Aggregate HMDA to tract-level (sum 1994-2002)."""
    hmda["tract_only"] = (
        hmda["census_tract"].str.replace(".", "", regex=False).str.zfill(6)
    )
    hmda["msa_tract_key"] = hmda["msamd"].astype(str) + "_" + hmda["tract_only"]

    tract_agg = (
        hmda.groupby(["msa_tract_key", "msamd"])
        .agg(
            num_loans=("loan_amount", "count"),
            total_loan_amount=("loan_amount", "sum"),
            years_with_data=("year", "nunique"),
        )
        .reset_index()
    )

    return tract_agg


def load_census_1996() -> pd.DataFrame:
    """Load base census from extended FFIEC data."""
    path = CENSUS_DIR / "census_1996.parquet"
    if not path.exists():
        raise FileNotFoundError(f"Census file not found: {path}")
    return pd.read_parquet(path)


def get_msa_size_categories(census: pd.DataFrame) -> dict:
    """Categorize MSAs by 1990 population."""
    msa_pop = census.groupby("msa_code")["population"].sum().reset_index()
    msa_pop.columns = ["msa_code", "msa_pop"]
    msa_pop = msa_pop[msa_pop["msa_code"] != "9999"]
    msa_pop = msa_pop[msa_pop["msa_code"] != ""]

    small_msas = set(msa_pop[msa_pop["msa_pop"] < 500_000]["msa_code"])
    medium_msas = set(
        msa_pop[(msa_pop["msa_pop"] >= 500_000) & (msa_pop["msa_pop"] <= 2_000_000)][
            "msa_code"
        ]
    )
    large_msas = set(msa_pop[msa_pop["msa_pop"] > 2_000_000]["msa_code"])

    return {"small": small_msas, "medium": medium_msas, "large": large_msas}


def apply_bhutta_filters(df: pd.DataFrame) -> pd.DataFrame:
    """Apply Bhutta sample restrictions."""
    result = df.copy()

    result = result[~result["state_code"].isin(["02", "15", "2"])]
    result = result[result["total_housing_units"] >= 100]
    result = result[result["owner_occupied_units"] > 0]
    result = result[result["pct_group_quarters"] < 0.30]
    result = result[result["num_loans"] > 0]
    result["orig_per_oou"] = result["num_loans"] / result["owner_occupied_units"]
    result = result[(result["orig_per_oou"] >= 0.25) & (result["orig_per_oou"] <= 20)]

    return result


def create_analysis_vars(df: pd.DataFrame) -> pd.DataFrame:
    """Create analysis variables."""
    result = df.copy()

    result["D"] = (result["TM"] < 0.80).astype(int)
    result["TM_c"] = result["TM"] - 0.80
    result["D_TM"] = result["D"] * result["TM_c"]
    result["ln_num_loans"] = np.log(result["num_loans"].clip(lower=1))
    result["ln_oou"] = np.log(result["owner_occupied_units"].clip(lower=1))
    result["ln_value"] = np.log(result["median_home_value"].clip(lower=1))

    return result


def run_rd_explicit_fe(
    df: pd.DataFrame,
    bandwidth: float,
    cubic: bool = False,
) -> dict:
    """
    Run RD regression with EXPLICIT MSA fixed effects (dummy variables).

    This may give different R² than demeaning approach.
    """
    # Apply bandwidth filter
    sample = df[(df["TM"] >= 0.80 - bandwidth) & (df["TM"] <= 0.80 + bandwidth)].copy()

    outcome = "ln_num_loans"
    treatment = ["D", "TM_c", "D_TM"]
    control_vars = [
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

    if bandwidth >= 0.20:
        sample["d_gse"] = (sample["TM"] <= 0.90).astype(int)
        control_vars.append("d_gse")

    if cubic:
        sample["TM_c2"] = sample["TM_c"] ** 2
        sample["TM_c3"] = sample["TM_c"] ** 3
        sample["D_TM_c2"] = sample["D"] * sample["TM_c2"]
        sample["D_TM_c3"] = sample["D"] * sample["TM_c3"]
        treatment = ["D", "TM_c", "TM_c2", "TM_c3", "D_TM", "D_TM_c2", "D_TM_c3"]

    regressors = treatment + control_vars

    # Drop NAs first
    reg_vars = [outcome] + regressors + ["msa_code"]
    sample = sample.dropna(subset=reg_vars)

    if len(sample) < 50:
        return {"error": "Insufficient observations", "n": len(sample)}

    # Create MSA dummies (explicit fixed effects)
    msa_dummies = pd.get_dummies(
        sample["msa_code"], prefix="msa", drop_first=True, dtype=float
    )

    # Build X with explicit MSA dummies - ensure all numeric
    X_regressors = sample[regressors].astype(float)
    X = pd.concat(
        [X_regressors.reset_index(drop=True), msa_dummies.reset_index(drop=True)],
        axis=1,
    )
    X = sm.add_constant(X)
    y = (
        sample[outcome].reset_index(drop=True).astype(float)
    )  # Run regression with clustered SEs - need to reset sample index to match
    sample_reset = sample.reset_index(drop=True)
    model = sm.OLS(y, X).fit(
        cov_type="cluster", cov_kwds={"groups": sample_reset["msa_code"]}
    )

    return {
        "coef": model.params["D"],
        "se": model.bse["D"],
        "t_stat": model.tvalues["D"],
        "p_value": model.pvalues["D"],
        "n": len(sample),
        "n_clusters": sample["msa_code"].nunique(),
        "r2": model.rsquared,
        "r2_adj": model.rsquared_adj,
    }


def run_rd_demeaned(
    df: pd.DataFrame,
    bandwidth: float,
    cubic: bool = False,
) -> dict:
    """
    Run RD regression with demeaned FE (for comparison).
    """
    sample = df[(df["TM"] >= 0.80 - bandwidth) & (df["TM"] <= 0.80 + bandwidth)].copy()

    outcome = "ln_num_loans"
    treatment = ["D", "TM_c", "D_TM"]
    control_vars = [
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

    if bandwidth >= 0.20:
        sample["d_gse"] = (sample["TM"] <= 0.90).astype(int)
        control_vars.append("d_gse")

    if cubic:
        sample["TM_c2"] = sample["TM_c"] ** 2
        sample["TM_c3"] = sample["TM_c"] ** 3
        sample["D_TM_c2"] = sample["D"] * sample["TM_c2"]
        sample["D_TM_c3"] = sample["D"] * sample["TM_c3"]
        treatment = ["D", "TM_c", "TM_c2", "TM_c3", "D_TM", "D_TM_c2", "D_TM_c3"]

    regressors = treatment + control_vars

    reg_vars = [outcome] + regressors + ["msa_code"]
    sample = sample.dropna(subset=reg_vars)

    if len(sample) < 50:
        return {"error": "Insufficient observations", "n": len(sample)}

    # Demean
    for col in [outcome] + regressors:
        sample[col + "_dm"] = sample.groupby("msa_code")[col].transform(
            lambda x: x - x.mean()
        )

    X = sample[[r + "_dm" for r in regressors]]
    y = sample[outcome + "_dm"]

    model = sm.OLS(y, X).fit(
        cov_type="cluster", cov_kwds={"groups": sample["msa_code"]}
    )

    return {
        "coef": model.params["D_dm"],
        "se": model.bse["D_dm"],
        "n": len(sample),
        "r2": model.rsquared,
    }


def main():
    print("=" * 70)
    print("BHUTTA (2011) RD REPLICATION - VERSION 5 (EXPLICIT MSA FE)")
    print("=" * 70)
    print()

    # Load data
    print("Loading HMDA data...")
    hmda_dfs = []
    for year in YEARS:
        df = load_hmda_year(year)
        if len(df) > 0:
            hmda_dfs.append(df)
            print(f"  {year}: {len(df):,} loans")

    hmda_all = pd.concat(hmda_dfs, ignore_index=True)
    print(f"  Total: {len(hmda_all):,} loans")

    print("\nAggregating to tract-level...")
    tract_agg = aggregate_hmda_to_tract_period(hmda_all)
    print(f"  Tracts: {len(tract_agg):,}")

    print("\nLoading census data...")
    census = load_census_1996()
    msa_cats = get_msa_size_categories(census)

    print("\nMerging and filtering...")
    merged = census.merge(
        tract_agg[
            ["msa_tract_key", "num_loans", "total_loan_amount", "years_with_data"]
        ],
        on="msa_tract_key",
        how="left",
    )
    merged["num_loans"] = merged["num_loans"].fillna(0)
    filtered = apply_bhutta_filters(merged)
    analysis = create_analysis_vars(filtered)
    print(f"  Final sample: {len(analysis):,}")

    # Filter to Large MSAs
    large_msas_df = analysis[analysis["msa_code"].isin(msa_cats["large"])]
    print(f"  Large MSAs: {len(large_msas_df):,}")

    # Run both approaches
    print("\n" + "=" * 70)
    print("COMPARING FE APPROACHES FOR h=0.05")
    print("=" * 70)

    result_explicit = run_rd_explicit_fe(large_msas_df, bandwidth=0.05)
    result_demeaned = run_rd_demeaned(large_msas_df, bandwidth=0.05)

    target = BHUTTA_TARGETS["large_msas_h05"]

    print(f"\n{'':20} {'Explicit FE':>14} {'Demeaned FE':>14} {'Bhutta':>14}")
    print("-" * 64)
    print(
        f"{'Coefficient:':20} {result_explicit['coef']:>14.4f} {result_demeaned['coef']:>14.4f} {target['coef']:>14.4f}"
    )
    print(
        f"{'Standard Error:':20} {result_explicit['se']:>14.4f} {result_demeaned['se']:>14.4f} {target['se']:>14.4f}"
    )
    print(
        f"{'N:':20} {result_explicit['n']:>14,} {result_demeaned['n']:>14,} {target['n']:>14,}"
    )
    print(
        f"{'R-squared:':20} {result_explicit['r2']:>14.4f} {result_demeaned['r2']:>14.4f} {'~0.869':>14}"
    )

    # Also test h=0.30
    print("\n" + "=" * 70)
    print("COMPARING FE APPROACHES FOR h=0.30")
    print("=" * 70)

    result_explicit_h30 = run_rd_explicit_fe(large_msas_df, bandwidth=0.30, cubic=True)
    result_demeaned_h30 = run_rd_demeaned(large_msas_df, bandwidth=0.30, cubic=True)

    target_h30 = BHUTTA_TARGETS["large_msas_h30"]

    print(f"\n{'':20} {'Explicit FE':>14} {'Demeaned FE':>14} {'Bhutta':>14}")
    print("-" * 64)
    print(
        f"{'Coefficient:':20} {result_explicit_h30['coef']:>14.4f} {result_demeaned_h30['coef']:>14.4f} {target_h30['coef']:>14.4f}"
    )
    print(
        f"{'R-squared:':20} {result_explicit_h30['r2']:>14.4f} {result_demeaned_h30['r2']:>14.4f} {'~0.869':>14}"
    )

    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)

    coef_match = result_explicit["coef"] / target["coef"] * 100
    print(f"\nExplicit FE coefficient match: {coef_match:.1f}% of target")
    print(f"R² with explicit FE: {result_explicit['r2']:.4f} (target ~0.869)")

    if result_explicit["r2"] > result_demeaned["r2"]:
        print("\n✓ Explicit FE gives HIGHER R² (more appropriate approach)")
    else:
        print("\n✗ R² similar between approaches (not the main issue)")


if __name__ == "__main__":
    main()
