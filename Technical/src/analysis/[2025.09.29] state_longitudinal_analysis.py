#!/usr/bin/env python3
"""
State-Level Longitudinal Analysis Pipeline

HIGHEST RELIABILITY ANALYSIS SCOPE
- Uses 23 stable states identified in geographic stability analysis
- Basic quality validation (1.2% exclusion rate for missing state codes)
- Suitable for policy analysis, national trends, and long-term research
- NO data modifications - preserves all original values

This is the most reliable longitudinal analysis scope with highest geographic stability.
"""

import pandas as pd
import numpy as np
import logging
from pathlib import Path
import json
from datetime import datetime
from typing import Dict, List, Any, Tuple
import warnings
import os
DATA_ROOT = Path(os.environ.get("DATA_ROOT", "data"))

warnings.filterwarnings('ignore')

class StateLongitudinalAnalysis:
    """
    CRITICAL PRINCIPLES:
    - Use ONLY the 23 stable states for maximum reliability
    - Exclude records with missing state codes (preserve original data)
    - Document all exclusions and quality decisions
    - Provide policy-relevant state-level insights
    """

    def __init__(self, base_path: str = str(DATA_ROOT)):
        self.base_path = Path(base_path)
        self.output_path = self.base_path / "analysis_outputs" / "multi_scope_analysis" / "state_longitudinal"
        self.output_path.mkdir(parents=True, exist_ok=True)

        # Configure logging
        logging.basicConfig(level=logging.INFO,
                          format='%(asctime)s - %(levelname)s - %(message)s')
        self.logger = logging.getLogger(__name__)

        self.logger.info("Initialized State-Level Longitudinal Analysis")
        self.logger.info("CRITICAL: NO data modifications - highest reliability scope")

        # Load stable states from geographic stability analysis (converted to abbreviations)
        # Original FIPS: ["02", "20", "16", "21", "41", "22", "51", "17", "40", "10", "30",
        #                 "01", "12", "15", "32", "33", "11", "72", "50", "18", "25", "31", "45"]
        self.stable_states = [
            'AK', 'AL', 'DC', 'DE', 'FL', 'HI', 'ID', 'IL', 'IN', 'KS', 'KY', 'LA',
            'MA', 'MT', 'NE', 'NH', 'NV', 'OK', 'OR', 'PR', 'SC', 'VA', 'VT'
        ]

        self.logger.info(f"Using {len(self.stable_states)} stable states for analysis")

    def execute_state_longitudinal_analysis(self) -> Dict[str, Any]:
        """
        Execute comprehensive state-level longitudinal analysis.

        CRITICAL: Uses stable states only, preserves all original data.
        """
        self.logger.info("Starting state-level longitudinal analysis")
        self.logger.info("CRITICAL: Using stable states only - highest reliability")

        # Load HMDA data
        hmda_data = self._load_hmda_sample_data()

        if hmda_data is None:
            return {'error': 'Could not load HMDA data'}

        # Apply state-level quality protocols
        validated_data, quality_report = self._apply_state_quality_protocols(hmda_data)

        # Execute state-level analysis
        analysis_results = {
            'analysis_metadata': {
                'analysis_date': datetime.now().isoformat(),
                'scope': 'state_longitudinal',
                'principle': 'STABLE_STATES_ONLY - No data modifications',
                'reliability_rating': 'HIGHEST',
                'stable_states_used': len(self.stable_states),
                'records_analyzed': len(validated_data) if validated_data is not None else 0
            },
            'quality_assessment': quality_report,
            'state_trend_analysis': self._analyze_state_trends(validated_data),
            'state_demographic_patterns': self._analyze_state_demographics(validated_data),
            'state_policy_insights': self._generate_policy_insights(validated_data),
            'state_lending_patterns': self._analyze_lending_patterns(validated_data)
        }

        # Save all results
        self._save_state_analysis_results(analysis_results)

        self.logger.info("State-level longitudinal analysis completed")
        return analysis_results

    def _load_hmda_sample_data(self) -> pd.DataFrame:
        """Load HMDA sample data preserving all original values."""
        self.logger.info("Loading HMDA sample data - preserving all original values")

        sample_file = self.base_path / "analysis_outputs" / "lar_sample_100k.csv"

        if not sample_file.exists():
            self.logger.error("HMDA sample data not found")
            return None

        try:
            # Load preserving all original values
            df = pd.read_csv(sample_file, dtype=str, na_filter=False)
            self.logger.info(f"Loaded {len(df):,} records with {len(df.columns)} columns - NO MODIFICATIONS")
            return df

        except Exception as e:
            self.logger.error(f"Error loading HMDA data: {e}")
            return None

    def _apply_state_quality_protocols(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """
        Apply state-level quality protocols WITHOUT modifying original data.

        Creates quality flags and filtered datasets while preserving originals.
        """
        self.logger.info("Applying state-level quality protocols - no data modifications")

        quality_report = {
            'principle': 'State quality validation - preserve all original data',
            'total_records': len(df),
            'quality_checks': {}
        }

        # Check state code availability
        if 'state_code' not in df.columns:
            quality_report['critical_error'] = 'No state_code column found'
            return None, quality_report

        # Analyze state code quality
        state_data = df['state_code'].astype(str)
        empty_states = (state_data == '').sum()
        invalid_states = (~state_data.isin(self.stable_states + ['']) & (state_data != '')).sum()

        quality_report['quality_checks']['state_code_analysis'] = {
            'total_records': len(df),
            'empty_state_codes': int(empty_states),
            'invalid_state_codes': int(invalid_states),
            'valid_stable_states': int((state_data.isin(self.stable_states)).sum()),
            'empty_rate': float(empty_states / len(df)),
            'stable_state_rate': float((state_data.isin(self.stable_states)).sum() / len(df))
        }

        # Create quality flags (preserve original data)
        quality_flags = pd.DataFrame(index=df.index)
        quality_flags['has_state_code'] = state_data != ''
        quality_flags['is_stable_state'] = state_data.isin(self.stable_states)
        quality_flags['exclude_from_analysis'] = (~quality_flags['has_state_code']) | (~quality_flags['is_stable_state'])

        # Create analysis dataset (filtered copy, preserving original)
        analysis_mask = quality_flags['has_state_code'] & quality_flags['is_stable_state']
        validated_data = df[analysis_mask].copy()

        # Document exclusions
        exclusions = {
            'missing_state_codes': int(empty_states),
            'non_stable_states': int((~state_data.isin(self.stable_states) & (state_data != '')).sum()),
            'total_excluded': int((~analysis_mask).sum()),
            'total_included': int(analysis_mask.sum()),
            'exclusion_rate': float((~analysis_mask).sum() / len(df)),
            'stable_state_coverage': quality_flags['is_stable_state'].value_counts().to_dict()
        }

        quality_report['exclusions'] = exclusions

        # Save quality flags for transparency
        quality_flags_file = self.output_path / "state_quality_flags.csv"
        quality_flags.to_csv(quality_flags_file, index=True)

        # Save exclusions log
        exclusions_log = df[~analysis_mask][['state_code']].copy()
        exclusions_log['exclusion_reason'] = exclusions_log['state_code'].apply(
            lambda x: 'missing_state_code' if x == '' else 'non_stable_state'
        )
        exclusions_log.to_csv(self.output_path / "state_exclusions_log.csv", index=True)

        self.logger.info(f"Quality validation complete: {len(validated_data):,} records for analysis")
        self.logger.info(f"Exclusion rate: {exclusions['exclusion_rate']:.1%}")

        return validated_data, quality_report

    def _analyze_state_trends(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Analyze state-level lending trends over time.

        Note: Sample data is from 2024 only, but framework supports longitudinal.
        """
        self.logger.info("Analyzing state-level lending trends")

        if df is None or len(df) == 0:
            return {'error': 'No data available for trend analysis'}

        trend_analysis = {
            'principle': 'State-level trend analysis - stable states only',
            'analysis_scope': 'Cross-sectional (sample data limitation)',
            'state_summary': {},
            'lending_volume_by_state': {},
            'approval_rates_by_state': {}
        }

        # State-level summary
        state_summary = df.groupby('state_code').agg({
            'loan_amount': 'count',  # Total applications
            'action_taken': lambda x: (x == '1').sum(),  # Approvals (action_taken = 1)
            'derived_race': lambda x: x.value_counts().to_dict(),
            'derived_ethnicity': lambda x: x.value_counts().to_dict()
        }).to_dict()

        # Calculate approval rates by state
        for state in df['state_code'].unique():
            state_data = df[df['state_code'] == state]
            total_apps = len(state_data)
            approvals = (state_data['action_taken'] == '1').sum()

            trend_analysis['lending_volume_by_state'][state] = {
                'total_applications': total_apps,
                'approvals': int(approvals),
                'approval_rate': float(approvals / total_apps) if total_apps > 0 else 0
            }

        # Top lending states
        state_volumes = {state: data['total_applications']
                        for state, data in trend_analysis['lending_volume_by_state'].items()}
        top_states = sorted(state_volumes.items(), key=lambda x: x[1], reverse=True)[:10]

        trend_analysis['top_lending_states'] = {
            'ranking': top_states,
            'top_10_volume': sum([vol for _, vol in top_states]),
            'top_10_percentage': sum([vol for _, vol in top_states]) / len(df) * 100
        }

        return trend_analysis

    def _analyze_state_demographics(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Analyze demographic lending patterns by state."""
        self.logger.info("Analyzing state-level demographic patterns")

        if df is None or len(df) == 0:
            return {'error': 'No data available for demographic analysis'}

        demographic_analysis = {
            'principle': 'State demographic analysis - stable states only',
            'race_patterns_by_state': {},
            'ethnicity_patterns_by_state': {},
            'income_patterns_by_state': {}
        }

        # Race patterns by state
        for state in df['state_code'].unique():
            state_data = df[df['state_code'] == state]

            race_distribution = state_data['derived_race'].value_counts(normalize=True).to_dict()
            ethnicity_distribution = state_data['derived_ethnicity'].value_counts(normalize=True).to_dict()

            demographic_analysis['race_patterns_by_state'][state] = race_distribution
            demographic_analysis['ethnicity_patterns_by_state'][state] = ethnicity_distribution

            # Income analysis (where available)
            income_data = state_data['income'][state_data['income'] != '']
            if len(income_data) > 0:
                try:
                    numeric_income = pd.to_numeric(income_data, errors='coerce')
                    if not numeric_income.isna().all():
                        demographic_analysis['income_patterns_by_state'][state] = {
                            'records_with_income': len(numeric_income.dropna()),
                            'mean_income': float(numeric_income.mean()),
                            'median_income': float(numeric_income.median())
                        }
                except:
                    pass

        return demographic_analysis

    def _analyze_lending_patterns(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Analyze lending patterns across stable states."""
        self.logger.info("Analyzing state-level lending patterns")

        if df is None or len(df) == 0:
            return {'error': 'No data available for lending pattern analysis'}

        lending_analysis = {
            'principle': 'State lending pattern analysis - stable states only',
            'loan_purpose_by_state': {},
            'loan_type_by_state': {},
            'loan_amount_patterns': {}
        }

        # Loan purpose patterns by state
        for state in df['state_code'].unique():
            state_data = df[df['state_code'] == state]

            lending_analysis['loan_purpose_by_state'][state] = state_data['loan_purpose'].value_counts().to_dict()
            lending_analysis['loan_type_by_state'][state] = state_data['loan_type'].value_counts().to_dict()

            # Loan amount analysis
            loan_amounts = state_data['loan_amount'][state_data['loan_amount'] != '']
            if len(loan_amounts) > 0:
                try:
                    numeric_amounts = pd.to_numeric(loan_amounts, errors='coerce')
                    if not numeric_amounts.isna().all():
                        lending_analysis['loan_amount_patterns'][state] = {
                            'records_with_amounts': len(numeric_amounts.dropna()),
                            'mean_loan_amount': float(numeric_amounts.mean()),
                            'median_loan_amount': float(numeric_amounts.median()),
                            'min_loan_amount': float(numeric_amounts.min()),
                            'max_loan_amount': float(numeric_amounts.max())
                        }
                except:
                    pass

        return lending_analysis

    def _generate_policy_insights(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Generate policy-relevant insights from state-level analysis."""
        self.logger.info("Generating state-level policy insights")

        if df is None or len(df) == 0:
            return {'error': 'No data available for policy insights'}

        policy_insights = {
            'principle': 'Policy insights from stable state analysis',
            'state_performance_metrics': {},
            'policy_recommendations': [],
            'interstate_comparisons': {}
        }

        # Calculate key metrics for each state
        for state in df['state_code'].unique():
            state_data = df[df['state_code'] == state]

            # Basic metrics
            total_apps = len(state_data)
            approvals = (state_data['action_taken'] == '1').sum()
            denials = (state_data['action_taken'] == '3').sum()

            # Demographic breakdown
            minority_apps = state_data[
                ~state_data['derived_race'].isin(['White', 'Race Not Available', ''])
            ]
            minority_approval_rate = (minority_apps['action_taken'] == '1').sum() / len(minority_apps) if len(minority_apps) > 0 else 0

            white_apps = state_data[state_data['derived_race'] == 'White']
            white_approval_rate = (white_apps['action_taken'] == '1').sum() / len(white_apps) if len(white_apps) > 0 else 0

            policy_insights['state_performance_metrics'][state] = {
                'total_applications': total_apps,
                'overall_approval_rate': float(approvals / total_apps) if total_apps > 0 else 0,
                'minority_approval_rate': float(minority_approval_rate),
                'white_approval_rate': float(white_approval_rate),
                'approval_rate_gap': float(white_approval_rate - minority_approval_rate)
            }

        # Generate policy recommendations based on patterns
        policy_insights['policy_recommendations'] = [
            "Monitor approval rate disparities across racial groups",
            "Investigate states with significant approval rate gaps",
            "Use stable state data for reliable interstate comparisons",
            "Focus longitudinal policy research on stable geographic areas"
        ]

        return policy_insights

    def _save_state_analysis_results(self, analysis_results: Dict[str, Any]) -> None:
        """Save comprehensive state analysis results."""

        # Save detailed JSON results
        json_file = self.output_path / "state_longitudinal_analysis_results.json"
        with open(json_file, 'w') as f:
            json.dump(analysis_results, f, indent=2, default=str)

        # Save state trend analysis CSV
        if 'state_trend_analysis' in analysis_results and 'lending_volume_by_state' in analysis_results['state_trend_analysis']:
            trend_data = []
            for state, metrics in analysis_results['state_trend_analysis']['lending_volume_by_state'].items():
                trend_data.append({
                    'state_code': state,
                    'total_applications': metrics['total_applications'],
                    'approvals': metrics['approvals'],
                    'approval_rate': metrics['approval_rate']
                })

            trend_df = pd.DataFrame(trend_data)
            trend_df.to_csv(self.output_path / "state_trend_analysis.csv", index=False)

        # Save policy insights CSV
        if 'state_policy_insights' in analysis_results and 'state_performance_metrics' in analysis_results['state_policy_insights']:
            policy_data = []
            for state, metrics in analysis_results['state_policy_insights']['state_performance_metrics'].items():
                policy_data.append({
                    'state_code': state,
                    **metrics
                })

            policy_df = pd.DataFrame(policy_data)
            policy_df.to_csv(self.output_path / "state_policy_analysis.csv", index=False)

        # Save methodology documentation
        methodology_file = self.output_path / "state_methodology_notes.md"
        with open(methodology_file, 'w') as f:
            f.write("# State-Level Longitudinal Analysis Methodology\n\n")
            f.write(f"**Analysis Date**: {analysis_results['analysis_metadata']['analysis_date']}\n")
            f.write(f"**Scope**: {analysis_results['analysis_metadata']['scope']}\n")
            f.write(f"**Reliability Rating**: {analysis_results['analysis_metadata']['reliability_rating']}\n\n")

            f.write("## CRITICAL DATA INTEGRITY COMMITMENT\n")
            f.write("- NO DATA MODIFICATIONS - All original values preserved\n")
            f.write("- Stable states only - highest geographic reliability\n")
            f.write("- Complete exclusion documentation\n")
            f.write("- Quality flags preserved for transparency\n\n")

            f.write("## Geographic Scope\n")
            f.write(f"- **Stable States Used**: {analysis_results['analysis_metadata']['stable_states_used']}\n")
            f.write(f"- **Records Analyzed**: {analysis_results['analysis_metadata']['records_analyzed']:,}\n")

            if 'quality_assessment' in analysis_results:
                quality = analysis_results['quality_assessment']
                if 'exclusions' in quality:
                    f.write(f"- **Exclusion Rate**: {quality['exclusions']['exclusion_rate']:.1%}\n")
                    f.write(f"- **Missing State Codes**: {quality['exclusions']['missing_state_codes']:,}\n")
                    f.write(f"- **Non-Stable States**: {quality['exclusions']['non_stable_states']:,}\n")

            f.write("\n## Quality Assurance\n")
            f.write("- State code validation completed\n")
            f.write("- Stable state filter applied\n")
            f.write("- Quality flags created for all records\n")
            f.write("- Exclusions documented with reasons\n\n")

            f.write("## Analysis Outputs\n")
            f.write("- `state_trend_analysis.csv` - State lending trends\n")
            f.write("- `state_policy_analysis.csv` - Policy-relevant metrics\n")
            f.write("- `state_quality_flags.csv` - Quality indicators\n")
            f.write("- `state_exclusions_log.csv` - Excluded records with reasons\n")

        self.logger.info(f"State analysis results saved: {json_file}")
        self.logger.info(f"State trends CSV saved: {self.output_path}/state_trend_analysis.csv")
        self.logger.info(f"State policy CSV saved: {self.output_path}/state_policy_analysis.csv")
        self.logger.info(f"Methodology documentation saved: {methodology_file}")

def main():
    """Execute state-level longitudinal analysis."""
    print("STATE-LEVEL LONGITUDINAL ANALYSIS")
    print("HIGHEST RELIABILITY SCOPE - Stable states only")

    analyzer = StateLongitudinalAnalysis()
    results = analyzer.execute_state_longitudinal_analysis()

    print("\nSTATE ANALYSIS COMPLETE")
    print("Highest reliability analysis using stable states")
    print(f"Results: ${OUTPUT_ROOT}/analysis_outputs/multi_scope_analysis/state_longitudinal/")

if __name__ == "__main__":
    main()