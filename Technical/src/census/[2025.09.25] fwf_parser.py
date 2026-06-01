from __future__ import annotations

import os
from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple

import pandas as pd
import yaml


@dataclass
class FWFField:
    name: str
    start: int
    end: int


def load_yaml_config(config_path: str) -> dict:
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def build_widths_from_excel(excel_path: str, name_col: str = "Column Name", start_col: str = "Start", end_col: str = "End") -> List[FWFField]:
    df = pd.read_excel(excel_path)
    cols = [c.strip() for c in df.columns]
    # try to auto-detect common headings
    def find(col: str, candidates: List[str]) -> str:
        for cand in candidates:
            if cand in cols:
                return cand
        raise KeyError(f"Missing column for {col} in {excel_path}, have: {cols}")

    name_c = find("name", [name_col, "Field Name", "Name", "Variable", "Label"])
    start_c = find("start", [start_col, "Start Pos", "Start", "Begin", "From"])
    end_c = find("end", [end_col, "End Pos", "End", "To"])

    out: List[FWFField] = []
    for _, row in df.iterrows():
        try:
            field_name = str(row[name_c]).strip()
            start_idx = int(row[start_c])
            end_idx = int(row[end_c])
            if not field_name or pd.isna(field_name):
                continue
            out.append(FWFField(field_name, start_idx, end_idx))
        except Exception:
            continue
    if not out:
        raise ValueError(f"No fields extracted from {excel_path}")
    return out


def detect_schema_columns(cols: List[str]) -> Tuple[str, Optional[str], Optional[str], Optional[str]]:
    # Returns (name_col, start_col, end_col, length_col)
    lowered = {c.lower(): c for c in cols}

    def pick(candidates: List[str]) -> Optional[str]:
        for cand in candidates:
            if cand.lower() in lowered:
                return lowered[cand.lower()]
        return None

    name_c = pick(["Element Label", "Field Name", "Name", "Variable", "Label", "Field"])
    start_c = pick(["Starting", "Start Pos", "Start", "Begin", "From"]) 
    end_c = pick(["Ending", "End Pos", "End", "To"]) 
    len_c = pick(["Length", "Len"]) 

    if name_c is None or (start_c is None and (end_c is None or len_c is None)):
        raise KeyError(f"Cannot detect schema columns from: {cols}")
    return name_c, start_c, end_c, len_c


def build_fields_from_csv(spec_df: pd.DataFrame) -> List[FWFField]:
    cols = list(spec_df.columns)
    name_c, start_c, end_c, len_c = detect_schema_columns(cols)
    fields: List[FWFField] = []
    for _, row in spec_df.iterrows():
        try:
            field_name = str(row[name_c]).strip()
            if not field_name or pd.isna(field_name):
                continue
            if start_c is not None:
                s = int(str(row[start_c]).strip())
            else:
                s = None  # fallback when only length and end given (unlikely)
            e: Optional[int] = None
            if end_c is not None and not pd.isna(row[end_c]):
                e = int(str(row[end_c]).strip())
            if e is None and s is not None and len_c is not None and not pd.isna(row[len_c]):
                ln = int(str(row[len_c]).strip())
                e = s + ln - 1
            if s is None or e is None:
                continue
            fields.append(FWFField(field_name, s, e))
        except Exception:
            continue
    if not fields:
        raise ValueError("No fields extracted from CSV schema")
    return fields


def widths_to_pandas_args(fields: List[FWFField]) -> Dict[str, List]:
    widths = [(f.end - f.start + 1) for f in fields]
    names = [f.name for f in fields]
    return {"widths": widths, "names": names}


def read_fwf_year(dat_path: str, fields: List[FWFField], dtype: Optional[Dict[str, str]] = None, row_limit: Optional[int] = None) -> pd.DataFrame:
    args = widths_to_pandas_args(fields)
    df = pd.read_fwf(
        dat_path,
        widths=args["widths"],
        header=None,
        dtype=dtype or object,
        nrows=row_limit,
    )
    # Ensure unique column names to satisfy Parquet writers
    df.columns = make_unique_column_names(args["names"]) 
    return df


