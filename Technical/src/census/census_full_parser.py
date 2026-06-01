"""
FFIEC Census Flat File Parser - Complete CSV Output Generator
==============================================================

Parses ALL FFIEC Census flat files (1990-2024) and outputs clean CSVs.

Data Format by Era:
- 1990-2011: Fixed-Width Format (.dat files)
- 2012-2024: CSV Format (already CSV, needs standardization)

Schema Inheritance for Fixed-Width Files:
- 1990-1991: Use 1990 guide (107 fields)
- 1992-1995: Use 1992 guide (114 fields)
- 1996: Use 1996 guide (314 fields)
- 1997-2002: Use 1997 guide (315 fields)
- 2003: Use 2003 guide (1259 fields)
- 2004: Use 2004 guide (1206 fields)
- 2005-2011: Use 2006 guide (1213 fields)

For 2008-2011, we use the 2006 schema (same format).

Created: 2025-12-07
"""

import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import pandas as pd
import numpy as np
import warnings
DATA_ROOT = Path(os.environ.get("DATA_ROOT", "data"))
OUTPUT_ROOT = Path(os.environ.get("OUTPUT_ROOT", "outputs"))

warnings.filterwarnings("ignore")


# ==============================================================================
# CONFIGURATION
# ==============================================================================

# Base paths
SRC_DIR = DATA_ROOT / "Inputs/Old/CRA_code/_files2/flatFiles/src"
GUIDE_DIR = Path(
    str(DATA_ROOT / "Inputs/Old/CRA_code/_files2/flatFiles/_flatFileGuide2")
)
SCHEMA_DIR = DATA_ROOT / "Inputs/Old/Python Stuff/schemas"
OUTPUT_DIR = OUTPUT_ROOT / "Outputs/census_csv"

# Schema inheritance mapping
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
    2008: "census_2006_guide.xlsx",  # Same schema as 2006
    2009: "census_2006_guide.xlsx",
    2010: "census_2006_guide.xlsx",
    2011: "census_2006_guide.xlsx",
}

# Years that are CSV format (not fixed-width)
CSV_YEARS = list(range(2012, 2025))

# All fixed-width years
FWF_YEARS = list(range(1990, 2012))


# ==============================================================================
# SCHEMA PARSING
# ==============================================================================


@dataclass
class SchemaField:
    """A field definition from the census schema."""

    field_num: int
    name: str
    start: int  # 1-indexed
    end: int  # 1-indexed, inclusive
    length: int
    field_type: str

    @property
    def colspec(self) -> Tuple[int, int]:
        """Return (start, end) for pandas read_fwf (0-indexed, end exclusive)."""
        return (self.start - 1, self.end)


def load_schema_from_csv(schema_path: Path) -> List[SchemaField]:
    """Load schema from pre-parsed CSV specification file."""
    df = pd.read_csv(schema_path)
    fields = []
    for _, row in df.iterrows():
        try:
            fields.append(
                SchemaField(
                    field_num=int(row["Field Number"]),
                    name=str(row["Element Label"]).strip(),
                    start=int(row["Starting"]),
                    end=int(row["Ending"]),
                    length=int(row["Length"]),
                    field_type=str(row["Type"]),
                )
            )
        except (ValueError, KeyError) as e:
            continue
    return fields


def load_schema_from_excel(guide_path: Path) -> List[SchemaField]:
    """Load schema from Excel guide file."""
    df = pd.read_excel(guide_path)

    # Handle column name variants
    name_col = None
    for col in ["ElementLabel", "Element Label", "element_label"]:
        if col in df.columns:
            name_col = col
            break
    if name_col is None:
        name_col = df.columns[1]  # Usually second column

    num_col = None
    for col in ["FieldNumber", "Field Number", "field_number"]:
        if col in df.columns:
            num_col = col
            break

    type_col = None
    for col in ["Type", "DataType", "type"]:
        if col in df.columns:
            type_col = col
            break

    fields = []
    for idx, row in df.iterrows():
        try:
            name = str(row[name_col]).strip()
            start = int(row["Starting"])
            end = int(row["Ending"])
            length = int(row["Length"]) if "Length" in df.columns else (end - start + 1)
            field_type = str(row.get(type_col, "N")) if type_col else "N"
            field_num = int(row[num_col]) if num_col else idx + 1

            if name and not pd.isna(name) and name != "nan":
                fields.append(
                    SchemaField(
                        field_num=field_num,
                        name=name,
                        start=start,
                        end=end,
                        length=length,
                        field_type=field_type,
                    )
                )
        except (ValueError, KeyError, TypeError):
            continue

    return fields


