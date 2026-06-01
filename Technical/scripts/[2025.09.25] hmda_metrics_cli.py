import argparse
import os
import sys

THIS_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(THIS_DIR, ".."))
SRC_DIR = os.path.join(PROJECT_ROOT, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from hmda.metrics import build_metrics


def main():
    parser = argparse.ArgumentParser(description="Compute HMDA approval/denial metrics and HHI")
    parser.add_argument("year", type=int, help="Year to process")
    parser.add_argument("--config", default="python_project.yaml")
    parser.add_argument("--nrows", type=int, default=None)
    args = parser.parse_args()

    out = build_metrics(args.year, config_path=args.config, nrows=args.nrows)
    for k, v in out.items():
        if v:
            print(k, v)


if __name__ == "__main__":
    main()



