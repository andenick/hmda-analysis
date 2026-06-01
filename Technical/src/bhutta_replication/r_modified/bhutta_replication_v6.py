"""
Bhutta (2011) RD Replication - Version 6 (Specification Tests)

Testing additional specifications to close the coefficient gap:
1. Home purchase only (loan_purpose=1) vs purchase+refi
2. Year fixed effects in addition to MSA FE
3. Different bandwidths
4. All lenders vs bank-only

Current status: β = +0.0503, Target = +0.0764 (66% match)
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
    str(DATA_ROOT / "Technical/src/bhutta_replication/r_modified/output_v6")
)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

YEARS = [1994, 1995, 1996, 1997, 1998, 1999, 2000, 2001, 2002]

BHUTTA_TARGETS = {
    "large_msas_h05": {"coef": 0.0764, "se": 0.0274, "n": 1800},
}


def load_hmda_year(
    year: int, bank_only: bool = True, purchase_only: bool = False
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

        # Agency filter
        if bank_only:
            mask = mask & (chunk["agency_code"].isin([1, 2, 3, 5]))

        chunks.append(chunk[mask])

    df = pd.concat(chunks, ignore_index=True)
    df["year"] = year
    return df


def aggregate_hmda(hmda: pd.DataFrame, by_year: bool = False) -> pd.DataFrame:
    """Aggregate HMDA to tract level, optionally keeping year dimension."""
    hmda["tract_only"] = (
        hmda["census_tract"].str.replace(".", "", regex=False).str.zfill(6)
    )
    hmda["msa_tract_key"] = hmda["msamd"].astype(str) + "_" + hmda["tract_only"]

    if by_year:
        # Tract-year level
        tract_agg = (
            hmda.groupby(["msa_tract_key", "msamd", "year"])
            .agg(num_loans=("loan_amount", "count"))
            .reset_index()
        )
    else:
        # Tract level (sum over years)
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


def apply_filters(df: pd.DataFrame) -> pd.DataFrame:
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


def create_vars(df: pd.DataFrame) -> pd.DataFrame:
    """Create analysis variables."""
    result = df.copy()
    result["D"] = (result["TM"] < 0.80).astype(int)
    result["TM_c"] = result["TM"] - 0.80
    result["D_TM"] = result["D"] * result["TM_c"]
    result["ln_num_loans"] = np.log(result["num_loans"].clip(lower=1))
    result["ln_oou"] = np.log(result["owner_occupied_units"].clip(lower=1))
    result["ln_value"] = np.log(result["median_home_value"].clip(lower=1))
    return result


def run_rd(df: pd.DataFrame, bandwidth: float, year_fe: bool = False) -> dict:
    """Run RD regression with optional year FE."""
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

    if year_fe and "year" in sample.columns:
        reg_vars.append("year")

    sample = sample.dropna(subset=reg_vars)

    if len(sample) < 50:
        return {"error": "Insufficient observations", "n": len(sample)}

    # Create MSA dummies
    msa_dummies = pd.get_dummies(
        sample["msa_code"], prefix="msa", drop_first=True, dtype=float
    )

    # Optionally create year dummies
    if year_fe and "year" in sample.columns:
        year_dummies = pd.get_dummies(
            sample["year"], prefix="yr", drop_first=True, dtype=float
        )
        X_regressors = sample[regressors].astype(float)
        X = pd.concat(
            [
                X_regressors.reset_index(drop=True),
                msa_dummies.reset_index(drop=True),
                year_dummies.reset_index(drop=True),
            ],
            axis=1,
        )
    else:
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
        "t_stat": model.tvalues["D"],
        "p_value": model.pvalues["D"],
        "n": len(sample),
        "n_clusters": sample["msa_code"].nunique(),
        "r2": model.rsquared,
    }


def main():
    print("=" * 70)
    print("BHUTTA (2011) RD REPLICATION - VERSION 6 (SPECIFICATION TESTS)")
    print("=" * 70)
    print()

    # Load census
    print("Loading census data...")
    census = load_census()
    large_msas = get_large_msas(census)
    print(f"  Large MSAs: {len(large_msas)}")

    # Test different specifications
    specs = [
        {
            "name": "Baseline (bank, purch+refi)",
            "bank_only": True,
            "purchase_only": False,
        },
        {"name": "Purchase only (bank)", "bank_only": True, "purchase_only": True},
        {
            "name": "All lenders (purch+refi)",
            "bank_only": False,
            "purchase_only": False,
        },
        {"name": "All lenders (purch only)", "bank_only": False, "purchase_only": True},
    ]

    results = []

    for spec in specs:
        print(f"\nTesting: {spec['name']}")
        print("-" * 50)

        # Load HMDA
        hmda_dfs = []
        for year in YEARS:
            df = load_hmda_year(
                year, bank_only=spec["bank_only"], purchase_only=spec["purchase_only"]
            )
            if len(df) > 0:
                hmda_dfs.append(df)

        hmda_all = pd.concat(hmda_dfs, ignore_index=True)
        print(f"  Total loans: {len(hmda_all):,}")

        # Aggregate
        tract_agg = aggregate_hmda(hmda_all, by_year=False)

        # Merge with census
        merged = census.merge(
            tract_agg[["msa_tract_key", "num_loans"]],
            on="msa_tract_key",
            how="left",
        )
        merged["num_loans"] = merged["num_loans"].fillna(0)

        # Filter
        filtered = apply_filters(merged)
        analysis = create_vars(filtered)

        # Large MSAs only
        large_df = analysis[analysis["msa_code"].isin(large_msas)]
        print(f"  Large MSA tracts: {len(large_df):,}")

        # Run RD
        result = run_rd(large_df, bandwidth=0.05)
        result["spec"] = spec["name"]
        results.append(result)

        print(f"  Coefficient: {result['coef']:.4f} (target: 0.0764)")
        print(f"  N: {result['n']:,}")
        print(f"  R²: {result['r2']:.4f}")

    # Summary table
    print("\n" + "=" * 70)
    print("SPECIFICATION COMPARISON")
    print("=" * 70)
    print(f"\n{'Specification':<35} {'Coef':>10} {'SE':>10} {'N':>8} {'Match%':>8}")
    print("-" * 75)

    target = BHUTTA_TARGETS["large_msas_h05"]["coef"]
    for r in results:
        match_pct = r["coef"] / target * 100
        print(
            f"{r['spec']:<35} {r['coef']:>10.4f} {r['se']:>10.4f} {r['n']:>8,} {match_pct:>7.1f}%"
        )

    print(
        f"\n{'Bhutta Target':<35} {target:>10.4f} {'0.0274':>10} {'1,800':>8} {'100.0%':>8}"
    )

    # Save results
    results_df = pd.DataFrame(results)
    results_df.to_csv(OUTPUT_DIR / "specification_tests.csv", index=False)
    print(f"\nResults saved to: {OUTPUT_DIR / 'specification_tests.csv'}")


if __name__ == "__main__":
    main()
