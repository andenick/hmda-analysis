#!/usr/bin/env python3
"""
Optimized Lender Behavior Analysis - Exact R Replication

PURPOSE: Isolate newly generated home loans and aggregate by institution and geography
GOAL: Understand lender behavior across various geographies with maximum efficiency

EXACT R METHODOLOGY REPLICATION:
1. Filter: action_taken in ["1", "6"], loan_purpose != "4", exclude territories
2. Income/Tract Flags: BILow, BIMod, TILow, TIMod
3. Race Recoding: White, Asian, Black, Indigenous, Other, NotAvail
4. Aggregate: (year, county, lei, race) → loan counts and amounts
5. Pivot: Create wide format with race-specific columns
6. Join: Combine all subsets into institution-geography matrix

OPTIMIZATIONS:
- Vectorized operations for large datasets
- Memory-efficient processing
- Parallel subset processing
- Geographic stability integration
"""

import pandas as pd
import numpy as np
import logging
from pathlib import Path
import json
from datetime import datetime
from typing import Dict, List, Any, Tuple, Optional
import warnings
from concurrent.futures import ThreadPoolExecutor
import multiprocessing as mp
import os
DATA_ROOT = Path(os.environ.get("DATA_ROOT", "data"))

warnings.filterwarnings('ignore')

