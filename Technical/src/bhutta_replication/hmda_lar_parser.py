"""
HMDA LAR (Loan Application Register) Parser for 1990-2006 Data

Processes the historical HMDA LAR files and aggregates to tract-year level
for merging with census data.

Key filters (following Bhutta 2011):
- action_taken == 1 (originated loans only)
- loan_purpose == 1 (home purchase) or 3 (refinance)
- owner_occupancy == 1 (owner-occupied)
- loan_type in [1, 2, 3] (conventional, FHA, VA)
"""

from pathlib import Path
from typing import Optional, List
import pandas as pd
import numpy as np
import os
DATA_ROOT = Path(os.environ.get("DATA_ROOT", "data"))
OUTPUT_ROOT = Path(os.environ.get("OUTPUT_ROOT", "outputs"))


# Column names for 1990-2006 HMDA LAR files (pipe-delimited)
LAR_COLUMNS = [
    "activity_year",
    "respondent_id",
    "agency_code",
    "loan_type",
    "loan_purpose",
    "occupancy_type",
    "loan_amount",
    "action_taken",
    "msamd",
    "state_code",
    "county_code",
    "census_tract",
    "applicant_race_1",
    "co_applicant_race_1",
    "applicant_sex",
    "co_applicant_sex",
    "income",
    "purchaser_type",
    "denial_reason_1",
    "denial_reason_2",
    "denial_reason_3",
    "edit_status",
    "sequence_number",
]

# Relevant action codes
ACTION_ORIGINATED = 1  # Loan originated
ACTION_APPROVED_NOT_ACCEPTED = 2  # Approved but not accepted
ACTION_DENIED = 3  # Denied
ACTION_WITHDRAWN = 4  # Withdrawn
ACTION_INCOMPLETE = 5  # File closed - incomplete

# Loan purpose codes
PURPOSE_HOME_PURCHASE = 1
PURPOSE_HOME_IMPROVEMENT = 2
PURPOSE_REFINANCE = 3

# Occupancy types
OCCUPANCY_OWNER = 1
OCCUPANCY_NOT_OWNER = 2
OCCUPANCY_NOT_APPLICABLE = 3


def parse_hmda_lar(
    filepath: Path,
    year: Optional[int] = None,
    sample_frac: Optional[float] = None,
    chunksize: int = 500000,
) -> pd.DataFrame:
    """
    Parse HMDA LAR file and filter to originated loans.

    Args:
        filepath: Path to LAR txt file
        year: Override year (if not in filename)
        sample_frac: Fraction to sample (for testing)
        chunksize: Rows per chunk for processing

    Returns:
        DataFrame with originated loans
    """
    filepath = Path(filepath)

    # Extract year from filename if not provided
    if year is None:
        import re

        match = re.search(r"(\d{4})", filepath.name)
        if match:
            year = int(match.group(1))

    chunks = []

    for chunk in pd.read_csv(
        filepath,
        sep="|",
        names=LAR_COLUMNS,
        dtype={
            "respondent_id": str,
            "state_code": str,
            "county_code": str,
            "census_tract": str,
            "msamd": str,
        },
        chunksize=chunksize,
        skiprows=1,  # Skip header if present
        on_bad_lines="skip",
    ):
        # Apply Bhutta filters
        filtered = chunk[
            (chunk["action_taken"] == ACTION_ORIGINATED)
            & (chunk["loan_purpose"].isin([PURPOSE_HOME_PURCHASE, PURPOSE_REFINANCE]))
            & (chunk["occupancy_type"] == OCCUPANCY_OWNER)
        ]

        if sample_frac and sample_frac < 1.0:
            filtered = filtered.sample(frac=sample_frac)

        chunks.append(filtered)

    df = pd.concat(chunks, ignore_index=True)

    if year:
        df["year"] = year

    return df


def aggregate_to_tract_year(df: pd.DataFrame) -> pd.DataFrame:
    """
    Aggregate loan-level data to tract-year level.

    Returns:
        DataFrame with tract-year aggregates
    """
    # Create tract key
    df["tract_key"] = (
        df["state_code"].astype(str).str.zfill(2)
        + df["county_code"].astype(str).str.zfill(3)
        + df["census_tract"].astype(str).str.replace(".", "").str.zfill(6)
    )

    # Aggregate
    agg = (
        df.groupby(["tract_key", "year", "msamd", "state_code", "county_code"])
        .agg(
            num_loans=("loan_amount", "count"),
            total_loan_amount=("loan_amount", "sum"),
            mean_loan_amount=("loan_amount", "mean"),
            median_income=("income", "median"),
        )
        .reset_index()
    )

    # Log transform
    agg["ln_num_loans"] = np.log(agg["num_loans"].clip(lower=1))
    agg["ln_total_amount"] = np.log(agg["total_loan_amount"].clip(lower=1))

    return agg


