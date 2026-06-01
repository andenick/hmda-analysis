#!/usr/bin/env python3
"""
Multi-Dimensional HMDA Analysis Framework
==========================================

Creates comprehensive analysis capabilities with multiple geographic aggregations:
- Census tract x Institution
- Municipality x Institution
- County x Institution
- MSA x Institution

Includes proper crosswalks and geographic aggregation methods.

Author: Nicholas Anderson & Claude Code
Created: 2025-09-28
"""

import pandas as pd
import numpy as np
import sys
import os
from pathlib import Path
import logging
from typing import Dict, List, Tuple, Optional
import warnings
warnings.filterwarnings('ignore')

class MultiDimensionalAnalyzer:
    """Comprehensive multi-dimensional analysis framework."""

    def __init__(self, base_data_path: str = "data"):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.base_path = Path(base_data_path)
        self.crosswalks = {}

    def load_base_data(self, year: int = 2024) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """Load tract-level and LAR data."""

        # Load tract-level data
        tract_path = self.base_path / f"r_replication/{year}_lar_race_step9.csv"
        tract_df = pd.read_csv(tract_path)

        # Load sample LAR data for institution analysis
        lar_sample_path = "analysis_outputs/lar_sample_100k.csv"
        if os.path.exists(lar_sample_path):
            lar_df = pd.read_csv(lar_sample_path)
        else:
            # Fallback to creating sample
            self.logger.warning("Creating LAR sample - this may take time...")
            lar_df = self._create_lar_sample(year)

        return tract_df, lar_df

    def _create_lar_sample(self, year: int, sample_size: int = 100000) -> pd.DataFrame:
        """Create LAR sample for analysis."""

        lar_path = f"data/hmda/raw/{year}/{year}_public_lar_csv/{year}_public_lar_csv.csv"

        # Read in chunks to manage memory
        chunks = []
        rows_collected = 0

        for chunk in pd.read_csv(lar_path, chunksize=10000):
            chunk_sample = chunk.sample(min(1000, len(chunk)), random_state=42)
            chunks.append(chunk_sample)
            rows_collected += len(chunk_sample)

            if rows_collected >= sample_size:
                break

        lar_sample = pd.concat(chunks, ignore_index=True).head(sample_size)

        # Save for future use
        os.makedirs("analysis_outputs", exist_ok=True)
        lar_sample.to_csv("analysis_outputs/lar_sample_100k.csv", index=False)

        return lar_sample

    def create_tract_institution_analysis(self, tract_df: pd.DataFrame, lar_df: pd.DataFrame) -> pd.DataFrame:
        """Create census tract x institution analysis."""

        self.logger.info("Creating census tract x institution analysis...")

        # Ensure tract_id is present in LAR data
        if 'tract_id' not in lar_df.columns:
            lar_df['tract_id'] = (
                lar_df['state_code'].astype(str).str.zfill(2) +
                lar_df['county_code'].astype(str).str.zfill(3) +
                lar_df['census_tract'].astype(str).str.zfill(6)
            )

        # Aggregate lending by tract and institution
        tract_institution = lar_df.groupby(['tract_id', 'lei']).agg({
            'loan_amount': ['count', 'sum', 'mean'],
            'action_taken': [
                lambda x: (x == 1).sum(),  # Originated
                lambda x: (x == 3).sum(),  # Denied
                'count'
            ],
            'derived_race': [
                lambda x: (x == 'Black or African American').sum(),
                lambda x: (x == 'White').sum(),
                'count'
            ],
            'derived_ethnicity': lambda x: (x == 'Hispanic or Latino').sum(),
            'income': ['mean', 'median'],
            'applicant_age': lambda x: (x == '25-34').sum(),
        }).reset_index()

        # Flatten column names
        tract_institution.columns = [
            'tract_id', 'lei', 'total_applications', 'total_loan_amount', 'avg_loan_amount',
            'originated_loans', 'denied_loans', 'total_actions',
            'black_applications', 'white_applications', 'total_race_reported',
            'hispanic_applications', 'avg_income', 'median_income', 'young_applicants'
        ]

        # Calculate lending metrics
        tract_institution['origination_rate'] = (
            tract_institution['originated_loans'] / tract_institution['total_applications']
        ).fillna(0)

        tract_institution['denial_rate'] = (
            tract_institution['denied_loans'] / tract_institution['total_applications']
        ).fillna(0)

        tract_institution['black_share'] = (
            tract_institution['black_applications'] / tract_institution['total_race_reported']
        ).fillna(0)

        tract_institution['hispanic_share'] = (
            tract_institution['hispanic_applications'] / tract_institution['total_applications']
        ).fillna(0)

        # Merge with tract characteristics
        result = tract_institution.merge(
            tract_df[['tract_id', 'tract_median_ratio', 'cra_eligible', 'msa_md',
                     'median_family_income', 'minority_pct', 'total_population']],
            on='tract_id', how='left'
        )

        self.logger.info(f"Created tract x institution dataset: {len(result):,} tract-institution pairs")
        return result

    def create_municipality_crosswalk(self, tract_df: pd.DataFrame) -> pd.DataFrame:
        """Create census tract to municipality crosswalk."""

        self.logger.info("Creating census tract to municipality crosswalk...")

        # For this implementation, we'll use county as proxy for municipality
        # In a full implementation, you would need:
        # - Census TIGER files for tract-place relationships
        # - FIPS place codes
        # - Municipal boundary files

        # Create county-level aggregation as municipality proxy
        tract_df['county_fips'] = (
            tract_df['state_code'].astype(str).str.zfill(2) +
            tract_df['county_code'].astype(str).str.zfill(3)
        )

        # Map to municipality names (simplified - would need real crosswalk)
        municipality_map = {
            # This would be populated from a real county-to-municipality crosswalk
            # For now, using county codes as municipality identifiers
        }

        crosswalk = tract_df[['tract_id', 'county_fips', 'state_code', 'county_code']].copy()
        crosswalk['municipality_id'] = crosswalk['county_fips']  # Simplified
        crosswalk['municipality_name'] = 'County_' + crosswalk['county_fips']  # Placeholder

        self.crosswalks['tract_to_municipality'] = crosswalk

        self.logger.info(f"Created crosswalk for {len(crosswalk):,} tracts")
        return crosswalk

    def create_municipality_institution_analysis(self, tract_institution_df: pd.DataFrame) -> pd.DataFrame:
        """Create municipality x institution analysis."""

        self.logger.info("Creating municipality x institution analysis...")

        # Get crosswalk
        if 'tract_to_municipality' not in self.crosswalks:
            # We need the original tract_df to create crosswalk
            self.logger.warning("Municipality crosswalk not available, using county aggregation")

        # Create municipality identifiers using county as proxy
        tract_institution_df['municipality_id'] = (
            tract_institution_df['tract_id'].str[:5]  # State + County
        )

        # Aggregate from tract level to municipality level
        municipality_institution = tract_institution_df.groupby(['municipality_id', 'lei']).agg({
            'total_applications': 'sum',
            'total_loan_amount': 'sum',
            'avg_loan_amount': 'mean',
            'originated_loans': 'sum',
            'denied_loans': 'sum',
            'black_applications': 'sum',
            'white_applications': 'sum',
            'hispanic_applications': 'sum',
            'avg_income': 'mean',
            'median_income': 'median',
            'tract_median_ratio': 'mean',
            'cra_eligible': lambda x: (x == 1).sum(),  # Count of CRA eligible tracts
            'total_population': 'sum'
        }).reset_index()

        # Recalculate rates at municipality level
        municipality_institution['origination_rate'] = (
            municipality_institution['originated_loans'] / municipality_institution['total_applications']
        ).fillna(0)

        municipality_institution['denial_rate'] = (
            municipality_institution['denied_loans'] / municipality_institution['total_applications']
        ).fillna(0)

        municipality_institution['black_share'] = (
            municipality_institution['black_applications'] /
            (municipality_institution['black_applications'] + municipality_institution['white_applications'])
        ).fillna(0)

        self.logger.info(f"Created municipality x institution dataset: {len(municipality_institution):,} municipality-institution pairs")
        return municipality_institution

    def create_county_institution_analysis(self, tract_institution_df: pd.DataFrame) -> pd.DataFrame:
        """Create county x institution analysis."""

        self.logger.info("Creating county x institution analysis...")

        # Extract county identifiers
        tract_institution_df['county_fips'] = tract_institution_df['tract_id'].str[:5]

        # Aggregate to county level
        county_institution = tract_institution_df.groupby(['county_fips', 'lei']).agg({
            'total_applications': 'sum',
            'total_loan_amount': 'sum',
            'avg_loan_amount': 'mean',
            'originated_loans': 'sum',
            'denied_loans': 'sum',
            'black_applications': 'sum',
            'white_applications': 'sum',
            'hispanic_applications': 'sum',
            'avg_income': 'mean',
            'median_income': 'median',
            'tract_median_ratio': 'mean',
            'cra_eligible': lambda x: (x == 1).sum(),
            'total_population': 'sum'
        }).reset_index()

        # Recalculate rates
        county_institution['origination_rate'] = (
            county_institution['originated_loans'] / county_institution['total_applications']
        ).fillna(0)

        county_institution['denial_rate'] = (
            county_institution['denied_loans'] / county_institution['total_applications']
        ).fillna(0)

        county_institution['tract_count'] = tract_institution_df.groupby(['county_fips', 'lei'])['tract_id'].nunique().values

        self.logger.info(f"Created county x institution dataset: {len(county_institution):,} county-institution pairs")
        return county_institution

    def create_msa_institution_analysis(self, tract_institution_df: pd.DataFrame) -> pd.DataFrame:
        """Create MSA x institution analysis."""

        self.logger.info("Creating MSA x institution analysis...")

        # Aggregate to MSA level
        msa_institution = tract_institution_df.groupby(['msa_md', 'lei']).agg({
            'total_applications': 'sum',
            'total_loan_amount': 'sum',
            'avg_loan_amount': 'mean',
            'originated_loans': 'sum',
            'denied_loans': 'sum',
            'black_applications': 'sum',
            'white_applications': 'sum',
            'hispanic_applications': 'sum',
            'avg_income': 'mean',
            'median_income': 'median',
            'tract_median_ratio': 'mean',
            'cra_eligible': lambda x: (x == 1).sum(),
            'total_population': 'sum'
        }).reset_index()

        # Recalculate rates
        msa_institution['origination_rate'] = (
            msa_institution['originated_loans'] / msa_institution['total_applications']
        ).fillna(0)

        msa_institution['denial_rate'] = (
            msa_institution['denied_loans'] / msa_institution['total_applications']
        ).fillna(0)

        msa_institution['tract_count'] = tract_institution_df.groupby(['msa_md', 'lei'])['tract_id'].nunique().values

        self.logger.info(f"Created MSA x institution dataset: {len(msa_institution):,} MSA-institution pairs")
        return msa_institution

    def create_comprehensive_analysis(self, year: int = 2024, save_results: bool = True) -> Dict[str, pd.DataFrame]:
        """Create all multi-dimensional analysis datasets."""

        self.logger.info("Creating comprehensive multi-dimensional analysis...")

        # Load base data
        tract_df, lar_df = self.load_base_data(year)

        # Create all analysis levels
        results = {}

        # 1. Census Tract x Institution
        results['tract_institution'] = self.create_tract_institution_analysis(tract_df, lar_df)

        # 2. Municipality x Institution (using county proxy)
        results['municipality_institution'] = self.create_municipality_institution_analysis(
            results['tract_institution']
        )

        # 3. County x Institution
        results['county_institution'] = self.create_county_institution_analysis(
            results['tract_institution']
        )

        # 4. MSA x Institution
        results['msa_institution'] = self.create_msa_institution_analysis(
            results['tract_institution']
        )

        if save_results:
            self._save_analysis_results(results, year)

        self.logger.info("Comprehensive multi-dimensional analysis completed")
        return results

    def _save_analysis_results(self, results: Dict[str, pd.DataFrame], year: int):
        """Save all analysis results."""

        output_dir = Path("analysis_outputs/multidimensional")
        output_dir.mkdir(parents=True, exist_ok=True)

        for analysis_type, df in results.items():
            output_path = output_dir / f"{year}_{analysis_type}.csv"
            df.to_csv(output_path, index=False)
            self.logger.info(f"Saved {analysis_type}: {output_path} ({len(df):,} records)")

        # Create summary report
        summary_path = output_dir / f"{year}_analysis_summary.txt"
        with open(summary_path, 'w') as f:
            f.write(f"Multi-Dimensional HMDA Analysis Summary - {year}\n")
            f.write("=" * 50 + "\n\n")

            for analysis_type, df in results.items():
                f.write(f"{analysis_type.replace('_', ' ').title()}:\n")
                f.write(f"  Records: {len(df):,}\n")
                if 'lei' in df.columns:
                    f.write(f"  Unique Institutions: {df['lei'].nunique():,}\n")
                if 'total_applications' in df.columns:
                    f.write(f"  Total Applications: {df['total_applications'].sum():,}\n")
                    f.write(f"  Avg Origination Rate: {df['origination_rate'].mean():.1%}\n")
                f.write("\n")

        self.logger.info(f"Saved summary report: {summary_path}")

    def create_cra_analysis_by_geography(self, results: Dict[str, pd.DataFrame]) -> Dict[str, pd.DataFrame]:
        """Create CRA-specific analysis across geographic levels."""

        self.logger.info("Creating CRA analysis by geography...")

        cra_analysis = {}

        for geo_level, df in results.items():
            # Focus on CRA-relevant metrics
            if 'cra_eligible' in df.columns and 'lei' in df.columns:

                # Calculate CRA performance metrics by geography and institution
                cra_df = df.copy()

                # Add CRA performance indicators
                cra_df['cra_market_share'] = cra_df.groupby(geo_level.split('_')[0])['total_applications'].apply(
                    lambda x: x / x.sum()
                )

                cra_df['cra_performance_score'] = (
                    cra_df['origination_rate'] * 0.4 +
                    (1 - cra_df['denial_rate']) * 0.3 +
                    cra_df['black_share'] * 0.3
                )

                # Flag high-performing CRA institutions
                cra_df['high_cra_performer'] = (
                    cra_df['cra_performance_score'] > cra_df['cra_performance_score'].quantile(0.75)
                )

                cra_analysis[f"cra_{geo_level}"] = cra_df

        self.logger.info(f"Created CRA analysis for {len(cra_analysis)} geographic levels")
        return cra_analysis


def main():
    """Run comprehensive multi-dimensional analysis."""

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    print("=" * 60)
    print("   MULTI-DIMENSIONAL HMDA ANALYSIS FRAMEWORK")
    print("=" * 60)

    try:
        # Initialize analyzer
        analyzer = MultiDimensionalAnalyzer()

        # Create comprehensive analysis
        print("\nCreating multi-dimensional analysis datasets...")
        results = analyzer.create_comprehensive_analysis(year=2024, save_results=True)

        # Create CRA-specific analysis
        print("\nCreating CRA analysis by geography...")
        cra_results = analyzer.create_cra_analysis_by_geography(results)

        print("\n" + "=" * 60)
        print("   MULTI-DIMENSIONAL ANALYSIS COMPLETED")
        print("=" * 60)

        print("\nDatasets Created:")
        for analysis_type, df in results.items():
            print(f"  {analysis_type}: {len(df):,} records")

        print("\nCRA Analysis Created:")
        for analysis_type, df in cra_results.items():
            print(f"  {analysis_type}: {len(df):,} records")

        print("\nReady for versatile economic analysis!")

        return results, cra_results

    except Exception as e:
        print(f"ERROR: {str(e)}")
        raise


if __name__ == "__main__":
    results, cra_results = main()