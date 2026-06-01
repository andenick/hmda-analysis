"""
Census Fixed-Width File Parser for Bhutta (2011) Replication

Parses FFIEC Census flat files with proper schema inheritance:
- 1990-1991: Use 1990 guide (107 fields)
- 1992-1995: Use 1992 guide (114 fields)
- 1996: Use 1996 guide (314 fields)
- 1997-2002: Use 1997 guide (315 fields)
- 2003: Use 2003 guide (1259 fields)
- 2004: Use 2004 guide (1206 fields)
- 2005-2007: Use 2006 guide (1213 fields)

Key Variables for Bhutta Replication (RD at TM=0.80):
- TM = Tract MFI / MSA MFI
- Housing units, owner-occupied units
- Median home value
- Race/ethnicity percentages
- Poverty level
- Housing age distribution
- Group quarters population
"""

import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import numpy as np
import pandas as pd


@dataclass
class SchemaField:
    """A field definition from the census schema."""

    name: str
    start: int  # 1-indexed
    end: int  # 1-indexed, inclusive

    @property
    def width(self) -> int:
        return self.end - self.start + 1


# Schema inheritance mapping: year -> guide file
SCHEMA_INHERITANCE = {
    1990: "census_1990_guide.xlsx",
    1991: "census_1990_guide.xlsx",
    1992: "census_1992_guide.xlsx",
    1993: "census_1992_guide.xlsx",
    1994: "census_1992_guide.xlsx",
    1995: "census_1992_guide.xlsx",
    1996: "census_1996_guide.xlsx",
    1997: "census_1997_guide.xlsx",
    1998: "census_1997_guide.xlsx",
    1999: "census_1997_guide.xlsx",
    2000: "census_1997_guide.xlsx",
    2001: "census_1997_guide.xlsx",
    2002: "census_1997_guide.xlsx",
    2003: "census_2003_guide.xlsx",
    2004: "census_2004_guide.xlsx",
    2005: "census_2006_guide.xlsx",
    2006: "census_2006_guide.xlsx",
    2007: "census_2006_guide.xlsx",
}


def find_guide_file(guide_dir: Path, base_name: str) -> Path:
    """Find the guide file with optional date prefix."""
    for f in guide_dir.iterdir():
        if f.suffix == ".xlsx" and base_name in f.name:
            return f
    raise FileNotFoundError(f"Guide file {base_name} not found in {guide_dir}")


def load_schema(guide_path: Path) -> List[SchemaField]:
    """Load schema from Excel guide file."""
    df = pd.read_excel(guide_path)

    # Handle both column name variants
    name_col = "ElementLabel" if "ElementLabel" in df.columns else "Element Label"

    fields = []
    for _, row in df.iterrows():
        try:
            name = str(row[name_col]).strip()
            start = int(row["Starting"])
            end = int(row["Ending"])
            if name and not pd.isna(name):
                fields.append(SchemaField(name, start, end))
        except (ValueError, KeyError):
            continue

    return fields


def get_schema_for_year(year: int, guide_dir: Path) -> List[SchemaField]:
    """Get the appropriate schema for a given year."""
    if year not in SCHEMA_INHERITANCE:
        raise ValueError(f"No schema mapping for year {year}")

    guide_name = SCHEMA_INHERITANCE[year]
    guide_path = find_guide_file(guide_dir, guide_name)
    return load_schema(guide_path)


def find_field_by_pattern(
    fields: List[SchemaField], patterns: List[str]
) -> Optional[SchemaField]:
    """Find a field matching any of the given patterns (case-insensitive)."""
    for field in fields:
        name_lower = field.name.lower()
        for pattern in patterns:
            if pattern.lower() in name_lower:
                return field
    return None


