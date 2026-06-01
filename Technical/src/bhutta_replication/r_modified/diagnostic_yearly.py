"""
Diagnostic: Year-by-Year RD Analysis for Bhutta (2011) Replication

PURPOSE: Understand why single-year analysis gives positive coefficient (+0.0697)
         but multi-year aggregation gives near-zero coefficient.

HYPOTHESIS: The aggregation method (summing originations) may be incorrect.
            Bhutta may be using a pooled panel approach with year fixed effects.
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
    str(DATA_ROOT / "Technical/src/bhutta_replication/r_modified/output_v2")
)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

YEARS = [1994, 1995, 1996, 1997, 1998, 1999, 2000, 2001, 2002]


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
        chunk["action_taken"] = pd.to_numeric(chunk["action_taken"], errors="coerce")
        chunk["loan_purpose"] = pd.to_numeric(chunk["loan_purpose"], errors="coerce")
        chunk["occupancy_type"] = pd.to_numeric(
            chunk["occupancy_type"], errors="coerce"
        )
        chunk["loan_amount"] = pd.to_numeric(chunk["loan_amount"], errors="coerce")
        chunk["agency_code"] = pd.to_numeric(chunk["agency_code"], errors="coerce")

        # Bhutta filters + BANKS ONLY
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


def aggregate_hmda_tract_year(hmda: pd.DataFrame) -> pd.DataFrame:
    """Aggregate HMDA to TRACT-YEAR level."""
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


def load_census_1996() -> pd.DataFrame:
    """Load base census characteristics."""
    path = CENSUS_DIR / "census_1996.parquet"
    df = pd.read_parquet(path)
    df["tract_in_msa"] = df["tract"].astype(str).str.zfill(6)
    df["msa_tract_key"] = df["msa_code"].astype(str) + "_" + df["tract_in_msa"]
    return df


def get_large_msas(census: pd.DataFrame) -> set:
    """Get MSAs with pop > 2M."""
    msa_pop = census.groupby("msa_code")["population"].sum().reset_index()
    msa_pop.columns = ["msa_code", "msa_pop"]
    msa_pop = msa_pop[~msa_pop["msa_code"].isin(["9999", 9999])]
    large = set(msa_pop[msa_pop["msa_pop"] > 2_000_000]["msa_code"])
    print(f"  Large MSAs (pop > 2M): {len(large)}")
    return large


def run_single_year_rd(
    merged: pd.DataFrame, large_msas: set, bandwidth: float = 0.05
) -> dict:
    """Run RD regression on a single year of data."""
    # Filter to large MSAs
    sample = merged[merged["msa_code"].isin(large_msas)].copy()

    # Apply Bhutta filters
    sample = sample[~sample["state_code"].astype(str).isin(["02", "15", "2"])]
    sample = sample[sample["total_housing_units"] >= 100]
    sample = sample[sample["num_loans"] > 0]

    # Originations per housing unit filter
    sample["orig_per_hu"] = sample["num_loans"] / sample["total_housing_units"]
    sample = sample[(sample["orig_per_hu"] >= 0.01) & (sample["orig_per_hu"] <= 3)]

    # Treatment indicator
    sample["D"] = (sample["TM"] < 0.80).astype(int)
    sample["TM_c"] = sample["TM"] - 0.80
    sample["D_TM"] = sample["D"] * sample["TM_c"]
    sample["ln_num_loans"] = np.log(sample["num_loans"].clip(lower=1))

    # Control variables
    sample["ln_oou"] = np.log(sample["owner_occupied_units"].clip(lower=1))
    sample["ln_value"] = np.log(sample["median_home_value"].clip(lower=1))
    sample["pct_pre1940"] = sample["housing_pre1940"] / sample[
        "total_housing_units"
    ].clip(lower=1)
    sample["pct_1940_69"] = sample["housing_1940_1969"] / sample[
        "total_housing_units"
    ].clip(lower=1)

    # Bandwidth filter
    sample = sample[
        (sample["TM"] >= 0.80 - bandwidth) & (sample["TM"] <= 0.80 + bandwidth)
    ]

    if len(sample) < 30:
        return {"error": "Insufficient observations", "n": len(sample)}

    # Regression
    regressors = [
        "D",
        "TM_c",
        "D_TM",
        "minority_pct",
        "ln_oou",
        "ln_value",
        "pct_pre1940",
        "pct_1940_69",
    ]
    reg_sample = sample.dropna(subset=["ln_num_loans"] + regressors + ["msa_code"])

    # MSA FE via demeaning
    for col in ["ln_num_loans"] + regressors:
        reg_sample[col + "_dm"] = reg_sample.groupby("msa_code")[col].transform(
            lambda x: x - x.mean()
        )

    X = reg_sample[[r + "_dm" for r in regressors]]
    y = reg_sample["ln_num_loans_dm"]

    if len(reg_sample) < 30:
        return {"error": "Insufficient after NA drop", "n": len(reg_sample)}

    try:
        model = sm.OLS(y, X).fit(
            cov_type="cluster", cov_kwds={"groups": reg_sample["msa_code"]}
        )
        return {
            "coef": model.params["D_dm"],
            "se": model.bse["D_dm"],
            "t_stat": model.tvalues["D_dm"],
            "p_value": model.pvalues["D_dm"],
            "n": len(reg_sample),
            "n_clusters": reg_sample["msa_code"].nunique(),
        }
    except Exception as e:
        return {"error": str(e), "n": len(reg_sample)}


def run_pooled_panel_rd(
    all_data: pd.DataFrame, large_msas: set, bandwidth: float = 0.05
) -> dict:
    """
    Run POOLED panel RD regression with YEAR fixed effects.

    This treats each tract-year as an observation, adding year FE.
    This may be what Bhutta actually does.
    """
    # Filter to large MSAs
    sample = all_data[all_data["msa_code"].isin(large_msas)].copy()

    # Apply Bhutta filters
    sample = sample[~sample["state_code"].astype(str).isin(["02", "15", "2"])]
    sample = sample[sample["total_housing_units"] >= 100]
    sample = sample[sample["num_loans"] > 0]

    # Originations per housing unit filter (per year, so relax threshold)
    sample["orig_per_hu"] = sample["num_loans"] / sample["total_housing_units"]
    sample = sample[(sample["orig_per_hu"] >= 0.001) & (sample["orig_per_hu"] <= 1)]

    # Treatment indicator
    sample["D"] = (sample["TM"] < 0.80).astype(int)
    sample["TM_c"] = sample["TM"] - 0.80
    sample["D_TM"] = sample["D"] * sample["TM_c"]
    sample["ln_num_loans"] = np.log(sample["num_loans"].clip(lower=1))

    # Control variables
    sample["ln_oou"] = np.log(sample["owner_occupied_units"].clip(lower=1))
    sample["ln_value"] = np.log(sample["median_home_value"].clip(lower=1))
    sample["pct_pre1940"] = sample["housing_pre1940"] / sample[
        "total_housing_units"
    ].clip(lower=1)
    sample["pct_1940_69"] = sample["housing_1940_1969"] / sample[
        "total_housing_units"
    ].clip(lower=1)

    # Bandwidth filter
    sample = sample[
        (sample["TM"] >= 0.80 - bandwidth) & (sample["TM"] <= 0.80 + bandwidth)
    ]

    if len(sample) < 100:
        return {"error": "Insufficient observations", "n": len(sample)}

    # Create year dummies
    year_dummies = pd.get_dummies(sample["year"], prefix="y", drop_first=True)
    sample = pd.concat(
        [sample.reset_index(drop=True), year_dummies.reset_index(drop=True)], axis=1
    )

    # Regression with MSA + Year FE via demeaning
    regressors = [
        "D",
        "TM_c",
        "D_TM",
        "minority_pct",
        "ln_oou",
        "ln_value",
        "pct_pre1940",
        "pct_1940_69",
    ]
    year_cols = [c for c in year_dummies.columns]
    all_regressors = regressors + year_cols

    reg_sample = sample.dropna(subset=["ln_num_loans"] + regressors + ["msa_code"])

    # MSA FE via demeaning (year FE via dummies)
    for col in ["ln_num_loans"] + regressors:
        reg_sample[col + "_dm"] = reg_sample.groupby("msa_code")[col].transform(
            lambda x: x - x.mean()
        )

    X_vars = [r + "_dm" for r in regressors] + year_cols
    X = reg_sample[X_vars]
    y = reg_sample["ln_num_loans_dm"]

    try:
        model = sm.OLS(y, X).fit(
            cov_type="cluster", cov_kwds={"groups": reg_sample["msa_code"]}
        )
        return {
            "coef": model.params["D_dm"],
            "se": model.bse["D_dm"],
            "t_stat": model.tvalues["D_dm"],
            "p_value": model.pvalues["D_dm"],
            "n": len(reg_sample),
            "n_tracts": reg_sample["msa_tract_key"].nunique(),
            "n_clusters": reg_sample["msa_code"].nunique(),
        }
    except Exception as e:
        return {"error": str(e), "n": len(reg_sample)}


def main():
    print("=" * 70)
    print("DIAGNOSTIC: Year-by-Year RD Analysis")
    print("=" * 70)
    print()

    # Load census once
    print("Loading census data...")
    census = load_census_1996()
    large_msas = get_large_msas(census)

    print("\n" + "=" * 70)
    print("PART 1: Single-Year RD Regressions (Large MSAs, h=0.05)")
    print("=" * 70)

    yearly_results = []
    all_tract_years = []

    for year in YEARS:
        print(f"\n--- Year {year} ---")
        print(f"  Loading HMDA data...", end=" ")
        hmda = load_hmda_year(year)
        if len(hmda) == 0:
            print("No data")
            continue
        print(f"{len(hmda):,} loans")

        # Aggregate to tract-year
        tract_year = aggregate_hmda_tract_year(hmda)
        print(f"  Tract-years: {len(tract_year):,}")

        # Merge with census
        merged = census.merge(
            tract_year[["msa_tract_key", "num_loans", "total_loan_amount", "year"]],
            on="msa_tract_key",
            how="inner",
        )
        print(f"  Merged: {len(merged):,}")

        # Run RD
        result = run_single_year_rd(merged, large_msas)
        if "error" not in result:
            print(
                f"  β = {result['coef']:.4f} (SE={result['se']:.4f}), N={result['n']}"
            )
            yearly_results.append({"year": year, **result})
        else:
            print(f"  Error: {result['error']}")

        # Store for pooled analysis
        merged_filtered = merged[merged["num_loans"] > 0].copy()
        all_tract_years.append(merged_filtered)

    # Summary of yearly results
    if yearly_results:
        print("\n" + "-" * 70)
        print("YEAR-BY-YEAR SUMMARY:")
        print("-" * 70)
        print(f"{'Year':<6} {'Coef':>10} {'SE':>10} {'t-stat':>10} {'N':>8}")
        print("-" * 50)
        for r in yearly_results:
            print(
                f"{r['year']:<6} {r['coef']:>10.4f} {r['se']:>10.4f} {r['t_stat']:>10.2f} {r['n']:>8,}"
            )

        avg_coef = np.mean([r["coef"] for r in yearly_results])
        print("-" * 50)
        print(f"{'Average':<6} {avg_coef:>10.4f}")
        print(f"\nTarget coefficient: +0.0764")

    # PART 2: Pooled panel regression
    print("\n" + "=" * 70)
    print("PART 2: Pooled Panel RD (Tract-Year as Obs, Year FE)")
    print("=" * 70)

    if all_tract_years:
        all_data = pd.concat(all_tract_years, ignore_index=True)
        print(f"\nTotal tract-year observations: {len(all_data):,}")
        print(f"Unique tracts: {all_data['msa_tract_key'].nunique():,}")

        result = run_pooled_panel_rd(all_data, large_msas)
        if "error" not in result:
            print(f"\nPooled Panel Results:")
            print(f"  β = {result['coef']:.4f}")
            print(f"  SE = {result['se']:.4f}")
            print(f"  t-stat = {result['t_stat']:.2f}")
            print(f"  N (tract-years) = {result['n']:,}")
            print(f"  N (unique tracts) = {result['n_tracts']:,}")
            print(f"  N (clusters/MSAs) = {result['n_clusters']}")
            print(f"\n  Target: β = +0.0764, N = 1,800 (tracts)")
        else:
            print(f"  Error: {result['error']}")

    # Save results
    if yearly_results:
        df = pd.DataFrame(yearly_results)
        df.to_csv(OUTPUT_DIR / "diagnostic_yearly_results.csv", index=False)
        print(f"\nResults saved to: {OUTPUT_DIR / 'diagnostic_yearly_results.csv'}")


if __name__ == "__main__":
    main()
