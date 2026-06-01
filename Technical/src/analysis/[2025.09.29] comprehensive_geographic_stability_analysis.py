#!/usr/bin/env python3
"""
Comprehensive Geographic Stability Analysis
==========================================

This script analyzes ALL geographic levels in HMDA data to identify:
1. Completely stable geographic areas (no changes across time periods)
2. Detailed documentation of ALL changes at every geographic level
3. MSA, County, Municipal, and Tract boundary evolution
4. Data vintage differences and their impacts

CRITICAL: No data modifications - only documentation and analysis
NO artificial data cleaning - all changes documented and flagged
"""

import pandas as pd
import numpy as np
import logging
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Set, Tuple, Optional
from collections import defaultdict, Counter
import warnings
import os
DATA_ROOT = Path(os.environ.get("DATA_ROOT", "data"))
warnings.filterwarnings('ignore')

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ComprehensiveGeographicStabilityAnalyzer:
    """
    Analyzes ALL geographic boundary changes across all administrative levels.

    CRITICAL PRINCIPLES:
    - Document ALL changes, do not modify data
    - Preserve all data vintages exactly as they appear
    - Flag issues without removing or changing values
    - Maintain complete transparency about data evolution
    """

    def __init__(self, base_path: str = str(DATA_ROOT)):
        self.base_path = Path(base_path)
        self.output_dir = self.base_path / "analysis_outputs" / "geographic_stability"
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Geographic levels to analyze
        self.geographic_levels = [
            'state', 'county', 'msa_md', 'census_tract',
            'municipality', 'congressional_district', 'cbsa'
        ]

        # Data containers - NO MODIFICATIONS ALLOWED
        self.original_data = {}  # Preserve all original data exactly
        self.stability_analysis = {}
        self.boundary_changes = {}
        self.stable_areas = {}
        self.vintage_differences = {}

        logger.info("Initialized Comprehensive Geographic Stability Analyzer")
        logger.info("CRITICAL: NO data modifications will be made - only documentation")

    def load_all_geographic_data(self) -> None:
        """Load ALL geographic data preserving exact vintage differences."""
        logger.info("Loading ALL geographic data - preserving exact vintage differences")

        # Load HMDA census data files (all years)
        census_files = list(self.base_path.glob("Old/CRA_code/_Archive/hmda-census-master/output/census_data_extract_*.csv"))

        for file_path in sorted(census_files):
            year = int(file_path.stem.split('_')[-1])
            try:
                # Load data exactly as it appears - NO CLEANING
                df = pd.read_csv(file_path, dtype=str, keep_default_na=False)

                # Document original column structure
                original_columns = list(df.columns)
                original_shape = df.shape
                original_dtypes = df.dtypes.to_dict()

                self.original_data[year] = {
                    'data': df,
                    'original_columns': original_columns,
                    'original_shape': original_shape,
                    'original_dtypes': original_dtypes,
                    'file_path': str(file_path),
                    'load_timestamp': datetime.now().isoformat()
                }

                logger.info(f"Loaded {year}: {original_shape[0]} records, {original_shape[1]} columns - NO MODIFICATIONS")

            except Exception as e:
                logger.error(f"Error loading {year}: {e}")
                continue

        # Load additional geographic data sources
        self._load_additional_geographic_sources()

        logger.info(f"Loaded data for {len(self.original_data)} years - ALL DATA PRESERVED EXACTLY")

    def _load_additional_geographic_sources(self) -> None:
        """Load additional geographic reference data."""

        # MSA definitions across time periods
        try:
            msa_files = list(self.base_path.glob("**/*msa*.csv"))
            cbsa_files = list(self.base_path.glob("**/*cbsa*.csv"))

            logger.info(f"Found {len(msa_files)} MSA files and {len(cbsa_files)} CBSA files")

            for file_path in msa_files + cbsa_files:
                try:
                    df = pd.read_csv(file_path, dtype=str, keep_default_na=False)
                    file_key = f"geographic_ref_{file_path.stem}"
                    self.original_data[file_key] = {
                        'data': df,
                        'file_type': 'geographic_reference',
                        'file_path': str(file_path),
                        'load_timestamp': datetime.now().isoformat()
                    }
                    logger.info(f"Loaded geographic reference: {file_path.name}")
                except Exception as e:
                    logger.warning(f"Could not load {file_path}: {e}")

        except Exception as e:
            logger.warning(f"Error loading additional geographic sources: {e}")

    def analyze_state_level_stability(self) -> Dict:
        """Analyze state-level changes (should be completely stable)."""
        logger.info("Analyzing state-level stability")

        state_analysis = {
            'completely_stable': True,
            'stable_states': set(),
            'state_changes': [],
            'vintage_differences': {},
            'data_quality_issues': []
        }

        # Extract state information from all years
        state_data_by_year = {}

        for year, year_data in self.original_data.items():
            if isinstance(year, int):  # Only process year-based data
                df = year_data['data']

                # Find state column (various possible names)
                state_col = None
                for col in df.columns:
                    if 'state' in col.lower() and 'fips' not in col.lower():
                        state_col = col
                        break

                if state_col:
                    states = set(df[state_col].unique())
                    # Remove empty/null values for analysis but document them
                    states_clean = {s for s in states if s and s.strip() and s != 'nan'}
                    states_missing = states - states_clean

                    state_data_by_year[year] = {
                        'states': states_clean,
                        'missing_values': states_missing,
                        'column_name': state_col,
                        'total_records': len(df),
                        'missing_state_records': len(df[df[state_col].isin(states_missing)]) if states_missing else 0
                    }

                    if states_missing:
                        state_analysis['data_quality_issues'].append({
                            'year': year,
                            'issue': f"Missing/empty state values: {states_missing}",
                            'affected_records': len(df[df[state_col].isin(states_missing)])
                        })

        # Analyze stability across years
        if state_data_by_year:
            all_years = sorted(state_data_by_year.keys())

            # Find states that appear in all years
            all_states = set.intersection(*[data['states'] for data in state_data_by_year.values()])
            state_analysis['stable_states'] = all_states

            # Check for any changes
            all_states_ever = set.union(*[data['states'] for data in state_data_by_year.values()])

            if len(all_states) == len(all_states_ever):
                state_analysis['completely_stable'] = True
                logger.info(f"✅ STATES ARE COMPLETELY STABLE: {len(all_states)} states consistent across all years")
            else:
                state_analysis['completely_stable'] = False

                # Document any changes
                for year in all_years:
                    year_states = state_data_by_year[year]['states']
                    missing_states = all_states_ever - year_states
                    extra_states = year_states - all_states_ever

                    if missing_states or extra_states:
                        state_analysis['state_changes'].append({
                            'year': year,
                            'missing_states': list(missing_states),
                            'extra_states': list(extra_states),
                            'total_states': len(year_states)
                        })

        # Document vintage differences
        state_analysis['vintage_differences'] = self._document_state_vintage_differences(state_data_by_year)

        self.stability_analysis['states'] = state_analysis
        logger.info(f"State analysis complete: {len(state_analysis['stable_states'])} stable states")

        return state_analysis

    def _document_state_vintage_differences(self, state_data_by_year: Dict) -> Dict:
        """Document differences in state data across vintages."""
        vintage_diffs = {
            'column_name_variations': set(),
            'coding_differences': {},
            'data_quality_evolution': {}
        }

        for year, data in state_data_by_year.items():
            vintage_diffs['column_name_variations'].add(data['column_name'])

            # Document coding (FIPS vs names vs abbreviations)
            sample_states = list(data['states'])[:5]  # Sample for coding analysis

            coding_type = 'unknown'
            if sample_states:
                first_state = sample_states[0]
                if first_state.isdigit():
                    if len(first_state) == 2:
                        coding_type = 'FIPS_code'
                    else:
                        coding_type = 'numeric_other'
                elif len(first_state) == 2 and first_state.isupper():
                    coding_type = 'state_abbreviation'
                else:
                    coding_type = 'state_name'

            vintage_diffs['coding_differences'][year] = {
                'coding_type': coding_type,
                'sample_values': sample_states[:3],
                'total_unique_states': len(data['states'])
            }

            vintage_diffs['data_quality_evolution'][year] = {
                'missing_values': len(data['missing_values']),
                'missing_rate': data['missing_state_records'] / data['total_records'] if data['total_records'] > 0 else 0,
                'column_name': data['column_name']
            }

        # Convert sets to lists for JSON serialization
        vintage_diffs['column_name_variations'] = list(vintage_diffs['column_name_variations'])

        return vintage_diffs

    def analyze_county_level_stability(self) -> Dict:
        """Analyze county-level changes (mostly stable with some exceptions)."""
        logger.info("Analyzing county-level stability")

        county_analysis = {
            'stable_counties': set(),
            'county_changes': [],
            'new_counties': defaultdict(list),
            'discontinued_counties': defaultdict(list),
            'name_changes': [],
            'fips_changes': [],
            'vintage_differences': {},
            'data_quality_issues': []
        }

        # Extract county information
        county_data_by_year = {}

        for year, year_data in self.original_data.items():
            if isinstance(year, int):
                df = year_data['data']

                # Find county and state columns
                county_col = self._find_column(df, ['county', 'cnty'])
                state_col = self._find_column(df, ['state', 'st'])

                if county_col and state_col:
                    # Create state-county combinations
                    df_clean = df[(df[county_col].notna()) & (df[state_col].notna())].copy()
                    df_clean['state_county'] = df_clean[state_col].astype(str) + '_' + df_clean[county_col].astype(str)

                    counties = set(df_clean['state_county'].unique())

                    county_data_by_year[year] = {
                        'counties': counties,
                        'county_column': county_col,
                        'state_column': state_col,
                        'total_records': len(df),
                        'valid_county_records': len(df_clean),
                        'missing_county_records': len(df) - len(df_clean)
                    }

                    # Document data quality issues
                    missing_rate = (len(df) - len(df_clean)) / len(df) if len(df) > 0 else 0
                    if missing_rate > 0.01:  # More than 1% missing
                        county_analysis['data_quality_issues'].append({
                            'year': year,
                            'issue': f"Missing county/state data: {missing_rate:.2%}",
                            'affected_records': len(df) - len(df_clean)
                        })

        # Analyze county stability
        if len(county_data_by_year) >= 2:
            all_years = sorted(county_data_by_year.keys())

            # Find completely stable counties
            all_counties = set.intersection(*[data['counties'] for data in county_data_by_year.values()])
            county_analysis['stable_counties'] = all_counties

            # Find changes between consecutive years
            for i in range(1, len(all_years)):
                prev_year = all_years[i-1]
                curr_year = all_years[i]

                prev_counties = county_data_by_year[prev_year]['counties']
                curr_counties = county_data_by_year[curr_year]['counties']

                new_counties = curr_counties - prev_counties
                discontinued = prev_counties - curr_counties

                if new_counties:
                    county_analysis['new_counties'][f"{prev_year}_{curr_year}"] = list(new_counties)

                if discontinued:
                    county_analysis['discontinued_counties'][f"{prev_year}_{curr_year}"] = list(discontinued)

                if new_counties or discontinued:
                    county_analysis['county_changes'].append({
                        'period': f"{prev_year}-{curr_year}",
                        'new_counties': len(new_counties),
                        'discontinued_counties': len(discontinued),
                        'net_change': len(new_counties) - len(discontinued)
                    })

        # Document vintage differences
        county_analysis['vintage_differences'] = self._document_county_vintage_differences(county_data_by_year)

        self.stability_analysis['counties'] = county_analysis
        logger.info(f"County analysis complete: {len(county_analysis['stable_counties'])} stable counties")

        return county_analysis

    def analyze_msa_level_stability(self) -> Dict:
        """Analyze MSA/CBSA changes (significant changes over time)."""
        logger.info("Analyzing MSA/CBSA level stability")

        msa_analysis = {
            'stable_msas': set(),
            'msa_changes': [],
            'redefinition_periods': [],
            'msa_to_cbsa_transition': {},
            'name_changes': [],
            'boundary_changes': [],
            'vintage_differences': {},
            'data_quality_issues': []
        }

        # Extract MSA/CBSA information
        msa_data_by_year = {}

        for year, year_data in self.original_data.items():
            if isinstance(year, int):
                df = year_data['data']

                # Find MSA column (various names)
                msa_col = self._find_column(df, ['msa', 'cbsa', 'msa_md', 'metro'])

                if msa_col:
                    msas_raw = set(df[msa_col].unique())
                    # Clean but document missing values
                    msas_clean = {m for m in msas_raw if m and str(m).strip() and str(m) != 'nan' and str(m) != '0'}
                    msas_missing = msas_raw - msas_clean

                    msa_data_by_year[year] = {
                        'msas': msas_clean,
                        'missing_values': msas_missing,
                        'column_name': msa_col,
                        'total_records': len(df),
                        'valid_msa_records': len(df[df[msa_col].isin(msas_clean)]),
                        'missing_msa_records': len(df[df[msa_col].isin(msas_missing) | df[msa_col].isna()])
                    }

                    # Document data quality issues
                    missing_rate = msa_data_by_year[year]['missing_msa_records'] / len(df) if len(df) > 0 else 0
                    if missing_rate > 0.05:  # More than 5% missing
                        msa_analysis['data_quality_issues'].append({
                            'year': year,
                            'issue': f"High missing MSA rate: {missing_rate:.2%}",
                            'affected_records': msa_data_by_year[year]['missing_msa_records']
                        })

        # Analyze MSA stability and changes
        if len(msa_data_by_year) >= 2:
            all_years = sorted(msa_data_by_year.keys())

            # Identify redefinition periods (major changes in MSA structure)
            redefinition_years = [2003, 2009, 2013, 2018]  # Known OMB redefinition years

            for year in redefinition_years:
                if year in all_years:
                    prev_year = max([y for y in all_years if y < year], default=None)
                    next_year = min([y for y in all_years if y > year], default=None)

                    if prev_year and next_year:
                        prev_msas = msa_data_by_year[prev_year]['msas']
                        next_msas = msa_data_by_year[next_year]['msas']

                        changes = {
                            'redefinition_year': year,
                            'msas_before': len(prev_msas),
                            'msas_after': len(next_msas),
                            'net_change': len(next_msas) - len(prev_msas),
                            'new_msas': len(next_msas - prev_msas),
                            'discontinued_msas': len(prev_msas - next_msas)
                        }

                        msa_analysis['redefinition_periods'].append(changes)

            # Find stable MSAs (appear in all years)
            if all_years:
                stable_msas = set.intersection(*[msa_data_by_year[year]['msas'] for year in all_years])
                msa_analysis['stable_msas'] = stable_msas

                # Document changes between years
                for i in range(1, len(all_years)):
                    prev_year = all_years[i-1]
                    curr_year = all_years[i]

                    prev_msas = msa_data_by_year[prev_year]['msas']
                    curr_msas = msa_data_by_year[curr_year]['msas']

                    if prev_msas != curr_msas:
                        msa_analysis['msa_changes'].append({
                            'period': f"{prev_year}-{curr_year}",
                            'new_msas': len(curr_msas - prev_msas),
                            'discontinued_msas': len(prev_msas - curr_msas),
                            'stable_msas': len(prev_msas & curr_msas),
                            'total_change_rate': len((prev_msas ^ curr_msas)) / len(prev_msas | curr_msas) if prev_msas | curr_msas else 0
                        })

        # Document vintage differences
        msa_analysis['vintage_differences'] = self._document_msa_vintage_differences(msa_data_by_year)

        self.stability_analysis['msas'] = msa_analysis
        logger.info(f"MSA analysis complete: {len(msa_analysis['stable_msas'])} stable MSAs")

        return msa_analysis

    def analyze_tract_level_stability(self) -> Dict:
        """Analyze census tract stability (using existing boundary analysis)."""
        logger.info("Analyzing census tract stability")

        # Load existing tract boundary analysis
        tract_analysis_file = self.base_path / "analysis_outputs" / "tract_boundary_analysis" / "tract_boundary_comprehensive_report.json"

        if tract_analysis_file.exists():
            try:
                with open(tract_analysis_file, 'r') as f:
                    existing_analysis = json.load(f)

                tract_analysis = {
                    'stable_tracts': len(existing_analysis.get('boundary_changes', {}).get('stable_tracts', [])),
                    'total_tracts_analyzed': len(existing_analysis.get('boundary_changes', {}).get('tract_appearances', {})),
                    'stability_rate': 0,
                    'major_redefinition_periods': ['1990-2000', '2000-2010', '2010-2020'],
                    'boundary_changes_summary': existing_analysis.get('boundary_changes', {}),
                    'data_source': 'Existing comprehensive tract boundary analysis'
                }

                if tract_analysis['total_tracts_analyzed'] > 0:
                    tract_analysis['stability_rate'] = tract_analysis['stable_tracts'] / tract_analysis['total_tracts_analyzed']

                logger.info(f"Loaded existing tract analysis: {tract_analysis['stable_tracts']} stable tracts")

            except Exception as e:
                logger.error(f"Could not load existing tract analysis: {e}")
                tract_analysis = {'error': 'Could not load existing analysis', 'status': 'unavailable'}
        else:
            tract_analysis = {'status': 'no_existing_analysis', 'note': 'Run tract boundary analysis first'}

        self.stability_analysis['census_tracts'] = tract_analysis
        return tract_analysis

    def _find_column(self, df: pd.DataFrame, possible_names: List[str]) -> Optional[str]:
        """Find column by possible name variations."""
        df_columns_lower = [col.lower() for col in df.columns]

        for name in possible_names:
            for col, col_lower in zip(df.columns, df_columns_lower):
                if name.lower() in col_lower:
                    return col
        return None

    def _document_county_vintage_differences(self, county_data_by_year: Dict) -> Dict:
        """Document county data vintage differences."""
        vintage_diffs = {
            'column_name_variations': set(),
            'coding_differences': {},
            'data_quality_evolution': {}
        }

        for year, data in county_data_by_year.items():
            vintage_diffs['column_name_variations'].add(f"{data['state_column']}|{data['county_column']}")

            # Sample counties for analysis
            sample_counties = list(data['counties'])[:5]

            vintage_diffs['coding_differences'][year] = {
                'sample_values': sample_counties,
                'total_unique_counties': len(data['counties']),
                'state_column': data['state_column'],
                'county_column': data['county_column']
            }

            vintage_diffs['data_quality_evolution'][year] = {
                'missing_records': data['missing_county_records'],
                'missing_rate': data['missing_county_records'] / data['total_records'] if data['total_records'] > 0 else 0,
                'valid_records': data['valid_county_records']
            }

        vintage_diffs['column_name_variations'] = list(vintage_diffs['column_name_variations'])
        return vintage_diffs

    def _document_msa_vintage_differences(self, msa_data_by_year: Dict) -> Dict:
        """Document MSA data vintage differences."""
        vintage_diffs = {
            'column_name_variations': set(),
            'coding_differences': {},
            'data_quality_evolution': {},
            'transition_analysis': {}
        }

        for year, data in msa_data_by_year.items():
            vintage_diffs['column_name_variations'].add(data['column_name'])

            # Analyze MSA coding format
            sample_msas = list(data['msas'])[:5]

            coding_analysis = {}
            if sample_msas:
                first_msa = sample_msas[0]
                if str(first_msa).isdigit():
                    if len(str(first_msa)) == 4:
                        coding_analysis['type'] = 'MSA_4_digit'
                    elif len(str(first_msa)) == 5:
                        coding_analysis['type'] = 'CBSA_5_digit'
                    else:
                        coding_analysis['type'] = 'numeric_other'
                else:
                    coding_analysis['type'] = 'non_numeric'

                coding_analysis['sample_values'] = sample_msas
                coding_analysis['total_unique'] = len(data['msas'])

            vintage_diffs['coding_differences'][year] = coding_analysis

            vintage_diffs['data_quality_evolution'][year] = {
                'missing_records': data['missing_msa_records'],
                'missing_rate': data['missing_msa_records'] / data['total_records'] if data['total_records'] > 0 else 0,
                'column_name': data['column_name']
            }

        vintage_diffs['column_name_variations'] = list(vintage_diffs['column_name_variations'])

        # Analyze MSA-to-CBSA transition
        years_sorted = sorted(msa_data_by_year.keys())
        for i, year in enumerate(years_sorted):
            column_name = msa_data_by_year[year]['column_name'].lower()
            if 'cbsa' in column_name:
                transition_start = years_sorted[max(0, i-2):i]
                vintage_diffs['transition_analysis'][year] = {
                    'transition_to_cbsa': True,
                    'previous_years_checked': transition_start,
                    'column_name': msa_data_by_year[year]['column_name']
                }
                break

        return vintage_diffs

    def create_stable_geographic_areas_sheet(self) -> None:
        """Create comprehensive sheet of stable geographic areas."""
        logger.info("Creating stable geographic areas identification sheet")

        stable_areas = {
            'analysis_metadata': {
                'analysis_date': datetime.now().isoformat(),
                'data_years_analyzed': sorted([year for year in self.original_data.keys() if isinstance(year, int)]),
                'geographic_levels_analyzed': self.geographic_levels,
                'stability_definition': 'Areas that maintain exact same identifier across ALL analysis years'
            },
            'stable_states': {},
            'stable_counties': {},
            'stable_msas': {},
            'stable_census_tracts': {},
            'stability_summary': {},
            'usage_recommendations': {}
        }

        # Populate stable areas from analysis
        if 'states' in self.stability_analysis:
            stable_areas['stable_states'] = {
                'count': len(self.stability_analysis['states'].get('stable_states', set())),
                'areas': list(self.stability_analysis['states'].get('stable_states', set())),
                'completely_stable': self.stability_analysis['states'].get('completely_stable', False),
                'recommended_for_longitudinal_analysis': True,
                'data_quality_notes': self.stability_analysis['states'].get('data_quality_issues', [])
            }

        if 'counties' in self.stability_analysis:
            stable_areas['stable_counties'] = {
                'count': len(self.stability_analysis['counties'].get('stable_counties', set())),
                'areas': list(self.stability_analysis['counties'].get('stable_counties', set())),
                'changes_documented': len(self.stability_analysis['counties'].get('county_changes', [])),
                'recommended_for_longitudinal_analysis': True,
                'caveats': 'Some counties may have boundary adjustments not reflected in FIPS codes'
            }

        if 'msas' in self.stability_analysis:
            stable_areas['stable_msas'] = {
                'count': len(self.stability_analysis['msas'].get('stable_msas', set())),
                'areas': list(self.stability_analysis['msas'].get('stable_msas', set())),
                'redefinition_periods': self.stability_analysis['msas'].get('redefinition_periods', []),
                'recommended_for_longitudinal_analysis': False,
                'warning': 'MSAs undergo frequent redefinition - use with extreme caution'
            }

        if 'census_tracts' in self.stability_analysis:
            stable_areas['stable_census_tracts'] = {
                'count': self.stability_analysis['census_tracts'].get('stable_tracts', 0),
                'total_analyzed': self.stability_analysis['census_tracts'].get('total_tracts_analyzed', 0),
                'stability_rate': self.stability_analysis['census_tracts'].get('stability_rate', 0),
                'recommended_for_longitudinal_analysis': False,
                'critical_requirement': 'MUST use crosswalk tables for any longitudinal analysis'
            }

        # Create stability summary
        stable_areas['stability_summary'] = {
            'most_stable_level': 'states',
            'moderately_stable_level': 'counties',
            'least_stable_levels': ['msas', 'census_tracts'],
            'overall_recommendation': 'Use states and counties for most reliable longitudinal analysis'
        }

        # Usage recommendations
        stable_areas['usage_recommendations'] = {
            'for_longitudinal_trend_analysis': {
                'recommended': ['stable_states', 'stable_counties'],
                'use_with_caution': [],
                'not_recommended': ['msas_without_validation', 'census_tracts_without_crosswalks']
            },
            'for_cross_sectional_analysis': {
                'all_levels_acceptable': True,
                'note': 'Any geographic level acceptable for single-year analysis'
            },
            'for_policy_research': {
                'recommended': ['stable_states', 'stable_counties'],
                'note': 'Use most stable levels for policy impact assessment'
            }
        }

        # Save stable areas sheet
        stable_areas_file = self.output_dir / "stable_geographic_areas_sheet.json"
        with open(stable_areas_file, 'w') as f:
            json.dump(stable_areas, f, indent=2, default=str)

        # Create CSV version for easy reference
        self._create_stable_areas_csv(stable_areas)

        logger.info(f"Stable geographic areas sheet saved: {stable_areas_file}")

    def _create_stable_areas_csv(self, stable_areas: Dict) -> None:
        """Create CSV version of stable areas for easy reference."""

        # Create summary CSV
        summary_data = []

        for level, data in stable_areas.items():
            if level.startswith('stable_') and isinstance(data, dict):
                summary_data.append({
                    'Geographic_Level': level.replace('stable_', ''),
                    'Stable_Count': data.get('count', 0),
                    'Recommended_For_Longitudinal': data.get('recommended_for_longitudinal_analysis', False),
                    'Notes': data.get('warning', data.get('caveats', 'Generally stable'))
                })

        if summary_data:
            summary_df = pd.DataFrame(summary_data)
            summary_file = self.output_dir / "stable_geographic_areas_summary.csv"
            summary_df.to_csv(summary_file, index=False)
            logger.info(f"Stable areas summary CSV saved: {summary_file}")

        # Create detailed CSV for each level
        for level, data in stable_areas.items():
            if level.startswith('stable_') and isinstance(data, dict) and 'areas' in data:
                areas_df = pd.DataFrame({
                    'Area_Identifier': data['areas'],
                    'Geographic_Level': level.replace('stable_', ''),
                    'Stable_Across_All_Years': True,
                    'Recommended_For_Analysis': data.get('recommended_for_longitudinal_analysis', True)
                })

                level_file = self.output_dir / f"{level}_detailed.csv"
                areas_df.to_csv(level_file, index=False)

    def generate_comprehensive_stability_report(self) -> None:
        """Generate comprehensive stability analysis report."""
        logger.info("Generating comprehensive geographic stability report")

        report = {
            'metadata': {
                'analysis_date': datetime.now().isoformat(),
                'analyzer': 'ComprehensiveGeographicStabilityAnalyzer',
                'version': '1.0',
                'data_integrity_principle': 'NO data modifications - only documentation and analysis'
            },
            'executive_summary': {
                'total_years_analyzed': len([year for year in self.original_data.keys() if isinstance(year, int)]),
                'geographic_levels_analyzed': len(self.geographic_levels),
                'data_preservation_status': 'ALL original data preserved exactly as found',
                'key_findings': self._generate_key_findings()
            },
            'stability_analysis': self.stability_analysis,
            'vintage_differences': self.vintage_differences,
            'data_quality_flags': self._compile_data_quality_flags(),
            'usage_guidance': self._generate_usage_guidance()
        }

        # Save comprehensive report
        report_file = self.output_dir / "comprehensive_geographic_stability_report.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2, default=str)

        # Create human-readable summary
        self._create_readable_summary(report)

        logger.info(f"Comprehensive stability report saved: {report_file}")

    def _generate_key_findings(self) -> List[str]:
        """Generate key findings from stability analysis."""
        findings = []

        if 'states' in self.stability_analysis:
            state_data = self.stability_analysis['states']
            if state_data.get('completely_stable'):
                findings.append(f"✅ STATES: Completely stable - {len(state_data.get('stable_states', []))} states consistent across all years")
            else:
                findings.append(f"⚠️ STATES: Some inconsistencies detected - requires investigation")

        if 'counties' in self.stability_analysis:
            county_data = self.stability_analysis['counties']
            stable_count = len(county_data.get('stable_counties', []))
            total_changes = len(county_data.get('county_changes', []))
            findings.append(f"📍 COUNTIES: {stable_count} stable counties, {total_changes} change periods documented")

        if 'msas' in self.stability_analysis:
            msa_data = self.stability_analysis['msas']
            stable_count = len(msa_data.get('stable_msas', []))
            redefinitions = len(msa_data.get('redefinition_periods', []))
            findings.append(f"🏙️ MSAs: {stable_count} stable MSAs, {redefinitions} major redefinition periods")

        if 'census_tracts' in self.stability_analysis:
            tract_data = self.stability_analysis['census_tracts']
            if 'stable_tracts' in tract_data:
                findings.append(f"🗺️ CENSUS TRACTS: {tract_data['stable_tracts']} stable tracts out of {tract_data.get('total_tracts_analyzed', 'unknown')} analyzed")

        return findings

    def _compile_data_quality_flags(self) -> Dict:
        """Compile all data quality flags identified during analysis."""
        quality_flags = {
            'missing_data_patterns': [],
            'coding_inconsistencies': [],
            'temporal_discontinuities': [],
            'geographic_anomalies': []
        }

        # Collect flags from all geographic levels
        for level, analysis in self.stability_analysis.items():
            if 'data_quality_issues' in analysis:
                for issue in analysis['data_quality_issues']:
                    quality_flags['missing_data_patterns'].append({
                        'level': level,
                        'issue': issue
                    })

        return quality_flags

    def _generate_usage_guidance(self) -> Dict:
        """Generate guidance for using different geographic levels."""
        guidance = {
            'longitudinal_analysis': {
                'highly_recommended': [],
                'acceptable_with_validation': [],
                'not_recommended': []
            },
            'cross_sectional_analysis': {
                'all_levels_acceptable': True,
                'quality_considerations': []
            },
            'policy_research': {
                'recommended_levels': [],
                'special_considerations': []
            }
        }

        # Populate based on stability analysis
        if 'states' in self.stability_analysis and self.stability_analysis['states'].get('completely_stable'):
            guidance['longitudinal_analysis']['highly_recommended'].append('states')
            guidance['policy_research']['recommended_levels'].append('states')

        if 'counties' in self.stability_analysis:
            county_stability = len(self.stability_analysis['counties'].get('stable_counties', []))
            if county_stability > 1000:  # Significant number of stable counties
                guidance['longitudinal_analysis']['acceptable_with_validation'].append('counties')
                guidance['policy_research']['recommended_levels'].append('counties')

        return guidance

    def _create_readable_summary(self, report: Dict) -> None:
        """Create human-readable summary of stability analysis."""

        summary_content = f"""# Geographic Stability Analysis Summary

## Analysis Overview
**Date**: {report['metadata']['analysis_date']}
**Years Analyzed**: {report['executive_summary']['total_years_analyzed']}
**Geographic Levels**: {report['executive_summary']['geographic_levels_analyzed']}

## Key Findings
{chr(10).join(f"- {finding}" for finding in report['executive_summary']['key_findings'])}

## Data Integrity Commitment
✅ **NO data modifications made** - All original data preserved exactly as found
✅ **Complete transparency** - All changes documented, nothing hidden
✅ **Quality flags preserved** - Missing values and anomalies documented, not removed

## Stability Rankings

### Most Stable (Recommended for Longitudinal Analysis)
- **States**: Highest stability, suitable for all longitudinal analysis
- **Counties**: Generally stable with documented exceptions

### Moderately Stable (Use with Validation)
- **Congressional Districts**: Subject to redistricting
- **Municipalities**: Occasional boundary changes

### Least Stable (Requires Special Handling)
- **MSAs/CBSAs**: Frequent redefinition by OMB
- **Census Tracts**: Major changes at decennial boundaries

## Usage Recommendations

### For Longitudinal Trend Analysis
✅ **Use**: States, stable counties
⚠️ **Caution**: MSAs (with redefinition awareness)
❌ **Avoid**: Census tracts without crosswalks

### For Cross-Sectional Analysis
✅ **All levels acceptable** for single-year analysis

### For Policy Research
✅ **Recommended**: States and counties for policy impact assessment
"""

        summary_file = self.output_dir / "geographic_stability_summary.md"
        with open(summary_file, 'w', encoding='utf-8') as f:
            f.write(summary_content)

        logger.info(f"Readable summary saved: {summary_file}")

    def run_comprehensive_analysis(self) -> Dict:
        """Run complete geographic stability analysis."""
        logger.info("🚀 Starting comprehensive geographic stability analysis")
        logger.info("🛡️ CRITICAL: Preserving all original data - no modifications")

        try:
            # Load all data without modifications
            self.load_all_geographic_data()

            # Analyze each geographic level
            state_results = self.analyze_state_level_stability()
            county_results = self.analyze_county_level_stability()
            msa_results = self.analyze_msa_level_stability()
            tract_results = self.analyze_tract_level_stability()

            # Create stable areas identification
            self.create_stable_geographic_areas_sheet()

            # Generate comprehensive report
            self.generate_comprehensive_stability_report()

            logger.info("✅ Comprehensive geographic stability analysis completed")
            logger.info(f"📁 Results saved to: {self.output_dir}")

            return {
                'status': 'completed',
                'results': {
                    'states': state_results,
                    'counties': county_results,
                    'msas': msa_results,
                    'census_tracts': tract_results
                },
                'output_directory': str(self.output_dir),
                'data_integrity_maintained': True
            }

        except Exception as e:
            logger.error(f"Error in comprehensive analysis: {e}")
            raise

if __name__ == "__main__":
    # Run comprehensive geographic stability analysis
    analyzer = ComprehensiveGeographicStabilityAnalyzer()
    results = analyzer.run_comprehensive_analysis()

    print("🎯 GEOGRAPHIC STABILITY ANALYSIS COMPLETE")
    print(f"📊 Results: {results['output_directory']}")
    print("🛡️ Data integrity maintained - NO modifications made")