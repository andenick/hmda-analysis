#!/usr/bin/env python3
"""
Streamlined HMDA Data Processor
Focused on processing sample data efficiently with comprehensive slicing
"""

import pandas as pd
import numpy as np
import logging
from pathlib import Path
import json
from datetime import datetime
from typing import Dict, List, Any
import warnings
import os
DATA_ROOT = Path(os.environ.get("DATA_ROOT", "data"))

warnings.filterwarnings('ignore')

class StreamlinedHMDAProcessor:
    """Streamlined processor for HMDA data with comprehensive slicing"""

    def __init__(self, base_path: str = str(DATA_ROOT)):
        self.base_path = Path(base_path)
        self.raw_data_path = self.base_path / "Technical" / "archive" / "new_input"
        self.output_path = self.base_path / "Output" / "Data" / "streamlined_analysis"
        self.output_path.mkdir(parents=True, exist_ok=True)

        # Configure logging
        log_file = self.output_path / f"streamlined_processing_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)

        self.logger.info("Streamlined HMDA Processor Initialized")

    def load_sample_data(self, sample_size: int = 100000) -> pd.DataFrame:
        """Load a sample of HMDA data for processing"""
        self.logger.info(f"Loading sample of {sample_size} rows from HMDA data...")

        # Find the HMDA file
        hmda_files = list(self.raw_data_path.glob("**/*2024_public_lar_csv.csv"))
        if not hmda_files:
            raise FileNotFoundError("No 2024 HMDA LAR file found")

        hmda_file = hmda_files[0]
        self.logger.info(f"Found HMDA file: {hmda_file}")

        # Read sample data
        data = pd.read_csv(hmda_file, nrows=sample_size, low_memory=False)
        self.logger.info(f"Loaded sample: {len(data)} rows, {len(data.columns)} columns")

        return self._clean_data(data)

    def _clean_data(self, data: pd.DataFrame) -> pd.DataFrame:
        """Clean and prepare data"""
        self.logger.info("Cleaning data...")

        # Replace common NA values
        na_values = ['NA', 'N/A', '', ' ', 'Exempt', '8888', '9999', '1111']
        data = data.replace(na_values, np.nan)

        # Convert key numeric columns
        numeric_cols = [
            'loan_amount', 'interest_rate', 'combined_loan_to_value_ratio',
            'rate_spread', 'total_loan_costs', 'origination_charges'
        ]

        for col in numeric_cols:
            if col in data.columns:
                data[col] = pd.to_numeric(data[col], errors='coerce')

        # Create FIPS code
        if 'state_code' in data.columns and 'county_code' in data.columns:
            data['fips'] = data['state_code'].astype(str).str.zfill(2) + data['county_code'].astype(str).str.zfill(3)

        # Clean categorical columns
        categorical_cols = ['derived_race', 'derived_ethnicity', 'derived_sex', 'action_taken']
        for col in categorical_cols:
            if col in data.columns:
                data[col] = data[col].astype(str).str.strip()
                data[col] = data[col].replace('nan', 'Unknown')

        return data

    def create_geographic_analysis(self, data: pd.DataFrame) -> Dict[str, pd.DataFrame]:
        """Create geographic analysis slices"""
        self.logger.info("Creating geographic analysis slices...")

        slices = {}

        # State-level analysis
        if 'state_code' in data.columns:
            state_analysis = data.groupby('state_code').agg({
                'loan_amount': ['count', 'sum', 'mean'],
                'action_taken': lambda x: (x == '1').mean(),  # Origination rate
                'derived_race': lambda x: (x != 'White').mean()  # Minority rate
            }).reset_index()
            state_analysis.columns = ['state_code', 'application_count', 'total_volume', 'avg_loan_size', 'origination_rate', 'minority_applicant_rate']
            slices['state_analysis'] = state_analysis

        # County-level analysis (sample due to potentially many counties)
        if 'fips' in data.columns:
            county_analysis = data.groupby('fips').agg({
                'loan_amount': ['count', 'sum', 'mean'],
                'action_taken': lambda x: (x == '1').mean(),
                'derived_race': lambda x: (x != 'White').mean()
            }).reset_index()
            county_analysis.columns = ['fips', 'application_count', 'total_volume', 'avg_loan_size', 'origination_rate', 'minority_applicant_rate']
            slices['county_analysis'] = county_analysis

        # MSA-level analysis
        if 'derived_msa_md' in data.columns:
            msa_analysis = data.groupby('derived_msa_md').agg({
                'loan_amount': ['count', 'sum', 'mean'],
                'action_taken': lambda x: (x == '1').mean(),
                'derived_race': lambda x: (x != 'White').mean()
            }).reset_index()
            msa_analysis.columns = ['msa_code', 'application_count', 'total_volume', 'avg_loan_size', 'origination_rate', 'minority_applicant_rate']
            slices['msa_analysis'] = msa_analysis

        return slices

    def create_demographic_analysis(self, data: pd.DataFrame) -> Dict[str, pd.DataFrame]:
        """Create demographic analysis slices"""
        self.logger.info("Creating demographic analysis slices...")

        slices = {}

        # Race-based analysis
        if 'derived_race' in data.columns:
            race_analysis = data.groupby('derived_race').agg({
                'loan_amount': ['count', 'sum', 'mean'],
                'action_taken': lambda x: (x == '1').mean()
            }).reset_index()
            race_analysis.columns = ['race', 'application_count', 'total_volume', 'avg_loan_size', 'origination_rate']
            slices['race_analysis'] = race_analysis

        # Ethnicity-based analysis
        if 'derived_ethnicity' in data.columns:
            ethnicity_analysis = data.groupby('derived_ethnicity').agg({
                'loan_amount': ['count', 'sum', 'mean'],
                'action_taken': lambda x: (x == '1').mean()
            }).reset_index()
            ethnicity_analysis.columns = ['ethnicity', 'application_count', 'total_volume', 'avg_loan_size', 'origination_rate']
            slices['ethnicity_analysis'] = ethnicity_analysis

        # Gender-based analysis
        if 'derived_sex' in data.columns:
            gender_analysis = data.groupby('derived_sex').agg({
                'loan_amount': ['count', 'sum', 'mean'],
                'action_taken': lambda x: (x == '1').mean()
            }).reset_index()
            gender_analysis.columns = ['gender', 'application_count', 'total_volume', 'avg_loan_size', 'origination_rate']
            slices['gender_analysis'] = gender_analysis

        # Cross-tabulation: Race x Ethnicity
        if 'derived_race' in data.columns and 'derived_ethnicity' in data.columns:
            cross_analysis = data.groupby(['derived_race', 'derived_ethnicity']).agg({
                'loan_amount': ['count', 'sum', 'mean'],
                'action_taken': lambda x: (x == '1').mean()
            }).reset_index()
            cross_analysis.columns = ['race', 'ethnicity', 'application_count', 'total_volume', 'avg_loan_size', 'origination_rate']
            slices['race_ethnicity_cross'] = cross_analysis

        return slices

    def create_loan_characteristics_analysis(self, data: pd.DataFrame) -> Dict[str, pd.DataFrame]:
        """Create loan characteristics analysis slices"""
        self.logger.info("Creating loan characteristics analysis slices...")

        slices = {}

        # Loan purpose analysis
        if 'loan_purpose' in data.columns:
            purpose_analysis = data.groupby('loan_purpose').agg({
                'loan_amount': ['count', 'sum', 'mean'],
                'action_taken': lambda x: (x == '1').mean()
            }).reset_index()
            purpose_analysis.columns = ['loan_purpose', 'application_count', 'total_volume', 'avg_loan_size', 'origination_rate']
            slices['loan_purpose_analysis'] = purpose_analysis

        # Loan type analysis
        if 'loan_type' in data.columns:
            type_analysis = data.groupby('loan_type').agg({
                'loan_amount': ['count', 'sum', 'mean'],
                'action_taken': lambda x: (x == '1').mean()
            }).reset_index()
            type_analysis.columns = ['loan_type', 'application_count', 'total_volume', 'avg_loan_size', 'origination_rate']
            slices['loan_type_analysis'] = type_analysis

        # Interest rate analysis (by quantiles)
        if 'interest_rate' in data.columns:
            rate_data = data['interest_rate'].fillna(0)
            if len(rate_data.unique()) > 1:
                try:
                    # Try to create quartiles
                    data['rate_quartile'] = pd.qcut(rate_data, q=4, duplicates='drop')
                    # Map quantile ranges to meaningful labels
                    rate_analysis = data.groupby('rate_quartile').agg({
                        'loan_amount': ['count', 'sum', 'mean'],
                        'action_taken': lambda x: (x == '1').mean(),
                        'derived_race': lambda x: (x != 'White').mean()
                    }).reset_index()
                    rate_analysis.columns = ['rate_quartile', 'application_count', 'total_volume', 'avg_loan_size', 'origination_rate', 'minority_rate']
                    slices['interest_rate_analysis'] = rate_analysis
                except ValueError:
                    # Fall back to simple categories if quartiles fail
                    data['rate_category'] = pd.cut(rate_data, bins=3, labels=['Low', 'Medium', 'High'])
                    rate_analysis = data.groupby('rate_category').agg({
                        'loan_amount': ['count', 'sum', 'mean'],
                        'action_taken': lambda x: (x == '1').mean(),
                        'derived_race': lambda x: (x != 'White').mean()
                    }).reset_index()
                    rate_analysis.columns = ['rate_category', 'application_count', 'total_volume', 'avg_loan_size', 'origination_rate', 'minority_rate']
                    slices['interest_rate_analysis'] = rate_analysis

        # LTV analysis
        if 'combined_loan_to_value_ratio' in data.columns:
            data['ltv_category'] = pd.cut(data['combined_loan_to_value_ratio'].fillna(0),
                                        bins=[0, 70, 80, 90, 100, float('inf')],
                                        labels=['Low LTV (<70%)', 'Moderate LTV (70-80%)', 'High LTV (80-90%)', 'Very High LTV (90-100%)', 'Underwater (>100%)'])
            ltv_analysis = data.groupby('ltv_category').agg({
                'loan_amount': ['count', 'sum', 'mean'],
                'action_taken': lambda x: (x == '1').mean(),
                'derived_race': lambda x: (x != 'White').mean()
            }).reset_index()
            ltv_analysis.columns = ['ltv_category', 'application_count', 'total_volume', 'avg_loan_size', 'origination_rate', 'minority_rate']
            slices['ltv_analysis'] = ltv_analysis

        return slices

    def create_institutional_analysis(self, data: pd.DataFrame) -> Dict[str, pd.DataFrame]:
        """Create institutional analysis slices"""
        self.logger.info("Creating institutional analysis slices...")

        slices = {}

        # Top lenders by volume
        if 'lei' in data.columns:
            lender_analysis = data.groupby('lei').agg({
                'loan_amount': ['count', 'sum', 'mean'],
                'action_taken': lambda x: (x == '1').mean()
            }).reset_index()
            lender_analysis.columns = ['lei', 'application_count', 'total_volume', 'avg_loan_size', 'origination_rate']
            lender_analysis = lender_analysis.sort_values('total_volume', ascending=False).head(50)
            slices['top_lenders'] = lender_analysis

        # Agency analysis
        if 'agency_code' in data.columns:
            agency_analysis = data.groupby('agency_code').agg({
                'loan_amount': ['count', 'sum', 'mean'],
                'action_taken': lambda x: (x == '1').mean(),
                'derived_race': lambda x: (x != 'White').mean()
            }).reset_index()
            agency_analysis.columns = ['agency_code', 'application_count', 'total_volume', 'avg_loan_size', 'origination_rate', 'minority_rate']
            slices['agency_analysis'] = agency_analysis

        return slices

    def create_disparity_analysis(self, data: pd.DataFrame) -> Dict[str, pd.DataFrame]:
        """Create disparity analysis slices"""
        self.logger.info("Creating disparity analysis slices...")

        slices = {}

        # Race-based disparity in loan amounts
        if 'derived_race' in data.columns and 'loan_amount' in data.columns:
            race_disparity = data.groupby('derived_race')['loan_amount'].describe().reset_index()
            slices['race_loan_amount_disparity'] = race_disparity

        # Approval rate disparity by race
        if 'derived_race' in data.columns and 'action_taken' in data.columns:
            approval_disparity = data.groupby('derived_race').agg({
                'action_taken': [('approved', lambda x: (x == '1').sum()),
                               ('total', 'count'),
                               ('approval_rate', lambda x: (x == '1').mean())]
            }).reset_index()
            approval_disparity.columns = ['race', 'approved_count', 'total_applications', 'approval_rate']
            slices['race_approval_disparity'] = approval_disparity

        # Interest rate disparity
        if 'derived_race' in data.columns and 'interest_rate' in data.columns:
            rate_disparity = data.groupby('derived_race')['interest_rate'].describe().reset_index()
            slices['race_interest_rate_disparity'] = rate_disparity

        # High-cost loan disparity
        if 'derived_race' in data.columns and 'interest_rate' in data.columns:
            data['high_cost'] = (data['interest_rate'] > data['interest_rate'].quantile(0.75)).astype(int)
            high_cost_disparity = data.groupby('derived_race')['high_cost'].mean().reset_index()
            high_cost_disparity.columns = ['race', 'high_cost_loan_rate']
            slices['high_cost_disparity'] = high_cost_disparity

        return slices

    def save_results(self, all_slices: Dict[str, Dict[str, pd.DataFrame]]) -> Dict[str, Any]:
        """Save all analysis results"""
        self.logger.info("Saving analysis results...")

        saved_files = {}
        total_slices = 0

        for category, slices in all_slices.items():
            category_files = {}
            for slice_name, data in slices.items():
                if not data.empty:
                    # Save as CSV
                    csv_file = self.output_path / f"{slice_name}.csv"
                    data.to_csv(csv_file, index=False)

                    # Save as Excel (single sheet per Nick's requirements)
                    excel_file = self.output_path / f"{slice_name}.xlsx"
                    data.to_excel(excel_file, index=False, sheet_name='Data')

                    category_files[slice_name] = {
                        'csv': str(csv_file),
                        'excel': str(excel_file),
                        'rows': len(data),
                        'columns': len(data.columns)
                    }
                    total_slices += 1

                    self.logger.info(f"Saved {slice_name}: {len(data)} rows, {len(data.columns)} columns")

            saved_files[category] = category_files

        # Save metadata
        metadata = {
            'processing_timestamp': datetime.now().isoformat(),
            'total_slices_saved': total_slices,
            'categories': list(saved_files.keys()),
            'files_saved': saved_files
        }

        metadata_file = self.output_path / "analysis_metadata.json"
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2, default=str)

        self.logger.info(f"Saved {total_slices} total analysis slices")
        return metadata

    def run_comprehensive_analysis(self, sample_size: int = 100000) -> Dict[str, Any]:
        """Run comprehensive HMDA analysis"""
        self.logger.info("Starting comprehensive HMDA analysis...")

        start_time = datetime.now()
        results = {
            'start_time': start_time,
            'sample_size': sample_size,
            'status': 'started'
        }

        try:
            # Load data
            data = self.load_sample_data(sample_size)
            results['data_loaded'] = len(data)

            # Run all analyses
            all_slices = {}

            # Geographic analysis
            all_slices['geographic'] = self.create_geographic_analysis(data)

            # Demographic analysis
            all_slices['demographic'] = self.create_demographic_analysis(data)

            # Loan characteristics analysis
            all_slices['loan_characteristics'] = self.create_loan_characteristics_analysis(data)

            # Institutional analysis
            all_slices['institutional'] = self.create_institutional_analysis(data)

            # Disparity analysis
            all_slices['disparity'] = self.create_disparity_analysis(data)

            # Save results
            metadata = self.save_results(all_slices)
            results['metadata'] = metadata

            # Generate summary
            summary = {
                'total_applications_analyzed': len(data),
                'total_loan_volume': data['loan_amount'].sum() if 'loan_amount' in data.columns else 0,
                'average_loan_size': data['loan_amount'].mean() if 'loan_amount' in data.columns else 0,
                'unique_states': data['state_code'].nunique() if 'state_code' in data.columns else 0,
                'unique_lenders': data['lei'].nunique() if 'lei' in data.columns else 0,
                'analysis_categories': len(all_slices),
                'total_slices_generated': metadata['total_slices_saved']
            }
            results['summary'] = summary

            end_time = datetime.now()
            results['end_time'] = end_time
            results['duration_seconds'] = (end_time - start_time).total_seconds()
            results['status'] = 'completed'

            self.logger.info(f"Analysis completed successfully in {results['duration_seconds']:.2f} seconds")
            self.logger.info(f"Generated {summary['total_slices_generated']} analysis slices from {len(data)} applications")

        except Exception as e:
            self.logger.error(f"Analysis failed: {str(e)}")
            results['status'] = 'failed'
            results['error'] = str(e)
            raise

        return results

def main():
    """Main execution function"""
    processor = StreamlinedHMDAProcessor()
    results = processor.run_comprehensive_analysis(sample_size=100000)

    print("\n" + "="*60)
    print("STREAMLINED HMDA ANALYSIS RESULTS")
    print("="*60)
    print(f"Status: {results['status']}")
    print(f"Applications analyzed: {results.get('data_loaded', 0):,}")
    print(f"Analysis categories: {results.get('summary', {}).get('analysis_categories', 0)}")
    print(f"Total slices generated: {results.get('summary', {}).get('total_slices_generated', 0)}")
    print(f"Processing time: {results.get('duration_seconds', 0):.2f} seconds")

    if results['status'] == 'completed':
        summary = results.get('summary', {})
        print(f"\nData Summary:")
        print(f"  Total loan volume: ${summary.get('total_loan_volume', 0):,.0f}")
        print(f"  Average loan size: ${summary.get('average_loan_size', 0):,.0f}")
        print(f"  Unique states: {summary.get('unique_states', 0)}")
        print(f"  Unique lenders: {summary.get('unique_lenders', 0)}")
        print(f"\nResults saved to: {processor.output_path}")

    return results

if __name__ == "__main__":
    main()