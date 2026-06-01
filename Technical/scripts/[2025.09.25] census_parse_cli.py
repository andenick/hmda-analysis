import argparse
import os
import sys

# Ensure local 'src' is importable when running as a script
THIS_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(THIS_DIR, ".."))
SRC_DIR = os.path.join(PROJECT_ROOT, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from census.fwf_parser import parse_ffiec_range


def main():
    parser = argparse.ArgumentParser(description="Parse FFIEC Census fixed-width files to Parquet/CSV")
    parser.add_argument("--years", nargs="*", type=int, help="Years to parse (e.g., 1998 2001 2006)")
    parser.add_argument("--config", default="python_project.yaml", help="Path to project YAML config")
    parser.add_argument("--row-limit", type=int, default=None, help="Optional number of rows to read for quick validation")
    args = parser.parse_args()

    if not args.years:
        print("No years specified; using config census_years_fixed_width")
    outputs = parse_ffiec_range(args.years or [], config_path=args.config, row_limit=args.row_limit)
    for out in outputs:
        print(out)


if __name__ == "__main__":
    main()


