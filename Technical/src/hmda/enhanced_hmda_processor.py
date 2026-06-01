#!/usr/bin/env python3
"""
Enhanced HMDA Data Processor
Comprehensive processing pipeline replicating and extending R methodology
Processes raw HMDA data "every which way" with multi-dimensional analysis
"""

import pandas as pd
import numpy as np
import logging
from pathlib import Path
import json
from datetime import datetime
from typing import Dict, List, Any, Tuple, Optional
import warnings
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor
import gc
import os
DATA_ROOT = Path(os.environ.get("DATA_ROOT", "data"))

warnings.filterwarnings('ignore')

@dataclass
class ProcessingConfig:
    """Configuration for HMDA data processing"""
    base_path: str = str(DATA_ROOT)
    chunk_size: int = 100000
    memory_limit_gb: float = 8.0
    output_format: str = "both"  # csv, excel, both
    include_derived_vars: bool = True
    enable_parallel: bool = True

class EnhancedHMDAProcessor:
    """
    Enhanced HMDA processor implementing R methodology replication
    with comprehensive slicing and dicing capabilities
    """

    def __init__(self, config: ProcessingConfig = None):
        self.config = config or ProcessingConfig()
        self.base_path = Path(self.config.base_path)

        # Setup paths
        self.raw_data_path = self.base_path / "Technical" / "archive" / "new_input"
        self.output_path = self.base_path / "Output" / "Data" / "enhanced_analysis"
        self.output_path.mkdir(parents=True, exist_ok=True)

        # Configure logging
        log_file = self.output_path / f"processing_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)

        self.logger.info("Enhanced HMDA Processor Initialized")
        self.logger.info(f"Configuration: {self.config}")

        # Initialize data structures
        self.raw_data = {}
        self.processed_data = {}
        self.metadata = {}

        # Define analysis columns (based on R methodology)
        self.sum_columns = [
            'loan_amount', 'combined_loan_to_value_ratio', 'interest_rate',
            'total_loan_costs', 'total_points_and_fees', 'origination_charges',
            'discount_points', 'lender_credits', 'loan_term', 'loan_to_value_ratio',
            'intro_rate_period', 'property_value', 'multifamily_affordable_units',
            'debt_to_income_ratio', 'loan_credit_score_type', 'co_applicant_credit_score_type'
        ]

        self.categorical_columns = [
            'activity_year', 'state_code', 'county_code', 'census_tract',
            'derived_ethnicity', 'derived_race', 'derived_sex', 'action_taken',
            'purchaser_type', 'preapproval', 'loan_type', 'loan_purpose',
            'lien_status', 'reverse_mortgage', 'open_end_line_of_credit',
            'business_or_commercial_purpose', 'hoepa_status'
        ]

    def load_raw_data(self, year: int = 2024) -> pd.DataFrame:
        """
        Load raw HMDA data with memory-efficient chunking
        Replicates R data loading methodology
        """
        self.logger.info(f"Loading {year} HMDA LAR data...")

        # Find the HMDA file
        hmda_files = list(self.raw_data_path.glob(f"**/*{year}_public_lar_csv.csv"))
        if not hmda_files:
            raise FileNotFoundError(f"No HMDA LAR file found for year {year}")

        hmda_file = hmda_files[0]
        self.logger.info(f"Found HMDA file: {hmda_file}")

        # Load data in chunks for memory efficiency
        chunks = []
        chunk_iter = pd.read_csv(hmda_file, chunksize=self.config.chunk_size, low_memory=False)

        total_rows = 0
        for i, chunk in enumerate(chunk_iter):
            self.logger.info(f"Processing chunk {i+1} ({len(chunk)} rows)")

            # Basic cleaning and type conversion
            chunk = self._clean_chunk(chunk)
            chunks.append(chunk)
            total_rows += len(chunk)

            # Memory management
            if len(chunks) >= 10:  # Process in batches of 10 chunks
                combined_chunk = pd.concat(chunks, ignore_index=True)
                self._process_chunk_batch(combined_chunk, f"batch_{i//10}")
                chunks = []
                gc.collect()

        # Process any remaining chunks
        if chunks:
            combined_chunk = pd.concat(chunks, ignore_index=True)
            self._process_chunk_batch(combined_chunk, f"batch_final")
            gc.collect()

        # Combine all processed intermediate files
        self.logger.info("Combining all processed batches...")
        intermediate_files = sorted(list(self.output_path.glob("intermediate_*.csv")))
        
        if not intermediate_files:
            self.logger.warning("No intermediate files were generated.")
            return pd.DataFrame()

        df_list = []
        for f in intermediate_files:
            self.logger.info(f"Reading batch file: {f.name}")
            df_list.append(pd.read_csv(f, low_memory=False))
            f.unlink() # Delete intermediate file

        final_data = pd.concat(df_list, ignore_index=True)
        self.logger.info(f"Successfully combined {len(intermediate_files)} batches into a single dataframe with {len(final_data)} rows.")

        self.logger.info(f"Loaded and processed {total_rows} total rows from {year} HMDA data")
        self.raw_data[year] = final_data

        return final_data

    def _clean_chunk(self, chunk: pd.DataFrame) -> pd.DataFrame:
        """Clean and standardize data chunk"""
        # Replace common NA values
        na_values = ['NA', 'N/A', '', ' ', 'Exempt', '8888', '9999', '1111']
        chunk = chunk.replace(na_values, np.nan)

        # Convert numeric columns with better error handling
        for col in self.sum_columns:
            if col in chunk.columns:
                # First convert to string to clean, then to numeric
                chunk[col] = chunk[col].astype(str).str.replace(',', '').str.replace('$', '').str.strip()
                chunk[col] = pd.to_numeric(chunk[col], errors='coerce')

        # Handle problematic columns specifically
        problematic_cols = ['rate_spread', 'interest_rate', 'combined_loan_to_value_ratio']
        for col in problematic_cols:
            if col in chunk.columns:
                chunk[col] = chunk[col].astype(str).str.replace('NA', '').str.replace('Exempt', '').str.strip()
                chunk[col] = pd.to_numeric(chunk[col], errors='coerce')

        # Standardize categorical columns
        for col in self.categorical_columns:
            if col in chunk.columns:
                chunk[col] = chunk[col].astype(str).str.strip()
                chunk[col] = chunk[col].replace('nan', np.nan)

        return chunk

    def _process_chunk_batch(self, chunk: pd.DataFrame, batch_name: str):
        """Process a batch of chunks and save intermediate results"""
        self.logger.info(f"Processing batch {batch_name}")

        # Apply basic aggregations
        processed = self._apply_r_methodology(chunk)

        # Save intermediate results using CSV to avoid type issues
        output_file = self.output_path / f"intermediate_{batch_name}.csv"
        processed.to_csv(output_file, index=False)

        self.logger.info(f"Saved intermediate batch: {output_file}")

    def _apply_r_methodology(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Apply R methodology replicating original analysis
        Based on CRA_HMDAProcessing23_NA.Rmd functions
        """
        # Create derived variables (replicating R binary indicators)
        data = self._create_derived_variables(data)

        # Apply geographic aggregations (replicating sum_columns function)
        data = self._apply_geographic_aggregations(data)

        # Apply income categorization
        data = self._categorize_income_levels(data)

        # Apply loan status categorization
        data = self._categorize_loan_status(data)

        return data

    def _create_derived_variables(self, data: pd.DataFrame) -> pd.DataFrame:
        """Create derived variables based on R methodology"""

        # Income-based binary indicators
        if 'loan_amount' in data.columns and 'income' in data.columns:
            data['loan_to_income_ratio'] = data['loan_amount'] / data['income']
            data['high_cost_loan'] = (data['interest_rate'] > data['interest_rate'].quantile(0.75)).astype(int)
            data['high_ltv_loan'] = (data['combined_loan_to_value_ratio'] > 90).astype(int)

        # Race and ethnicity combinations (replicating R logic)
        if 'derived_race' in data.columns and 'derived_ethnicity' in data.columns:
            data['minority borrower'] = (
                (data['derived_race'].isin(['Black or African American', 'American Indian or Alaska Native',
                                          'Asian', 'Native Hawaiian or Other Pacific Islander'])) |
                (data['derived_ethnicity'] == 'Hispanic or Latino')
            ).astype(int)

        # Geographic identifiers - ensure proper string conversion
        if 'county_code' in data.columns and 'state_code' in data.columns:
            data['fips'] = data['state_code'].astype(str).str.zfill(2) + data['county_code'].astype(str).str.zfill(3)

        return data

    def _apply_geographic_aggregations(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Apply geographic aggregations replicating R sum_columns function
        Groups by FIPS, County, State, hmda_lender_id, inst_name
        """
        if 'fips' in data.columns and len(data) > 1000:  # Only aggregate for substantial datasets

            group_cols = ['fips', 'state_code', 'county_code']
            if 'lei' in data.columns:
                group_cols.append('lei')
            if 'derived_msa_md' in data.columns:
                group_cols.append('derived_msa_md')

            # Filter to only columns that exist
            available_sum_cols = [col for col in self.sum_columns if col in data.columns]
            available_group_cols = [col for col in group_cols if col in data.columns]

            if available_sum_cols and available_group_cols:
                aggregated = data.groupby(available_group_cols)[available_sum_cols].agg([
                    'sum', 'mean', 'count', 'std'
                ]).reset_index()

                # Flatten column names
                aggregated.columns = ['_'.join(col).strip() if col[1] else col[0] for col in aggregated.columns]

                return data

        return data

    def _categorize_income_levels(self, data: pd.DataFrame) -> pd.DataFrame:
        """Create income level categories based on area median income"""
        if 'income' in data.columns:
            # Create income brackets (simplified version of R logic)
            data['income_category'] = pd.cut(
                data['income'],
                bins=[0, 30000, 60000, 100000, 150000, float('inf')],
                labels=['Low', 'Moderate', 'Middle', 'Upper-Middle', 'High']
            )

        return data

    def _categorize_loan_status(self, data: pd.DataFrame) -> pd.DataFrame:
        """Create loan status categories"""
        if 'action_taken' in data.columns:
            # Map action_taken to meaningful categories (based on HMDA documentation)
            action_mapping = {
                '1': 'Loan originated',
                '2': 'Application approved but not accepted',
                '3': 'Application denied',
                '4': 'Application withdrawn by applicant',
                '5': 'File closed for incompleteness',
                '6': 'Purchased loan',
                '7': 'Preapproval request denied',
                '8': 'Preapproval request approved but not accepted'
            }

            data['loan_status'] = data['action_taken'].map(action_mapping).fillna('Unknown')

        return data

    def process_geographic_slicing(self, data: pd.DataFrame) -> Dict[str, pd.DataFrame]:
        """
        Create comprehensive geographic slices
        Replicates and extends R geographic analysis
        """
        self.logger.info("Creating geographic slices...")

        slices = {}

        # State-level analysis
        if 'state_code' in data.columns:
            slices['state_level'] = self._analyze_by_geography(data, 'state_code', 'State')

        # County-level analysis
        if 'fips' in data.columns:
            slices['county_level'] = self._analyze_by_geography(data, 'fips', 'County')

        # MSA-level analysis
        if 'derived_msa_md' in data.columns:
            slices['msa_level'] = self._analyze_by_geography(data, 'derived_msa_md', 'MSA')

        # Tract-level analysis (sample due to size)
        if 'census_tract' in data.columns and len(data) > 10000:
            tract_sample = data.sample(n=min(10000, len(data)), random_state=42)
            slices['tract_sample'] = self._analyze_by_geography(tract_sample, 'census_tract', 'Tract')

        self.logger.info(f"Created {len(slices)} geographic slices")
        return slices

    def _analyze_by_geography(self, data: pd.DataFrame, geo_col: str, geo_name: str) -> pd.DataFrame:
        """Analyze data by specific geographic level"""

        # Group by geography
        group_cols = [geo_col]
        if 'derived_race' in data.columns:
            group_cols.append('derived_race')
        if 'derived_ethnicity' in data.columns:
            group_cols.append('derived_ethnicity')
        if 'loan_status' in data.columns:
            group_cols.append('loan_status')

        # Filter available columns
        available_sum_cols = [col for col in self.sum_columns if col in data.columns]
        available_group_cols = [col for col in group_cols if col in data.columns]

        if available_sum_cols and available_group_cols:
            analysis = data.groupby(available_group_cols)[available_sum_cols].agg([
                'count', 'sum', 'mean', 'median', 'std'
            ]).reset_index()

            # Flatten columns
            analysis.columns = [f"{col[0]}_{col[1]}" if col[1] else col[0] for col in analysis.columns]

            # Add geographic metadata
            analysis['geographic_level'] = geo_name
            analysis['processing_timestamp'] = datetime.now()

            return analysis

        return pd.DataFrame()

    def process_temporal_slicing(self, data: pd.DataFrame) -> Dict[str, pd.DataFrame]:
        """Create temporal analysis slices"""
        self.logger.info("Creating temporal slices...")

        slices = {}

        if 'activity_year' in data.columns:
            # Year-over-year analysis
            yearly_analysis = data.groupby('activity_year').size().reset_index(name='loan_count')
            slices['yearly_trends'] = yearly_analysis

            # Multi-year comparison if data available
            if data['activity_year'].nunique() > 1:
                for year in data['activity_year'].unique():
                    year_data = data[data['activity_year'] == year]
                    year_slice = self.process_geographic_slicing(year_data)
                    for key, value in year_slice.items():
                        slices[f"{key}_{year}"] = value

        return slices

    def process_institutional_slicing(self, data: pd.DataFrame) -> Dict[str, pd.DataFrame]:
        """Create institution-level analysis slices"""
        self.logger.info("Creating institutional slices...")

        slices = {}

        if 'lei' in data.columns:
            # Top lenders by volume
            lender_volume = data.groupby('lei').agg({
                'loan_amount': ['count', 'sum'],
                'activity_year': 'nunique'
            }).reset_index()
            lender_volume.columns = ['lei', 'loan_count', 'total_volume', 'years_active']
            lender_volume = lender_volume.sort_values('total_volume', ascending=False)

            slices['lender_rankings'] = lender_volume.head(100)  # Top 100

            # Agency-level analysis
            if 'agency_code' in data.columns:
                agency_analysis = data.groupby('agency_code').agg({
                    'loan_amount': ['count', 'sum', 'mean'],
                    'derived_race': 'nunique'
                }).reset_index()
                agency_analysis.columns = ['agency_code', 'loan_count', 'total_volume', 'avg_loan_size', 'diverse_markets']
                slices['agency_analysis'] = agency_analysis

        return slices

    def process_demographic_slicing(self, data: pd.DataFrame) -> Dict[str, pd.DataFrame]:
        """Create demographic and disparity analysis slices"""
        self.logger.info("Creating demographic slices...")

        slices = {}

        # Race-based analysis
        if 'derived_race' in data.columns:
            race_analysis = data.groupby('derived_race').agg({
                'loan_amount': ['count', 'sum', 'mean'],
                'action_taken': lambda x: (x == '1').mean()  # Origination rate
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

        # Income-based analysis
        if 'income_category' in data.columns:
            income_analysis = data.groupby('income_category').agg({
                'loan_amount': ['count', 'sum', 'mean'],
                'action_taken': lambda x: (x == '1').mean()
            }).reset_index()
            income_analysis.columns = ['income_category', 'application_count', 'total_volume', 'avg_loan_size', 'origination_rate']
            slices['income_analysis'] = income_analysis

        return slices

    def save_results(self, slices: Dict[str, pd.DataFrame]) -> Dict[str, str]:
        """Save processed results in multiple formats"""
        self.logger.info("Saving processed results...")

        saved_files = {}

        for slice_name, data in slices.items():
            if not data.empty:
                # Save as CSV
                csv_file = self.output_path / f"{slice_name}.csv"
                data.to_csv(csv_file, index=False)

                # Save as Excel (single sheet per Nick's requirements)
                excel_file = self.output_path / f"{slice_name}.xlsx"
                data.to_excel(excel_file, index=False, sheet_name='Data')

                saved_files[slice_name] = {
                    'csv': str(csv_file),
                    'excel': str(excel_file),
                    'rows': len(data),
                    'columns': len(data.columns)
                }

                self.logger.info(f"Saved {slice_name}: {len(data)} rows, {len(data.columns)} columns")

        # Save metadata
        metadata_file = self.output_path / "processing_metadata.json"
        with open(metadata_file, 'w') as f:
            json.dump(saved_files, f, indent=2, default=str)

        self.logger.info(f"Saved {len(saved_files)} processed slices")
        return saved_files

    def run_comprehensive_analysis(self, year: int = 2024) -> Dict[str, Any]:
        """
        Run comprehensive HMDA analysis with all slicing dimensions
        Main execution method
        """
        self.logger.info("Starting comprehensive HMDA analysis...")

        results = {
            'processing_start': datetime.now(),
            'year': year,
            'status': 'started'
        }

        try:
            # Step 1: Load raw data
            raw_data = self.load_raw_data(year)
            results['data_loaded'] = len(raw_data)

            # Step 2: Apply R methodology
            processed_data = self._apply_r_methodology(raw_data)
            results['data_processed'] = len(processed_data)

            # Step 3: Create all slices
            all_slices = {}

            # Geographic slicing
            geo_slices = self.process_geographic_slicing(processed_data)
            all_slices.update(geo_slices)

            # Temporal slicing
            temp_slices = self.process_temporal_slicing(processed_data)
            all_slices.update(temp_slices)

            # Institutional slicing
            inst_slices = self.process_institutional_slicing(processed_data)
            all_slices.update(inst_slices)

            # Demographic slicing
            demo_slices = self.process_demographic_slicing(processed_data)
            all_slices.update(demo_slices)

            # Step 4: Save results
            saved_files = self.save_results(all_slices)
            results['saved_files'] = saved_files
            results['total_slices'] = len(all_slices)

            # Step 5: Generate summary
            summary = self._generate_summary(saved_files, processed_data)
            results['summary'] = summary
            results['processing_end'] = datetime.now()
            results['status'] = 'completed'
            results['duration'] = (results['processing_end'] - results['processing_start']).total_seconds()

            self.logger.info(f"Analysis completed successfully in {results['duration']:.2f} seconds")
            self.logger.info(f"Generated {len(all_slices)} analysis slices")

        except Exception as e:
            self.logger.error(f"Analysis failed: {str(e)}")
            results['status'] = 'failed'
            results['error'] = str(e)
            raise

        return results

    def _generate_summary(self, saved_files: Dict[str, Any], data: pd.DataFrame) -> Dict[str, Any]:
        """Generate analysis summary"""
        summary = {
            'total_applications': len(data),
            'total_loan_volume': data['loan_amount'].sum() if 'loan_amount' in data.columns else 0,
            'average_loan_size': data['loan_amount'].mean() if 'loan_amount' in data.columns else 0,
            'unique_states': data['state_code'].nunique() if 'state_code' in data.columns else 0,
            'unique_counties': data['fips'].nunique() if 'fips' in data.columns else 0,
            'unique_lenders': data['lei'].nunique() if 'lei' in data.columns else 0,
            'analysis_slices_generated': len(saved_files),
            'processing_timestamp': datetime.now()
        }

        return summary

def main():
    """Main execution function"""
    config = ProcessingConfig(
        chunk_size=25000,  # Smaller chunks to avoid memory issues
        memory_limit_gb=4.0,
        output_format="both"
    )

    processor = EnhancedHMDAProcessor(config)
    results = processor.run_comprehensive_analysis(year=2024)

    print("Analysis Results:")
    print(f"Status: {results['status']}")
    print(f"Applications processed: {results.get('data_loaded', 0):,}")
    print(f"Slices generated: {results.get('total_slices', 0)}")
    print(f"Processing time: {results.get('duration', 0):.2f} seconds")

    if results['status'] == 'completed':
        print(f"Results saved to: {processor.output_path}")

    return results

if __name__ == "__main__":
    main()