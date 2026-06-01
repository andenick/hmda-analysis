#!/usr/bin/env python3
import os
import sys
from datetime import datetime
import pandas as pd
import numpy as np

R_DIR = os.path.join("Old", "CRA_code", "_files2", "2017toPresent", "int")
PY_DIR = os.path.join("data", "r_replication")

STEPS = [
    "step2",
    "step3",
    "step4",
    "step5",
    "step6",
    "step6_banks",
    "step7",
    "step8",
]


def log(msg: str):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {msg}")


def load_pair(year: int, step: str):
    r_path = os.path.join(R_DIR, f"{year}_lar_race_{step}.csv")
    py_path = os.path.join(PY_DIR, f"{year}_lar_race_{step}.csv")
    r_df = pd.read_csv(r_path) if os.path.exists(r_path) else None
    py_df = pd.read_csv(py_path) if os.path.exists(py_path) else None
    return r_df, py_df, r_path, py_path


def compare_totals(r_df: pd.DataFrame, py_df: pd.DataFrame):
    r_num_cols = r_df.select_dtypes(include=[np.number]).columns
    py_num_cols = py_df.select_dtypes(include=[np.number]).columns
    common = sorted(set(r_num_cols) & set(py_num_cols))
    rows = []
    for col in common:
        r_sum = r_df[col].sum()
        py_sum = py_df[col].sum()
        diff = py_sum - r_sum
        pct = (diff / r_sum * 100.0) if r_sum not in (0, 0.0) else np.nan
        rows.append({
            "column": col,
            "r_total": r_sum,
            "py_total": py_sum,
            "difference": diff,
            "percent_diff": pct,
            "is_zero": np.isclose(diff, 0),
        })
    return pd.DataFrame(rows)


def write_report(year: int, results: dict, out_path: str):
    with pd.ExcelWriter(out_path, engine="openpyxl") as writer:
        # summary
        summary_rows = []
        for step, data in results.items():
            totals_df = data.get("totals")
            if totals_df is None or totals_df.empty:
                continue
            zero = int(totals_df["is_zero"].sum())
            total = int(len(totals_df))
            summary_rows.append({
                "Step": step,
                "Numeric Columns Compared": total,
                "Zero Differences": zero,
                "Match Rate %": round(100.0 * zero / total, 2) if total else 0.0,
            })
        pd.DataFrame(summary_rows).to_excel(writer, sheet_name="Summary", index=False)
        # details per step
        for step, data in results.items():
            totals_df = data.get("totals")
            if totals_df is None or totals_df.empty:
                continue
            totals_sorted = totals_df.sort_values("difference", key=np.abs, ascending=False)
            totals_sorted.to_excel(writer, sheet_name=f"{step}_totals", index=False)


def main():
    year = int(sys.argv[1]) if len(sys.argv) > 1 else 2019
    out_path = f"comparison_data/full_compare_{year}.xlsx"
    os.makedirs("comparison_data", exist_ok=True)

    log(f"Comparing R vs Python for {year}")
    results = {}

    for step in STEPS:
        r_df, py_df, r_path, py_path = load_pair(year, step)
        if r_df is None:
            log(f"R file missing: {r_path}")
            continue
        if py_df is None:
            log(f"Python file missing: {py_path}")
            continue
        log(f"Loaded {step}: R {r_df.shape}, PY {py_df.shape}")
        totals = compare_totals(r_df, py_df)
        results[step] = {"totals": totals}
        log(f"  Zero diffs: {int(totals['is_zero'].sum())}/{len(totals)}")

    write_report(year, results, out_path)
    log(f"Wrote report: {out_path}")


if __name__ == "__main__":
    main()


