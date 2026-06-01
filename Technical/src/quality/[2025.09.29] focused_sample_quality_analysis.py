#!/usr/bin/env python3
"""
Focused Sample Data Quality Analysis

Quick analysis of the 100K sample data to identify specific quality issues
without processing the large full dataset.
"""

import pandas as pd
import numpy as np
from pathlib import Path
import json
from datetime import datetime
import os
OUTPUT_ROOT = os.environ.get("OUTPUT_ROOT", "outputs")

def analyze_sample_quality():
    """Analyze quality issues in the 100K sample data."""

    print("FOCUSED SAMPLE DATA QUALITY ANALYSIS")
    print("CRITICAL: NO data modifications - analysis only")

    # Load sample data
    sample_file = OUTPUT_ROOT / "analysis_outputs/lar_sample_100k.csv"

    if not sample_file.exists():
        print("ERROR: Sample file not found")
        return

    # Load preserving all original values
    df = pd.read_csv(sample_file, dtype=str, na_filter=False)

    print(f"\nAnalyzing {len(df):,} records with {len(df.columns)} columns")

    # Geographic field analysis
    print("\n=== GEOGRAPHIC FIELD QUALITY ===")
    geo_fields = ['state_code', 'county_code', 'census_tract', 'derived_msa_md']

    for field in geo_fields:
        if field in df.columns:
            field_data = df[field].astype(str)
            empty_count = (field_data == '').sum()
            unique_count = len(field_data.unique())

            print(f"{field}:")
            print(f"  - Empty values: {empty_count:,} ({empty_count/len(df)*100:.1f}%)")
            print(f"  - Unique values: {unique_count:,}")
            print(f"  - Sample values: {field_data.unique()[:5].tolist()}")

            if field == 'county_code':
                # Check for decimal issues
                has_decimals = field_data.str.contains(r'\.').sum()
                if has_decimals > 0:
                    print(f"  - WARNING: {has_decimals:,} county codes have decimal points")

    # Missing value analysis
    print("\n=== MISSING VALUE PATTERNS ===")
    total_cells = len(df) * len(df.columns)
    empty_strings = (df == '').sum().sum()

    print(f"Total cells: {total_cells:,}")
    print(f"Empty strings: {empty_strings:,} ({empty_strings/total_cells*100:.2f}%)")

    # High missing rate columns
    print("\nColumns with >10% missing values:")
    for col in df.columns:
        col_data = df[col].astype(str)
        empty_rate = (col_data == '').sum() / len(df)
        if empty_rate > 0.1:
            print(f"  - {col}: {empty_rate*100:.1f}% missing")

    # Key field distributions
    print("\n=== KEY FIELD DISTRIBUTIONS ===")
    key_fields = ['action_taken', 'loan_purpose', 'derived_race', 'derived_ethnicity']

    for field in key_fields:
        if field in df.columns:
            value_counts = df[field].value_counts().head(3)
            print(f"{field}:")
            for value, count in value_counts.items():
                print(f"  - {value}: {count:,} ({count/len(df)*100:.1f}%)")

    # Numeric field analysis
    print("\n=== NUMERIC FIELD QUALITY ===")
    numeric_fields = ['loan_amount', 'income', 'property_value']

    for field in numeric_fields:
        if field in df.columns:
            field_data = df[field].astype(str)
            empty_count = (field_data == '').sum()

            # Try to identify numeric values
            numeric_mask = field_data.str.isnumeric() | field_data.str.match(r'^\d+\.\d+$')
            numeric_count = numeric_mask.sum()

            print(f"{field}:")
            print(f"  - Empty values: {empty_count:,}")
            print(f"  - Numeric values: {numeric_count:,} ({numeric_count/len(df)*100:.1f}%)")

            if numeric_count > 0:
                try:
                    numeric_data = pd.to_numeric(field_data[numeric_mask], errors='coerce')
                    if not numeric_data.isna().all():
                        print(f"  - Range: ${numeric_data.min():,.0f} to ${numeric_data.max():,.0f}")
                        print(f"  - Mean: ${numeric_data.mean():,.0f}")
                except:
                    print(f"  - Could not analyze numeric range")

    # Data quality summary
    print("\n=== QUALITY SUMMARY ===")

    # Critical issues
    critical_issues = []

    # Check geographic completeness
    if 'state_code' in df.columns:
        empty_states = (df['state_code'] == '').sum()
        if empty_states > 0:
            critical_issues.append(f"{empty_states:,} records missing state codes")

    if 'county_code' in df.columns:
        empty_counties = (df['county_code'] == '').sum()
        if empty_counties > 0:
            critical_issues.append(f"{empty_counties:,} records missing county codes")

        # Check decimal format issue
        has_decimals = df['county_code'].str.contains(r'\.').sum()
        if has_decimals > 0:
            critical_issues.append(f"{has_decimals:,} county codes have decimal format (should be integers)")

    if critical_issues:
        print("CRITICAL ISSUES:")
        for issue in critical_issues:
            print(f"  WARNING: {issue}")
    else:
        print("CHECK MARK: No critical geographic field issues found")

    # Recommendations
    print("\n=== RECOMMENDATIONS ===")
    print("1. PRESERVE ALL DATA - Do not remove or modify any values")
    print("2. Document missing value patterns for transparency")
    print("3. Investigate decimal county codes (conversion artifacts?)")
    print("4. Use geographic stability findings for longitudinal analysis")
    print("5. Consider creating quality flags rather than excluding data")

    # Save results
    output_path = OUTPUT_ROOT / "analysis_outputs/data_quality"
    output_path.mkdir(parents=True, exist_ok=True)

    results = {
        'analysis_date': datetime.now().isoformat(),
        'records_analyzed': len(df),
        'critical_issues': critical_issues,
        'geographic_field_summary': {
            field: {
                'empty_count': int((df[field] == '').sum()),
                'unique_count': int(df[field].nunique())
            } for field in geo_fields if field in df.columns
        },
        'overall_missing_rate': float(empty_strings / total_cells),
        'recommendations': [
            "Preserve all original data values",
            "Document quality issues without fixing",
            "Use quality flags for analysis decisions",
            "Apply geographic stability framework"
        ]
    }

    with open(output_path / "focused_sample_quality_results.json", 'w') as f:
        json.dump(results, f, indent=2)

    print(f"\nResults saved to: {output_path}/focused_sample_quality_results.json")
    print("\nQUALITY ANALYSIS COMPLETE - All original data preserved")

if __name__ == "__main__":
    analyze_sample_quality()