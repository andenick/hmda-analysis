#!/usr/bin/env python3
"""
HMDA Dashboard Data Integration Script
====================================
Automatically updates the enhanced analysis files for the dashboard
after comprehensive processing completes.
"""

import pandas as pd
import numpy as np
from pathlib import Path
import logging
import json
from datetime import datetime
import time
import os
DATA_ROOT = Path(os.environ.get("DATA_ROOT", "data"))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class DashboardDataIntegrator:
    """Integrates comprehensive HMDA results into dashboard-ready formats"""

    def __init__(self):
        self.base_path = DATA_ROOT
        self.comprehensive_path = self.base_path / "Output/Data/comprehensive_hmda_results"
        self.enhanced_path = self.base_path / "Output/Data/enhanced_analysis"
        self.standardized_path = self.base_path / "Output/Data/standardized_datasets"

        # Ensure output directories exist
        self.enhanced_path.mkdir(parents=True, exist_ok=True)
        self.standardized_path.mkdir(parents=True, exist_ok=True)

    def check_comprehensive_processing_complete(self):
        """Check if all years have been processed"""
        logger.info("Checking comprehensive processing status...")

        expected_years = [2019, 2020, 2021, 2022, 2023, 2024]
        completed_years = []

        for year in expected_years:
            file_path = self.comprehensive_path / f"{year}_hmda_final_aggregated.csv"
            if file_path.exists():
                completed_years.append(year)
                logger.info(f"✅ {year}: Processing complete")
            else:
                logger.info(f"⏳ {year}: Processing pending")

        return completed_years

    def load_comprehensive_data(self, years):
        """Load all completed years of comprehensive data"""
        logger.info(f"Loading comprehensive data for years: {years}")

        all_data = []

        for year in years:
            file_path = self.comprehensive_path / f"{year}_hmda_final_aggregated.csv"
            try:
                df = pd.read_csv(file_path, low_memory=False)
                df['year'] = year  # Add year column
                all_data.append(df)
                logger.info(f"✅ Loaded {year}: {len(df):,} records")
            except Exception as e:
                logger.error(f"✗ Error loading {year}: {str(e)}")

        if all_data:
            combined_data = pd.concat(all_data, ignore_index=True)
            logger.info(f"✅ Combined data: {len(combined_data):,} total records")
            return combined_data
        else:
            logger.warning("⚠ No data loaded")
            return pd.DataFrame()

    def create_state_level_analysis(self, combined_data):
        """Create state-level analysis for dashboard"""
        logger.info("Creating state-level analysis...")

        if combined_data.empty:
            logger.warning("⚠ No data available for state analysis")
            return pd.DataFrame()

        # Aggregate by state
        state_analysis = combined_data.groupby(['state_code', 'state_name', 'year']).agg({
            'application_count': ['sum', 'count'],
            'loan_amount_sum': 'sum',
            'loan_amount_mean': 'mean',
            'origination_count': 'sum',
            'denial_count': 'sum',
            'institution_count': 'nunique'
        }).round(2)

        # Flatten column names
        state_analysis.columns = ['_'.join(col).strip() for col in state_analysis.columns]

        # Calculate rates
        state_analysis['origination_rate_mean'] = (
            state_analysis['origination_count_sum'] / state_analysis['application_count_sum'] * 100
        ).round(2)

        state_analysis['denial_rate_mean'] = (
            state_analysis['denial_count_sum'] / state_analysis['application_count_sum'] * 100
        ).round(2)

        # Add unique institution count
        state_analysis['institution_count'] = combined_data.groupby(['state_code', 'year'])['lei'].nunique().values

        # Reset index for cleaner output
        state_analysis = state_analysis.reset_index()

        # Reorder columns for clarity
        column_order = [
            'state_code', 'state_name', 'year',
            'application_count_sum', 'origination_count_sum', 'denial_count_sum',
            'origination_rate_mean', 'denial_rate_mean',
            'loan_amount_sum', 'loan_amount_mean', 'institution_count'
        ]

        # Filter to existing columns
        state_analysis = state_analysis[[col for col in column_order if col in state_analysis.columns]]

        logger.info(f"✅ State analysis created: {len(state_analysis):,} records")
        return state_analysis

    def create_county_level_analysis(self, combined_data):
        """Create county-level analysis for dashboard"""
        logger.info("Creating county-level analysis...")

        if combined_data.empty:
            logger.warning("⚠ No data available for county analysis")
            return pd.DataFrame()

        # Aggregate by county
        county_analysis = combined_data.groupby(['state_code', 'state_name', 'county_name', 'county_fips', 'year']).agg({
            'application_count': 'sum',
            'loan_amount_sum': 'sum',
            'loan_amount_mean': 'mean',
            'origination_count': 'sum',
            'denial_count': 'sum',
            'lei': 'nunique'
        }).round(2)

        # Calculate rates
        county_analysis['origination_rate_mean'] = (
            county_analysis['origination_count'] / county_analysis['application_count'] * 100
        ).round(2)

        county_analysis['denial_rate_mean'] = (
            county_analysis['denial_count'] / county_analysis['application_count'] * 100
        ).round(2)

        # Reset index and clean up
        county_analysis = county_analysis.reset_index()
        county_analysis['institution_count'] = county_analysis['lei']
        county_analysis = county_analysis.drop('lei', axis=1)

        logger.info(f"✅ County analysis created: {len(county_analysis):,} records")
        return county_analysis

    def create_demographic_analysis(self, combined_data):
        """Create demographic analysis by race and ethnicity"""
        logger.info("Creating demographic analysis...")

        if combined_data.empty:
            logger.warning("⚠ No data available for demographic analysis")
            return pd.DataFrame(), pd.DataFrame()

        # Race analysis
        race_analysis = combined_data.groupby(['derived_race', 'year']).agg({
            'application_count': 'sum',
            'loan_amount_sum': 'sum',
            'loan_amount_mean': 'mean',
            'origination_count': 'sum',
            'denial_count': 'sum'
        }).round(2)

        race_analysis['origination_rate_mean'] = (
            race_analysis['origination_count'] / race_analysis['application_count'] * 100
        ).round(2)

        race_analysis['denial_rate_mean'] = (
            race_analysis['denial_count'] / race_analysis['application_count'] * 100
        ).round(2)

        race_analysis = race_analysis.reset_index()

        # Ethnicity analysis
        ethnicity_analysis = combined_data.groupby(['derived_ethnicity', 'year']).agg({
            'application_count': 'sum',
            'loan_amount_sum': 'sum',
            'loan_amount_mean': 'mean',
            'origination_count': 'sum',
            'denial_count': 'sum'
        }).round(2)

        ethnicity_analysis['origination_rate_mean'] = (
            ethnicity_analysis['origination_count'] / ethnicity_analysis['application_count'] * 100
        ).round(2)

        ethnicity_analysis['denial_rate_mean'] = (
            ethnicity_analysis['denial_count'] / ethnicity_analysis['application_count'] * 100
        ).round(2)

        ethnicity_analysis = ethnicity_analysis.reset_index()

        logger.info(f"✅ Race analysis created: {len(race_analysis):,} records")
        logger.info(f"✅ Ethnicity analysis created: {len(ethnicity_analysis):,} records")

        return race_analysis, ethnicity_analysis

    def create_lender_rankings(self, combined_data):
        """Create lender rankings by state and nationally"""
        logger.info("Creating lender rankings...")

        if combined_data.empty:
            logger.warning("⚠ No data available for lender rankings")
            return pd.DataFrame()

        # National lender rankings
        national_rankings = combined_data.groupby(['lei', 'institution_name', 'year']).agg({
            'application_count': 'sum',
            'loan_amount_sum': 'sum',
            'loan_amount_mean': 'mean',
            'origination_count': 'sum',
            'denial_count': 'sum'
        }).round(2)

        national_rankings['origination_rate_mean'] = (
            national_rankings['origination_count'] / national_rankings['application_count'] * 100
        ).round(2)

        national_rankings = national_rankings.reset_index()
        national_rankings = national_rankings.sort_values(['year', 'application_count'], ascending=[True, False])

        # State-level lender rankings (top 10 per state)
        state_rankings = []
        for state in combined_data['state_code'].unique():
            state_data = combined_data[combined_data['state_code'] == state]

            state_leaders = state_data.groupby(['lei', 'institution_name', 'year']).agg({
                'application_count': 'sum',
                'loan_amount_sum': 'sum',
                'origination_count': 'sum'
            }).round(2)

            state_leaders['origination_rate_mean'] = (
                state_leaders['origination_count'] / state_leaders['application_count'] * 100
            ).round(2)

            state_leaders = state_leaders.reset_index()
            state_leaders['state_code'] = state
            state_leaders = state_leaders.nlargest(10, 'application_count')
            state_rankings.append(state_leaders)

        if state_rankings:
            state_lender_rankings = pd.concat(state_rankings, ignore_index=True)
        else:
            state_lender_rankings = pd.DataFrame()

        logger.info(f"✅ National lender rankings created: {len(national_rankings):,} records")
        logger.info(f"✅ State lender rankings created: {len(state_lender_rankings):,} records")

        # For dashboard, use state-level rankings
        return state_lender_rankings

    def save_enhanced_analysis(self, state_data, county_data, race_data, ethnicity_data, lender_data):
        """Save all enhanced analysis files"""
        logger.info("Saving enhanced analysis files...")

        files_saved = []

        # State level
        if not state_data.empty:
            state_file = self.enhanced_path / "state_level.csv"
            state_data.to_csv(state_file, index=False)
            files_saved.append(state_file)
            logger.info(f"✅ Saved: {state_file}")

        # County level
        if not county_data.empty:
            county_file = self.enhanced_path / "county_level.csv"
            county_data.to_csv(county_file, index=False)
            files_saved.append(county_file)
            logger.info(f"✅ Saved: {county_file}")

        # Race analysis
        if not race_data.empty:
            race_file = self.enhanced_path / "race_analysis.csv"
            race_data.to_csv(race_file, index=False)
            files_saved.append(race_file)
            logger.info(f"✅ Saved: {race_file}")

        # Ethnicity analysis
        if not ethnicity_data.empty:
            ethnicity_file = self.enhanced_path / "ethnicity_analysis.csv"
            ethnicity_data.to_csv(ethnicity_file, index=False)
            files_saved.append(ethnicity_file)
            logger.info(f"✅ Saved: {ethnicity_file}")

        # Lender rankings
        if not lender_data.empty:
            lender_file = self.enhanced_path / "lender_rankings.csv"
            lender_data.to_csv(lender_file, index=False)
            files_saved.append(lender_file)
            logger.info(f"✅ Saved: {lender_file}")

        return files_saved

    def create_metadata_summary(self, years, files_saved):
        """Create metadata summary of the integration process"""
        logger.info("Creating metadata summary...")

        metadata = {
            "integration_timestamp": datetime.now().isoformat(),
            "years_processed": years,
            "files_created": [str(f.relative_to(self.base_path)) for f in files_saved],
            "data_source": "HMDA Comprehensive Processing Results",
            "dashboard_ready": True,
            "version": "1.0.0"
        }

        metadata_file = self.enhanced_path / "integration_metadata.json"
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)

        logger.info(f"✅ Metadata saved: {metadata_file}")
        return metadata

    def run_integration(self):
        """Run the complete integration process"""
        logger.info("="*80)
        logger.info("HMDA DASHBOARD DATA INTEGRATION STARTING")
        logger.info("="*80)

        try:
            # Check processing status
            completed_years = self.check_comprehensive_processing_complete()

            if not completed_years:
                logger.error("✗ No years have been processed yet. Run comprehensive processor first.")
                return False

            logger.info(f"📊 Integrating data for {len(completed_years)} years: {completed_years}")

            # Load data
            combined_data = self.load_comprehensive_data(completed_years)

            if combined_data.empty:
                logger.error("✗ No data loaded. Aborting integration.")
                return False

            # Create analyses
            state_data = self.create_state_level_analysis(combined_data)
            county_data = self.create_county_level_analysis(combined_data)
            race_data, ethnicity_data = self.create_demographic_analysis(combined_data)
            lender_data = self.create_lender_rankings(combined_data)

            # Save files
            files_saved = self.save_enhanced_analysis(
                state_data, county_data, race_data, ethnicity_data, lender_data
            )

            # Create metadata
            metadata = self.create_metadata_summary(completed_years, files_saved)

            logger.info("="*80)
            logger.info("✅ INTEGRATION COMPLETED SUCCESSFULLY")
            logger.info("="*80)
            logger.info(f"📊 Years integrated: {completed_years}")
            logger.info(f"📁 Files created: {len(files_saved)}")
            logger.info(f"📈 Records processed: {len(combined_data):,}")
            logger.info("🚀 Dashboard is ready for deployment!")
            logger.info("="*80)

            return True

        except Exception as e:
            logger.error(f"✗ Integration failed: {str(e)}")
            logger.error("Please check the logs and try again.")
            return False

def main():
    """Main execution function"""
    integrator = DashboardDataIntegrator()

    # Monitor for new data and integrate when available
    while True:
        completed_years = integrator.check_comprehensive_processing_complete()

        # Check if new data is available that hasn't been integrated
        if len(completed_years) >= 1:  # At least 2019 should be complete
            try:
                success = integrator.run_integration()
                if success:
                    logger.info("🎉 Integration successful! Dashboard updated with latest data.")
                    break
                else:
                    logger.warning("Integration failed, will retry in 5 minutes...")
            except Exception as e:
                logger.error(f"Integration error: {str(e)}")

        logger.info("⏳ Waiting for comprehensive processing to complete...")
        time.sleep(300)  # Wait 5 minutes before checking again

if __name__ == "__main__":
    main()