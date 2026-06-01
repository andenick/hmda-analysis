"""
Parse FFIEC Census Flat Files using handmade schemas.

The schemas are in Excel format in:
${OUTPUT_ROOT}/Inputs/Old/CRA_code/_files2/flatFiles/_flatFileGuide2/

Key fields for Bhutta (2011) replication:
- MSA Code: positions 5-8
- State Code: positions 9-10
- Census Tract: positions 14-19
- Central City Flag: position 20
- Minority Percentage: positions 24-29 (2 decimals)
- Decennial MSA MFI Percentage (TM): positions 30-35 (2 decimals)
- Population: positions 44-51
- Total Housing Units: positions 1496-1503
- Owner Occupancy (critical!): positions 1544-1551
- Median Home Value: positions 2264-2271
- Housing pre-1940: positions 1888-1895
- Housing 1940-1949: positions 1880-1887
- Housing 1950-1959: positions 1872-1879
- Housing 1960-1969: positions 1864-1871
"""

import pandas as pd
import numpy as np
from pathlib import Path
import os
DATA_ROOT = Path(os.environ.get("DATA_ROOT", "data"))
OUTPUT_ROOT = Path(os.environ.get("OUTPUT_ROOT", "outputs"))

# Directories
FLAT_FILE_DIR = Path(
    str(DATA_ROOT / "Inputs/Old/CRA_code/_files2/flatFiles/src")
)
OUTPUT_DIR = OUTPUT_ROOT / "Technical/data/census_parsed"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# Field definitions for 1990-2002 flat files (1990 Census format)
# Format: (name, start_pos, end_pos, has_decimal_places)
# Note: positions are 1-indexed in the guide, but Python uses 0-indexed
FIELD_SPEC_1990_2002 = {
    "year": (0, 4),  # "As of" Date
    "msa_code": (4, 8),  # MSA Code
    "state_code": (8, 10),  # FIPS State Code
    "county_code": (10, 13),  # FIPS County Code
    "tract": (13, 19),  # Census tract-BNA
    "central_city_flag": (19, 20),  # Central City Flag
    "minority_pct_raw": (23, 29),  # Minority Percentage (2 decimals)
    "tm_raw": (29, 35),  # Decennial MSA MFI Percentage (2 decimals)
    "msa_mfi": (35, 43),  # HUD Estimated MSA MFI
    "population": (43, 51),  # Persons/Population
    "total_housing_units": (1495, 1503),  # Total Housing Units
    "owner_occupied_units": (1543, 1551),  # Tenure_Owner Occupancy
    "renter_occupied_units": (1551, 1559),  # Tenure_Renter
    "median_home_value": (2263, 2271),  # Median Value
    "housing_pre1940": (1887, 1895),  # 1939 or earlier
    "housing_1940_1949": (1879, 1887),  # 1940-1949
    "housing_1950_1959": (1871, 1879),  # 1950-1959
    "housing_1960_1969": (1863, 1871),  # 1960-1969
}


def parse_flat_file(filepath: Path, field_spec: dict) -> pd.DataFrame:
    """Parse a fixed-width FFIEC census flat file."""
    records = []

    with open(filepath, "r", encoding="latin-1") as f:
        for line_num, line in enumerate(f, 1):
            if len(line.strip()) == 0:
                continue

            record = {}
            try:
                for field_name, (start, end) in field_spec.items():
                    if end <= len(line):
                        value = line[start:end].strip()
                        record[field_name] = value
                    else:
                        record[field_name] = ""
                records.append(record)
            except Exception as e:
                if line_num <= 5:
                    print(f"  Warning: Error on line {line_num}: {e}")
                continue

    df = pd.DataFrame(records)
    return df


