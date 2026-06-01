"""
Diagnostic script to check loan counts and outcome variable construction.

Questions:
1. Are we counting loans correctly?
2. What's the distribution of log(loans) near the cutoff?
3. Is there a discontinuity in the raw means?
"""

import pandas as pd
import numpy as np
from pathlib import Path
import os
DATA_ROOT = Path(os.environ.get("DATA_ROOT", "data"))
OUTPUT_ROOT = Path(os.environ.get("OUTPUT_ROOT", "outputs"))

HMDA_DIR = DATA_ROOT / "Inputs/Old/CRA_code/_files2/1990to2006/src"
CENSUS_DIR = OUTPUT_ROOT / "Technical/data/census_parsed_v2"

YEARS = [1994, 1995, 1996, 1997, 1998, 1999, 2000, 2001, 2002]


def load_hmda_summary():
    """Load HMDA and summarize loan counts."""
    total_loans = 0
    bank_loans = 0

    for year in YEARS:
        patterns = [f"*HMDA_LAR_{year}.txt", f"*hmda_lar_{year}.txt", f"*{year}*.txt"]
        filepath = None
        for pattern in patterns:
            matches = list(HMDA_DIR.glob(pattern))
            if matches:
                filepath = matches[0]
                break

        if filepath is None:
            continue

        for chunk in pd.read_csv(
            filepath,
            sep="|",
            chunksize=500000,
            dtype={"census_tract": str, "msamd": str, "loan_amount": str},
        ):
            chunk["action_taken"] = pd.to_numeric(
                chunk["action_taken"], errors="coerce"
            )
            chunk["loan_purpose"] = pd.to_numeric(
                chunk["loan_purpose"], errors="coerce"
            )
            chunk["occupancy_type"] = pd.to_numeric(
                chunk["occupancy_type"], errors="coerce"
            )
            chunk["agency_code"] = pd.to_numeric(chunk["agency_code"], errors="coerce")

            # All originated loans
            originated = chunk[chunk["action_taken"] == 1]
            total_loans += len(originated)

            # Bhutta sample: originated, home purchase/refi, owner-occupied, in MSA, BANKS ONLY
            bhutta_sample = originated[
                (originated["loan_purpose"].isin([1, 3]))
                & (originated["occupancy_type"] == 1)
                & (originated["msamd"].notna())
                & (originated["msamd"] != "")
                & (originated["agency_code"].isin([1, 2, 3, 5]))  # Banks only
            ]
            bank_loans += len(bhutta_sample)

    return total_loans, bank_loans