def get_key_field_mapping(
    fields: List[SchemaField], year: int
) -> Dict[str, Optional[SchemaField]]:
    """
    Map key variable names to schema fields for Bhutta replication.

    Returns standardized variable names mapped to their schema fields.
    """
    mapping = {}

    # Identifiers (always present)
    mapping["year"] = find_field_by_pattern(fields, ["as of date", 'as of" date'])
    mapping["msa_code"] = find_field_by_pattern(
        fields, ["msa", "metropolitan statistical area", "metropolitan area (ma) code"]
    )
    mapping["state_code"] = find_field_by_pattern(fields, ["fips state"])
    mapping["county_code"] = find_field_by_pattern(fields, ["fips county"])
    mapping["tract"] = find_field_by_pattern(fields, ["census tract", "tract-bna"])
    mapping["central_city_flag"] = find_field_by_pattern(
        fields, ["central city flag", "principal city flag"]
    )

    # Income variables - critical for TM calculation
    if year >= 2004:
        # Post-2004 uses MSA/MD terminology
        mapping["msa_mfi"] = find_field_by_pattern(
            fields, ["msa/md median family income"]
        )
        mapping["tract_mfi_pct"] = find_field_by_pattern(
            fields, ["msa/md median family income percentage"]
        )
        mapping["tract_mfi"] = find_field_by_pattern(
            fields, ["median family income in 1999"]
        )
    elif year == 2003:
        # 2003 uses MA (Metropolitan Area) terminology
        mapping["msa_mfi"] = find_field_by_pattern(fields, ["ma median family income"])
        mapping["tract_mfi_pct"] = find_field_by_pattern(
            fields, ["ma median family income percentage"]
        )
        mapping["tract_mfi"] = find_field_by_pattern(
            fields, ["median family income in 1999"]
        )
    else:
        # Pre-2003 uses simpler MSA terminology
        mapping["msa_mfi"] = find_field_by_pattern(
            fields, ["msa median family income", "decennial msa median"]
        )
        mapping["tract_mfi_pct"] = find_field_by_pattern(
            fields,
            [
                "decennial msa median family income percentage",
                "median family income percentage",
            ],
        )
        mapping["tract_mfi"] = find_field_by_pattern(fields, ["median family income"])

    # Housing variables
    mapping["total_housing_units"] = find_field_by_pattern(
        fields, ["total housing units"]
    )
    mapping["owner_occupied_units"] = find_field_by_pattern(
        fields, ["owner occupied", "owner-occupied"]
    )
    mapping["median_home_value"] = find_field_by_pattern(
        fields, ["median value", "median home value"]
    )

    # Population
    mapping["population"] = find_field_by_pattern(
        fields, ["persons/population", "total population"]
    )
    mapping["minority_pct"] = find_field_by_pattern(fields, ["minority percentage"])
    mapping["minority_pop"] = find_field_by_pattern(fields, ["minority population"])

    # Race breakdown
    mapping["black_pop"] = find_field_by_pattern(
        fields, ["black or african american alone", "black population"]
    )
    mapping["hispanic_pop"] = find_field_by_pattern(
        fields, ["hispanic population", "total hispanic"]
    )
    mapping["white_pop"] = find_field_by_pattern(
        fields, ["white alone", "white population"]
    )

    # Poverty
    mapping["poverty_pop"] = find_field_by_pattern(
        fields, ["income below poverty level total", "below poverty"]
    )
    mapping["poverty_universe"] = find_field_by_pattern(
        fields, ["population for whom poverty status"]
    )

    # Age
    mapping["pop_65_over"] = find_field_by_pattern(
        fields, ["65 years and over", "65 and over", "over 65"]
    )

    # Group quarters
    mapping["group_quarters_pop"] = find_field_by_pattern(
        fields, ["population in group quarters"]
    )

    # Housing age
    mapping["housing_pre1940"] = find_field_by_pattern(
        fields, ["built 1939 or earlier", "pre-1940", "built_1939"]
    )
    mapping["housing_1940_1969"] = find_field_by_pattern(
        fields, ["built 1940", "built_1940"]
    )  # Need to sum 1940-1969

    return mapping


def parse_census_file(
    dat_path: Path,
    fields: List[SchemaField],
    key_mapping: Dict[str, Optional[SchemaField]],
    n_rows: Optional[int] = None,
) -> pd.DataFrame:
    """
    Parse a census fixed-width file and extract key variables.

    Args:
        dat_path: Path to the .dat file
        fields: Full schema field list
        key_mapping: Mapping of standardized names to schema fields
        n_rows: Optional row limit for testing

    Returns:
        DataFrame with standardized column names
    """
    # Build colspecs for pandas read_fwf (0-indexed, end exclusive)
    colspecs = []
    names = []

    for std_name, field in key_mapping.items():
        if field is not None:
            colspecs.append((field.start - 1, field.end))  # Convert to 0-indexed
            names.append(std_name)

    # Parse file
    df = pd.read_fwf(dat_path, colspecs=colspecs, names=names, dtype=str, nrows=n_rows)

    return df


def parse_year(
    year: int,
    src_dir: Path,
    guide_dir: Path,
    output_dir: Path,
    n_rows: Optional[int] = None,
    output_format: str = "parquet",
) -> Path:
    """
    Parse census data for a single year.

    Args:
        year: Census year to parse
        src_dir: Directory containing year subdirectories with .dat files
        guide_dir: Directory containing Excel schema guides
        output_dir: Directory to write output files
        n_rows: Optional row limit for testing
        output_format: "parquet" or "csv"

    Returns:
        Path to output file
    """
    # Find data file
    dat_candidates = [
        src_dir / str(year) / f"census_{year}.dat",
        src_dir / str(year) / f"census{year}.dat",
        src_dir / str(year) / f"Census_{year}.dat",
    ]
    dat_path = next((p for p in dat_candidates if p.exists()), None)
    if dat_path is None:
        raise FileNotFoundError(f"No census data file found for {year} in {src_dir}")

    # Load schema
    fields = get_schema_for_year(year, guide_dir)
    key_mapping = get_key_field_mapping(fields, year)

    # Parse file
    df = parse_census_file(dat_path, fields, key_mapping, n_rows)

    # Post-processing
    df = post_process_census_data(df, year)

    # Save output
    output_dir.mkdir(parents=True, exist_ok=True)
    if output_format == "parquet":
        out_path = output_dir / f"census_{year}.parquet"
        df.to_parquet(out_path, index=False)
    else:
        out_path = output_dir / f"census_{year}.csv"
        df.to_csv(out_path, index=False)

    return out_path


