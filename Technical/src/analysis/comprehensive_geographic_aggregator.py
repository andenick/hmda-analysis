#!/usr/bin/env python3
"""
Comprehensive Geographic Aggregation Tool for HMDA Data
Aggregates HMDA data at multiple geographic levels including:
- State
- County  
- Census Tract
- MSA/Metropolitan Division
- Municipality (via census tract to place crosswalk)
- ZIP Code
"""

import pandas as pd
import numpy as np
import logging
from pathlib import Path
import json
from datetime import datetime
from typing import Dict, List, Any, Tuple, Optional
import warnings
import os
DATA_ROOT = Path(os.environ.get("DATA_ROOT", "data"))

warnings.filterwarnings('ignore')

class ComprehensiveGeographicAggregator:
    """
    Aggregates HMDA data at multiple geographic levels
    Designed for flexibility and extensibility
    """

    def __init__(self, base_path: str = str(DATA_ROOT)):
        self.base_path = Path(base_path)
        self.input_path = self.base_path / "Output" / "Data" / "enhanced_analysis"
        self.output_path = self.base_path / "Output" / "Data" / "geographic_aggregations"
        self.output_path.mkdir(parents=True, exist_ok=True)

        # Configure logging
        log_file = self.output_path / f"geographic_aggregation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        self.logger.info("Comprehensive Geographic Aggregator Initialized")

        # Define aggregation functions
        self.agg_functions = {
            'loan_amount': ['count', 'sum', 'mean', 'median', 'std'],
            'interest_rate': ['mean', 'median', 'std'],
            'combined_loan_to_value_ratio': ['mean', 'median'],
            'property_value': ['mean', 'median'],
            'income': ['mean', 'median'],
            'debt_to_income_ratio': ['mean', 'median']
        }

    def load_processed_data(self) -> pd.DataFrame:
        """Load processed HMDA data from enhanced analysis"""
        self.logger.info("Loading processed HMDA data...")
        
        # Look for the most recent processing metadata
        metadata_files = list(self.input_path.glob("processing_metadata.json"))
        
        if metadata_files:
            with open(metadata_files[0], 'r') as f:
                metadata = json.load(f)
                self.logger.info(f"Found processing metadata: {len(metadata)} files")
        
        # Load intermediate files if they exist, otherwise look for final outputs
        csv_files = list(self.input_path.glob("intermediate_*.csv"))
        
        if csv_files:
            self.logger.info(f"Found {len(csv_files)} intermediate files. Loading...")
            dfs = []
            for f in sorted(csv_files):
                self.logger.info(f"Loading {f.name}...")
                dfs.append(pd.read_csv(f, low_memory=False))
            
            data = pd.concat(dfs, ignore_index=True)
            self.logger.info(f"Loaded {len(data):,} rows from {len(csv_files)} files")
            return data
        else:
            self.logger.warning("No intermediate files found. Looking for alternative data sources...")
            # Try to load from streamlined analysis
            streamlined_path = self.base_path / "Output" / "Data" / "streamlined_analysis"
            csv_files = list(streamlined_path.glob("*.csv"))
            if csv_files:
                # Load the largest file as it's likely the main dataset
                largest_file = max(csv_files, key=lambda x: x.stat().st_size)
                self.logger.info(f"Loading from streamlined analysis: {largest_file.name}")
                return pd.read_csv(largest_file, low_memory=False)
            
            raise FileNotFoundError("No processed data found. Please run the enhanced processor first.")

    def aggregate_by_state(self, data: pd.DataFrame) -> pd.DataFrame:
        """Aggregate data by state"""
        self.logger.info("Aggregating by state...")
        
        if 'state_code' not in data.columns:
            self.logger.warning("state_code column not found")
            return pd.DataFrame()
        
        # Select available numeric columns
        available_cols = [col for col in self.agg_functions.keys() if col in data.columns]
        
        if not available_cols:
            self.logger.warning("No aggregatable columns found")
            return pd.DataFrame()
        
        # Create aggregation dictionary
        agg_dict = {col: self.agg_functions[col] for col in available_cols}
        
        # Add categorical aggregations
        if 'action_taken' in data.columns:
            agg_dict['action_taken'] = lambda x: (x == '1').mean()  # Origination rate
        
        if 'derived_race' in data.columns:
            agg_dict['derived_race'] = lambda x: (x != 'White').mean()  # Minority rate
        
        # Perform aggregation
        state_agg = data.groupby('state_code').agg(agg_dict).reset_index()
        
        # Flatten column names
        state_agg.columns = ['_'.join(map(str, col)).strip('_') if isinstance(col, tuple) else col 
                             for col in state_agg.columns]
        
        # Add metadata
        state_agg['geographic_level'] = 'State'
        state_agg['aggregation_timestamp'] = datetime.now()
        
        self.logger.info(f"Created state-level aggregation: {len(state_agg)} states")
        return state_agg

    def aggregate_by_county(self, data: pd.DataFrame) -> pd.DataFrame:
        """Aggregate data by county (FIPS code)"""
        self.logger.info("Aggregating by county...")
        
        if 'fips' not in data.columns:
            self.logger.warning("fips column not found")
            return pd.DataFrame()
        
        # Remove invalid FIPS codes
        data = data[data['fips'].notna()].copy()
        data = data[data['fips'].astype(str).str.len() == 5].copy()
        
        # Select available numeric columns
        available_cols = [col for col in self.agg_functions.keys() if col in data.columns]
        
        if not available_cols:
            self.logger.warning("No aggregatable columns found")
            return pd.DataFrame()
        
        # Create aggregation dictionary
        agg_dict = {col: self.agg_functions[col] for col in available_cols}
        
        # Add categorical aggregations
        if 'action_taken' in data.columns:
            agg_dict['action_taken'] = lambda x: (x == '1').mean()
        
        if 'derived_race' in data.columns:
            agg_dict['derived_race'] = lambda x: (x != 'White').mean()
        
        if 'lei' in data.columns:
            agg_dict['lei'] = 'nunique'  # Count unique lenders
        
        # Perform aggregation
        county_agg = data.groupby('fips').agg(agg_dict).reset_index()
        
        # Flatten column names
        county_agg.columns = ['_'.join(map(str, col)).strip('_') if isinstance(col, tuple) else col 
                              for col in county_agg.columns]
        
        # Add state code from FIPS
        county_agg['state_code'] = county_agg['fips'].astype(str).str[:2]
        
        # Add metadata
        county_agg['geographic_level'] = 'County'
        county_agg['aggregation_timestamp'] = datetime.now()
        
        self.logger.info(f"Created county-level aggregation: {len(county_agg)} counties")
        return county_agg

    def aggregate_by_tract(self, data: pd.DataFrame) -> pd.DataFrame:
        """Aggregate data by census tract"""
        self.logger.info("Aggregating by census tract...")
        
        if 'census_tract' not in data.columns:
            self.logger.warning("census_tract column not found")
            return pd.DataFrame()
        
        # Remove invalid tract codes
        data = data[data['census_tract'].notna()].copy()
        
        # Select available numeric columns
        available_cols = [col for col in self.agg_functions.keys() if col in data.columns]
        
        if not available_cols:
            self.logger.warning("No aggregatable columns found")
            return pd.DataFrame()
        
        # Create aggregation dictionary
        agg_dict = {col: self.agg_functions[col] for col in available_cols}
        
        # Add categorical aggregations
        if 'action_taken' in data.columns:
            agg_dict['action_taken'] = lambda x: (x == '1').mean()
        
        if 'derived_race' in data.columns:
            agg_dict['derived_race'] = lambda x: (x != 'White').mean()
        
        # Group by tract and optionally county/state
        group_cols = ['census_tract']
        if 'fips' in data.columns:
            group_cols.append('fips')
        if 'state_code' in data.columns:
            group_cols.append('state_code')
        
        # Perform aggregation
        tract_agg = data.groupby(group_cols).agg(agg_dict).reset_index()
        
        # Flatten column names
        tract_agg.columns = ['_'.join(map(str, col)).strip('_') if isinstance(col, tuple) else col 
                             for col in tract_agg.columns]
        
        # Add metadata
        tract_agg['geographic_level'] = 'Census Tract'
        tract_agg['aggregation_timestamp'] = datetime.now()
        
        self.logger.info(f"Created tract-level aggregation: {len(tract_agg)} census tracts")
        return tract_agg

    def aggregate_by_msa(self, data: pd.DataFrame) -> pd.DataFrame:
        """Aggregate data by MSA/Metropolitan Division"""
        self.logger.info("Aggregating by MSA...")
        
        if 'derived_msa_md' not in data.columns:
            self.logger.warning("derived_msa_md column not found")
            return pd.DataFrame()
        
        # Remove invalid MSA codes
        data = data[data['derived_msa_md'].notna()].copy()
        data = data[data['derived_msa_md'] != 'NA'].copy()
        
        # Select available numeric columns
        available_cols = [col for col in self.agg_functions.keys() if col in data.columns]
        
        if not available_cols:
            self.logger.warning("No aggregatable columns found")
            return pd.DataFrame()
        
        # Create aggregation dictionary
        agg_dict = {col: self.agg_functions[col] for col in available_cols}
        
        # Add categorical aggregations
        if 'action_taken' in data.columns:
            agg_dict['action_taken'] = lambda x: (x == '1').mean()
        
        if 'derived_race' in data.columns:
            agg_dict['derived_race'] = lambda x: (x != 'White').mean()
        
        if 'lei' in data.columns:
            agg_dict['lei'] = 'nunique'
        
        # Perform aggregation
        msa_agg = data.groupby('derived_msa_md').agg(agg_dict).reset_index()
        
        # Flatten column names
        msa_agg.columns = ['_'.join(map(str, col)).strip('_') if isinstance(col, tuple) else col 
                           for col in msa_agg.columns]
        
        # Add metadata
        msa_agg['geographic_level'] = 'MSA'
        msa_agg['aggregation_timestamp'] = datetime.now()
        
        self.logger.info(f"Created MSA-level aggregation: {len(msa_agg)} MSAs")
        return msa_agg

    def aggregate_by_institution_and_geography(self, data: pd.DataFrame, 
                                              geo_level: str = 'county') -> pd.DataFrame:
        """Aggregate by institution within geographic areas"""
        self.logger.info(f"Aggregating by institution and {geo_level}...")
        
        # Determine geographic column
        geo_col_map = {
            'state': 'state_code',
            'county': 'fips',
            'msa': 'derived_msa_md',
            'tract': 'census_tract'
        }
        
        geo_col = geo_col_map.get(geo_level.lower())
        if not geo_col or geo_col not in data.columns:
            self.logger.warning(f"Geographic column for {geo_level} not found")
            return pd.DataFrame()
        
        if 'lei' not in data.columns:
            self.logger.warning("lei (lender identifier) column not found")
            return pd.DataFrame()
        
        # Remove invalid values
        data = data[data[geo_col].notna()].copy()
        data = data[data['lei'].notna()].copy()
        
        # Select available numeric columns
        available_cols = [col for col in self.agg_functions.keys() if col in data.columns]
        
        if not available_cols:
            self.logger.warning("No aggregatable columns found")
            return pd.DataFrame()
        
        # Create aggregation dictionary
        agg_dict = {col: self.agg_functions[col] for col in available_cols}
        
        # Add categorical aggregations
        if 'action_taken' in data.columns:
            agg_dict['action_taken'] = lambda x: (x == '1').mean()
        
        if 'derived_race' in data.columns:
            agg_dict['derived_race'] = lambda x: (x != 'White').mean()
        
        # Perform aggregation
        inst_geo_agg = data.groupby([geo_col, 'lei']).agg(agg_dict).reset_index()
        
        # Flatten column names
        inst_geo_agg.columns = ['_'.join(map(str, col)).strip('_') if isinstance(col, tuple) else col 
                                for col in inst_geo_agg.columns]
        
        # Add metadata
        inst_geo_agg['geographic_level'] = f'{geo_level.capitalize()}_Institution'
        inst_geo_agg['aggregation_timestamp'] = datetime.now()
        
        self.logger.info(f"Created {geo_level}-institution aggregation: {len(inst_geo_agg)} rows")
        return inst_geo_agg

    def save_aggregations(self, aggregations: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
        """Save all aggregations to CSV and Excel"""
        self.logger.info("Saving aggregations...")
        
        saved_files = {}
        
        for name, data in aggregations.items():
            if not data.empty:
                # Save as CSV
                csv_file = self.output_path / f"{name}_aggregation.csv"
                data.to_csv(csv_file, index=False)
                
                # Save as Excel
                excel_file = self.output_path / f"{name}_aggregation.xlsx"
                data.to_excel(excel_file, index=False, sheet_name='Data')
                
                saved_files[name] = {
                    'csv': str(csv_file),
                    'excel': str(excel_file),
                    'rows': len(data),
                    'columns': len(data.columns)
                }
                
                self.logger.info(f"Saved {name}: {len(data):,} rows, {len(data.columns)} columns")
        
        # Save metadata
        metadata = {
            'aggregation_timestamp': datetime.now().isoformat(),
            'total_aggregations': len(aggregations),
            'aggregations': saved_files
        }
        
        metadata_file = self.output_path / "aggregation_metadata.json"
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2, default=str)
        
        self.logger.info(f"Saved {len(saved_files)} aggregations")
        return metadata

    def run_comprehensive_aggregation(self) -> Dict[str, Any]:
        """Run all geographic aggregations"""
        self.logger.info("Starting comprehensive geographic aggregation...")
        
        start_time = datetime.now()
        results = {'start_time': start_time, 'status': 'started'}
        
        try:
            # Load processed data
            data = self.load_processed_data()
            results['data_loaded'] = len(data)
            
            # Run all aggregations
            aggregations = {}
            
            # State-level
            aggregations['state'] = self.aggregate_by_state(data)
            
            # County-level
            aggregations['county'] = self.aggregate_by_county(data)
            
            # Tract-level
            aggregations['tract'] = self.aggregate_by_tract(data)
            
            # MSA-level
            aggregations['msa'] = self.aggregate_by_msa(data)
            
            # Institution-Geography cross-tabs
            aggregations['county_institution'] = self.aggregate_by_institution_and_geography(data, 'county')
            aggregations['state_institution'] = self.aggregate_by_institution_and_geography(data, 'state')
            aggregations['msa_institution'] = self.aggregate_by_institution_and_geography(data, 'msa')
            
            # Save all aggregations
            metadata = self.save_aggregations(aggregations)
            results['metadata'] = metadata
            results['aggregations_created'] = len(aggregations)
            
            # Generate summary
            summary = {
                'total_records_processed': len(data),
                'aggregations_generated': len(aggregations),
                'geographic_levels': list(aggregations.keys()),
                'output_files': len(metadata['aggregations']) * 2  # CSV + Excel
            }
            results['summary'] = summary
            
            end_time = datetime.now()
            results['end_time'] = end_time
            results['duration_seconds'] = (end_time - start_time).total_seconds()
            results['status'] = 'completed'
            
            self.logger.info(f"Aggregation completed in {results['duration_seconds']:.2f} seconds")
            self.logger.info(f"Generated {len(aggregations)} geographic aggregations")
            
        except Exception as e:
            self.logger.error(f"Aggregation failed: {str(e)}")
            results['status'] = 'failed'
            results['error'] = str(e)
            raise
        
        return results

def main():
    """Main execution function"""
    aggregator = ComprehensiveGeographicAggregator()
    results = aggregator.run_comprehensive_aggregation()
    
    print("\n" + "="*60)
    print("COMPREHENSIVE GEOGRAPHIC AGGREGATION RESULTS")
    print("="*60)
    print(f"Status: {results['status']}")
    print(f"Records processed: {results.get('data_loaded', 0):,}")
    print(f"Aggregations created: {results.get('aggregations_created', 0)}")
    print(f"Processing time: {results.get('duration_seconds', 0):.2f} seconds")
    
    if results['status'] == 'completed':
        summary = results.get('summary', {})
        print(f"\nSummary:")
        print(f"  Geographic levels: {len(summary.get('geographic_levels', []))}")
        print(f"  Output files: {summary.get('output_files', 0)}")
        print(f"\nResults saved to: {aggregator.output_path}")
    
    return results

if __name__ == "__main__":
    main()

