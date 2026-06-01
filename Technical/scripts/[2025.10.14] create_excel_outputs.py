#!/usr/bin/env python3
"""
Create Excel Outputs from HMDA CSV Data
Following Nick's one-sheet requirement - exactly one sheet per file

Author: Claude Code Agent
Date: October 14, 2025
Purpose: Convert key CSV files to Excel format for HMDA project delivery
"""

import pandas as pd
from pathlib import Path
from datetime import datetime
import sys

def generate_compliant_filename(description: str, extension: str) -> str:
    """Generate Druck-compliant filename with date prefix."""
    date_str = datetime.now().strftime("%Y.%m.%d")
    # Clean description: replace underscores with spaces, use Title Case
    clean_desc = description.replace('_', ' ').title()
    return f"[{date_str}] {clean_desc}.{extension}"

def create_excel_from_csv(csv_path: Path, output_dir: Path, description: str) -> bool:
    """
    Convert CSV file to Excel with single sheet and professional formatting.

    Args:
        csv_path: Path to source CSV file
        output_dir: Directory to save Excel file
        description: Description for output filename

    Returns:
        True if successful, False otherwise
    """
    try:
        print(f"Processing: {csv_path.name}")

        # Read CSV file
        df = pd.read_csv(csv_path)
        print(f"  - Loaded {len(df):,} rows, {len(df.columns)} columns")

        # Generate output filename
        excel_filename = generate_compliant_filename(description, "xlsx")
        excel_path = output_dir / excel_filename

        # Create Excel writer with single sheet
        with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
            # Write to single sheet named 'Data'
            df.to_excel(writer, sheet_name='Data', index=False)

        # Verify single sheet compliance
        excel_file = pd.ExcelFile(excel_path)
        assert len(excel_file.sheet_names) == 1, f"FAILED: Multiple sheets detected in {excel_filename}"

        print(f"  ✓ Created: {excel_filename} ({excel_path.stat().st_size:,} bytes)")
        print(f"  ✓ Single sheet compliance: PASSED")

        return True

    except Exception as e:
        print(f"  ✗ Error processing {csv_path.name}: {e}")
        return False

def main():
    """Main execution function."""
    print("=" * 80)
    print("HMDA EXCEL OUTPUT CREATION")
    print("Following Nick's One-Sheet Requirement")
    print("=" * 80)
    print()

    # Set up paths
    project_root = Path(__file__).parent.parent.parent
    csv_dir = project_root / "Output/Data/analysis_outputs"
    excel_output_dir = project_root / "Output/Data"

    print(f"Project root: {project_root}")
    print(f"CSV source directory: {csv_dir}")
    print(f"Excel output directory: {excel_output_dir}")
    print()

    # Ensure output directory exists
    excel_output_dir.mkdir(parents=True, exist_ok=True)

    # Define priority CSV files for conversion
    priority_files = [
        {
            "csv_file": "[2025.09.28] analysis_ready_2024.csv",
            "description": "hmda_analysis_ready_2024",
            "priority": "HIGH - Main analysis dataset"
        },
        {
            "csv_file": "[2025.09.28] lar_sample_100k.csv",
            "description": "hmda_lar_sample_100k",
            "priority": "HIGH - Large sample dataset"
        },
        {
            "csv_file": "[2025.09.29] geographic_stability_rankings.csv",
            "description": "geographic_stability_rankings",
            "priority": "MEDIUM - Geographic analysis"
        },
        {
            "csv_file": "[2025.09.29] stable_counties_detailed.csv",
            "description": "stable_counties_detailed",
            "priority": "MEDIUM - County stability data"
        },
        {
            "csv_file": "[2025.09.29] stable_geographic_areas_summary.csv",
            "description": "stable_geographic_areas_summary",
            "priority": "MEDIUM - Geographic summary"
        }
    ]

    print("CONVERSION PLAN:")
    print(f"{'Priority':<6} {'Description':<35} {'CSV File'}")
    print("-" * 80)

    for file_info in priority_files:
        csv_path = csv_dir / file_info["csv_file"]
        status = "AVAILABLE" if csv_path.exists() else "MISSING"
        print(f"{file_info['priority']:<6} {file_info['description']:<35} {status}")

    print()
    print("STARTING CONVERSION:")
    print()

    # Convert files
    successful_conversions = 0
    attempted_conversions = 0

    for file_info in priority_files:
        csv_path = csv_dir / file_info["csv_file"]

        if csv_path.exists():
            attempted_conversions += 1
            print(f"Priority: {file_info['priority']}")

            if create_excel_from_csv(csv_path, excel_output_dir, file_info["description"]):
                successful_conversions += 1
            print()
        else:
            print(f"Skipping missing file: {file_info['csv_file']}")
            print()

    # Summary
    print("=" * 80)
    print("CONVERSION SUMMARY")
    print("=" * 80)
    print(f"Files attempted: {attempted_conversions}")
    print(f"Successful conversions: {successful_conversions}")
    print(f"Failed conversions: {attempted_conversions - successful_conversions}")
    print()

    if successful_conversions > 0:
        print("✅ SUCCESS: Excel outputs created following Nick's one-sheet requirement")
        print("Excel files are ready in Output/Data/")

        # List created Excel files
        excel_files = list(excel_output_dir.glob("*.xlsx"))
        if excel_files:
            print("\nCreated Excel files:")
            for excel_file in excel_files:
                size = excel_file.stat().st_size
                print(f"  - {excel_file.name} ({size:,} bytes)")
    else:
        print("❌ FAILED: No Excel files were created")
        return 1

    # Compliance check
    print("\nCOMPLIANCE VERIFICATION:")
    excel_files = list(excel_output_dir.glob("*.xlsx"))
    compliant_files = 0

    for excel_file in excel_files:
        try:
            xl = pd.ExcelFile(excel_file)
            if len(xl.sheet_names) == 1:
                compliant_files += 1
                print(f"  ✓ {excel_file.name}: 1 sheet (COMPLIANT)")
            else:
                print(f"  ✗ {excel_file.name}: {len(xl.sheet_names)} sheets (NON-COMPLIANT)")
        except Exception as e:
            print(f"  ✗ {excel_file.name}: Cannot verify ({e})")

    print(f"\nCompliance rate: {compliant_files}/{len(excel_files)} files with single sheets")

    if compliant_files == len(excel_files) and len(excel_files) > 0:
        print("🎉 ALL EXCEL FILES COMPLY WITH NICK'S ONE-SHEET REQUIREMENT!")
        return 0
    else:
        print("⚠️  Some files don't meet compliance requirements")
        return 1

if __name__ == "__main__":
    sys.exit(main())