def save_output(df: pd.DataFrame, out_base: str, format: str = "parquet") -> None:
    os.makedirs(os.path.dirname(out_base), exist_ok=True)
    if format == "parquet":
        df.to_parquet(out_base + ".parquet", index=False)
    elif format == "csv":
        df.to_csv(out_base + ".csv", index=False)
    else:
        raise ValueError("Unsupported format: " + format)


def parse_ffiec_year(year: int, config: dict, row_limit: Optional[int] = None) -> str:
    src_root = config["raw_paths"]["ffiec_census_src"]
    out_dir = os.path.join(config["outputs"]["data_dir"], "census")
    fmt = config["processing"]["output_format"]

    # Support fixed-width (<=2011) and CSV (>=2012) inputs
    candidates = [
        os.path.join(src_root, f"{year}", f"census_{year}.dat"),
        os.path.join(src_root, f"{year}", f"census{year}.DAT"),
        os.path.join(src_root, f"{year}", f"census{year}.dat"),
        os.path.join(src_root, f"{year}", f"Census{year}.csv"),
        os.path.join(src_root, f"{year}", f"census{year}.csv"),
        os.path.join(src_root, f"{year}", f"Census{year}.CSV"),
    ]
    dat_path = next((p for p in candidates if os.path.exists(p)), None)
    if dat_path is None:
        raise FileNotFoundError(f"No census file found for {year} under {src_root}")

    # schema path detection (use supplied CSV specs or Excel guides within repo)
    schema_csv_2002 = "Old/Python Stuff/schemas/ffiec_census_fwf_spec_2002.csv"
    schema_csv_2006 = "Old/Python Stuff/schemas/ffiec_census_fwf_spec_2006.csv"

    fields: List[FWFField]
    if dat_path.lower().endswith(".csv"):
        # CSV files often lack headers; load with header=None and set leading columns
        df = pd.read_csv(dat_path, dtype=object, header=None)
        # Assign basic leading column names for joins; retain others as generic
        base_cols = ["Year", "MSA_MD", "State", "County"]
        remaining = [f"col_{i}" for i in range(len(df.columns) - len(base_cols))]
        df.columns = make_unique_column_names(base_cols + remaining)
        out_base = os.path.join(out_dir, f"census_data_{year}")
        save_output(df, out_base, format=fmt)
        return out_base + (".parquet" if fmt == "parquet" else ".csv")

    if year >= 2003:
        if os.path.exists(schema_csv_2006):
            spec_df = pd.read_csv(schema_csv_2006)
            fields = build_fields_from_csv(spec_df)
        else:
            # fallback to Excel guide
            guide_path = f"Old/CRA_code/_files2/flatFiles/_flatFileGuide2/census_2006_guide.xlsx"
            fields = build_widths_from_excel(guide_path)
    else:
        if os.path.exists(schema_csv_2002):
            spec_df = pd.read_csv(schema_csv_2002)
            fields = build_fields_from_csv(spec_df)
        else:
            guide_path = f"Old/CRA_code/_files2/flatFiles/_flatFileGuide2/census_2002_guide.xlsx"
            fields = build_widths_from_excel(guide_path)

    df = read_fwf_year(dat_path, fields, row_limit=row_limit)
    out_base = os.path.join(out_dir, f"census_data_{year}")
    save_output(df, out_base, format=fmt)
    return out_base + (".parquet" if fmt == "parquet" else ".csv")


def parse_ffiec_range(years: List[int], config_path: str = "python_project.yaml", row_limit: Optional[int] = None) -> List[str]:
    config = load_yaml_config(config_path)
    written: List[str] = []
    # if empty, use config fixed-width years
    target_years = years or list(config["processing"]["census_years_fixed_width"])
    for yr in target_years:
        written.append(parse_ffiec_year(yr, config, row_limit=row_limit))
    return written


def make_unique_column_names(names: List[str]) -> List[str]:
    """Make column names unique by appending suffixes for duplicates."""
    seen: Dict[str, int] = {}
    result: List[str] = []
    for name in names:
        base = str(name)
        if base not in seen:
            seen[base] = 1
            result.append(base)
        else:
            seen[base] += 1
            result.append(f"{base}__{seen[base]}")
    return result


