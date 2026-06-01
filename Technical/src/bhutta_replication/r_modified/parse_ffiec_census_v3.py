"""
Parse FFIEC Census Flat Files - Version 3 (Bhutta Exact Match)

Enhanced version that extracts ALL variables needed for EXACT Bhutta (2011) replication:
- Separate % Black and % Hispanic (not combined minority_pct)
- % Mobile Homes (separate from "other")
- % Built 1980-89 (new addition)
- All existing variables from v2

Key improvements over v2:
1. Separate race variables matching Bhutta Table 1 exactly
2. % Built 1980-89 added (was missing)
3. % Mobile Homes separated properly
4. Removes poverty_pct from final output (not in Bhutta specification)

Field positions verified from: [2025.01.02] census_1996_guide.xlsx
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
OUTPUT_DIR = OUTPUT_ROOT / "Technical/data/census_parsed_v3"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# Extended field definitions for 1996 flat files (Bhutta's base year)
# Format: (name, start_pos, end_pos)  -- positions are 1-indexed in guide, 0-indexed here
FIELD_SPEC_V3 = {
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
    # Race/Ethnicity - SEPARATE per Bhutta Table 1
    # NotHispanicOriginByRace_Black: positions 100-107 (guide is 1-indexed)
    "pop_black_nonhisp": (99, 107),  # Black non-Hispanic population
    # Hispanic: positions 172-179
    "pop_hispanic": (171, 179),  # Hispanic population (all races)
    # Age breakdown - for "% age 65+" control
    "pop_65_plus": (219, 227),  # Population 65 and over
    "pop_all_ages": (227, 235),  # All Ages Count
    # Group quarters - for group quarters filter
    "gq_correctional": (259, 267),
    "gq_nursing": (267, 275),
    "gq_mental": (275, 283),
    "gq_juvenile": (283, 291),
    "gq_other_inst": (291, 299),
    "gq_college": (299, 307),
    "gq_military": (307, 315),
    "gq_homeless": (315, 323),
    "gq_visible_street": (323, 331),
    "gq_other": (331, 339),
    # Housing totals
    "total_housing_units": (1495, 1503),  # Total Housing Units (positions 1496-1503)
    "owner_occupied_units": (
        1543,
        1551,
    ),  # Tenure_Owner Occupancy (positions 1544-1551)
    "renter_occupied_units": (1551, 1559),  # Tenure_Renter (positions 1552-1559)
    # Property types - for single-family, 2-4 family, 5+ family, mobile homes
    "hu_1_detached": (1559, 1567),  # 1 Unit Detached (positions 1560-1567)
    "hu_1_attached": (1567, 1575),  # 1 Unit Attached (positions 1568-1575)
    "hu_2_units": (1575, 1583),  # 2 Units (positions 1576-1583)
    "hu_3_4_units": (1583, 1591),  # 3&4 Units (positions 1584-1591)
    "hu_5_plus": (1655, 1663),  # 5+ Units (positions 1656-1663)
    # Mobile Home/Trailer: positions 1640-1647 (SEPARATE from "other")
    "hu_mobile_home": (1639, 1647),  # Mobile Home/Trailer
    # Other: positions 1648-1655
    "hu_other": (1647, 1655),  # Other housing types
    # Housing value
    "median_home_value": (2263, 2271),  # Median Value (positions 2264-2271)
    # Housing by year built - for pre-1940, 1940-69, and 1980-89 controls
    # 1989-March 1990: positions 1832-1839
    "housing_1989_1990": (1831, 1839),
    # 1985-1988: positions 1840-1847
    "housing_1985_1988": (1839, 1847),
    # 1980-1984: positions 1848-1855
    "housing_1980_1984": (1847, 1855),
    # 1970-1979: positions 1856-1863
    "housing_1970_1979": (1855, 1863),
    # 1960-1969: positions 1864-1871
    "housing_1960_1969": (1863, 1871),
    # 1950-1959: positions 1872-1879
    "housing_1950_1959": (1871, 1879),
    # 1940-1949: positions 1880-1887
    "housing_1940_1949": (1879, 1887),
    # 1939 or earlier: positions 1888-1895
    "housing_pre1940": (1887, 1895),
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
                for field_name, (start, end) in FIELD_SPEC_V3.items():
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
    """Clean and convert parsed census data with all Bhutta variables."""
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

    # Income
    result["msa_mfi"] = pd.to_numeric(df["msa_mfi"], errors="coerce")

    # Population
    result["population"] = pd.to_numeric(df["population"], errors="coerce")
    result["pop_65_plus"] = pd.to_numeric(df["pop_65_plus"], errors="coerce")
    result["pop_all_ages"] = pd.to_numeric(df["pop_all_ages"], errors="coerce")

    # Race/Ethnicity - SEPARATE (Bhutta Table 1 requirement)
    result["pop_black"] = pd.to_numeric(df["pop_black_nonhisp"], errors="coerce")
    result["pop_hispanic"] = pd.to_numeric(df["pop_hispanic"], errors="coerce")

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
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
    result["group_quarters_pop"] = df[gq_cols].sum(axis=1)

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
    result["hu_mobile_home"] = pd.to_numeric(df["hu_mobile_home"], errors="coerce")
    result["hu_other"] = pd.to_numeric(df["hu_other"], errors="coerce")

    # Housing value
    result["median_home_value"] = pd.to_numeric(
        df["median_home_value"], errors="coerce"
    )

    # Housing by year built
    result["housing_1989_1990"] = pd.to_numeric(
        df["housing_1989_1990"], errors="coerce"
    )
    result["housing_1985_1988"] = pd.to_numeric(
        df["housing_1985_1988"], errors="coerce"
    )
    result["housing_1980_1984"] = pd.to_numeric(
        df["housing_1980_1984"], errors="coerce"
    )
    result["housing_1970_1979"] = pd.to_numeric(
        df["housing_1970_1979"], errors="coerce"
    )
    result["housing_1960_1969"] = pd.to_numeric(
        df["housing_1960_1969"], errors="coerce"
    )
    result["housing_1950_1959"] = pd.to_numeric(
        df["housing_1950_1959"], errors="coerce"
    )
    result["housing_1940_1949"] = pd.to_numeric(
        df["housing_1940_1949"], errors="coerce"
    )
    result["housing_pre1940"] = pd.to_numeric(df["housing_pre1940"], errors="coerce")

    # Derived variables for regression (Bhutta Table 1 exact match)
    total_hu = result["total_housing_units"].clip(lower=1)
    pop = result["population"].clip(lower=1)

    # % Black and % Hispanic (SEPARATE - Bhutta requirement)
    result["pct_black"] = result["pop_black"].fillna(0) / pop
    result["pct_hispanic"] = result["pop_hispanic"].fillna(0) / pop

    # % age 65+ (Bhutta control)
    result["pct_age_65_plus"] = result["pop_65_plus"].fillna(0) / pop

    # % group quarters (for filter: < 30%)
    result["pct_group_quarters"] = result["group_quarters_pop"] / pop

    # Property type percentages (Bhutta controls)
    # % Detached (single-family detached)
    result["pct_detached"] = result["hu_1_detached"].fillna(0) / total_hu
    # % Single-family (detached + attached) - for compatibility
    result["pct_single_family"] = (
        result["hu_1_detached"].fillna(0) + result["hu_1_attached"].fillna(0)
    ) / total_hu
    # % Multifamily buildings (2+ units)
    result["pct_multifamily"] = (
        result["hu_2_units"].fillna(0)
        + result["hu_3_4_units"].fillna(0)
        + result["hu_5_plus"].fillna(0)
    ) / total_hu
    # % 2-4 family (for compatibility)
    result["pct_2_4_family"] = (
        result["hu_2_units"].fillna(0) + result["hu_3_4_units"].fillna(0)
    ) / total_hu
    # % 5+ units (for compatibility)
    result["pct_5_plus"] = result["hu_5_plus"].fillna(0) / total_hu
    # % Mobile homes (SEPARATE - Bhutta Table 1)
    result["pct_mobile_homes"] = result["hu_mobile_home"].fillna(0) / total_hu

    # Housing age percentages (Bhutta controls)
    # % Built 1980-89 (NEW - was missing in v2)
    result["housing_1980_1989"] = (
        result["housing_1989_1990"].fillna(0)
        + result["housing_1985_1988"].fillna(0)
        + result["housing_1980_1984"].fillna(0)
    )
    result["pct_built_1980_89"] = result["housing_1980_1989"] / total_hu

    # % Built 1940-69
    result["housing_1940_1969"] = (
        result["housing_1940_1949"].fillna(0)
        + result["housing_1950_1959"].fillna(0)
        + result["housing_1960_1969"].fillna(0)
    )
    result["pct_1940_69"] = result["housing_1940_1969"] / total_hu

    # % Built pre-1940
    result["pct_pre1940"] = result["housing_pre1940"].fillna(0) / total_hu

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
    raw_df = parse_flat_file(filepath)
    print(f"  Raw records: {len(raw_df):,}")

    print(f"  Cleaning and computing derived variables...")
    clean_df = clean_census_data(raw_df)

    # Validation
    oou_valid = (clean_df["owner_occupied_units"] > 0).sum()
    print(f"  Tracts with OOU > 0: {oou_valid:,} ({oou_valid/len(clean_df)*100:.1f}%)")
    print(f"  Mean OOU: {clean_df['owner_occupied_units'].mean():.1f}")
    print(f"  Mean Total HU: {clean_df['total_housing_units'].mean():.1f}")
    print(f"  Mean % Black: {clean_df['pct_black'].mean()*100:.1f}%")
    print(f"  Mean % Hispanic: {clean_df['pct_hispanic'].mean()*100:.1f}%")
    print(f"  Mean % age 65+: {clean_df['pct_age_65_plus'].mean()*100:.1f}%")
    print(f"  Mean % mobile homes: {clean_df['pct_mobile_homes'].mean()*100:.1f}%")
    print(f"  Mean % built 1980-89: {clean_df['pct_built_1980_89'].mean()*100:.1f}%")

    return clean_df


def main():
    print("=" * 70)
    print("PARSING FFIEC CENSUS FLAT FILES - VERSION 3 (BHUTTA EXACT MATCH)")
    print("=" * 70)
    print()
    print("New variables added:")
    print("  - pct_black (separate from minority_pct)")
    print("  - pct_hispanic (separate from minority_pct)")
    print("  - pct_mobile_homes (separate from 'other')")
    print("  - pct_built_1980_89 (was missing)")
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

        # Use 1996 as the base census year (Bhutta's reference)
        base_df = [df for df in all_dfs if df["year"].iloc[0] == 1996]
        if base_df:
            base_df = base_df[0]
            print(f"\n1996 Census (base year for Bhutta):")
            print(f"  Total tracts: {len(base_df):,}")
            print(f"  Mean OOU: {base_df['owner_occupied_units'].mean():.1f}")
            print(f"  Mean Total HU: {base_df['total_housing_units'].mean():.1f}")
            print(f"\nBhutta Table 1 Control Variables:")
            print(f"  Mean % Black: {base_df['pct_black'].mean()*100:.1f}%")
            print(f"  Mean % Hispanic: {base_df['pct_hispanic'].mean()*100:.1f}%")
            print(f"  Mean % age 65+: {base_df['pct_age_65_plus'].mean()*100:.1f}%")
            print(f"  Mean % detached: {base_df['pct_detached'].mean()*100:.1f}%")
            print(f"  Mean % multifamily: {base_df['pct_multifamily'].mean()*100:.1f}%")
            print(
                f"  Mean % mobile homes: {base_df['pct_mobile_homes'].mean()*100:.1f}%"
            )
            print(
                f"  Mean % built 1980-89: {base_df['pct_built_1980_89'].mean()*100:.1f}%"
            )
            print(f"  Mean % built 1940-69: {base_df['pct_1940_69'].mean()*100:.1f}%")
            print(f"  Mean % built pre-1940: {base_df['pct_pre1940'].mean()*100:.1f}%")

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
