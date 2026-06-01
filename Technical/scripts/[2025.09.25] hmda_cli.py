import argparse
import os
import sys

THIS_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(THIS_DIR, ".."))
SRC_DIR = os.path.join(PROJECT_ROOT, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from hmda.process import process_hmda


def main():
    parser = argparse.ArgumentParser(description="Process HMDA LAR/Panel into aggregated outputs")
    parser.add_argument("--years", nargs="*", type=int, help="Years to process (e.g., 2019 2020)")
    parser.add_argument("--config", default="python_project.yaml", help="Path to project YAML config")
    parser.add_argument("--nrows", type=int, default=None, help="Optional number of rows to read for validation")
    args = parser.parse_args()

    outputs = process_hmda(args.years or None, config_path=args.config, nrows=args.nrows)
    for out in outputs:
        print(out)


if __name__ == "__main__":
    main()