def clean_census_data(df: pd.DataFrame) -> pd.DataFrame:
    """Clean and convert parsed census data."""
    result = pd.DataFrame()

    # Key identifiers
    result["year"] = pd.to_numeric(df["year"], errors="coerce")
    result["msa_code"] = df["msa_code"].str.strip()
    result["state_code"] = df["state_code"].str.strip()
    result["county_code"] = df["county_code"].str.strip()
    result["tract"] = df["tract"].str.strip()
    result["central_city_flag"] = df["central_city_flag"].str.strip()

    # Percentages (divide by 100)
    result["minority_pct"] = (
        pd.to_numeric(df["minority_pct_raw"], errors="coerce") / 100
    )
    result["TM"] = (
        pd.to_numeric(df["tm_raw"], errors="coerce") / 100
    )  # This is tract MFI / MSA MFI

    # Numeric fields
    result["msa_mfi"] = pd.to_numeric(df["msa_mfi"], errors="coerce")
    result["population"] = pd.to_numeric(df["population"], errors="coerce")
    result["total_housing_units"] = pd.to_numeric(
        df["total_housing_units"], errors="coerce"
    )
    result["owner_occupied_units"] = pd.to_numeric(
        df["owner_occupied_units"], errors="coerce"
    )
    result["renter_occupied_units"] = pd.to_numeric(
        df["renter_occupied_units"], errors="coerce"
    )
    result["median_home_value"] = pd.to_numeric(
        df["median_home_value"], errors="coerce"
    )
    result["housing_pre1940"] = pd.to_numeric(df["housing_pre1940"], errors="coerce")
    result["housing_1940_1949"] = pd.to_numeric(
        df["housing_1940_1949"], errors="coerce"
    )
    result["housing_1950_1959"] = pd.to_numeric(
        df["housing_1950_1959"], errors="coerce"
    )
    result["housing_1960_1969"] = pd.to_numeric(
        df["housing_1960_1969"], errors="coerce"
    )

    # Derived fields
    result["housing_1940_1969"] = (
        result["housing_1940_1949"].fillna(0)
        + result["housing_1950_1959"].fillna(0)
        + result["housing_1960_1969"].fillna(0)
    )

    # Create tract key for merging
    result["msa_tract_key"] = result["msa_code"] + "_" + result["tract"]

    return result


def process_year(year: int) -> pd.DataFrame:
    """Process a single year of census data."""
    filepath = FLAT_FILE_DIR / str(year) / f"census_{year}.dat"

    if not filepath.exists():
        print(f"  File not found: {filepath}")
        return None

    print(f"  Parsing {filepath.name}...")
    raw_df = parse_flat_file(filepath, FIELD_SPEC_1990_2002)
    print(f"  Raw records: {len(raw_df):,}")

    print(f"  Cleaning data...")
    clean_df = clean_census_data(raw_df)

    # Basic validation
    oou_valid = (clean_df["owner_occupied_units"] > 0).sum()
    print(f"  Tracts with OOU > 0: {oou_valid:,} ({oou_valid/len(clean_df)*100:.1f}%)")
    print(f"  Mean OOU: {clean_df['owner_occupied_units'].mean():.1f}")
    print(f"  Mean Total HU: {clean_df['total_housing_units'].mean():.1f}")

    return clean_df


def main():
    print("=" * 70)
    print("PARSING FFIEC CENSUS FLAT FILES")
    print("=" * 70)
    print()

    # Process years 1994-2002 (Bhutta's period)
    all_dfs = []

    for year in range(1994, 2003):
        print(f"\nProcessing {year}...")
        df = process_year(year)
        if df is not None:
            # Save individual year
            output_path = OUTPUT_DIR / f"census_{year}.parquet"
            df.to_parquet(output_path, index=False)
            print(f"  Saved to {output_path.name}")
            all_dfs.append(df)

    if all_dfs:
        # Also create a combined file for 1996 (base year for Bhutta)
        print("\n" + "=" * 70)
        print("SUMMARY")
        print("=" * 70)

        # Use 1996 as the base census year (matches Bhutta's methodology)
        base_df = [df for df in all_dfs if df["year"].iloc[0] == 1996]
        if base_df:
            base_df = base_df[0]
            print(f"\n1996 Census (base year for Bhutta):")
            print(f"  Total tracts: {len(base_df):,}")
            print(f"  Mean OOU: {base_df['owner_occupied_units'].mean():.1f}")
            print(f"  Mean Total HU: {base_df['total_housing_units'].mean():.1f}")
            print(f"  Mean Population: {base_df['population'].mean():.1f}")

            # Check large MSAs
            msa_pop = base_df.groupby("msa_code")["population"].sum().reset_index()
            msa_pop = msa_pop[~msa_pop["msa_code"].isin(["9999", ""])]
            large_msas = msa_pop[msa_pop["population"] > 2_000_000]
            print(f"  Large MSAs (pop > 2M): {len(large_msas)}")

            # Bhutta Table 1 validation
            near_cutoff = base_df[(base_df["TM"] >= 0.70) & (base_df["TM"] < 0.90)]
            print(f"\n  Tracts near cutoff (0.70 <= TM < 0.90):")
            print(f"    Count: {len(near_cutoff):,}")
            print(f"    Mean OOU: {near_cutoff['owner_occupied_units'].mean():.1f}")
            print(f"    (Bhutta Table 1 shows ~864-1017)")

    print("\n" + "=" * 70)
    print("DONE - New census files saved to:", OUTPUT_DIR)
    print("=" * 70)


if __name__ == "__main__":
    main()