def process_all_years(
    data_dir: Path,
    years: List[int] = None,
    output_path: Optional[Path] = None,
    sample_frac: Optional[float] = None,
) -> pd.DataFrame:
    """
    Process all HMDA LAR files and aggregate.

    Args:
        data_dir: Directory containing LAR files
        years: Years to process (default: 1994-2002)
        output_path: Optional path to save results
        sample_frac: Fraction to sample (for testing)

    Returns:
        Aggregated tract-year DataFrame
    """
    years = years or list(range(1994, 2003))
    data_dir = Path(data_dir)

    all_data = []

    for year in years:
        # Find file for year (handle date prefix format)
        patterns = [
            f"*HMDA_LAR_{year}.txt",
            f"*hmda_lar_{year}.txt",
            f"HMDA_LAR_{year}.txt",
        ]

        filepath = None
        for pattern in patterns:
            matches = list(data_dir.glob(pattern))
            if matches:
                filepath = matches[0]
                break

        if filepath is None:
            print(f"Warning: No file found for year {year}")
            continue

        print(f"Processing {year}...")

        try:
            df = parse_hmda_lar(filepath, year=year, sample_frac=sample_frac)
            agg = aggregate_to_tract_year(df)
            all_data.append(agg)
            print(f"  {len(df):,} loans -> {len(agg):,} tract-years")
        except Exception as e:
            print(f"  Error: {e}")
            continue

    result = pd.concat(all_data, ignore_index=True)

    if output_path:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        result.to_parquet(output_path)
        print(f"Saved to {output_path}")

    return result


def merge_with_census(
    hmda_df: pd.DataFrame, census_dir: Path, bandwidth: float = 0.05
) -> pd.DataFrame:
    """
    Merge HMDA tract-year data with census data.

    Args:
        hmda_df: HMDA tract-year aggregates
        census_dir: Directory with census parquet files
        bandwidth: RD bandwidth around 0.80 cutoff

    Returns:
        Merged analysis-ready DataFrame
    """
    census_dir = Path(census_dir)

    # Load census data
    census_dfs = []
    for year in hmda_df["year"].unique():
        census_path = census_dir / f"census_{year}.parquet"
        if census_path.exists():
            df = pd.read_parquet(census_path)
            df["year"] = year
            census_dfs.append(df)

    if not census_dfs:
        raise FileNotFoundError(f"No census files found in {census_dir}")

    census = pd.concat(census_dfs, ignore_index=True)

    # Create tract key in census
    census["tract_key"] = (
        census["state_code"].astype(str).str.zfill(2)
        + census["county_code"].astype(str).str.zfill(3)
        + census["tract"].astype(str).str.zfill(6)
    )

    # Merge
    merged = census.merge(
        hmda_df, on=["tract_key", "year"], how="left", suffixes=("", "_hmda")
    )

    # Fill missing loan counts with 0
    merged["num_loans"] = merged["num_loans"].fillna(0)
    merged["ln_num_loans"] = np.log(merged["num_loans"].clip(lower=1))

    # Apply bandwidth filter
    merged = merged[
        (merged["TM"] >= 0.80 - bandwidth) & (merged["TM"] <= 0.80 + bandwidth)
    ]

    # Create treatment indicator
    merged["D"] = (merged["TM"] < 0.80).astype(int)

    return merged


if __name__ == "__main__":
    # Example usage
    import sys

    data_dir = Path(
        str(DATA_ROOT / "Inputs/Old/CRA_code/_files2/1990to2006/src")
    )
    census_dir = OUTPUT_ROOT / "Technical/data/census_bhutta"
    output_dir = OUTPUT_ROOT / "Technical/data/hmda_processed"

    # Process with small sample for testing
    print("Processing HMDA LAR files (1% sample for testing)...")
    hmda_agg = process_all_years(
        data_dir,
        years=[1996, 1997, 1998],  # Start with subset
        output_path=output_dir / "hmda_tract_year_sample.parquet",
        sample_frac=0.01,  # 1% sample for testing
    )

    print(f"\nTotal tract-years: {len(hmda_agg):,}")
    print(f"Years: {sorted(hmda_agg['year'].unique())}")

    # Merge with census
    print("\nMerging with census data...")
    analysis_df = merge_with_census(hmda_agg, census_dir, bandwidth=0.05)

    print(f"Analysis sample (h=0.05): {len(analysis_df):,} tract-years")
    print(f"Treatment (D=1): {(analysis_df['D'] == 1).sum():,}")
    print(f"Control (D=0): {(analysis_df['D'] == 0).sum():,}")
