import argparse
import os
import sys

THIS_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(THIS_DIR, ".."))
SRC_DIR = os.path.join(PROJECT_ROOT, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from hmda.enrich import enrich_segments_with_census


def main():
    parser = argparse.ArgumentParser(description="Enrich HMDA segments with FFIEC census context")
    parser.add_argument("year", type=int)
    parser.add_argument("--config", default="python_project.yaml")
    parser.add_argument("--limit", type=int, default=10000)
    args = parser.parse_args()

    out = enrich_segments_with_census(args.year, config_path=args.config, limit=args.limit)
    print(out)


if __name__ == "__main__":
    main()