def find_guide_file(guide_dir: Path, base_name: str) -> Optional[Path]:
    """Find the guide file with optional date prefix."""
    for f in guide_dir.iterdir():
        if f.suffix == ".xlsx" and base_name in f.name:
            return f
    return None


def get_schema_for_year(year: int) -> List[SchemaField]:
    """Get the appropriate schema for a given year."""
    if year not in SCHEMA_INHERITANCE:
        raise ValueError(f"No schema mapping for year {year}")

    guide_name = SCHEMA_INHERITANCE[year]

    # Try to load from Excel guide
    guide_path = find_guide_file(GUIDE_DIR, guide_name)
    if guide_path:
        return load_schema_from_excel(guide_path)

    # Fall back to CSV schema files
    if year <= 2002:
        csv_schema = SCHEMA_DIR / "[2025.09.06] ffiec_census_fwf_spec_2002.csv"
    else:
        csv_schema = SCHEMA_DIR / "[2025.09.06] ffiec_census_fwf_spec_2006.csv"

    if csv_schema.exists():
        return load_schema_from_csv(csv_schema)

    raise FileNotFoundError(f"No schema found for year {year}")


# ==============================================================================
# FILE DISCOVERY
# ==============================================================================


def find_dat_file(year: int) -> Optional[Path]:
    """Find the .dat file for a given year."""
    year_dir = SRC_DIR / str(year)
    if not year_dir.exists():
        return None

    # Try various naming conventions
    patterns = [
        f"census_{year}.dat",
        f"census{year}.dat",
        f"Census_{year}.dat",
        f"Census{year}.DAT",
        f"census{year}.DAT",
    ]

    for pattern in patterns:
        path = year_dir / pattern
        if path.exists():
            return path

    # Glob for any .dat file
    dat_files = list(year_dir.glob("*.dat")) + list(year_dir.glob("*.DAT"))
    if dat_files:
        return dat_files[0]

    return None


def find_csv_file(year: int) -> Optional[Path]:
    """Find the CSV file for a given year (2012+)."""
    year_dir = SRC_DIR / str(year)
    if not year_dir.exists():
        return None

    # Look for CSV files
    csv_files = list(year_dir.glob("*.csv")) + list(year_dir.glob("*.CSV"))
    if csv_files:
        return csv_files[0]

    return None


# ==============================================================================
# PARSING FUNCTIONS
# ==============================================================================


def clean_column_name(name: str) -> str:
    """Convert field name to clean column name."""
    # Remove special characters and convert to snake_case
    name = name.lower()
    name = name.replace("/", "_")
    name = name.replace("-", "_")
    name = name.replace(" ", "_")
    name = name.replace(",", "")
    name = name.replace("(", "")
    name = name.replace(")", "")
    name = name.replace('"', "")
    name = name.replace("'", "")
    name = name.replace(".", "")
    # Remove consecutive underscores
    while "__" in name:
        name = name.replace("__", "_")
    # Remove leading/trailing underscores
    name = name.strip("_")
    return name


def parse_fwf_year(year: int, n_rows: Optional[int] = None) -> pd.DataFrame:
    """Parse a fixed-width format census file."""
    dat_path = find_dat_file(year)
    if dat_path is None:
        raise FileNotFoundError(f"No .dat file found for year {year}")

    print(f"  Reading: {dat_path.name}")

    # Get schema
    schema = get_schema_for_year(year)
    print(f"  Schema: {len(schema)} fields")

    # Build colspecs and names
    colspecs = [field.colspec for field in schema]
    names = [clean_column_name(field.name) for field in schema]

    # Handle duplicate column names by adding suffix
    seen = {}
    unique_names = []
    for name in names:
        if name in seen:
            seen[name] += 1
            unique_names.append(f"{name}_{seen[name]}")
        else:
            seen[name] = 0
            unique_names.append(name)

    # Parse file
    df = pd.read_fwf(
        dat_path, colspecs=colspecs, names=unique_names, dtype=str, nrows=n_rows
    )

    # Add year column
    df["census_year"] = year

    return df


