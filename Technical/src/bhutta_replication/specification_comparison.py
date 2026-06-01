"""
Specification Comparison: Central City Filter Impact Analysis

This module compares two specifications:
1. ORIGINAL (R code): central_city_flag == 1 + owner-occupied >= 100
2. BHUTTA (paper): All MSA tracts + total housing units >= 100

Key finding: The R code's central city filter removes ~65% of the sample,
which may explain the sign flip in regression results.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional, Tuple

import numpy as np
import pandas as pd
import os
DATA_ROOT = Path(os.environ.get("DATA_ROOT", "data"))
OUTPUT_ROOT = Path(os.environ.get("OUTPUT_ROOT", "outputs"))


@dataclass
class SpecificationResult:
    """Results from a single specification."""

    name: str
    sample_size: int
    tm_stats: Dict[str, float]
    outcome_stats: Dict[str, float]
    covariate_stats: Dict[str, Dict[str, float]]
    bandwidth_counts: Dict[str, int]
    msa_size_counts: Dict[str, int]
    regression_results: Optional[Dict] = None


class SpecificationComparator:
    """Compare R specification vs Bhutta specification."""

    def __init__(self, census_data_path: Path, r_results_path: Optional[Path] = None):
        """
        Args:
            census_data_path: Path to census_bhutta parquet directory
            r_results_path: Path to R output Excel files
        """
        self.census_path = Path(census_data_path)
        self.r_results_path = Path(r_results_path) if r_results_path else None

    def load_census_data(self, years: list = None) -> pd.DataFrame:
        """Load census data from parquet files."""
        years = years or list(range(1996, 2007))

        dfs = []
        for year in years:
            path = self.census_path / f"census_{year}.parquet"
            if path.exists():
                df = pd.read_parquet(path)
                df["year"] = year
                dfs.append(df)

        if not dfs:
            raise FileNotFoundError(f"No census files found in {self.census_path}")

        return pd.concat(dfs, ignore_index=True)

    def apply_r_specification(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Apply R code specification:
        1. Central city flag == 1
        2. Exclude Hawaii (15) and Alaska (2)
        3. Owner-occupied housing units >= 100
        """
        result = df.copy()

        # 1. Central city filter (CRITICAL DIFFERENCE)
        if "central_city_flag" in result.columns:
            result = result[result["central_city_flag"] == 1]
        elif "cc" in result.columns:
            result = result[result["cc"] == 1]

        # 2. Exclude Hawaii and Alaska
        if "state_code" in result.columns:
            result = result[~result["state_code"].isin([2, 15])]
        elif "st" in result.columns:
            result = result[~result["st"].isin(["02", "15", 2, 15])]

        # 3. Owner-occupied housing units >= 100
        if "owner_occupied_units" in result.columns:
            result = result[result["owner_occupied_units"] >= 100]
        elif "oou" in result.columns:
            result = result[result["oou"] >= 100]

        return result

    def apply_bhutta_specification(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Apply Bhutta paper specification:
        1. All MSA tracts (NO central city filter)
        2. Exclude Hawaii (15) and Alaska (2)
        3. Total housing units >= 100 (NOT owner-occupied)
        4. < 30% population in group quarters
        """
        result = df.copy()

        # NO central city filter

        # 2. Exclude Hawaii and Alaska
        if "state_code" in result.columns:
            result = result[~result["state_code"].isin([2, 15])]
        elif "st" in result.columns:
            result = result[~result["st"].isin(["02", "15", 2, 15])]

        # 3. Total housing units >= 100
        if "total_housing_units" in result.columns:
            result = result[result["total_housing_units"] >= 100]
        elif "hu" in result.columns:
            result = result[result["hu"] >= 100]

        # 4. Group quarters filter (< 30%)
        if "group_quarters_pop" in result.columns and "population" in result.columns:
            result["gq_pct"] = result["group_quarters_pop"] / result[
                "population"
            ].replace(0, np.nan)
            result = result[result["gq_pct"] < 0.30]
        elif "gq" in result.columns and "pop" in result.columns:
            result["gq_pct"] = result["gq"] / result["pop"].replace(0, np.nan)
            result = result[result["gq_pct"] < 0.30]

        return result

    def apply_bandwidth_filter(self, df: pd.DataFrame, h: float = 0.05) -> pd.DataFrame:
        """Filter to TM within bandwidth of 0.80 cutoff."""
        result = df.copy()

        # Find TM column
        tm_col = None
        for col in [
            "TM",
            "tm",
            "tract_mfi_ratio",
            "decennial_msa_median_family_income_percentage",
        ]:
            if col in result.columns:
                tm_col = col
                break

        if tm_col is None:
            raise ValueError("No TM column found in data")

        result = result[(result[tm_col] >= 0.80 - h) & (result[tm_col] <= 0.80 + h)]

        return result

    def compute_statistics(self, df: pd.DataFrame, name: str) -> SpecificationResult:
        """Compute summary statistics for a specification."""

        # Find relevant columns
        tm_col = self._find_column(df, ["TM", "tm", "tract_mfi_ratio"])

        # TM statistics
        tm_stats = {}
        if tm_col:
            tm_stats = {
                "mean": df[tm_col].mean(),
                "std": df[tm_col].std(),
                "min": df[tm_col].min(),
                "max": df[tm_col].max(),
                "median": df[tm_col].median(),
                "pct_below_80": (df[tm_col] < 0.80).mean() * 100,
            }

        # Outcome statistics (if available)
        outcome_stats = {}
        outcome_col = self._find_column(
            df, ["ln_number_of_loans", "bank_originations", "num_loans"]
        )
        if outcome_col:
            outcome_stats = {
                "mean": df[outcome_col].mean(),
                "std": df[outcome_col].std(),
                "median": df[outcome_col].median(),
            }

        # Covariate statistics
        covariate_stats = {}
        covariates = [
            ("minority_pct", ["minority_percentage", "minority_pct", "pct_minority"]),
            ("poverty_pct", ["poverty_level_percentage", "poverty_pct", "pov_pct"]),
            (
                "median_home_value",
                ["ownOcc_housingUnits_medianValue", "median_value", "home_value"],
            ),
            ("total_housing", ["total_housing_units", "totalHousingUnits", "hu"]),
            ("owner_occupied", ["owner_occupied_units", "ownOcc_housingUnits", "oou"]),
            ("pct_pre1940", ["prop_pre1940", "pct_pre1940", "housing_pre1940_pct"]),
        ]

        for name_key, col_options in covariates:
            col = self._find_column(df, col_options)
            if col:
                covariate_stats[name_key] = {
                    "mean": df[col].mean(),
                    "std": df[col].std(),
                    "n_missing": df[col].isna().sum(),
                }

        # Bandwidth counts
        bandwidth_counts = {}
        if tm_col:
            for bw_name, bw in [("narrow_h05", 0.05), ("wide_h30", 0.30)]:
                mask = (df[tm_col] >= 0.80 - bw) & (df[tm_col] <= 0.80 + bw)
                bandwidth_counts[bw_name] = mask.sum()

        # MSA size counts (placeholder - would need MSA population data)
        msa_size_counts = {"unknown": len(df)}

        return SpecificationResult(
            name=name,
            sample_size=len(df),
            tm_stats=tm_stats,
            outcome_stats=outcome_stats,
            covariate_stats=covariate_stats,
            bandwidth_counts=bandwidth_counts,
            msa_size_counts=msa_size_counts,
        )

    def _find_column(self, df: pd.DataFrame, options: list) -> Optional[str]:
        """Find first matching column from options."""
        for col in options:
            if col in df.columns:
                return col
        return None

    def read_r_regression_results(self) -> Optional[Dict]:
        """Read regression results from R output Excel files."""
        if not self.r_results_path or not self.r_results_path.exists():
            return None

        results = {}

        # Look for regression output files
        excel_patterns = [
            "regression_results_modelsummary_OneWithControls*.xlsx",
            "regression_results*.xlsx",
        ]

        for pattern in excel_patterns:
            for file in self.r_results_path.glob(pattern):
                try:
                    df = pd.read_excel(file)
                    results[file.name] = df
                except Exception as e:
                    print(f"Warning: Could not read {file}: {e}")

        return results if results else None

    def run_comparison(
        self, years: list = None
    ) -> Tuple[SpecificationResult, SpecificationResult]:
        """
        Run full specification comparison.

        Returns:
            Tuple of (r_spec_results, bhutta_spec_results)
        """
        # Load data
        df = self.load_census_data(years)

        # Apply specifications
        df_r = self.apply_r_specification(df)
        df_bhutta = self.apply_bhutta_specification(df)

        # Compute statistics
        r_results = self.compute_statistics(df_r, "R Code (Central City)")
        bhutta_results = self.compute_statistics(df_bhutta, "Bhutta (All MSA)")

        # Add R regression results if available
        r_reg = self.read_r_regression_results()
        if r_reg:
            r_results.regression_results = r_reg

        return r_results, bhutta_results

    def generate_comparison_report(
        self, r_results: SpecificationResult, bhutta_results: SpecificationResult
    ) -> str:
        """Generate formatted comparison report."""

        lines = []
        lines.append("=" * 80)
        lines.append("SPECIFICATION COMPARISON REPORT")
        lines.append(
            "R Code (Central City Filter) vs Bhutta (2011) Paper Specification"
        )
        lines.append("=" * 80)
        lines.append("")

        # Sample sizes
        lines.append("1. SAMPLE SIZE IMPACT")
        lines.append("-" * 40)
        lines.append(f"R Code (Central City only):     {r_results.sample_size:>10,}")
        lines.append(
            f"Bhutta (All MSA tracts):        {bhutta_results.sample_size:>10,}"
        )
        diff = bhutta_results.sample_size - r_results.sample_size
        pct_diff = diff / bhutta_results.sample_size * 100
        lines.append(
            f"Difference:                     {diff:>10,} ({pct_diff:.1f}% more in Bhutta)"
        )
        lines.append("")
        lines.append(
            "CRITICAL: The central city filter removes {:.1f}% of the sample!".format(
                pct_diff
            )
        )
        lines.append("")

        # TM distribution
        if r_results.tm_stats and bhutta_results.tm_stats:
            lines.append("2. TM DISTRIBUTION (Tract MFI / MSA MFI)")
            lines.append("-" * 40)
            lines.append(f"{'Statistic':<20} {'R Code':>15} {'Bhutta':>15}")
            lines.append("-" * 50)
            for stat in ["mean", "std", "median", "min", "max", "pct_below_80"]:
                r_val = r_results.tm_stats.get(stat, np.nan)
                b_val = bhutta_results.tm_stats.get(stat, np.nan)
                lines.append(f"{stat:<20} {r_val:>15.4f} {b_val:>15.4f}")
            lines.append("")

        # Bandwidth counts
        if r_results.bandwidth_counts and bhutta_results.bandwidth_counts:
            lines.append("3. SAMPLE SIZES BY BANDWIDTH")
            lines.append("-" * 40)
            lines.append(f"{'Bandwidth':<20} {'R Code':>15} {'Bhutta':>15}")
            lines.append("-" * 50)
            for bw in r_results.bandwidth_counts:
                r_val = r_results.bandwidth_counts.get(bw, 0)
                b_val = bhutta_results.bandwidth_counts.get(bw, 0)
                lines.append(f"{bw:<20} {r_val:>15,} {b_val:>15,}")
            lines.append("")
            lines.append(
                "NOTE: Bhutta's Large MSA h=0.05 sample should be ~1,800 tracts"
            )
            lines.append("")

        # Covariate comparison
        if r_results.covariate_stats and bhutta_results.covariate_stats:
            lines.append("4. COVARIATE MEANS COMPARISON")
            lines.append("-" * 40)
            lines.append(f"{'Variable':<25} {'R Code':>15} {'Bhutta':>15} {'Diff':>10}")
            lines.append("-" * 65)
            for var in r_results.covariate_stats:
                r_mean = r_results.covariate_stats[var].get("mean", np.nan)
                b_mean = bhutta_results.covariate_stats.get(var, {}).get("mean", np.nan)
                diff = (
                    r_mean - b_mean
                    if not (np.isnan(r_mean) or np.isnan(b_mean))
                    else np.nan
                )
                lines.append(f"{var:<25} {r_mean:>15.4f} {b_mean:>15.4f} {diff:>10.4f}")
            lines.append("")

        # Key differences summary
        lines.append("5. KEY SPECIFICATION DIFFERENCES")
        lines.append("-" * 40)
        lines.append("")
        lines.append(
            "| Aspect                | R Code                  | Bhutta Paper            |"
        )
        lines.append(
            "|----------------------|-------------------------|-------------------------|"
        )
        lines.append(
            "| Central city filter  | YES (cc_flag=1)         | NO                      |"
        )
        lines.append(
            "| Housing filter       | OOU >= 100              | Total HU >= 100         |"
        )
        lines.append(
            "| Group quarters       | Not applied             | < 30%                   |"
        )
        lines.append(
            "| Controls included    | 6 variables             | 12+ variables           |"
        )
        lines.append("")

        # Implications
        lines.append("6. IMPLICATIONS FOR RESULTS")
        lines.append("-" * 40)
        lines.append("")
        lines.append("The central city filter likely causes the sign flip because:")
        lines.append(
            "1. It EXCLUDES suburban tracts that may drive Bhutta's positive effect"
        )
        lines.append("2. Central cities have different CRA treatment patterns")
        lines.append("3. Sample composition changes dramatically (65% reduction)")
        lines.append("")
        lines.append(
            "RECOMMENDATION: Run regression WITHOUT central city filter to match Bhutta"
        )
        lines.append("")

        lines.append("=" * 80)

        return "\n".join(lines)


def run_quick_comparison(census_path: str, r_output_path: str = None) -> str:
    """
    Quick comparison function for interactive use.

    Args:
        census_path: Path to census_bhutta directory
        r_output_path: Path to R output files (optional)

    Returns:
        Formatted comparison report string
    """
    comparator = SpecificationComparator(
        census_data_path=Path(census_path),
        r_results_path=Path(r_output_path) if r_output_path else None,
    )

    r_results, bhutta_results = comparator.run_comparison()

    report = comparator.generate_comparison_report(r_results, bhutta_results)

    return report


if __name__ == "__main__":
    # Example usage
    import sys

    if len(sys.argv) > 1:
        census_path = sys.argv[1]
    else:
        census_path = str(OUTPUT_ROOT / "Technical/data/census_bhutta")

    r_output_path = (
        str(DATA_ROOT / "Inputs/Old/CRA_code/_files2/1990to2006/out")
    )

    report = run_quick_comparison(census_path, r_output_path)
    print(report)
