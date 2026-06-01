"""
Parse FFIEC Census Flat Files - Version 2 (Extended Variables)

Enhanced version that extracts ALL variables needed for Bhutta (2011) replication:
- Age 65+ population (positions 220-227)
- Property type breakdown (1-unit, 2-4 units, 5+ units)
- Group quarters population

Key improvements over v1:
1. Extracts all control variables Bhutta uses
2. Calculates derived percentages correctly
3. Pre-computes variables for regression
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
OUTPUT_DIR = OUTPUT_ROOT / "Technical/data/census_parsed_v2"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# Extended field definitions for 1990-2002 flat files
# Format: (name, start_pos, end_pos)  -- positions are 0-indexed
FIELD_SPEC_EXTENDED = {
    # Key identifiers
    "year": (0, 4),  # "As of" Date
    "msa_code": (4, 8),  # MSA Code
    "state_code": (8, 10),  # FIPS State Code
    "county_code": (10, 13),  # FIPS County Code
    "tract": (13, 19),  # Census tract-BNA
    "central_city_flag": (19, 20),  # Central City Flag
    # Income and demographics
    "minority_pct_raw": (23, 29),  # Minority Percentage (2 decimals)
    "tm_raw": (29, 35),  # Decennial MSA MFI Percentage (2 decimals)
    "msa_mfi": (35, 43),  # HUD Estimated MSA MFI
    "population": (43, 51),  # Total Population
    # Age breakdown - for "% age 65+" control
    "pop_65_plus": (219, 227),  # Population 65 and over (row 34)
    "pop_all_ages": (227, 235),  # All Ages Count (row 35)
    # Group quarters - for group quarters filter
    "gq_correctional": (259, 267),  # Correctional
    "gq_nursing": (267, 275),  # Nursing homes
    "gq_mental": (275, 283),  # Mental hospitals
    "gq_juvenile": (283, 291),  # Juvenile
    "gq_other_inst": (291, 299),  # Other institutional
    "gq_college": (299, 307),  # College
    "gq_military": (307, 315),  # Military
    "gq_homeless": (315, 323),  # Homeless shelters
    "gq_visible_street": (323, 331),  # Visible in street
    "gq_other": (331, 339),  # Other group quarters
    # Poverty level
    "poverty_pct_raw": (1419, 1425),  # Poverty Level Percentage (2 decimals)
    # Housing totals
    "total_housing_units": (1495, 1503),  # Total Housing Units
    "owner_occupied_units": (1543, 1551),  # Tenure_Owner Occupancy
    "renter_occupied_units": (1551, 1559),  # Tenure_Renter
    # Property types - for single-family, 2-4 family, 5+ family controls
    "hu_1_detached": (1559, 1567),  # 1 Unit Detached
    "hu_1_attached": (1567, 1575),  # 1 Unit Attached
    "hu_2_units": (1575, 1583),  # 2 Units
    "hu_3_4_units": (1583, 1591),  # 3&4 Units
    "hu_5_plus": (1655, 1663),  # 5+ Units
    "hu_mobile_other": (1591, 1599),  # Mobile Homes + Other
    # Housing value
    "median_home_value": (2263, 2271),  # Median Value
    # Housing by year built - for pre-1940 and 1940-69 controls
    "housing_pre1940": (1887, 1895),  # 1939 or earlier
    "housing_1940_1949": (1879, 1887),  # 1940-1949
    "housing_1950_1959": (1871, 1879),  # 1950-1959
    "housing_1960_1969": (1863, 1871),  # 1960-1969
}


def parse_flat_file(filepath: Path) -> pd.DataFrame:
    """Parse a fixed-width FFIEC census flat file."""
    records = []

    with open(filepath, "r", encoding="latin-1") as f:
        for line_num, line in enumerate(f, 1):
            if len(line.strip()) == 0:
                continue

            record = {}
            try:
                for field_name, (start, end) in FIELD_SPEC_EXTENDED.items():
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

    return pd.DataFrame(records)


def clean_census_data(df: pd.DataFrame) -> pd.DataFrame:
    """Clean and convert parsed census data with all variables."""
    result = pd.DataFrame()

    # Key identifiers
    result["year"] = pd.to_numeric(df["year"], errors="coerce")
    result["msa_code"] = df["msa_code"].str.strip()
    result["state_code"] = df["state_code"].str.strip()
    result["county_code"] = df["county_code"].str.strip()
    result["tract"] = df["tract"].str.strip()
    result["central_city_flag"] = df["central_city_flag"].str.strip()

    # Percentages (divide by 100 since they have 2 decimal places)
    result["minority_pct"] = (
        pd.to_numeric(df["minority_pct_raw"], errors="coerce") / 100
    )
    result["TM"] = pd.to_numeric(df["tm_raw"], errors="coerce") / 100
    result["poverty_pct"] = pd.to_numeric(df["poverty_pct_raw"], errors="coerce") / 100

    # Income
    result["msa_mfi"] = pd.to_numeric(df["msa_mfi"], errors="coerce")

    # Population
    result["population"] = pd.to_numeric(df["population"], errors="coerce")
    result["pop_65_plus"] = pd.to_numeric(df["pop_65_plus"], errors="coerce")
    result["pop_all_ages"] = pd.to_numeric(df["pop_all_ages"], errors="coerce")

    # Group quarters - sum all components
    gq_cols = [
        "gq_correctional",
        "gq_nursing",
        "gq_mental",
        "gq_juvenile",
        "gq_other_inst",
        "gq_college",
        "gq_military",
        "gq_homeless",
        "gq_visible_street",
        "gq_other",
    ]
    for col in gq_cols:
        result[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
    result["group_quarters_pop"] = result[gq_cols].sum(axis=1)

    # Housing totals
    result["total_housing_units"] = pd.to_numeric(
        df["total_housing_units"], errors="coerce"
    )
    result["owner_occupied_units"] = pd.to_numeric(
        df["owner_occupied_units"], errors="coerce"
    )
    result["renter_occupied_units"] = pd.to_numeric(
        df["renter_occupied_units"], errors="coerce"
    )

    # Property types
    result["hu_1_detached"] = pd.to_numeric(df["hu_1_detached"], errors="coerce")
    result["hu_1_attached"] = pd.to_numeric(df["hu_1_attached"], errors="coerce")
    result["hu_2_units"] = pd.to_numeric(df["hu_2_units"], errors="coerce")
    result["hu_3_4_units"] = pd.to_numeric(df["hu_3_4_units"], errors="coerce")
    result["hu_5_plus"] = pd.to_numeric(df["hu_5_plus"], errors="coerce")
    result["hu_mobile_other"] = pd.to_numeric(df["hu_mobile_other"], errors="coerce")

    # Housing value
    result["median_home_value"] = pd.to_numeric(
        df["median_home_value"], errors="coerce"
    )

    # Housing by year built
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

    # Derived variables for regression
    total_hu = result["total_housing_units"].clip(lower=1)
    pop = result["population"].clip(lower=1)

    # % age 65+ (Bhutta control)
    result["pct_age_65_plus"] = result["pop_65_plus"].fillna(0) / pop

    # % group quarters (for filter: < 30%)
    result["pct_group_quarters"] = result["group_quarters_pop"] / pop

    # Property type percentages (Bhutta controls)
    result["pct_single_family"] = (
        result["hu_1_detached"].fillna(0) + result["hu_1_attached"].fillna(0)
    ) / total_hu
    result["pct_2_4_family"] = (
        result["hu_2_units"].fillna(0) + result["hu_3_4_units"].fillna(0)
    ) / total_hu
    result["pct_5_plus"] = result["hu_5_plus"].fillna(0) / total_hu

    # Housing age percentages (Bhutta controls)
    result["pct_pre1940"] = result["housing_pre1940"].fillna(0) / total_hu
    result["housing_1940_1969"] = (
        result["housing_1940_1949"].fillna(0)
        + result["housing_1950_1959"].fillna(0)
        + result["housing_1960_1969"].fillna(0)
    )
    result["pct_1940_69"] = result["housing_1940_1969"] / total_hu

    # Create tract key for merging
    result["msa_tract_key"] = result["msa_code"] + "_" + result["tract"]

    # Drop temporary group quarter columns
    result = result.drop(columns=gq_cols)

    return result


def process_year(year: int) -> pd.DataFrame:
    """Process a single year of census data."""
    filepath = FLAT_FILE_DIR / str(year) / f"census_{year}.dat"

    if not filepath.exists():
        print(f"  File not found: {filepath}")
        return None

    print(f"  Parsing {filepath.name}...")
    raw_df = parse_flat_file(filepath)
    print(f"  Raw records: {len(raw_df):,}")

    print(f"  Cleaning and computing derived variables...")
    clean_df = clean_census_data(raw_df)

    # Validation
    oou_valid = (clean_df["owner_occupied_units"] > 0).sum()
    print(f"  Tracts with OOU > 0: {oou_valid:,} ({oou_valid/len(clean_df)*100:.1f}%)")
    print(f"  Mean OOU: {clean_df['owner_occupied_units'].mean():.1f}")
    print(f"  Mean Total HU: {clean_df['total_housing_units'].mean():.1f}")
    print(f"  Mean % age 65+: {clean_df['pct_age_65_plus'].mean()*100:.1f}%")
    print(f"  Mean % group quarters: {clean_df['pct_group_quarters'].mean()*100:.1f}%")
    print(f"  Mean % single-family: {clean_df['pct_single_family'].mean()*100:.1f}%")

    return clean_df


def main():
    print("=" * 70)
    print("PARSING FFIEC CENSUS FLAT FILES - VERSION 2 (EXTENDED VARIABLES)")
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
        print("\n" + "=" * 70)
        print("SUMMARY")
        print("=" * 70)

        # Use 1996 as the base census year
        base_df = [df for df in all_dfs if df["year"].iloc[0] == 1996]
        if base_df:
            base_df = base_df[0]
            print(f"\n1996 Census (base year for Bhutta):")
            print(f"  Total tracts: {len(base_df):,}")
            print(f"  Mean OOU: {base_df['owner_occupied_units'].mean():.1f}")
            print(f"  Mean Total HU: {base_df['total_housing_units'].mean():.1f}")
            print(f"  Mean % age 65+: {base_df['pct_age_65_plus'].mean()*100:.1f}%")
            print(
                f"  Mean % single-family: {base_df['pct_single_family'].mean()*100:.1f}%"
            )
            print(f"  Mean % 2-4 family: {base_df['pct_2_4_family'].mean()*100:.1f}%")
            print(f"  Mean % 5+ units: {base_df['pct_5_plus'].mean()*100:.1f}%")

            # Check group quarters filter
            low_gq = (base_df["pct_group_quarters"] < 0.30).sum()
            print(
                f"\n  Tracts with <30% group quarters: {low_gq:,} ({low_gq/len(base_df)*100:.1f}%)"
            )

            # Check large MSAs
            msa_pop = base_df.groupby("msa_code")["population"].sum().reset_index()
            msa_pop = msa_pop[~msa_pop["msa_code"].isin(["9999", ""])]
            large_msas = msa_pop[msa_pop["population"] > 2_000_000]
            print(f"\n  Large MSAs (pop > 2M): {len(large_msas)}")

    print("\n" + "=" * 70)
    print("DONE - New census files saved to:", OUTPUT_DIR)
    print("=" * 70)


if __name__ == "__main__":
    main()