def parse_csv_year(year: int, n_rows: Optional[int] = None) -> pd.DataFrame:
    """Parse a CSV format census file (2012+)."""
    csv_path = find_csv_file(year)
    if csv_path is None:
        raise FileNotFoundError(f"No CSV file found for year {year}")

    print(f"  Reading: {csv_path.name}")

    # Read CSV
    df = pd.read_csv(csv_path, dtype=str, nrows=n_rows, low_memory=False)

    # Clean column names
    df.columns = [clean_column_name(str(col)) for col in df.columns]

    # Add year column if not present
    if "census_year" not in df.columns:
        df["census_year"] = year

    print(f"  Columns: {len(df.columns)}")

    return df


def parse_year(year: int, n_rows: Optional[int] = None) -> pd.DataFrame:
    """Parse census data for a single year (auto-detects format)."""
    if year in CSV_YEARS:
        return parse_csv_year(year, n_rows)
    else:
        return parse_fwf_year(year, n_rows)


# ==============================================================================
# OUTPUT FUNCTIONS
# ==============================================================================


def save_to_csv(df: pd.DataFrame, year: int, output_dir: Path) -> Path:
    """Save DataFrame to CSV with standardized naming."""
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"census_{year}.csv"
    df.to_csv(output_path, index=False)
    return output_path


def get_file_stats(df: pd.DataFrame) -> Dict:
    """Get basic statistics about parsed data."""
    return {
        "n_rows": len(df),
        "n_columns": len(df.columns),
    }


# ==============================================================================
# MAIN PROCESSING
# ==============================================================================


def process_year(year: int, output_dir: Path, n_rows: Optional[int] = None) -> Dict:
    """Process a single year and return status."""
    result = {
        "year": year,
        "status": "pending",
        "output_path": None,
        "stats": None,
        "error": None,
    }

    try:
        # Parse
        df = parse_year(year, n_rows)

        # Save
        output_path = save_to_csv(df, year, output_dir)

        # Stats
        stats = get_file_stats(df)

        result["status"] = "success"
        result["output_path"] = str(output_path)
        result["stats"] = stats

    except Exception as e:
        result["status"] = "error"
        result["error"] = str(e)

    return result


def process_all_years(
    years: Optional[List[int]] = None,
    output_dir: Optional[Path] = None,
    n_rows: Optional[int] = None,
) -> List[Dict]:
    """Process multiple years of census data."""

    if years is None:
        years = FWF_YEARS + CSV_YEARS

    if output_dir is None:
        output_dir = OUTPUT_DIR

    output_dir.mkdir(parents=True, exist_ok=True)

    results = []

    for year in sorted(years):
        print(f"\n[{year}] Processing...")
        result = process_year(year, output_dir, n_rows)
        results.append(result)
        if result["status"] == "success":
            print(
                f"  ✓ {result['stats']['n_rows']:,} rows, {result['stats']['n_columns']} cols"
            )
            print(f"  → {result['output_path']}")
        else:
            print(f"  ✗ {result['error']}")

    return results


def print_summary(results: List[Dict]):
    """Print summary of processing results."""
    success = [r for r in results if r["status"] == "success"]
    errors = [r for r in results if r["status"] == "error"]

    print("\n" + "=" * 70)
    print("PROCESSING SUMMARY")
    print("=" * 70)
    print(f"Total years processed: {len(results)}")
    print(f"Successful: {len(success)}")
    print(f"Failed: {len(errors)}")

    if errors:
        print("\nFailed years:")
        for r in errors:
            print(f"  {r['year']}: {r['error']}")

    if success:
        total_rows = sum(r["stats"]["n_rows"] for r in success)
        print(f"\nTotal rows across all files: {total_rows:,}")
        print(f"Output directory: {OUTPUT_DIR}")


# ==============================================================================
# MAIN
# ==============================================================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Parse FFIEC Census flat files to CSV")
    parser.add_argument(
        "--years",
        type=int,
        nargs="+",
        default=None,
        help="Specific years to parse (default: all 1990-2024)",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=str(OUTPUT_DIR),
        help="Output directory for CSV files",
    )
    parser.add_argument(
        "--limit", type=int, default=None, help="Limit rows per file (for testing)"
    )

    args = parser.parse_args()

    print("=" * 70)
    print("FFIEC Census Flat File Parser")
    print("=" * 70)
    print(f"Source: {SRC_DIR}")
    print(f"Output: {args.output_dir}")

    results = process_all_years(
        years=args.years,
        output_dir=Path(args.output_dir),
        n_rows=args.limit,
    )

    print_summary(results)