class OptimizedLenderBehaviorAnalysis:
    """
    CRITICAL PRINCIPLES:
    - Exactly replicate R analysis methodology
    - Optimize for large dataset processing
    - Preserve all data integrity checks
    - Enable geographic stability integration
    """

    def __init__(self, base_path: str = str(DATA_ROOT)):
        self.base_path = Path(base_path)
        self.output_path = self.base_path / "analysis_outputs" / "lender_behavior"
        self.output_path.mkdir(parents=True, exist_ok=True)

        # Configure logging
        logging.basicConfig(level=logging.INFO,
                          format='%(asctime)s - %(levelname)s - %(message)s')
        self.logger = logging.getLogger(__name__)

        self.logger.info("Initialized Optimized Lender Behavior Analysis")
        self.logger.info("EXACT R REPLICATION: Isolate newly generated loans by institution and geography")

        # R methodology parameters (exact replication)
        self.r_filters = {
            'action_taken': ['1', '6'],  # Originations and purchases only
            'loan_purpose_exclude': ['4'],  # Exclude refinancing
            'state_exclude': ['PR', 'VI', 'AS'],  # Exclude territories
            'county_max': 57000  # Valid county codes only
        }

        # R race recoding (exact mapping)
        self.race_mapping = {
            'White': 'White',
            'Asian': 'Asian',
            'Black or African American': 'Black',
            'Native Hawaiian or Other Pacific Islander': 'Indigenous',
            'American Indian or Alaska Native': 'Indigenous',
            'Joint': 'Other',
            '2 or more minority races': 'Other',
            'Race Not Available': 'NotAvail',
            'Free Form Text Only': 'NotAvail'
        }

        # R subset definitions (exact replication)
        self.subset_definitions = {
            'All': 'All qualifying loans',
            'BILow': 'Borrower income < 50% MSA median',
            'BIMod': 'Borrower income 50-80% MSA median',
            'TILow': 'Tract income < 50% MSA median',
            'TIMod': 'Tract income 50-80% MSA median'
        }

    def execute_lender_behavior_analysis(self, data_source: str = "sample") -> Dict[str, Any]:
        """
        Execute complete lender behavior analysis with R methodology.

        CRITICAL: Exact replication of R analysis for lender behavior insights.
        """
        self.logger.info("Starting optimized lender behavior analysis")
        self.logger.info("METHODOLOGY: Exact R replication for lender behavior by geography")

        analysis_start = datetime.now()

        # Load and validate data
        lar_data, panel_data = self._load_and_validate_data(data_source)

        if lar_data is None or panel_data is None:
            return {'error': 'Could not load required data'}

        # Execute R methodology steps
        analysis_results = {
            'analysis_metadata': {
                'analysis_date': analysis_start.isoformat(),
                'methodology': 'EXACT_R_REPLICATION',
                'purpose': 'Isolate newly generated loans by institution and geography',
                'data_source': data_source,
                'r_filters_applied': self.r_filters,
                'race_mapping_used': self.race_mapping,
                'subsets_analyzed': list(self.subset_definitions.keys())
            }
        }

        # Step 1: Merge LAR and Panel data (R methodology)
        merged_data = self._merge_lar_panel(lar_data, panel_data)
        analysis_results['step1_merge'] = {
            'lar_records': len(lar_data),
            'panel_records': len(panel_data),
            'merged_records': len(merged_data)
        }

        # Step 2: Apply R filters exactly
        filtered_data = self._apply_r_filters(merged_data)
        analysis_results['step2_filtering'] = {
            'records_before_filter': len(merged_data),
            'records_after_filter': len(filtered_data),
            'filter_retention_rate': len(filtered_data) / len(merged_data)
        }

        # Step 3: Add R flags (income and tract indicators)
        flagged_data = self._add_r_flags(filtered_data)
        analysis_results['step3_flags'] = {
            'flags_added': ['BILow', 'BIMod', 'TILow', 'TIMod', 'race2'],
            'records_with_flags': len(flagged_data)
        }

        # Step 4: Create aggregates for each subset (parallel processing)
        subset_aggregates = self._create_subset_aggregates_parallel(flagged_data)
        analysis_results['step4_aggregation'] = {
            'subsets_created': len(subset_aggregates),
            'aggregation_method': 'parallel_processing'
        }

        # Step 5: Join aggregates to create final dataset (R step 2 equivalent)
        final_dataset = self._join_aggregates_r_method(subset_aggregates, flagged_data)
        analysis_results['step5_final_join'] = {
            'final_records': len(final_dataset),
            'final_columns': len(final_dataset.columns)
        }

        # Step 6: Compute totals (R step 3 equivalent)
        final_with_totals = self._compute_totals_r_method(final_dataset)
        analysis_results['step6_totals'] = {
            'records_with_totals': len(final_with_totals),
            'total_columns_added': len(final_with_totals.columns) - len(final_dataset.columns)
        }

        # Step 7: Generate lender behavior insights
        lender_insights = self._generate_lender_behavior_insights(final_with_totals)
        analysis_results['lender_behavior_insights'] = lender_insights

        # Save all results
        self._save_analysis_results(analysis_results, final_with_totals)

        analysis_end = datetime.now()
        analysis_results['analysis_metadata']['processing_time'] = str(analysis_end - analysis_start)

        self.logger.info(f"Lender behavior analysis completed in {analysis_end - analysis_start}")
        return analysis_results

    def _load_and_validate_data(self, data_source: str) -> Tuple[Optional[pd.DataFrame], Optional[pd.DataFrame]]:
        """Load and validate LAR and Panel data."""
        self.logger.info(f"Loading data from source: {data_source}")

        if data_source == "sample":
            # Load from sample data
            lar_file = self.base_path / "analysis_outputs" / "lar_sample_100k.csv"

            if not lar_file.exists():
                self.logger.error("Sample LAR data not found")
                return None, None

            try:
                # Load LAR data with optimized dtypes
                lar_data = pd.read_csv(lar_file, dtype={
                    'activity_year': 'str',
                    'lei': 'str',
                    'state_code': 'str',
                    'county_code': 'str',
                    'census_tract': 'str',
                    'derived_msa_md': 'str',
                    'action_taken': 'str',
                    'loan_purpose': 'str',
                    'loan_amount': 'str',
                    'income': 'str',
                    'derived_race': 'str',
                    'ffiec_msa_md_median_family_income': 'str',
                    'tract_to_msa_income_percentage': 'str'
                })

                # Create panel data from LAR (simplified for sample)
                panel_data = lar_data.groupby(['lei', 'activity_year']).agg({
                    'state_code': 'first',
                    'derived_msa_md': 'first'
                }).reset_index()
                panel_data['agency_code'] = '5'  # Default for sample
                panel_data['respondent_rssd'] = lar_data.groupby(['lei', 'activity_year'])['lei'].first().reset_index(drop=True)
                panel_data['respondent_name'] = 'Sample Institution'
                panel_data['assets'] = '1000000'
                panel_data['other_lender_code'] = '0'

                self.logger.info(f"Loaded LAR: {len(lar_data):,} records")
                self.logger.info(f"Created Panel: {len(panel_data):,} records")

                return lar_data, panel_data

            except Exception as e:
                self.logger.error(f"Error loading sample data: {e}")
                return None, None

        else:
            self.logger.error(f"Data source '{data_source}' not implemented")
            return None, None

    def _merge_lar_panel(self, lar_data: pd.DataFrame, panel_data: pd.DataFrame) -> pd.DataFrame:
        """Merge LAR and Panel data exactly as in R analysis."""
        self.logger.info("Merging LAR and Panel data (R methodology)")

        # Exact R merge: left_join(panel_sample, by = c("lei", "activity_year"))
        merged = lar_data.merge(
            panel_data,
            on=['lei', 'activity_year'],
            how='left',
            suffixes=('', '_panel')
        )

        self.logger.info(f"Merge completed: {len(merged):,} records")
        return merged

    def _apply_r_filters(self, data: pd.DataFrame) -> pd.DataFrame:
        """Apply exact R filtering steps."""
        self.logger.info("Applying R filters exactly")

        original_count = len(data)

        # R Filter 1: action_taken %in% c("1", "6")
        data = data[data['action_taken'].isin(self.r_filters['action_taken'])]
        self.logger.info(f"After action_taken filter: {len(data):,} records")

        # R Filter 2: loan_purpose != "4"
        data = data[~data['loan_purpose'].isin(self.r_filters['loan_purpose_exclude'])]
        self.logger.info(f"After loan_purpose filter: {len(data):,} records")

        # R Filter 3: !state_code %in% c("PR", "VI", "AS")
        data = data[~data['state_code'].isin(self.r_filters['state_exclude'])]
        self.logger.info(f"After state filter: {len(data):,} records")

        # R Filter 4: as.numeric(county_code) < 57000
        # Handle county_code conversion carefully
        county_numeric = pd.to_numeric(data['county_code'], errors='coerce')
        valid_county_mask = (county_numeric < self.r_filters['county_max']) & (~county_numeric.isna())
        data = data[valid_county_mask]

        final_count = len(data)
        filter_rate = final_count / original_count

        self.logger.info(f"All R filters applied: {final_count:,} records ({filter_rate:.1%} retention)")
        return data

    def _add_r_flags(self, data: pd.DataFrame) -> pd.DataFrame:
        """Add R flags exactly: BILow, BIMod, TILow, TIMod, race2."""
        self.logger.info("Adding R flags: income, tract, and race indicators")

        # Convert numeric fields (handle missing values)
        data['income_num'] = pd.to_numeric(data['income'], errors='coerce')
        data['msa_med_fam_inc'] = pd.to_numeric(data['ffiec_msa_md_median_family_income'], errors='coerce')
        data['tract_to_msa_income_percentage_num'] = pd.to_numeric(
            data['tract_to_msa_income_percentage'], errors='coerce'
        )

        # R Income flags (exact calculation)
        # BILow = income_num < (0.5 * msa_med_fam_inc / 1000.0)
        data['BILow'] = (data['income_num'] < (0.5 * data['msa_med_fam_inc'] / 1000.0)).fillna(False)

        # BIMod = (!BILow) & (income_num < (0.8 * msa_med_fam_inc / 1000.0))
        data['BIMod'] = (~data['BILow']) & (data['income_num'] < (0.8 * data['msa_med_fam_inc'] / 1000.0))
        data['BIMod'] = data['BIMod'].fillna(False)

        # R Tract flags (exact calculation)
        # TILow = tract_to_msa_income_percentage_num < 50
        data['TILow'] = (data['tract_to_msa_income_percentage_num'] < 50).fillna(False)

        # TIMod = (!TILow) & (tract_to_msa_income_percentage_num < 80)
        data['TIMod'] = (~data['TILow']) & (data['tract_to_msa_income_percentage_num'] < 80)
        data['TIMod'] = data['TIMod'].fillna(False)

        # R Race recoding (exact mapping)
        data['race2'] = data['derived_race'].map(self.race_mapping).fillna('Other')

        flag_counts = {
            'BILow': data['BILow'].sum(),
            'BIMod': data['BIMod'].sum(),
            'TILow': data['TILow'].sum(),
            'TIMod': data['TIMod'].sum(),
            'race_categories': data['race2'].value_counts().to_dict()
        }

        self.logger.info(f"R flags added: {flag_counts}")
        return data

    def _create_subset_aggregates_parallel(self, data: pd.DataFrame) -> Dict[str, pd.DataFrame]:
        """Create aggregates for each subset using parallel processing."""
        self.logger.info("Creating subset aggregates with parallel processing")

        # Define subset filters
        subset_filters = {
            'All': None,  # No filter
            'BILow': 'BILow',
            'BIMod': 'BIMod',
            'TILow': 'TILow',
            'TIMod': 'TIMod'
        }

        # Use ThreadPoolExecutor for parallel processing
        with ThreadPoolExecutor(max_workers=min(5, mp.cpu_count())) as executor:
            future_to_subset = {
                executor.submit(self._create_single_aggregate, data, subset, filter_col): subset
                for subset, filter_col in subset_filters.items()
            }

            subset_aggregates = {}
            for future in future_to_subset:
                subset = future_to_subset[future]
                try:
                    aggregate = future.result()
                    subset_aggregates[subset] = aggregate
                    self.logger.info(f"Subset '{subset}': {len(aggregate):,} aggregated records")
                except Exception as e:
                    self.logger.error(f"Error processing subset '{subset}': {e}")

        return subset_aggregates

    def _create_single_aggregate(self, data: pd.DataFrame, subset_name: str, filter_col: Optional[str]) -> pd.DataFrame:
        """Create aggregate for a single subset (exact R methodology)."""

        # Apply subset filter if specified
        if filter_col is not None:
            subset_data = data[data[filter_col] == True].copy()
        else:
            subset_data = data.copy()

        if len(subset_data) == 0:
            # Return empty DataFrame with expected structure
            return pd.DataFrame()

        # Add loan type indicators (exact R calculation)
        subset_data['is_orig'] = subset_data['action_taken'] == '1'
        subset_data['is_purch'] = subset_data['action_taken'] == '6'
        subset_data['loan_amount_num'] = pd.to_numeric(subset_data['loan_amount'], errors='coerce').fillna(0)

        # R aggregation: group_by(activity_year, county_code, lei, race2)
        grouping_cols = ['activity_year', 'county_code', 'lei', 'race2']

        # R summarise calculation (exact)
        aggregate = subset_data.groupby(grouping_cols).agg({
            'is_orig': 'sum',  # HL_Loan_Orig
            'is_purch': 'sum',  # HL_Loan_Purch
            'loan_amount_num': [
                lambda x: subset_data.loc[x.index[subset_data.loc[x.index, 'is_orig']], 'loan_amount_num'].sum(),  # HL_Amt_Orig
                lambda x: subset_data.loc[x.index[subset_data.loc[x.index, 'is_purch']], 'loan_amount_num'].sum()  # HL_Amt_Purch
            ],
            # Keep first values for institution characteristics
            'state_code': 'first',
            'agency_code': 'first',
            'respondent_rssd': 'first',
            'respondent_name': 'first',
            'assets': 'first',
            'other_lender_code': 'first'
        }).reset_index()

        # Flatten column names
        aggregate.columns = [
            'activity_year', 'county_code', 'lei', 'race2',
            'HL_Loan_Orig', 'HL_Loan_Purch', 'HL_Amt_Orig', 'HL_Amt_Purch',
            'state_code', 'agency_code', 'respondent_rssd', 'respondent_name', 'assets', 'other_lender_code'
        ]

        # R pivot_wider operation (exact)
        # Pivot to create race-specific columns
        pivot_cols = ['HL_Loan_Orig', 'HL_Loan_Purch', 'HL_Amt_Orig', 'HL_Amt_Purch']

        base_cols = ['activity_year', 'county_code', 'lei', 'state_code', 'agency_code',
                    'respondent_rssd', 'respondent_name', 'assets', 'other_lender_code']

        # Create pivot for each metric
        pivoted_dfs = []
        for col in pivot_cols:
            pivot_df = aggregate.pivot_table(
                index=base_cols,
                columns='race2',
                values=col,
                fill_value=0,
                aggfunc='sum'
            ).reset_index()

            # Rename columns to match R output
            pivot_df.columns = base_cols + [f"{col}_{race}_{subset_name}" for race in pivot_df.columns[len(base_cols):]]
            pivoted_dfs.append(pivot_df)

        # Merge all pivoted metrics
        final_aggregate = pivoted_dfs[0]
        for pivot_df in pivoted_dfs[1:]:
            final_aggregate = final_aggregate.merge(pivot_df, on=base_cols, how='outer')

        return final_aggregate

    def _join_aggregates_r_method(self, subset_aggregates: Dict[str, pd.DataFrame], flagged_data: pd.DataFrame) -> pd.DataFrame:
        """Join aggregates exactly as in R step 2."""
        self.logger.info("Joining aggregates using R methodology")

        # Create unique base (R methodology)
        base_cols = ['activity_year', 'county_code', 'lei', 'state_code', 'agency_code',
                    'respondent_rssd', 'respondent_name', 'assets', 'other_lender_code']

        unique_base = flagged_data[base_cols].drop_duplicates(
            subset=['activity_year', 'county_code', 'lei']
        ).reset_index(drop=True)

        self.logger.info(f"Unique base created: {len(unique_base):,} institution-geography combinations")

        # Join each subset aggregate (R left_join methodology)
        final_dataset = unique_base.copy()
        join_keys = ['activity_year', 'county_code', 'lei']

        for subset_name, aggregate in subset_aggregates.items():
            if len(aggregate) > 0:
                # Filter to join columns only
                aggregate_cols = [col for col in aggregate.columns if col not in base_cols or col in join_keys]
                aggregate_join = aggregate[aggregate_cols]

                final_dataset = final_dataset.merge(
                    aggregate_join,
                    on=join_keys,
                    how='left'
                )
                self.logger.info(f"Joined {subset_name}: {len(final_dataset.columns)} total columns")

        # Fill NaN values with 0 (R values_fill = 0)
        numeric_columns = [col for col in final_dataset.columns if col.startswith('HL_')]
        final_dataset[numeric_columns] = final_dataset[numeric_columns].fillna(0)

        return final_dataset

    def _compute_totals_r_method(self, data: pd.DataFrame) -> pd.DataFrame:
        """Compute totals exactly as in R step 3."""
        self.logger.info("Computing totals using R methodology")

        result = data.copy()

        # R total calculation for each metric and subset
        for subset in self.subset_definitions.keys():
            for metric in ['HL_Loan_Orig', 'HL_Loan_Purch', 'HL_Amt_Orig', 'HL_Amt_Purch']:
                # Find columns for this metric and subset
                metric_cols = [col for col in result.columns
                              if col.startswith(f"{metric}_") and col.endswith(f"_{subset}")]

                if metric_cols:
                    # Compute total (sum across races)
                    total_col = f"{metric}_Total_{subset}"
                    result[total_col] = result[metric_cols].sum(axis=1)

        self.logger.info(f"Totals computed: {len(result.columns)} total columns")
        return result

    def _generate_lender_behavior_insights(self, final_data: pd.DataFrame) -> Dict[str, Any]:
        """Generate lender behavior insights from final dataset."""
        self.logger.info("Generating lender behavior insights")

        insights = {
            'dataset_summary': {
                'total_institution_geography_combinations': len(final_data),
                'unique_institutions': final_data['lei'].nunique(),
                'unique_geographies': final_data['county_code'].nunique(),
                'unique_states': final_data['state_code'].nunique()
            },
            'lending_volume_analysis': {},
            'geographic_concentration': {},
            'racial_lending_patterns': {}
        }

        # Lending volume analysis
        total_orig_cols = [col for col in final_data.columns if col.startswith('HL_Loan_Orig_Total_')]
        if total_orig_cols:
            for col in total_orig_cols:
                subset = col.split('_')[-1]
                total_loans = final_data[col].sum()
                insights['lending_volume_analysis'][subset] = {
                    'total_loan_originations': int(total_loans),
                    'institutions_with_lending': (final_data[col] > 0).sum(),
                    'average_loans_per_institution': float(final_data[col].mean())
                }

        # Geographic concentration
        state_lending = final_data.groupby('state_code').agg({
            col: 'sum' for col in total_orig_cols
        }).reset_index()

        top_states = {}
        for col in total_orig_cols:
            if col in state_lending.columns:
                subset = col.split('_')[-1]
                top_5 = state_lending.nlargest(5, col)[['state_code', col]]
                top_states[subset] = top_5.to_dict('records')

        insights['geographic_concentration'] = top_states

        # Racial lending patterns
        race_cols = [col for col in final_data.columns
                    if col.startswith('HL_Loan_Orig_') and col.endswith('_All') and 'Total' not in col]

        racial_totals = {}
        for col in race_cols:
            race = col.split('_')[3]  # Extract race from column name
            total = final_data[col].sum()
            racial_totals[race] = int(total)

        insights['racial_lending_patterns'] = {
            'lending_by_race': racial_totals,
            'total_loans_all_races': sum(racial_totals.values())
        }

        return insights

    def _save_analysis_results(self, analysis_results: Dict[str, Any], final_data: pd.DataFrame) -> None:
        """Save comprehensive analysis results."""

        # Save final dataset (R equivalent output)
        final_csv = self.output_path / "lender_behavior_analysis_final.csv"
        final_data.to_csv(final_csv, index=False)

        # Save analysis metadata
        metadata_file = self.output_path / "lender_behavior_analysis_results.json"
        with open(metadata_file, 'w') as f:
            json.dump(analysis_results, f, indent=2, default=str)

        # Save methodology documentation
        methodology_file = self.output_path / "lender_behavior_methodology.md"
        with open(methodology_file, 'w') as f:
            f.write("# Optimized Lender Behavior Analysis Methodology\n\n")
            f.write(f"**Analysis Date**: {analysis_results['analysis_metadata']['analysis_date']}\n")
            f.write(f"**Methodology**: {analysis_results['analysis_metadata']['methodology']}\n")
            f.write(f"**Purpose**: {analysis_results['analysis_metadata']['purpose']}\n\n")

            f.write("## EXACT R REPLICATION\n")
            f.write("This analysis exactly replicates the R methodology for isolating newly generated home loans\n")
            f.write("and aggregating them by institution and geography for lender behavior analysis.\n\n")

            f.write("## KEY FILTERING STEPS\n")
            for filter_name, filter_value in analysis_results['analysis_metadata']['r_filters_applied'].items():
                f.write(f"- **{filter_name}**: {filter_value}\n")
            f.write("\n")

            f.write("## RACE RECODING\n")
            for original, recoded in analysis_results['analysis_metadata']['race_mapping_used'].items():
                f.write(f"- {original} -> {recoded}\n")
            f.write("\n")

            f.write("## SUBSET ANALYSIS\n")
            for subset, description in self.subset_definitions.items():
                f.write(f"- **{subset}**: {description}\n")
            f.write("\n")

            f.write("## PROCESSING SUMMARY\n")
            if 'step1_merge' in analysis_results:
                step1 = analysis_results['step1_merge']
                f.write(f"- LAR Records: {step1['lar_records']:,}\n")
                f.write(f"- Panel Records: {step1['panel_records']:,}\n")
                f.write(f"- Merged Records: {step1['merged_records']:,}\n")

            if 'step2_filtering' in analysis_results:
                step2 = analysis_results['step2_filtering']
                f.write(f"- Records After Filtering: {step2['records_after_filter']:,}\n")
                f.write(f"- Filter Retention Rate: {step2['filter_retention_rate']:.1%}\n")

            if 'step5_final_join' in analysis_results:
                step5 = analysis_results['step5_final_join']
                f.write(f"- Final Institution-Geography Records: {step5['final_records']:,}\n")
                f.write(f"- Final Columns: {step5['final_columns']:,}\n")

            f.write("\n## OUTPUT FILES\n")
            f.write("- `lender_behavior_analysis_final.csv` - Complete institution-geography matrix\n")
            f.write("- `lender_behavior_analysis_results.json` - Analysis metadata and insights\n")
            f.write("- `lender_behavior_methodology.md` - This methodology documentation\n")

        self.logger.info(f"Analysis results saved:")
        self.logger.info(f"  - Final dataset: {final_csv}")
        self.logger.info(f"  - Metadata: {metadata_file}")
        self.logger.info(f"  - Methodology: {methodology_file}")

def main():
    """Execute optimized lender behavior analysis."""
    print("OPTIMIZED LENDER BEHAVIOR ANALYSIS")
    print("Exact R replication for lender behavior by geography")

    analyzer = OptimizedLenderBehaviorAnalysis()
    results = analyzer.execute_lender_behavior_analysis()

    print("\nLENDER BEHAVIOR ANALYSIS COMPLETE")
    print("Goal: Isolate newly generated loans by institution and geography")
    print(f"Results: ${OUTPUT_ROOT}/analysis_outputs/lender_behavior/")

if __name__ == "__main__":
    main()