def post_process_census_data(df: pd.DataFrame, year: int) -> pd.DataFrame:
    """
    Post-process parsed census data:
    - Convert numeric columns
    - Calculate TM (tract MFI / MSA MFI)
    - Calculate derived variables
    """
    df = df.copy()

    # Convert numeric columns
    numeric_cols = [
        "msa_mfi",
        "tract_mfi",
        "tract_mfi_pct",
        "total_housing_units",
        "owner_occupied_units",
        "median_home_value",
        "population",
        "minority_pop",
        "minority_pct",
        "black_pop",
        "hispanic_pop",
        "white_pop",
        "poverty_pop",
        "poverty_universe",
        "pop_65_over",
        "group_quarters_pop",
        "housing_pre1940",
        "housing_1940_1969",
    ]

    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # Calculate TM (tract relative income)
    if "tract_mfi_pct" in df.columns:
        # Direct percentage available
        df["TM"] = df["tract_mfi_pct"] / 100.0
    elif "tract_mfi" in df.columns and "msa_mfi" in df.columns:
        # Calculate from MFI values
        df["TM"] = df["tract_mfi"] / df["msa_mfi"]

    # Calculate poverty rate
    if "poverty_pop" in df.columns and "poverty_universe" in df.columns:
        df["poverty_rate"] = df["poverty_pop"] / df["poverty_universe"]

    # Calculate race percentages
    if "black_pop" in df.columns and "population" in df.columns:
        df["black_pct"] = df["black_pop"] / df["population"] * 100
    if "hispanic_pop" in df.columns and "population" in df.columns:
        df["hispanic_pct"] = df["hispanic_pop"] / df["population"] * 100

    # Log transforms for regression
    for col in ["total_housing_units", "owner_occupied_units", "median_home_value"]:
        if col in df.columns:
            df[f"ln_{col}"] = df[col].apply(
                lambda x: np.log(x) if pd.notna(x) and x > 0 else np.nan
            )

    # Add year column if not present
    if "year" not in df.columns:
        df["year_data"] = year

    return df


def parse_year_range(
    years: List[int],
    src_dir: Path,
    guide_dir: Path,
    output_dir: Path,
    n_rows: Optional[int] = None,
    output_format: str = "parquet",
) -> List[Path]:
    """Parse multiple years of census data."""
    outputs = []
    for year in years:
        try:
            out_path = parse_year(
                year, src_dir, guide_dir, output_dir, n_rows, output_format
            )
            outputs.append(out_path)
            print(f"✓ Parsed {year}: {out_path}")
        except Exception as e:
            print(f"✗ Failed {year}: {e}")
    return outputs


def validate_parsed_data(df: pd.DataFrame, year: int) -> Dict[str, any]:
    """
    Validate parsed census data with sanity checks.

    Returns dict with validation results.
    """
    results = {
        "year": year,
        "n_rows": len(df),
        "n_tracts": df["tract"].nunique() if "tract" in df.columns else None,
        "n_msas": df["msa_code"].nunique() if "msa_code" in df.columns else None,
    }

    # TM distribution checks
    if "TM" in df.columns:
        tm = df["TM"].dropna()
        results["TM_mean"] = tm.mean()
        results["TM_median"] = tm.median()
        results["TM_std"] = tm.std()
        results["TM_min"] = tm.min()
        results["TM_max"] = tm.max()
        results["TM_near_cutoff"] = (
            (tm >= 0.75) & (tm <= 0.85)
        ).sum()  # Near 0.80 cutoff

    # Housing checks
    if "total_housing_units" in df.columns:
        hu = df["total_housing_units"].dropna()
        results["housing_mean"] = hu.mean()
        results["housing_min100"] = (hu >= 100).sum()  # Bhutta filter

    # Missing data
    for col in ["TM", "msa_code", "tract", "total_housing_units"]:
        if col in df.columns:
            results[f"{col}_missing_pct"] = df[col].isna().mean() * 100

    return results


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Parse FFIEC Census flat files")
    parser.add_argument(
        "--years",
        type=int,
        nargs="+",
        default=[1996, 1997, 1998, 1999, 2000, 2001, 2002, 2003, 2004, 2005, 2006],
        help="Years to parse",
    )
    parser.add_argument(
        "--src-dir", type=str, required=True, help="Source directory with year subdirs"
    )
    parser.add_argument(
        "--guide-dir", type=str, required=True, help="Directory with Excel guides"
    )
    parser.add_argument(
        "--output-dir", type=str, required=True, help="Output directory"
    )
    parser.add_argument("--format", choices=["parquet", "csv"], default="parquet")
    parser.add_argument(
        "--limit", type=int, default=None, help="Limit rows per file (for testing)"
    )

    args = parser.parse_args()

    outputs = parse_year_range(
        years=args.years,
        src_dir=Path(args.src_dir),
        guide_dir=Path(args.guide_dir),
        output_dir=Path(args.output_dir),
        n_rows=args.limit,
        output_format=args.format,
    )

    print(f"\nParsed {len(outputs)} files")
