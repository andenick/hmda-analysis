#!/usr/bin/env python3
"""
Systemic Banks Analysis CLI
===========================

Command-line interface for analyzing systemically important US banks using HMDA data.

Usage:
    python scripts/analyze_systemic_banks.py --year 2019 --top-n 50
    python scripts/analyze_systemic_banks.py --year 2020 --top-n 100 --min-loans 5000
"""

import os
import sys
import argparse
from datetime import datetime

# Add src to path
THIS_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(THIS_DIR, ".."))
SRC_DIR = os.path.join(PROJECT_ROOT, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from banks.systemic_banks import SystemicBanksAnalyzer


def print_status(message: str, step: str = "INFO"):
    """Print formatted status messages with timestamps."""
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] {step}: {message}")


def main():
    """Main CLI function."""
    parser = argparse.ArgumentParser(
        description="Analyze systemically important US banks using HMDA data",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Analyze top 50 systemic banks for 2019
  python scripts/analyze_systemic_banks.py --year 2019 --top-n 50
  
  # Analyze top 100 banks with stricter criteria
  python scripts/analyze_systemic_banks.py --year 2020 --top-n 100 --min-loans 10000 --min-states 10
  
  # Generate report for multiple years
  python scripts/analyze_systemic_banks.py --years 2019 2020 2021 --top-n 50
        """
    )
    
    parser.add_argument("--year", type=int, help="Year to analyze (single year)")
    parser.add_argument("--years", nargs="+", type=int, help="Years to analyze (multiple years)")
    parser.add_argument("--top-n", type=int, default=50, help="Number of top banks to identify (default: 50)")
    parser.add_argument("--min-loans", type=int, default=1000, help="Minimum number of loans (default: 1000)")
    parser.add_argument("--min-states", type=int, default=5, help="Minimum number of states (default: 5)")
    parser.add_argument("--output-dir", default="data/banks", help="Output directory (default: data/banks)")
    parser.add_argument("--config", default="python_project.yaml", help="Config file path")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose output")
    
    args = parser.parse_args()
    
    # Determine years to analyze
    if args.years:
        years = args.years
    elif args.year:
        years = [args.year]
    else:
        years = [2019]  # Default year
    
    print_status(f"Starting systemic banks analysis")
    print_status(f"Years: {years}")
    print_status(f"Top N: {args.top_n}")
    print_status(f"Min loans: {args.min_loans}")
    print_status(f"Min states: {args.min_states}")
    print_status(f"Output directory: {args.output_dir}")
    
    try:
        # Initialize analyzer
        print_status("Initializing systemic banks analyzer...")
        analyzer = SystemicBanksAnalyzer(config_path=args.config)
        
        # Process each year
        results = {}
        for year in years:
            print_status(f"Processing year {year}...")
            
            try:
                # Generate report for this year
                report_path = analyzer.generate_systemic_bank_report(
                    year=year,
                    top_n=args.top_n,
                    output_dir=args.output_dir
                )
                
                results[year] = {
                    'status': 'success',
                    'report_path': report_path
                }
                
                print_status(f"Year {year} completed successfully: {report_path}")
                
            except Exception as e:
                print_status(f"Error processing year {year}: {str(e)}", "ERROR")
                results[year] = {
                    'status': 'error',
                    'error': str(e)
                }
        
        # Summary
        print_status("Analysis complete!")
        print_status("Results summary:")
        for year, result in results.items():
            if result['status'] == 'success':
                print_status(f"  {year}: ✅ Success - {result['report_path']}")
            else:
                print_status(f"  {year}: ❌ Error - {result['error']}")
        
        # Show output directory contents
        if os.path.exists(args.output_dir):
            files = os.listdir(args.output_dir)
            print_status(f"Generated files in {args.output_dir}:")
            for file in sorted(files):
                print_status(f"  - {file}")
        
    except Exception as e:
        print_status(f"Fatal error: {str(e)}", "ERROR")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
