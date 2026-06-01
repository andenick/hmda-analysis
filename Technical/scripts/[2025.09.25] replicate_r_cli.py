import argparse
import os
import sys

THIS_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(THIS_DIR, ".."))
SRC_DIR = os.path.join(PROJECT_ROOT, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from hmda.replicate_r import replicate_year


def main():
    parser = argparse.ArgumentParser(description="Replicate R final outputs (step2-6) for HMDA")
    parser.add_argument("years", nargs="*", type=int, help="Years to replicate (e.g., 2019 2020)")
    parser.add_argument("--config", default="python_project.yaml")
    parser.add_argument("--nrows", type=int, default=None, help="Optional row limit for validation runs")
    args = parser.parse_args()

    years = args.years or [2019, 2020, 2021, 2022]
    for y in years:
        out = replicate_year(y, config_path=args.config, nrows=args.nrows)
        for k, v in out.items():
            print(y, k, v)


if __name__ == "__main__":
    main()


