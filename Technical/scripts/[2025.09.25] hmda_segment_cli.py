import argparse
import os
import sys

THIS_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(THIS_DIR, ".."))
SRC_DIR = os.path.join(PROJECT_ROOT, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from hmda.segment import segment_hmda


def main():
    parser = argparse.ArgumentParser(description="Segment HMDA data by lender/borrower/loan attributes")
    parser.add_argument("year", type=int, help="Year to segment (e.g., 2019)")
    parser.add_argument("--config", default="python_project.yaml", help="Path to project YAML config")
    parser.add_argument("--nrows", type=int, default=None, help="Row limit for validation")
    args = parser.parse_args()

    out = segment_hmda(args.year, config_path=args.config, nrows=args.nrows)
    print(out)


if __name__ == "__main__":
    main()


