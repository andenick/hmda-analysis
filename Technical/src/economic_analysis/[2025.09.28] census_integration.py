#!/usr/bin/env python3
"""
Census Integration Module for HMDA Economic Analysis Framework
============================================================

This module handles census data integration for economic analysis,
providing the critical tract-level variables needed for Bhutta replication
and regression discontinuity analysis.

Key Features:
- Census data loading and validation
- HMDA-census joining with proper key matching
- Tract median ratio calculation for RD analysis
- Group quarters and housing unit filtering variables
- Support for historical and modern data formats

Author: Nicholas Anderson & Claude Code
Created: 2025-09-28
"""

import os
import sys
from pathlib import Path
from typing import Dict, List, Optional, Union, Tuple
import logging

import pandas as pd
import numpy as np


class CensusIntegrator:
    """
    Census data integration for HMDA economic analysis.

    Handles loading, joining, and enriching HMDA data with census tract
    characteristics required for regression discontinuity analysis.
    """

    def __init__(self,
                 data_path: str = "data",
                 output_path: str = "analysis_outputs",
                 log_level: str = "INFO"):
        """
        Initialize Census Integrator.

        Args:
            data_path: Base data directory path
            output_path: Output directory for enriched data
            log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
        """
        self.data_path = Path(data_path)
        self.output_path = Path(output_path)

        # Setup logging
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.setLevel(getattr(logging, log_level.upper()))

        # Ensure output directory exists
        self.output_path.mkdir(parents=True, exist_ok=True)

        self.logger.info("Census Integrator initialized")
        self.logger.info(f"Data path: {self.data_path}")
        self.logger.info(f"Output path: {self.output_path}")

    def load_census_data(self, year: int) -> pd.DataFrame:
        """
        Load census data for specified year.

        Args:
            year: Census data year

        Returns:
            DataFrame with census tract characteristics
        """
        self.logger.info(f"Loading census data for year {year}")

        # Try multiple potential census file locations
        census_paths = [
            self.data_path / "census" / f"census_data_{year}.parquet",
            self.data_path / "census" / f"census_data_{year}.csv",
            self.data_path / "raw" / "census" / f"census_{year}.dat",
        ]

        census_df = None
        for path in census_paths:
            if path.exists():
                self.logger.info(f"Found census file: {path}")

                if path.suffix == ".parquet":
                    census_df = pd.read_parquet(path)
                elif path.suffix == ".csv":
                    census_df = pd.read_csv(path)
                else:
                    self.logger.warning(f"Unsupported census file format: {path}")
                    continue

                break

        if census_df is None:
            raise FileNotFoundError(f"No census data found for year {year}")

        self.logger.info(f"Loaded census data: {len(census_df):,} records")
        return census_df

    def load_hmda_data(self, year: int, step: str = "step9") -> pd.DataFrame:
        """
        Load HMDA data for specified year and processing step.

        Args:
            year: HMDA data year
            step: Processing step (step9, raw, etc.)

        Returns:
            DataFrame with HMDA loan records
        """
        self.logger.info(f"Loading HMDA data for year {year}, step {step}")

        # Try multiple potential HMDA file locations
        hmda_paths = [
            self.data_path / "r_replication" / f"{year}_lar_race_{step}.csv",
            self.data_path / "hmda" / "processed" / f"{year}_lar_race_{step}.csv",
            self.data_path / "hmda" / "raw" / f"{year}" / "2024_public_lar_csv" / "2024_public_lar_csv.csv",
        ]

        # For 2024, use the new format
        if year == 2024:
            hmda_paths.insert(0,
                self.data_path / "hmda" / "raw" / "2024" / "2024_public_lar_csv" / "2024_public_lar_csv.csv"
            )

        hmda_df = None
        for path in hmda_paths:
            if path.exists():
                self.logger.info(f"Found HMDA file: {path}")
                hmda_df = pd.read_csv(path)
                break

        if hmda_df is None:
            raise FileNotFoundError(f"No HMDA data found for year {year}")

        self.logger.info(f"Loaded HMDA data: {len(hmda_df):,} records")
        return hmda_df

    def extract_tract_info(self, hmda_df: pd.DataFrame, year: int) -> pd.DataFrame:
        """
        Extract tract-level information from HMDA data.

        Modern HMDA data (2018+) includes tract characteristics directly.
        Historical data requires separate census joining.

        Args:
            hmda_df: HMDA loan application records
            year: Data year

        Returns:
            DataFrame with tract-level aggregated data
        """
        self.logger.info(f"Extracting tract-level information for year {year}")

        # Check if modern format with built-in tract variables
        modern_tract_cols = [
            'tract_to_msa_income_percentage',
            'tract_population',
            'tract_minority_population_percent',
            'ffiec_msa_md_median_family_income',
            'tract_owner_occupied_units',
            'tract_one_to_four_family_homes'
        ]

        has_modern_format = all(col in hmda_df.columns for col in modern_tract_cols)

        if has_modern_format and year >= 2018:
            self.logger.info("Using modern HMDA format with embedded tract characteristics")
            return self._extract_modern_tract_info(hmda_df)
        else:
            self.logger.info("Using historical format - requires census joining")
            return self._extract_historical_tract_info(hmda_df, year)

    def _extract_modern_tract_info(self, hmda_df: pd.DataFrame) -> pd.DataFrame:
        """Extract tract info from modern HMDA format (2018+)."""

        # Create tract identifier
        hmda_df['tract_id'] = (
            hmda_df['state_code'].astype(str).str.zfill(2) +
            hmda_df['county_code'].astype(str).str.zfill(3) +
            hmda_df['census_tract'].astype(str).str.zfill(6)
        )

        # Aggregate to tract level for economic analysis
        tract_cols = [
            'tract_id', 'state_code', 'county_code', 'census_tract',
            'derived_msa_md', 'tract_to_msa_income_percentage',
            'tract_population', 'tract_minority_population_percent',
            'ffiec_msa_md_median_family_income', 'tract_owner_occupied_units',
            'tract_one_to_four_family_homes', 'tract_median_age_of_housing_units'
        ]

        # Keep only available columns
        available_cols = [col for col in tract_cols if col in hmda_df.columns]

        # Aggregate to tract level (take first non-null value for tract characteristics)
        tract_df = hmda_df[available_cols].groupby('tract_id').first().reset_index()

        # Calculate key variables for regression discontinuity
        tract_df['tract_median_ratio'] = tract_df['tract_to_msa_income_percentage'] / 100.0
        tract_df['msa_md'] = tract_df['derived_msa_md']
        tract_df['median_family_income'] = tract_df['ffiec_msa_md_median_family_income']
        tract_df['minority_pct'] = tract_df['tract_minority_population_percent'] / 100.0
        tract_df['total_housing_units'] = tract_df['tract_one_to_four_family_homes']
        tract_df['total_population'] = tract_df['tract_population']

        # Estimate group quarters percentage (not directly available in modern format)
        # Use housing occupancy as proxy: occupied / (occupied + vacant) approximation
        if 'tract_owner_occupied_units' in tract_df.columns and 'tract_one_to_four_family_homes' in tract_df.columns:
            tract_df['group_quarters_pct'] = 1.0 - (
                tract_df['tract_owner_occupied_units'] /
                tract_df['tract_one_to_four_family_homes'].replace(0, np.nan)
            )
            tract_df['group_quarters_pct'] = tract_df['group_quarters_pct'].fillna(0).clip(0, 1)
        else:
            self.logger.warning("Cannot calculate group_quarters_pct - using default 0.1")
            tract_df['group_quarters_pct'] = 0.1

        self.logger.info(f"Extracted {len(tract_df):,} tracts with modern format")
        return tract_df

    def _extract_historical_tract_info(self, hmda_df: pd.DataFrame, year: int) -> pd.DataFrame:
        """Extract tract info from historical HMDA format (pre-2018)."""

        # Load corresponding census data
        census_df = self.load_census_data(year)

        # Create tract identifiers for joining
        if 'census_tract' in hmda_df.columns:
            hmda_df['tract_id'] = (
                hmda_df['state_code'].astype(str).str.zfill(2) +
                hmda_df['county_code'].astype(str).str.zfill(3) +
                hmda_df['census_tract'].astype(str).str.zfill(6)
            )
        else:
            # Handle older format variations
            hmda_df['tract_id'] = (
                hmda_df['fips'].astype(str).str.zfill(5) +
                hmda_df.get('tract', hmda_df.get('census_tract_number', '000000')).astype(str).str.zfill(6)
            )

        # Prepare census data for joining
        census_df = self._prepare_census_for_joining(census_df, year)

        # Join HMDA with census
        hmda_with_census = hmda_df.merge(
            census_df,
            on='tract_id',
            how='left'
        )

        # Aggregate to tract level
        tract_df = self._aggregate_to_tract_level(hmda_with_census)

        self.logger.info(f"Extracted {len(tract_df):,} tracts with historical format")
        return tract_df

    def _prepare_census_for_joining(self, census_df: pd.DataFrame, year: int) -> pd.DataFrame:
        """Prepare census data for joining with HMDA data."""

        # Standardize column names based on census year format
        if year <= 2010:
            # Older census format
            tract_id_cols = ['state', 'county', 'tract']
        else:
            # Newer census format
            tract_id_cols = ['State', 'County', 'Tract']

        # Create standardized tract identifier
        if all(col in census_df.columns for col in tract_id_cols):
            census_df['tract_id'] = (
                census_df[tract_id_cols[0]].astype(str).str.zfill(2) +
                census_df[tract_id_cols[1]].astype(str).str.zfill(3) +
                census_df[tract_id_cols[2]].astype(str).str.zfill(6)
            )

        # Standardize key variable names
        column_mapping = {
            'MSA_MD': 'msa_md',
            'Tract Median Family Income': 'tract_median_income',
            'MSA/MD Median Family Income': 'msa_median_income',
            'Tract to MSA/MD Income %': 'tract_median_ratio',
            'Total Population': 'total_population',
            'Minority Population %': 'minority_pct',
            'Total Housing Units': 'total_housing_units',
            'Owner Occupied Units': 'owner_occupied_units',
            'Group Quarters %': 'group_quarters_pct'
        }

        for old_name, new_name in column_mapping.items():
            if old_name in census_df.columns:
                census_df[new_name] = census_df[old_name]

        # Calculate tract median ratio if not directly available
        if 'tract_median_ratio' not in census_df.columns:
            if 'tract_median_income' in census_df.columns and 'msa_median_income' in census_df.columns:
                census_df['tract_median_ratio'] = (
                    census_df['tract_median_income'] /
                    census_df['msa_median_income'].replace(0, np.nan)
                )

        # Estimate group quarters if not available
        if 'group_quarters_pct' not in census_df.columns:
            if 'owner_occupied_units' in census_df.columns and 'total_housing_units' in census_df.columns:
                census_df['group_quarters_pct'] = 1.0 - (
                    census_df['owner_occupied_units'] /
                    census_df['total_housing_units'].replace(0, np.nan)
                )
                census_df['group_quarters_pct'] = census_df['group_quarters_pct'].fillna(0.1).clip(0, 1)

        return census_df

    def _aggregate_to_tract_level(self, hmda_with_census: pd.DataFrame) -> pd.DataFrame:
        """Aggregate HMDA-census joined data to tract level."""

        # Group by tract and aggregate
        agg_dict = {}

        # Tract characteristics (take first non-null)
        tract_char_cols = [
            'tract_median_ratio', 'msa_md', 'median_family_income',
            'total_population', 'minority_pct', 'total_housing_units',
            'group_quarters_pct', 'owner_occupied_units'
        ]

        for col in tract_char_cols:
            if col in hmda_with_census.columns:
                agg_dict[col] = 'first'

        # Lending activity (sum)
        lending_cols = [col for col in hmda_with_census.columns if 'HL_' in col or 'loan' in col.lower()]
        for col in lending_cols:
            agg_dict[col] = 'sum'

        # Aggregate
        tract_df = hmda_with_census.groupby('tract_id').agg(agg_dict).reset_index()

        return tract_df

    def create_analysis_ready_dataset(self, year: int, save: bool = True) -> pd.DataFrame:
        """
        Create analysis-ready dataset with HMDA and census data joined.

        Args:
            year: Data year to process
            save: Whether to save the result to file

        Returns:
            DataFrame ready for economic analysis
        """
        self.logger.info(f"Creating analysis-ready dataset for year {year}")

        # Load HMDA data
        hmda_df = self.load_hmda_data(year)

        # Extract tract-level information
        tract_df = self.extract_tract_info(hmda_df, year)

        # Validate required variables for regression discontinuity
        required_vars = [
            'tract_median_ratio', 'msa_md', 'total_housing_units', 'group_quarters_pct'
        ]

        missing_vars = [var for var in required_vars if var not in tract_df.columns]
        if missing_vars:
            self.logger.warning(f"Missing required variables: {missing_vars}")

        # Add analysis variables
        tract_df['year'] = year
        tract_df['cra_eligible'] = (tract_df['tract_median_ratio'] < 0.80).astype(int)
        tract_df['tmr_centered'] = tract_df['tract_median_ratio'] - 0.80

        # Data quality checks
        self.logger.info("Performing data quality checks...")

        # Check tract median ratio distribution
        tmr_stats = tract_df['tract_median_ratio'].describe()
        self.logger.info(f"Tract median ratio stats: min={tmr_stats['min']:.3f}, "
                        f"max={tmr_stats['max']:.3f}, mean={tmr_stats['mean']:.3f}")

        # Check around RD cutoff
        around_cutoff = tract_df[
            (tract_df['tract_median_ratio'] >= 0.75) &
            (tract_df['tract_median_ratio'] <= 0.85)
        ]
        self.logger.info(f"Tracts around 80% cutoff (75%-85%): {len(around_cutoff):,}")

        # Check group quarters filtering
        if 'group_quarters_pct' in tract_df.columns:
            gq_high = (tract_df['group_quarters_pct'] > 0.30).sum()
            self.logger.info(f"Tracts with >30% group quarters: {gq_high:,} "
                           f"({gq_high/len(tract_df)*100:.1f}%)")

        if save:
            output_file = self.output_path / f"analysis_ready_{year}.csv"
            tract_df.to_csv(output_file, index=False)
            self.logger.info(f"Saved analysis-ready dataset: {output_file}")

        self.logger.info(f"Analysis-ready dataset created: {len(tract_df):,} tracts")
        return tract_df

    def create_multi_year_dataset(self, years: List[int], save: bool = True) -> pd.DataFrame:
        """
        Create multi-year analysis dataset.

        Args:
            years: List of years to include
            save: Whether to save the result

        Returns:
            Combined multi-year DataFrame
        """
        self.logger.info(f"Creating multi-year dataset for years: {years}")

        datasets = []
        for year in years:
            try:
                df = self.create_analysis_ready_dataset(year, save=False)
                datasets.append(df)
                self.logger.info(f"Successfully processed year {year}")
            except Exception as e:
                self.logger.error(f"Failed to process year {year}: {e}")
                continue

        if not datasets:
            raise ValueError("No datasets successfully created")

        # Combine all years
        combined_df = pd.concat(datasets, ignore_index=True)

        if save:
            output_file = self.output_path / f"analysis_ready_multi_year_{min(years)}_{max(years)}.csv"
            combined_df.to_csv(output_file, index=False)
            self.logger.info(f"Saved multi-year dataset: {output_file}")

        self.logger.info(f"Multi-year dataset created: {len(combined_df):,} tract-years")
        return combined_df

    def validate_for_bhutta_replication(self, df: pd.DataFrame) -> Dict[str, bool]:
        """
        Validate dataset for Bhutta replication requirements.

        Args:
            df: Analysis dataset to validate

        Returns:
            Dictionary of validation results
        """
        self.logger.info("Validating dataset for Bhutta replication")

        validation = {}

        # Required variables
        required_vars = [
            'tract_median_ratio', 'msa_md', 'total_housing_units',
            'group_quarters_pct', 'cra_eligible', 'year'
        ]

        for var in required_vars:
            validation[f"has_{var}"] = var in df.columns
            if not validation[f"has_{var}"]:
                self.logger.error(f"Missing required variable: {var}")

        # Data quality checks
        if 'tract_median_ratio' in df.columns:
            tmr_valid = (
                (df['tract_median_ratio'] >= 0.1) &
                (df['tract_median_ratio'] <= 3.0)
            ).all()
            validation['tract_median_ratio_valid'] = tmr_valid

            # Check RD sample around cutoff
            around_cutoff = df[
                (df['tract_median_ratio'] >= 0.75) &
                (df['tract_median_ratio'] <= 0.85)
            ]
            validation['sufficient_rd_sample'] = len(around_cutoff) >= 100

            self.logger.info(f"RD sample around cutoff: {len(around_cutoff):,} tracts")

        # Group quarters availability for Bhutta filtering
        if 'group_quarters_pct' in df.columns:
            gq_variation = df['group_quarters_pct'].std() > 0.01
            validation['group_quarters_variation'] = gq_variation

            # Bhutta filter impact
            before_filter = len(df)
            after_filter = len(df[df['group_quarters_pct'] <= 0.30])
            filter_impact = (before_filter - after_filter) / before_filter
            validation['bhutta_filter_impact'] = filter_impact > 0.1

            self.logger.info(f"Bhutta group quarters filter impact: {filter_impact:.1%}")

        # Overall validation
        validation['ready_for_analysis'] = all([
            validation.get('has_tract_median_ratio', False),
            validation.get('has_msa_md', False),
            validation.get('has_group_quarters_pct', False),
            validation.get('sufficient_rd_sample', False)
        ])

        if validation['ready_for_analysis']:
            self.logger.info("Dataset validated successfully for Bhutta replication")
        else:
            self.logger.warning("Dataset validation failed - missing requirements")

        return validation


def main():
    """Demonstration of census integration capabilities."""

    # Initialize integrator
    integrator = CensusIntegrator()

    # Available years
    available_years = [2019, 2020, 2021, 2022, 2023, 2024]

    print("Census Integration Module Demonstration")
    print("=====================================")

    # Test with available data
    for year in available_years:
        try:
            print(f"\nProcessing year {year}...")
            dataset = integrator.create_analysis_ready_dataset(year)

            # Validate for Bhutta replication
            validation = integrator.validate_for_bhutta_replication(dataset)

            print(f"Year {year}: {len(dataset):,} tracts")
            print(f"Ready for analysis: {validation['ready_for_analysis']}")

        except FileNotFoundError as e:
            print(f"Year {year}: Data not available")
        except Exception as e:
            print(f"Year {year}: Error - {str(e)}")

    # Create multi-year dataset with available data
    try:
        available = [year for year in available_years if year in [2019, 2024]]  # Known available
        if available:
            print(f"\nCreating multi-year dataset for years: {available}")
            multi_year = integrator.create_multi_year_dataset(available)
            print(f"Multi-year dataset: {len(multi_year):,} tract-years")
    except Exception as e:
        print(f"Multi-year creation failed: {e}")


if __name__ == "__main__":
    main()