def analyze_discontinuity():
    """Check for discontinuity in raw means at the cutoff."""
    # Load pre-built data
    census = pd.read_parquet(CENSUS_DIR / "census_1996.parquet")

    # Get large MSAs
    msa_pop = census.groupby("msa_code")["population"].sum().reset_index()
    msa_pop = msa_pop[~msa_pop["msa_code"].isin(["9999", ""])]
    large_msas = set(msa_pop[msa_pop["population"] > 2_000_000]["msa_code"])

    census = census[census["msa_code"].isin(large_msas)]
    print(f"Large MSA tracts: {len(census):,}")

    # Load HMDA tract-level data
    hmda_dfs = []
    for year in YEARS:
        patterns = [f"*HMDA_LAR_{year}.txt", f"*hmda_lar_{year}.txt", f"*{year}*.txt"]
        filepath = None
        for pattern in patterns:
            matches = list(HMDA_DIR.glob(pattern))
            if matches:
                filepath = matches[0]
                break

        if filepath is None:
            continue

        chunks = []
        for chunk in pd.read_csv(
            filepath,
            sep="|",
            chunksize=500000,
            dtype={"census_tract": str, "msamd": str, "loan_amount": str},
        ):
            chunk["action_taken"] = pd.to_numeric(
                chunk["action_taken"], errors="coerce"
            )
            chunk["loan_purpose"] = pd.to_numeric(
                chunk["loan_purpose"], errors="coerce"
            )
            chunk["occupancy_type"] = pd.to_numeric(
                chunk["occupancy_type"], errors="coerce"
            )
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

        hmda_dfs.append(pd.concat(chunks, ignore_index=True))

    hmda = pd.concat(hmda_dfs, ignore_index=True)
    hmda["tract_only"] = (
        hmda["census_tract"].str.replace(".", "", regex=False).str.zfill(6)
    )
    hmda["msa_tract_key"] = hmda["msamd"].astype(str) + "_" + hmda["tract_only"]

    # Aggregate to tract
    tract_loans = hmda.groupby("msa_tract_key").size().reset_index(name="num_loans")

    # Merge with census
    merged = census.merge(tract_loans, on="msa_tract_key", how="left")
    merged["num_loans"] = merged["num_loans"].fillna(0)

    # Apply filters
    merged = merged[merged["total_housing_units"] >= 100]
    merged = merged[merged["owner_occupied_units"] > 0]
    merged = merged[merged["pct_group_quarters"] < 0.30]
    merged = merged[merged["num_loans"] > 0]
    merged["orig_per_oou"] = merged["num_loans"] / merged["owner_occupied_units"]
    merged = merged[(merged["orig_per_oou"] >= 0.25) & (merged["orig_per_oou"] <= 20)]

    print(f"After filters: {len(merged):,} tracts")

    # Create bins around cutoff
    merged["ln_loans"] = np.log(merged["num_loans"])

    bins = [(0.70, 0.75), (0.75, 0.80), (0.80, 0.85), (0.85, 0.90)]

    print("\n" + "=" * 60)
    print("RAW DISCONTINUITY CHECK")
    print("=" * 60)
    print(f"{'TM Range':15} {'N':>8} {'Mean ln(loans)':>15} {'Mean loans':>12}")
    print("-" * 60)

    for low, high in bins:
        subset = merged[(merged["TM"] >= low) & (merged["TM"] < high)]
        if len(subset) > 0:
            mean_ln = subset["ln_loans"].mean()
            mean_loans = subset["num_loans"].mean()
            print(
                f"[{low:.2f}, {high:.2f})   {len(subset):>8,} {mean_ln:>15.4f} {mean_loans:>12.1f}"
            )

    # Compute raw discontinuity
    below = merged[(merged["TM"] >= 0.75) & (merged["TM"] < 0.80)]
    above = merged[(merged["TM"] >= 0.80) & (merged["TM"] < 0.85)]

    if len(below) > 0 and len(above) > 0:
        disc = below["ln_loans"].mean() - above["ln_loans"].mean()
        print(f"\nRaw discontinuity (below - above): {disc:.4f}")
        print("  (Bhutta target: ~0.0764)")

    return merged


def main():
    print("=" * 70)
    print("DIAGNOSTIC: CHECKING LOAN COUNTS AND OUTCOME VARIABLE")
    print("=" * 70)

    # Check loan counts
    print("\nStep 1: Counting loans...")
    total, bank = load_hmda_summary()
    print(f"  Total originated loans (1994-2002): {total:,}")
    print(f"  Bank loans (agency 1,2,3,5): {bank:,}")
    print(f"  Bank share: {bank/total*100:.1f}%")

    # Analyze discontinuity
    print("\nStep 2: Analyzing discontinuity...")
    merged = analyze_discontinuity()

    # Show tract-level stats
    print("\n" + "=" * 60)
    print("TRACT-LEVEL SUMMARY (Large MSAs, h=0.05)")
    print("=" * 60)

    h05 = merged[(merged["TM"] >= 0.75) & (merged["TM"] <= 0.85)]
    print(f"Tracts in h=0.05 window: {len(h05):,}")
    print(f"  Mean loans per tract: {h05['num_loans'].mean():.1f}")
    print(f"  Median loans per tract: {h05['num_loans'].median():.1f}")
    print(f"  Mean ln(loans): {h05['ln_loans'].mean():.4f}")
    print(f"  Std ln(loans): {h05['ln_loans'].std():.4f}")


if __name__ == "__main__":
    main()
