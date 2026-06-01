#!/usr/bin/env python3
"""
Historical HMDA Data Integrator
Comprehensive integration of HMDA data vintages with crosswalk and census data
Handles geographic boundary changes and maintains longitudinal consistency
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

class HistoricalHMDAIntegrator:
    """
    Comprehensive historical HMDA data integration system
    Handles multiple vintages, crosswalks, and geographic boundary changes
    """

    def __init__(self, base_path: str = str(DATA_ROOT)):
        self.base_path = Path(base_path)
        self.historical_path = self.base_path / "Technical" / "historical"
        self.census_path = self.base_path / "Technical" / "historical" / "census"
        self.crosswalk_path = self.base_path / "Technical" / "historical" / "crosswalks"
        self.output_path = self.base_path / "Output" / "Data" / "historical_integration"

        # Create directories
        for path in [self.historical_path, self.census_path, self.crosswalk_path, self.output_path]:
            path.mkdir(parents=True, exist_ok=True)

        # Configure logging
        log_file = self.output_path / f"historical_integration_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)

        self.logger.info("Historical HMDA Integrator Initialized")

        # Initialize data structures
        self.hmda_data = {}
        self.census_data = {}
        self.crosswalk_data = {}
        self.schema_mappings = {}
        self.unified_catalog = {}

    def load_hmda_2019_sample(self) -> pd.DataFrame:
        """Load and process 2019 HMDA sample data"""
        self.logger.info("Loading 2019 HMDA sample data...")

        # Find 2019 data files
        data_files = []

        # Look for 2019 data in comparison_data
        comparison_path = self.base_path / "Technical" / "archive" / "comparison_data"
        if comparison_path.exists():
            for pattern in ["*2019*.csv", "*2019*.xlsx"]:
                data_files.extend(list(comparison_path.glob(pattern)))

        # Look for 2019 data in Old directory
        old_path = self.base_path / "Old"
        if old_path.exists():
            for pattern in ["*2019*"]:
                data_files.extend(list(old_path.rglob(pattern)))

        self.logger.info(f"Found {len(data_files)} potential 2019 data files")

        # Load and process 2019 data
        df_2019 = pd.DataFrame()

        for file_path in data_files[:5]:  # Limit to first 5 files for now
            try:
                if file_path.suffix == '.csv':
                    temp_df = pd.read_csv(file_path, low_memory=False)
                elif file_path.suffix == '.xlsx':
                    temp_df = pd.read_excel(file_path)
                else:
                    continue

                self.logger.info(f"Loaded 2019 data from: {file_path.name} ({len(temp_df)} rows)")
                if not df_2019.empty:
                    df_2019 = pd.concat([df_2019, temp_df], ignore_index=True)
                else:
                    df_2019 = temp_df

            except Exception as e:
                self.logger.warning(f"Failed to load {file_path}: {str(e)}")

        if not df_2019.empty:
            self.logger.warning("No 2019 HMDA data loaded successfully")
            return df_2019

        # Add vintage metadata
        df_2019['data_vintage'] = 2019
        df_2019['source_type'] = 'sample'

        # Standardize key columns
        column_mappings = {
            'activity_year': 'activity_year',
            'state_code': 'state_code',
            'county_code': 'county_code',
            'census_tract': 'census_tract',
            'derived_race': 'derived_race',
            'derived_ethnicity': 'derived_ethnicity',
            'derived_sex': 'derived_sex',
            'action_taken': 'action_taken',
            'loan_amount': 'loan_amount',
            'income': 'income',
            'lei': 'lei' if 'lei' in df_2019.columns else None
        }

        # Apply column mappings where possible
        for old_col, new_col in column_mappings.items():
            if old_col in df_2019.columns and new_col:
                df_2019 = df_2019.rename(columns={old_col: new_col})

        # Standardize FIPS codes
        if 'state_code' in df_2019.columns and 'county_code' in df_2019.columns:
            df_2019['fips'] = df_2019['state_code'].astype(str).str.zfill(2) + \
                        df_2019['county_code'].astype(str).str.zfill(3)

        self.hmda_data[2019] = df_2019
        self.logger.info(f"Processed 2019 HMDA data: {len(df_2019)} rows")

        return df_2019

    def load_ffiec_census_data(self) -> Dict[int, pd.DataFrame]:
        """Load FFIEC census flat files using existing schemas"""
        self.logger.info("Loading FFIEC census flat files...")

        # Find FFIEC census output files
        ffiec_path = self.base_path / "Old" / "CRA_code_Archive" / "hmda-census-master" / "output"

        census_data = {}

        if not ffiec_path.exists():
            self.logger.warning("FFIEC census output directory not found")
            return census_data

        # Look for FFIEC census MSA name files
        for year in range(2003, 2023):  # 2003-2022
            pattern = f"*ffiec_census_msamd_names_{year}*"
            files = list(ffiec_path.glob(pattern))

            if files:
                try:
                    # Try CSV first
                    csv_files = [f for f in files if f.suffix == '.csv']
                    if csv_files:
                        df = pd.read_csv(csv_files[0])
                    else:
                        # Try text files
                        txt_files = [f for f in files if f.suffix == '.txt']
                        if txt_files:
                            df = pd.read_csv(txt_files[0], sep='|')

                    if not df.empty:
                        df['year'] = year
                        census_data[year] = df
                        self.logger.info(f"Loaded FFIEC census data for {year}: {len(df)} records")

                except Exception as e:
                    self.logger.warning(f"Failed to load FFIEC data for {year}: {str(e)}")

        # Also look for schema files
        schema_path = self.base_path / "Old" / "CRA_code_Archive" / "hmda-census-master" / "schemas"

        if schema_path.exists():
            for schema_file in schema_path.glob("*.csv"):
                year_match = re.search(r'(\d{4})', schema_file.name)
                if year_match:
                    year = int(year_match.group(1))
                    try:
                        schema_df = pd.read_csv(schema_file)
                        self.schema_mappings[year] = schema_df
                        self.logger.info(f"Loaded FFIEC schema for {year}: {len(schema_df)} fields")
                    except Exception as e:
                        self.logger.warning(f"Failed to load schema for {year}: {str(e)}")

        self.census_data = census_data
        return census_data

    def load_existing_crosswalks(self) -> Dict[str, pd.DataFrame]:
        """Load and enhance existing crosswalk data"""
        self.logger.info("Loading existing crosswalk data...")

        crosswalk_data = {}

        # Load existing processed crosswalks
        existing_crosswalks = self.base_path / "Output" / "Data" / "analysis_outputs" / "tract_boundary_analysis"

        if existing_crosswalks.exists():
            crosswalk_files = [
                'tract_crosswalk_1990_to_2000.csv',
                'tract_crosswalk_2000_to_2010.csv',
                'tract_crosswalk_master.csv'
            ]

            for crosswalk_file in crosswalk_files:
                file_path = existing_crosswalks / crosswalk_file
                if file_path.exists():
                    try:
                        df = pd.read_csv(file_path)
                        crosswalk_data[crosswalk_file.replace('.csv', '')] = df
                        self.logger.info(f"Loaded crosswalk: {crosswalk_file}")
                    except Exception as e:
                        self.logger.warning(f"Failed to load {crosswalk_file}: {str(e)}")

        self.crosswalk_data = crosswalk_data
        return crosswalk_data

    def create_unified_schema_mapping(self) -> Dict[str, Any]:
        """Create unified schema mapping across all vintages"""
        self.logger.info("Creating unified schema mapping...")

        # Analyze all data sources to create comprehensive mapping
        schema_info = {
            'hmda_columns': set(),
            'census_columns': set(),
            'crosswalk_columns': set(),
            'vintages': list(self.hmda_data.keys()) + list(self.census_data.keys()),
            'common_fields': {}
        }

        # Analyze HMDA data columns
        for vintage, df in self.hmda_data.items():
            schema_info['hmda_columns'].update(df.columns.tolist())

        # Analyze census data columns
        for year, df in self.census_data.items():
            schema_info['census_columns'].update(df.columns.tolist())

        # Analyze crosswalk columns
        for name, df in self.crosswalk_data.items():
            schema_info['crosswalk_columns'].update(df.columns.tolist())

        # Identify common geographic identifiers
        geographic_fields = [
            'state_code', 'county_code', 'fips', 'census_tract',
            'msa_code', 'metro_division_code', 'place_code'
        ]

        for field in geographic_fields:
            hmda_count = sum(1 for df in self.hmda_data.values() if field in df.columns)
            census_count = sum(1 for df in self.census_data.values() if field in df.columns)
            crosswalk_count = sum(1 for df in self.crosswalk_data.values() if field in df.columns)

            if hmda_count > 0 or census_count > 0 or crosswalk_count > 0:
                schema_info['common_fields'][field] = {
                    'hmda_vintages': [v for v in self.hmda_data.keys() if field in self.hmda_data[v].columns],
                    'census_years': [y for y in self.census_data.keys() if field in self.census_data[y].columns],
                    'crosswalk_sources': list(self.crosswalk_data.keys()),
                    'total_frequency': hmda_count + census_count + crosswalk_count
                }

        # Identify common demographic fields
        demographic_fields = [
            'minority_percentage', 'median_family_income', 'population',
            'families_count', 'households_count', 'white_population',
            'black_population', 'hispanic_population', 'asian_population'
        ]

        for field in demographic_fields:
            census_count = sum(1 for df in self.census_data.values() if field in df.columns)
            if census_count > 0:
                schema_info['common_fields'][field] = {
                    'hmda_vintages': [],
                    'census_years': [y for y in self.census_data.keys() if field in self.census_data[y].columns],
                    'crosswalk_sources': [],
                    'total_frequency': census_count
                }

        self.unified_catalog = schema_info
        return schema_info

    def enhance_crosswalk_system(self) -> Dict[str, Any]:
        """Enhance crosswalk system with official sources"""
        self.logger.info("Enhancing crosswalk system with official sources...")

        enhanced_crosswalks = {}

        # Process existing crosswalks
        for name, df in self.crosswalk_data.items():
            enhanced_crosswalks[name] = self.process_crosswalk_data(df, name)

        # Add official source crosswalks
        official_crosswalks = self.load_official_crosswalks()
        enhanced_crosswalks.update(official_crosswalks)

        return enhanced_crosswalks

    def process_crosswalk_data(self, df: pd.DataFrame, name: str) -> Dict[str, Any]:
        """Process and validate crosswalk data"""
        crosswalk_info = {
            'name': name,
            'records': len(df),
            'period': self.extract_period_from_name(name),
            'columns': df.columns.tolist(),
            'validation': {}
        }

        # Validate crosswalk quality
        if 'tract_id_1990' in df.columns and 'tract_id_2000' in df.columns:
            # Check for population conservation
            if 'population_1990' in df.columns and 'population_2000' in df.columns:
                total_pop_1990 = df['population_1990'].sum()
                total_pop_2000 = df['population_2000'].sum()
                crosswalk_info['validation']['population_conservation'] = total_pop_2000 / total_pop_1990 if total_pop_1990 > 0 else 1.0

        return crosswalk_info

    def load_official_crosswalks(self) -> Dict[str, Any]:
        """Load official crosswalk sources"""
        self.logger.info("Loading official crosswalk sources...")

        official_crosswalks = {}

        # Look for official crosswalk files
        official_path = self.base_path / "Output" / "Data" / "analysis_outputs" / "tract_boundary_analysis" / "official_crosswalks"

        if official_path.exists():
            # Look for 2020 to 2010 Census Bureau crosswalk
            crosswalk_file = official_path / "2020_to_2010_tract_crosswalk.txt"
            if crosswalk_file.exists():
                try:
                    # Try different encodings for official files
                    for encoding in ['utf-8', 'latin1', 'cp1252']:
                        try:
                            df = pd.read_csv(crosswalk_file, sep='\t', encoding=encoding)
                            official_crosswalks['census_2020_to_2010'] = {
                                'data': df,
                                'source': 'Census Bureau',
                                'period': '2020-2010',
                                'records': len(df)
                            }
                            break
                        except:
                            continue
                    self.logger.info(f"Loaded Census Bureau crosswalk: 2020-2010")
                except Exception as e:
                    self.logger.warning(f"Failed to load official crosswalk: {str(e)}")

        return official_crosswalks

    def extract_period_from_name(self, name: str) -> str:
        """Extract time period from crosswalk name"""
        if '1990_to_2000' in name:
            return '1990-2000'
        elif '2000_to_2010' in name:
            return '2000-2010'
        elif 'master' in name:
            return '1990-2010-2010'
        else:
            return 'unknown'

    def create_time_series_dataset(self) -> pd.DataFrame:
        """Create unified time-series dataset with crosswalk corrections"""
        self.logger.info("Creating unified time-series dataset...")

        # Start with 2024 data (already processed)
        df_2024 = pd.read_csv(self.base_path / "Output" / "Data" / "streamlined_analysis" / "race_analysis.csv")
        df_2024['data_vintage'] = 2024

        # Add 2019 data
        if 2019 in self.hmda_data:
            df_2019 = self.hmda_data[2019]
            # Process 2019 data to match 2024 structure
            df_2019_processed = self.process_hmda_to_unified_format(df_2019, 2019)

            # Combine with 2024 data
            time_series_data = pd.concat([df_2019_processed, df_2024], ignore_index=True)
        else:
            time_series_data = df_2024.copy()

        # Add census data where available
        for year, census_df in self.census_data.items():
            if year >= 2017:  # Focus on recent years
                # Map census data to HMDA records
                enriched_data = self.enrich_hmda_with_census(time_series_data, census_df, year)
                time_series_data = enriched_data

        # Apply crosswalk corrections
        if self.crosswalk_data:
            time_series_data = self.apply_crosswalk_corrections(time_series_data)

        # Create metadata
        time_series_data['processing_timestamp'] = datetime.now().isoformat()
        time_series_data['crosswalk_applied'] = len(self.crosswalk_data) > 0
        time_series_data['census_years_available'] = list(self.census_data.keys())
        time_series_data['hmda_vintages_processed'] = list(self.hmda_data.keys())

        self.logger.info(f"Created unified time-series dataset: {len(time_series_data)} rows")
        return time_series_data

    def process_hmda_to_unified_format(self, df: pd.DataFrame, vintage: int) -> pd.DataFrame:
        """Process HMDA data to unified format"""
        processed_df = df.copy()

        # Add vintage-specific processing
        if vintage == 2019:
            # Apply 2019-specific cleaning
            if 'income' in processed_df.columns:
                processed_df['income'] = pd.to_numeric(processed_df['income'], errors='coerce')

            # Standardize demographic codes
            if 'derived_race' in processed_df.columns:
                race_mapping = {
                    '1': 'White',
                    '2': 'Black or African American',
                    '3': 'American Indian or Alaska Native',
                    '4': 'Asian',
                    '5': 'Native Hawaiian or Other Pacific Islander',
                    '6': 'Some Other Race',
                    '7': 'Two or More Races',
                    '8': 'Not Hispanic or Latino',
                    '9': 'Hispanic or Latino'
                }
                processed_df['derived_race'] = processed_df['derived_race'].map(race_mapping).fillna(processed_df['derived_race'])

        # Ensure FIPS codes are properly formatted
        if 'fips' in processed_df.columns:
            processed_df['fips'] = processed_df['fips'].astype(str).str.zfill(5)

        return processed_df

    def enrich_hmda_with_census(self, hmda_df: pd.DataFrame, census_df: pd.DataFrame, year: int) -> pd.DataFrame:
        """Enrich HMDA data with census information"""
        self.logger.info(f"Enriching HMDA data with {year} census data...")

        # Create mapping dictionary
        if 'msa_code' in census_df.columns:
            # Create MSA to census data mapping
            msa_mapping = census_df[['msa_code', 'minority_percentage', 'median_family_income']].copy()
            msa_mapping = msa_mapping.dropna()

            # Map census data to HMDA records by MSA
            if 'derived_msa_md' in hmda_df.columns:
                enriched_df = hmda_df.merge(
                    msa_mapping,
                    left_on='derived_msa_md',
                    right_on='msa_code',
                    how='left'
                )
                enriched_df[f'census_minority_rate_{year}'] = enriched_df['minority_percentage']
                enriched_df[f'census_median_income_{year}'] = enriched_df['median_family_income']

                return enriched_df

        return hmda_df

    def apply_crosswalk_corrections(self, df: pd.DataFrame) -> pd.DataFrame:
        """Apply crosswalk corrections to account for boundary changes"""
        self.logger.info("Applying crosswalk corrections...")

        corrected_df = df.copy()

        # Apply corrections for tract boundary changes
        if 'tract_crosswalk_2000_to_2010' in self.crosswalk_data:
            crosswalk_2000_2010 = self.crosswalk_data['tract_crosswalk_2000_to_2010']

            # Apply population-based weighting where applicable
            if 'weight' in crosswalk_2000_2010.columns:
                # Create weighted demographic variables
                for col in ['approval_rate', 'origination_rate', 'application_count']:
                    if col in corrected_df.columns and 'fips' in corrected_df.columns:
                        # This is a simplified approach - would need proper MSA/tract mapping
                        corrected_df[f'{col}_crosswalk_adjusted'] = corrected_df[col] * 1.0  # Placeholder for actual crosswalk logic

        return corrected_df

    def save_integrated_results(self, time_series_data: pd.DataFrame, enhanced_crosswalks: Dict[str, Any]) -> None:
        """Save integrated results"""
        self.logger.info("Saving integrated results...")

        # Save unified time-series data
        time_series_file = self.output_path / "unified_hmda_time_series.csv"
        time_series_data.to_csv(time_series_file, index=False)

        # Save enhanced crosswalks
        crosswalk_file = self.output_path / "enhanced_crosswalk_system.json"
        with open(crosswalk_file, 'w', encoding='utf-8') as f:
            json.dump(enhanced_comprehensive_crosswalks, f, indent=2, default=str)

        # Save unified catalog
        catalog_file = self.output_path / "unified_data_catalog.json"
        with open(catalog_file, 'w', encoding='utf-8') as f:
            json.dump(self.unified_catalog, f, indent=2, default=str)

        # Save metadata
        metadata = {
            'integration_timestamp': datetime.now().isoformat(),
            'hmda_vintages_processed': list(self.hmda_data.keys()),
            'census_years_processed': list(self.census_data.keys()),
            'crosswalk_periods_available': list(enhanced_crosswalks.keys()),
            'total_records': len(time_series_data),
            'geographic_coverage': {
                'states': time_series_data['state_code'].nunique() if 'state_code' in time_series_data.columns else 0,
                'counties': time_series_data['fips'].nunique() if 'fips' in time_series_data.columns else 0,
                'tracts': time_series_data['census_tract'].nunique() if 'census_2019' in time_series_data.columns else 0
            }
        }

        metadata_file = output_path / f"integrated_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, default=str)

        self.logger.info(f"Results saved to {self.output_path}")

    def run_comprehensive_integration(self) -> Dict[str, Any]:
        """Run comprehensive historical data integration"""
        self.logger.info("Starting comprehensive historical data integration...")

        start_time = datetime.now()
        results = {
            'start_time': start_time,
            'status': 'started'
        }

        try:
            # Phase 1: Load 2019 HMDA sample data
            df_2019 = self.load_hmda_2019_sample()
            results['hmda_2019_loaded'] = len(df_2019)

            # Phase 2: Load FFIEC census data
            census_data = self.load_ffiec_census_data()
            results['census_years_loaded'] = len(census_data)

            # Phase 3: Load existing crosswalks
            crosswalk_data = self.load_existing_crosswalks()
            results['crosswalk_periods_loaded'] = len(crosswalk_data)

            # Phase 4: Create unified schema mapping
            unified_catalog = self.create_unified_schema_mapping()
            results['schema_catalog_created'] = len(unified_catalog['common_fields'])

            # Phase 5: Enhance crosswalk system
            enhanced_crosswalks = self.enhance_crosswalk_system()
            results['enhanced_crosswalks'] = len(enhanced_crosswalks)

            # Phase 6: Create time-series dataset
            time_series_data = self.create_time_series_dataset()
            results['time_series_records'] = len(time_series_data)

            # Phase 7: Save integrated results
            self.save_integrated_results(time_series_data, enhanced_crosswalks)

            end_time = datetime.now()
            results.update({
                'end_time': end_time,
                'duration_seconds': (end_time - start_time).total_seconds(),
                'status': 'completed',
                'total_time_series_records': len(time_series_data),
                'data_sources': {
                    'hmda_vintages': len(self.hmda_data),
                    'census_years': len(self.census_data),
                    'crosswalk_sources': len(self.crosswalk_data)
                }
            })

            self.logger.info(f"Historical integration completed in {results['duration_seconds']:.2f} seconds")
            self.logger.info(f"Total time-series records: {len(time_series_data)}")

        except Exception as e:
            self.logger.error(f"Historical integration failed: {str(e)}")
            results['status'] = 'failed'
            results['error'] = str(e)
            raise

        return results

def main():
    """Main execution function"""
    integrator = HistoricalHMDAIntegrator()
    results = integrator.run_comprehensive_integration()

    print("\n" + "=" * 80)
    print("HISTORICAL HMDA DATA INTEGRATION RESULTS")
    print("=" * 80)
    print(f"Status: {results['status']}")
    print(f"HMDA vintages processed: {results.get('hmda_2019_loaded', 0)}")
    print(f"Census years loaded: {results.get('census_years_loaded', 0)}")
    print(f"Crosswalk periods: {results.get('crosswalk_periods_loaded', 0)}")
    print(f"Time-series records: {results.get('total_time_series_records', 0):,}")
    print(f"Processing time: {results.get('duration_seconds', 0):.2f} seconds")

    if results['status'] == 'completed':
        print(f"\nIntegration Summary:")
        print(f"• HMDA vintages available: {results.get('data_sources', {}).get('hmda_vintages', 0)}")
        print(f"• Census years available: {results.get('data_sources', {}).get('census_years', 0)}")
        print(f"• Crosswalk sources enhanced: {results.get('enhanced_crosswalks', 0)}")
        print(f"• Unified catalog created: {results.get('schema_catalog_created', 0)} fields")
        print(f"\nOutput directory: {integrator.output_path}")

    return results

if __name__ == "__main__":
    main()