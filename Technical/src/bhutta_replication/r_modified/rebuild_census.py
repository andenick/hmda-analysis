"""
Rebuild census_bhutta data with correct field parsing.

The original census_bhutta files had incorrect owner_occupied_units
values due to parsing issues with zero-padded string fields.
"""

import pandas as pd
import numpy as np
from pathlib import Path
import os
OUTPUT_ROOT = os.environ.get("OUTPUT_ROOT", "outputs")

CENSUS_RAW_DIR = OUTPUT_ROOT / "Technical/data/census"
OUTPUT_DIR = OUTPUT_ROOT / "Technical/data/census_bhutta_v2"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def safe_numeric(series):
    """Convert string to numeric, handling zero-padding."""
    return pd.to_numeric(series.astype(str).str.strip(), errors='coerce').fillna(0)


def process_census_year(year: int) -> pd.DataFrame:
    """Process raw census data for a given year."""
    path = CENSUS_RAW_DIR / f"census_data_{year}.parquet"
    if not path.exists():
        print(f"  No data for {year}")
        return None

    df = pd.read_parquet(path)

    # Build clean dataset
    result = pd.DataFrame({
        'msa_code': df['Metropolitan Statistical Area (MSA) Code'].astype(str).str.strip(),
        'state_code': df['FIPS State Code'].astype(str).str.strip(),
        'tract': df['Census tract-BNA'].astype(str).str.strip(),
        'central_city_flag': df['Central City Flag'].astype(str).str.strip(),
        'TM': safe_numeric(df['Decennial MSA Median Family Income Percentage']) / 100,  # Convert to ratio
        'total_housing_units': safe_numeric(df['Total Housing Units']),
        'owner_occupied_units': safe_numeric(df['Owner Occupancy']),
        'median_home_value': safe_numeric(df['Median Value']),
        'population': safe_numeric(df['Persons/Population']),
        'minority_pct': safe_numeric(df['Minority Percentage']) / 100,  # Convert to ratio
    })

    # Housing age - sum 1940-1969 columns
    housing_1940_49 = safe_numeric(df['1940 – 1949'])
    housing_1950_59 = safe_numeric(df['1950 – 1959'])
    housing_1960_69 = safe_numeric(df['1960 – 1969'])
    result['housing_1940_1969'] = housing_1940_49 + housing_1950_59 + housing_1960_69
    result['housing_pre1940'] = safe_numeric(df['1939 or earlier'])

    result['year'] = year

    return result


def main():
    print("Rebuilding census_bhutta data with correct field parsing...")

    # Process years 1996-2006 (covering Bhutta's period + extras)
    for year in range(1996, 2007):
        print(f"Processing {year}...")
        df = process_census_year(year)
        if df is not None:
            # Check OOU values
            oou_nonzero = (df['owner_occupied_units'] > 0).sum()
            print(f"  Tracts: {len(df):,}, with OOU > 0: {oou_nonzero:,}")

            # Save
            df.to_parquet(OUTPUT_DIR / f"census_{year}.parquet", index=False)
            print(f"  Saved to census_{year}.parquet")

    print("\nDone! New census files in:", OUTPUT_DIR)


if __name__ == "__main__":
    main()
