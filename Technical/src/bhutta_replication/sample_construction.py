"""
Bhutta (2011) Sample Construction

Implements the exact sample restrictions from the paper:
1. Urban areas only (MSA tracts)
2. Excludes Hawaii and Alaska
3. At least 100 housing units (1990)
4. Non-zero owner-occupied units
5. Less than 30% population in group quarters
6. Between 0.25 and 20 originations per owner-occupied unit (1994-2002)
7. TM within bandwidth of cutoff (0.80)

CRITICAL: Does NOT filter to central city only (unlike current R code)
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd


@dataclass
class SampleConfig:
    """Configuration for Bhutta sample construction."""

    # Geographic filters
    exclude_states: List[int] = field(default_factory=lambda: [2, 15])  # Alaska, Hawaii
    urban_only: bool = True  # Exclude rural tracts

    # Tract-level filters
    min_housing_units: int = 100  # Total housing units (NOT owner-occupied)
    min_owner_occupied: int = 1  # At least 1 OOU
    max_group_quarters_pct: float = 0.30  # < 30% in group quarters

    # Lending activity filters
    min_orig_per_oou: float = 0.25  # Over 1994-2002 period
    max_orig_per_oou: float = 20.0  # Over 1994-2002 period

    # RD design
    cutoff: float = 0.80  # CRA eligibility threshold
    bandwidths: Dict[str, float] = field(
        default_factory=lambda: {
            "narrow": 0.05,  # TM in [0.75, 0.85]
            "wide": 0.30,  # TM in [0.50, 1.10]
        }
    )

    # MSA size thresholds (1990 population)
    msa_size_thresholds: Dict[str, Tuple[int, int]] = field(
        default_factory=lambda: {
            "small": (0, 500_000),
            "medium": (500_000, 2_000_000),
            "large": (2_000_000, float("inf")),
        }
    )

    # Time period
    start_year: int = 1994
    end_year: int = 2002

    # Central city filter - CRITICAL: Bhutta does NOT use this
    central_city_only: bool = False


class BhuttaSampleConstructor:
    """Constructs analysis sample following Bhutta (2011) specifications."""

    def __init__(self, config: Optional[SampleConfig] = None):
        self.config = config or SampleConfig()
        self.filter_log: List[Dict] = []

    def _log_filter(self, name: str, before: int, after: int, description: str = ""):
        """Log filtering step for transparency."""
        self.filter_log.append(
            {
                "filter": name,
                "before": before,
                "after": after,
                "dropped": before - after,
                "pct_dropped": (before - after) / before * 100 if before > 0 else 0,
                "description": description,
            }
        )

    def construct_sample(
        self,
        census_df: pd.DataFrame,
        hmda_df: pd.DataFrame,
        msa_pop_df: Optional[pd.DataFrame] = None,
        bandwidth: str = "narrow",
    ) -> pd.DataFrame:
        """
        Construct analysis sample from census and HMDA data.

        Args:
            census_df: Census tract-level data with TM, housing vars, demographics
            hmda_df: HMDA loan-level or tract-aggregated lending data
            msa_pop_df: MSA population data for size classification (optional)
            bandwidth: "narrow" (h=0.05) or "wide" (h=0.30)

        Returns:
            DataFrame ready for RD analysis
        """
        self.filter_log = []  # Reset log

        df = census_df.copy()
        initial_n = len(df)

        # 1. Geographic filters
        df = self._apply_geographic_filters(df)

        # 2. Tract-level filters
        df = self._apply_tract_filters(df)

        # 3. Bandwidth filter (RD)
        df = self._apply_bandwidth_filter(df, bandwidth)

        # 4. Merge HMDA lending data
        df = self._merge_lending_data(df, hmda_df)

        # 5. Lending activity filters
        df = self._apply_lending_filters(df)

        # 6. MSA size classification
        if msa_pop_df is not None:
            df = self._classify_msa_size(df, msa_pop_df)

        # 7. Create analysis variables
        df = self._create_analysis_vars(df)

        self._log_filter("Final sample", initial_n, len(df), "After all filters")

        return df

    def _apply_geographic_filters(self, df: pd.DataFrame) -> pd.DataFrame:
        """Apply geographic sample restrictions."""
        n_before = len(df)

        # Exclude Alaska and Hawaii
        if "state_code" in df.columns:
            df = df[~df["state_code"].astype(int).isin(self.config.exclude_states)]
            self._log_filter(
                "Exclude AK/HI",
                n_before,
                len(df),
                f"Dropped states {self.config.exclude_states}",
            )
            n_before = len(df)

        # Urban only (in MSA)
        if self.config.urban_only and "msa_code" in df.columns:
            # Non-metro areas typically coded as 99999 or similar
            df = df[
                (df["msa_code"].notna())
                & (df["msa_code"].astype(str) != "99999")
                & (df["msa_code"].astype(str) != "")
            ]
            self._log_filter("Urban only", n_before, len(df), "MSA tracts only")
            n_before = len(df)

        # CRITICAL: Central city filter (Bhutta does NOT use this)
        if self.config.central_city_only and "central_city_flag" in df.columns:
            df = df[df["central_city_flag"].astype(str) == "1"]
            self._log_filter(
                "Central city only",
                n_before,
                len(df),
                "WARNING: Bhutta does NOT use this filter",
            )

        return df

    def _apply_tract_filters(self, df: pd.DataFrame) -> pd.DataFrame:
        """Apply tract-level sample restrictions."""
        n_before = len(df)

        # Min housing units (total, NOT owner-occupied)
        if "total_housing_units" in df.columns:
            df = df[df["total_housing_units"] >= self.config.min_housing_units]
            self._log_filter(
                "Min housing units",
                n_before,
                len(df),
                f">= {self.config.min_housing_units} total housing units",
            )
            n_before = len(df)

        # Min owner-occupied units
        if "owner_occupied_units" in df.columns:
            df = df[df["owner_occupied_units"] >= self.config.min_owner_occupied]
            self._log_filter(
                "Min OOU",
                n_before,
                len(df),
                f">= {self.config.min_owner_occupied} owner-occupied units",
            )
            n_before = len(df)

        # Max group quarters percentage
        if "group_quarters_pop" in df.columns and "population" in df.columns:
            df["group_quarters_pct"] = df["group_quarters_pop"] / df["population"]
            df = df[df["group_quarters_pct"] < self.config.max_group_quarters_pct]
            self._log_filter(
                "Max group quarters",
                n_before,
                len(df),
                f"< {self.config.max_group_quarters_pct * 100}% in group quarters",
            )

        return df

    def _apply_bandwidth_filter(self, df: pd.DataFrame, bandwidth: str) -> pd.DataFrame:
        """Apply RD bandwidth filter."""
        n_before = len(df)

        if "TM" not in df.columns:
            raise ValueError(
                "Census data must contain 'TM' column (tract MFI / MSA MFI)"
            )

        h = self.config.bandwidths.get(bandwidth, 0.05)
        lower = self.config.cutoff - h
        upper = self.config.cutoff + h

        df = df[(df["TM"] >= lower) & (df["TM"] <= upper)]
        self._log_filter(
            f"Bandwidth h={h}",
            n_before,
            len(df),
            f"TM in [{lower:.2f}, {upper:.2f}]",
        )

        return df

    def _merge_lending_data(
        self, df: pd.DataFrame, hmda_df: pd.DataFrame
    ) -> pd.DataFrame:
        """Merge HMDA lending data to census tracts."""
        n_before = len(df)

        # Create tract key for merging
        if "tract_key" not in df.columns:
            df["tract_key"] = (
                df["state_code"].astype(str).str.zfill(2)
                + df["county_code"].astype(str).str.zfill(3)
                + df["tract"].astype(str).str.zfill(6)
            )

        if "tract_key" not in hmda_df.columns:
            hmda_df = hmda_df.copy()
            hmda_df["tract_key"] = (
                hmda_df["state_code"].astype(str).str.zfill(2)
                + hmda_df["county_code"].astype(str).str.zfill(3)
                + hmda_df["tract"].astype(str).str.zfill(6)
            )

        # Aggregate HMDA to tract level if needed
        if "bank_originations" not in hmda_df.columns:
            hmda_agg = (
                hmda_df.groupby("tract_key")
                .agg(
                    bank_originations=("loan_amount", "count"),
                    total_loan_amount=("loan_amount", "sum"),
                )
                .reset_index()
            )
        else:
            hmda_agg = hmda_df[
                ["tract_key", "bank_originations", "total_loan_amount"]
            ].drop_duplicates()

        # Merge
        df = df.merge(hmda_agg, on="tract_key", how="left")

        # Fill missing with 0 (tracts with no loans)
        df["bank_originations"] = df["bank_originations"].fillna(0)
        df["total_loan_amount"] = df["total_loan_amount"].fillna(0)

        self._log_filter("Merge HMDA", n_before, len(df), "Left join on tract_key")

        return df

    def _apply_lending_filters(self, df: pd.DataFrame) -> pd.DataFrame:
        """Apply lending activity filters."""
        n_before = len(df)

        # Originations per owner-occupied unit
        if "owner_occupied_units" in df.columns and "bank_originations" in df.columns:
            df["orig_per_oou"] = df["bank_originations"] / df["owner_occupied_units"]

            df = df[
                (df["orig_per_oou"] >= self.config.min_orig_per_oou)
                & (df["orig_per_oou"] <= self.config.max_orig_per_oou)
            ]
            self._log_filter(
                "Lending activity",
                n_before,
                len(df),
                f"Orig/OOU in [{self.config.min_orig_per_oou}, {self.config.max_orig_per_oou}]",
            )

        return df

    def _classify_msa_size(
        self, df: pd.DataFrame, msa_pop_df: pd.DataFrame
    ) -> pd.DataFrame:
        """Classify MSAs by 1990 population size."""
        df = df.merge(
            msa_pop_df[["msa_code", "population_1990"]],
            on="msa_code",
            how="left",
        )

        def classify_size(pop):
            if pd.isna(pop):
                return "unknown"
            for size, (low, high) in self.config.msa_size_thresholds.items():
                if low <= pop < high:
                    return size
            return "unknown"

        df["msa_size"] = df["population_1990"].apply(classify_size)

        return df

    def _create_analysis_vars(self, df: pd.DataFrame) -> pd.DataFrame:
        """Create variables for RD analysis."""
        # Treatment indicator
        df["D"] = (df["TM"] < self.config.cutoff).astype(int)

        # Centered assignment variable
        df["TM_centered"] = df["TM"] - self.config.cutoff

        # Log outcome
        df["ln_bank_orig"] = np.log(df["bank_originations"].clip(lower=1))
        df["ln_loan_amount"] = np.log(df["total_loan_amount"].clip(lower=1))

        # Log controls
        if "total_housing_units" in df.columns:
            df["ln_housing_units"] = np.log(df["total_housing_units"].clip(lower=1))
        if "owner_occupied_units" in df.columns:
            df["ln_owner_occ"] = np.log(df["owner_occupied_units"].clip(lower=1))
        if "median_home_value" in df.columns:
            df["ln_home_value"] = np.log(df["median_home_value"].clip(lower=1))

        # Housing age proportions
        if "housing_pre1940" in df.columns and "total_housing_units" in df.columns:
            df["pct_pre1940"] = df["housing_pre1940"] / df["total_housing_units"]
        if "housing_1940_1969" in df.columns and "total_housing_units" in df.columns:
            df["pct_1940_1969"] = df["housing_1940_1969"] / df["total_housing_units"]

        # Race percentages
        if "black_pop" in df.columns and "population" in df.columns:
            df["pct_black"] = df["black_pop"] / df["population"] * 100
        if "hispanic_pop" in df.columns and "population" in df.columns:
            df["pct_hispanic"] = df["hispanic_pop"] / df["population"] * 100

        # Age percentage
        if "pop_65_over" in df.columns and "population" in df.columns:
            df["pct_65_over"] = df["pop_65_over"] / df["population"] * 100

        # Poverty rate
        if "poverty_pop" in df.columns and "poverty_universe" in df.columns:
            df["poverty_rate"] = df["poverty_pop"] / df["poverty_universe"]

        # Group quarters percentage
        if "group_quarters_pop" in df.columns and "population" in df.columns:
            df["pct_group_quarters"] = df["group_quarters_pop"] / df["population"] * 100

        # GSE goal indicator (TM <= 0.90)
        df["D_gse"] = (df["TM"] <= 0.90).astype(int)

        return df

    def get_filter_report(self) -> pd.DataFrame:
        """Return dataframe summarizing all filtering steps."""
        return pd.DataFrame(self.filter_log)

    def print_filter_report(self):
        """Print formatted filter report."""
        print("\n" + "=" * 80)
        print("SAMPLE CONSTRUCTION REPORT - Bhutta (2011) Specification")
        print("=" * 80)

        report = self.get_filter_report()
        for _, row in report.iterrows():
            print(f"\n{row['filter']}:")
            print(f"  Before: {row['before']:,}")
            print(f"  After:  {row['after']:,}")
            print(f"  Dropped: {row['dropped']:,} ({row['pct_dropped']:.1f}%)")
            if row["description"]:
                print(f"  Note: {row['description']}")

        print("\n" + "=" * 80)
        final = report.iloc[-1]
        print(f"FINAL SAMPLE SIZE: {final['after']:,} tracts")
        print("=" * 80)


def construct_bhutta_sample_from_files(
    census_dir: Path,
    hmda_path: Path,
    years: List[int] = None,
    bandwidth: str = "narrow",
    central_city_only: bool = False,
) -> pd.DataFrame:
    """
    Convenience function to construct Bhutta sample from file paths.

    Args:
        census_dir: Directory containing census parquet files
        hmda_path: Path to HMDA data file
        years: Years to include (default: 1994-2002)
        bandwidth: "narrow" or "wide"
        central_city_only: If True, restrict to central city tracts
                          WARNING: Bhutta does NOT use this filter

    Returns:
        Analysis-ready DataFrame
    """
    years = years or list(range(1994, 2003))

    # Load census data
    census_dfs = []
    for year in years:
        census_file = census_dir / f"census_{year}.parquet"
        if census_file.exists():
            df = pd.read_parquet(census_file)
            df["census_year"] = year
            census_dfs.append(df)

    if not census_dfs:
        raise FileNotFoundError(f"No census files found in {census_dir}")

    census_df = pd.concat(census_dfs, ignore_index=True)

    # Load HMDA data
    hmda_df = pd.read_parquet(hmda_path)

    # Configure and construct sample
    config = SampleConfig(central_city_only=central_city_only)
    constructor = BhuttaSampleConstructor(config)

    sample_df = constructor.construct_sample(
        census_df=census_df, hmda_df=hmda_df, bandwidth=bandwidth
    )

    constructor.print_filter_report()

    return sample_df
