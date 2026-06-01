#!/usr/bin/env python3
"""
Census Tract Boundary Validation Framework
==========================================

This module provides comprehensive validation tools for ensuring that
census tract boundary changes are properly handled in longitudinal
HMDA analysis. It implements automated checks, validation procedures,
and quality assurance protocols.

Features:
- Automatic boundary change detection
- Data continuity validation
- Population anomaly identification
- Geographic consistency checks
- Crosswalk table validation
- Quality score calculation
"""

import pandas as pd
import numpy as np
import logging
import json
import warnings
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Set, Tuple, Optional, Union
from collections import defaultdict, Counter
import os
DATA_ROOT = Path(os.environ.get("DATA_ROOT", "data"))

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class TractBoundaryValidator:
    """
    Comprehensive validation framework for tract boundary changes in HMDA data.
    """

    def __init__(self, base_path: str = str(DATA_ROOT)):
        self.base_path = Path(base_path)
        self.validation_dir = self.base_path / "validation_outputs" / "tract_boundary"
        self.validation_dir.mkdir(parents=True, exist_ok=True)

        # Validation thresholds
        self.validation_thresholds = {
            'max_population_change_ratio': 5.0,
            'min_population_change_ratio': 0.2,
            'max_missing_years_percent': 10.0,
            'min_data_continuity_score': 0.8,
            'max_boundary_change_frequency': 0.3
        }

        # Validation results storage
        self.validation_results = {
            'boundary_changes': [],
            'population_anomalies': [],
            'continuity_issues': [],
            'geographic_inconsistencies': [],
            'data_quality_flags': [],
            'validation_scores': {}
        }

        logger.info("Initialized TractBoundaryValidator")

    def validate_tract_stability(self, tract_data: Dict[int, pd.DataFrame]) -> Dict:
        """
        Validate the stability of census tracts across time periods.

        Args:
            tract_data: Dictionary of {year: DataFrame} containing tract data

        Returns:
            Dictionary containing validation results
        """
        logger.info("Validating tract stability across time periods")

        stability_results = {
            'stable_tracts': set(),
            'unstable_tracts': defaultdict(list),
            'tract_lifespans': {},
            'boundary_change_events': [],
            'stability_scores': {}
        }

        # Track tract appearances
        tract_appearances = defaultdict(list)
        all_years = sorted(tract_data.keys())

        for year, df in tract_data.items():
            if 'tract_id' in df.columns:
                for tract_id in df['tract_id'].unique():
                    tract_appearances[tract_id].append(year)

        # Analyze each tract's stability
        for tract_id, appearances in tract_appearances.items():
            appearances = sorted(appearances)
            expected_span = appearances[-1] - appearances[0] + 1
            actual_span = len(appearances)

            # Calculate stability score
            stability_score = actual_span / expected_span if expected_span > 0 else 0
            stability_results['stability_scores'][tract_id] = stability_score

            # Record lifespan
            stability_results['tract_lifespans'][tract_id] = {
                'first_year': appearances[0],
                'last_year': appearances[-1],
                'total_years': actual_span,
                'expected_years': expected_span,
                'stability_score': stability_score
            }

            # Identify stability classification
            if stability_score >= 0.9:
                stability_results['stable_tracts'].add(tract_id)
            else:
                # Find gaps in appearance
                gaps = []
                for i in range(1, len(appearances)):
                    if appearances[i] - appearances[i-1] > 1:
                        gaps.append((appearances[i-1], appearances[i]))

                stability_results['unstable_tracts'][tract_id] = {
                    'appearances': appearances,
                    'gaps': gaps,
                    'stability_score': stability_score
                }

        # Identify boundary change events
        decennial_years = [1990, 2000, 2010, 2020]
        for i in range(len(decennial_years) - 1):
            prev_year = decennial_years[i]
            next_year = decennial_years[i + 1]

            if prev_year in tract_data and next_year in tract_data:
                prev_tracts = set(tract_data[prev_year]['tract_id'])
                next_tracts = set(tract_data[next_year]['tract_id'])

                new_tracts = next_tracts - prev_tracts
                discontinued_tracts = prev_tracts - next_tracts

                if new_tracts or discontinued_tracts:
                    stability_results['boundary_change_events'].append({
                        'period': f"{prev_year}-{next_year}",
                        'new_tracts': len(new_tracts),
                        'discontinued_tracts': len(discontinued_tracts),
                        'net_change': len(new_tracts) - len(discontinued_tracts)
                    })

        self.validation_results['stability_analysis'] = stability_results
        logger.info(f"Stability validation complete: {len(stability_results['stable_tracts'])} stable tracts")
        return stability_results

    def validate_population_continuity(self, tract_data: Dict[int, pd.DataFrame]) -> Dict:
        """
        Validate population continuity and identify anomalous changes.

        Args:
            tract_data: Dictionary of tract data by year

        Returns:
            Dictionary containing population validation results
        """
        logger.info("Validating population continuity across tract boundaries")

        population_results = {
            'normal_changes': [],
            'anomalous_changes': [],
            'missing_population_data': [],
            'zero_population_tracts': [],
            'extreme_growth_tracts': [],
            'extreme_decline_tracts': []
        }

        # Analyze population changes year-over-year
        years = sorted(tract_data.keys())
        for i in range(1, len(years)):
            prev_year = years[i-1]
            curr_year = years[i]

            prev_data = tract_data[prev_year].set_index('tract_id')['Population']
            curr_data = tract_data[curr_year].set_index('tract_id')['Population']

            # Find common tracts
            common_tracts = set(prev_data.index) & set(curr_data.index)

            for tract_id in common_tracts:
                prev_pop = prev_data.loc[tract_id]
                curr_pop = curr_data.loc[tract_id]

                # Handle missing or zero population
                if pd.isna(prev_pop) or pd.isna(curr_pop):
                    population_results['missing_population_data'].append({
                        'tract_id': tract_id,
                        'period': f"{prev_year}-{curr_year}",
                        'prev_population': prev_pop,
                        'curr_population': curr_pop
                    })
                    continue

                if prev_pop == 0 or curr_pop == 0:
                    population_results['zero_population_tracts'].append({
                        'tract_id': tract_id,
                        'period': f"{prev_year}-{curr_year}",
                        'prev_population': prev_pop,
                        'curr_population': curr_pop
                    })
                    continue

                # Calculate change ratio
                change_ratio = curr_pop / prev_pop if prev_pop > 0 else float('inf')

                change_record = {
                    'tract_id': tract_id,
                    'period': f"{prev_year}-{curr_year}",
                    'prev_population': prev_pop,
                    'curr_population': curr_pop,
                    'change_ratio': change_ratio,
                    'absolute_change': curr_pop - prev_pop,
                    'percent_change': ((curr_pop - prev_pop) / prev_pop) * 100
                }

                # Classify change
                if change_ratio > self.validation_thresholds['max_population_change_ratio']:
                    population_results['extreme_growth_tracts'].append(change_record)
                    population_results['anomalous_changes'].append({**change_record, 'anomaly_type': 'extreme_growth'})
                elif change_ratio < self.validation_thresholds['min_population_change_ratio']:
                    population_results['extreme_decline_tracts'].append(change_record)
                    population_results['anomalous_changes'].append({**change_record, 'anomaly_type': 'extreme_decline'})
                else:
                    population_results['normal_changes'].append(change_record)

        self.validation_results['population_continuity'] = population_results
        logger.info(f"Population validation complete: {len(population_results['anomalous_changes'])} anomalies found")
        return population_results

    def validate_crosswalk_quality(self, crosswalk_tables: Dict) -> Dict:
        """
        Validate the quality and completeness of crosswalk tables.

        Args:
            crosswalk_tables: Dictionary of crosswalk DataFrames by period

        Returns:
            Dictionary containing crosswalk validation results
        """
        logger.info("Validating crosswalk table quality")

        crosswalk_results = {
            'completeness_scores': {},
            'relationship_distributions': {},
            'weight_validations': {},
            'missing_relationships': [],
            'duplicate_relationships': [],
            'invalid_weights': []
        }

        for period, crosswalk_df in crosswalk_tables.items():
            period_results = self._validate_single_crosswalk(crosswalk_df, period)

            crosswalk_results['completeness_scores'][period] = period_results['completeness_score']
            crosswalk_results['relationship_distributions'][period] = period_results['relationship_types']
            crosswalk_results['weight_validations'][period] = period_results['weight_validation']

            if period_results['missing_relationships']:
                crosswalk_results['missing_relationships'].extend(period_results['missing_relationships'])

            if period_results['duplicate_relationships']:
                crosswalk_results['duplicate_relationships'].extend(period_results['duplicate_relationships'])

            if period_results['invalid_weights']:
                crosswalk_results['invalid_weights'].extend(period_results['invalid_weights'])

        self.validation_results['crosswalk_quality'] = crosswalk_results
        logger.info("Crosswalk validation complete")
        return crosswalk_results

    def _validate_single_crosswalk(self, crosswalk_df: pd.DataFrame, period: str) -> Dict:
        """Validate a single crosswalk table."""
        results = {
            'completeness_score': 0.0,
            'relationship_types': {},
            'weight_validation': {},
            'missing_relationships': [],
            'duplicate_relationships': [],
            'invalid_weights': []
        }

        if crosswalk_df.empty:
            return results

        # Calculate completeness score
        total_relationships = len(crosswalk_df)
        valid_relationships = crosswalk_df.dropna().shape[0]
        results['completeness_score'] = valid_relationships / total_relationships if total_relationships > 0 else 0

        # Analyze relationship types
        if 'relationship_type' in crosswalk_df.columns:
            results['relationship_types'] = crosswalk_df['relationship_type'].value_counts().to_dict()

        # Validate weights
        if 'weight' in crosswalk_df.columns:
            weights = crosswalk_df['weight'].dropna()
            results['weight_validation'] = {
                'mean_weight': weights.mean(),
                'min_weight': weights.min(),
                'max_weight': weights.max(),
                'weights_sum_to_one_count': 0  # Would need grouping logic
            }

            # Find invalid weights
            invalid_weights = crosswalk_df[
                (crosswalk_df['weight'] < 0) |
                (crosswalk_df['weight'] > 1) |
                crosswalk_df['weight'].isna()
            ]

            for _, row in invalid_weights.iterrows():
                results['invalid_weights'].append({
                    'period': period,
                    'weight': row.get('weight'),
                    'relationship_type': row.get('relationship_type')
                })

        # Check for duplicates
        id_cols = [col for col in crosswalk_df.columns if 'tract_id' in col]
        if len(id_cols) >= 2:
            duplicates = crosswalk_df[crosswalk_df.duplicated(subset=id_cols, keep=False)]
            for _, row in duplicates.iterrows():
                results['duplicate_relationships'].append({
                    'period': period,
                    'source_tract': row[id_cols[0]],
                    'target_tract': row[id_cols[1]]
                })

        return results

    def validate_geographic_consistency(self, tract_data: Dict[int, pd.DataFrame]) -> Dict:
        """
        Validate geographic consistency of tract assignments.

        Args:
            tract_data: Dictionary of tract data by year

        Returns:
            Dictionary containing geographic validation results
        """
        logger.info("Validating geographic consistency")

        geo_results = {
            'state_consistency_issues': [],
            'county_consistency_issues': [],
            'msa_consistency_issues': [],
            'tract_migration_events': []
        }

        # Track geographic assignments for each tract
        tract_geo_history = defaultdict(list)

        for year, df in tract_data.items():
            if all(col in df.columns for col in ['tract_id', 'State', 'County']):
                for _, row in df.iterrows():
                    tract_geo_history[row['tract_id']].append({
                        'year': year,
                        'state': row['State'],
                        'county': row['County'],
                        'msa_md': row.get('MSA/MD', None)
                    })

        # Check for inconsistencies
        for tract_id, history in tract_geo_history.items():
            if len(history) <= 1:
                continue

            # Check state consistency
            states = set(record['state'] for record in history)
            if len(states) > 1:
                geo_results['state_consistency_issues'].append({
                    'tract_id': tract_id,
                    'states': list(states),
                    'history': history
                })

            # Check county consistency
            counties = set(record['county'] for record in history)
            if len(counties) > 1:
                geo_results['county_consistency_issues'].append({
                    'tract_id': tract_id,
                    'counties': list(counties),
                    'history': history
                })

            # Check MSA consistency
            msas = set(record['msa_md'] for record in history if record['msa_md'] is not None)
            if len(msas) > 1:
                geo_results['msa_consistency_issues'].append({
                    'tract_id': tract_id,
                    'msas': list(msas),
                    'history': history
                })

        self.validation_results['geographic_consistency'] = geo_results
        logger.info(f"Geographic validation complete: {len(geo_results['state_consistency_issues'])} state issues found")
        return geo_results

    def calculate_overall_quality_score(self) -> Dict:
        """
        Calculate an overall data quality score based on all validations.

        Returns:
            Dictionary containing quality scores and metrics
        """
        logger.info("Calculating overall data quality score")

        quality_metrics = {
            'stability_score': 0.0,
            'population_continuity_score': 0.0,
            'crosswalk_quality_score': 0.0,
            'geographic_consistency_score': 0.0,
            'overall_quality_score': 0.0,
            'quality_grade': 'F',
            'critical_issues': [],
            'recommendations': []
        }

        # Calculate component scores
        if 'stability_analysis' in self.validation_results:
            stable_count = len(self.validation_results['stability_analysis']['stable_tracts'])
            total_count = len(self.validation_results['stability_analysis']['tract_lifespans'])
            quality_metrics['stability_score'] = stable_count / total_count if total_count > 0 else 0

        if 'population_continuity' in self.validation_results:
            normal_changes = len(self.validation_results['population_continuity']['normal_changes'])
            total_changes = normal_changes + len(self.validation_results['population_continuity']['anomalous_changes'])
            quality_metrics['population_continuity_score'] = normal_changes / total_changes if total_changes > 0 else 0

        if 'crosswalk_quality' in self.validation_results:
            completeness_scores = list(self.validation_results['crosswalk_quality']['completeness_scores'].values())
            quality_metrics['crosswalk_quality_score'] = np.mean(completeness_scores) if completeness_scores else 0

        if 'geographic_consistency' in self.validation_results:
            geo_issues = (
                len(self.validation_results['geographic_consistency']['state_consistency_issues']) +
                len(self.validation_results['geographic_consistency']['county_consistency_issues'])
            )
            # Assume total tracts for denominator (would need actual count)
            quality_metrics['geographic_consistency_score'] = max(0, 1 - (geo_issues / 10000))  # Rough estimate

        # Calculate overall score
        scores = [
            quality_metrics['stability_score'],
            quality_metrics['population_continuity_score'],
            quality_metrics['crosswalk_quality_score'],
            quality_metrics['geographic_consistency_score']
        ]
        quality_metrics['overall_quality_score'] = np.mean([s for s in scores if s > 0])

        # Assign quality grade
        overall_score = quality_metrics['overall_quality_score']
        if overall_score >= 0.9:
            quality_metrics['quality_grade'] = 'A'
        elif overall_score >= 0.8:
            quality_metrics['quality_grade'] = 'B'
        elif overall_score >= 0.7:
            quality_metrics['quality_grade'] = 'C'
        elif overall_score >= 0.6:
            quality_metrics['quality_grade'] = 'D'
        else:
            quality_metrics['quality_grade'] = 'F'

        # Generate recommendations based on scores
        if quality_metrics['stability_score'] < 0.8:
            quality_metrics['critical_issues'].append("High tract instability detected")
            quality_metrics['recommendations'].append("Implement comprehensive crosswalk validation")

        if quality_metrics['population_continuity_score'] < 0.8:
            quality_metrics['critical_issues'].append("Significant population anomalies detected")
            quality_metrics['recommendations'].append("Review and validate population data sources")

        if quality_metrics['crosswalk_quality_score'] < 0.8:
            quality_metrics['critical_issues'].append("Crosswalk tables have quality issues")
            quality_metrics['recommendations'].append("Improve crosswalk table construction methodology")

        self.validation_results['quality_metrics'] = quality_metrics
        logger.info(f"Quality score calculation complete: Overall grade = {quality_metrics['quality_grade']}")
        return quality_metrics

    def generate_validation_report(self) -> None:
        """Generate comprehensive validation report."""
        logger.info("Generating validation report")

        report = {
            'metadata': {
                'validation_date': datetime.now().isoformat(),
                'validator': 'TractBoundaryValidator',
                'version': '1.0'
            },
            'validation_results': self.validation_results,
            'summary': {
                'total_validations_performed': len([k for k in self.validation_results.keys() if k != 'validation_scores']),
                'critical_issues_found': len(self.validation_results.get('quality_metrics', {}).get('critical_issues', [])),
                'overall_quality_grade': self.validation_results.get('quality_metrics', {}).get('quality_grade', 'Unknown')
            }
        }

        # Save JSON report
        report_file = self.validation_dir / "tract_boundary_validation_report.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2, default=str)

        # Save markdown summary
        summary_file = self.validation_dir / "validation_summary.md"
        self._save_validation_summary(report, summary_file)

        logger.info(f"Validation report saved to {report_file}")

    def _save_validation_summary(self, report: dict, file_path: Path) -> None:
        """Save human-readable validation summary."""
        with open(file_path, 'w') as f:
            f.write("# Census Tract Boundary Validation Report\n\n")
            f.write(f"**Validation Date:** {report['metadata']['validation_date']}\n\n")

            # Summary
            summary = report['summary']
            f.write("## Validation Summary\n\n")
            f.write(f"- **Validations Performed:** {summary['total_validations_performed']}\n")
            f.write(f"- **Critical Issues Found:** {summary['critical_issues_found']}\n")
            f.write(f"- **Overall Quality Grade:** {summary['overall_quality_grade']}\n\n")

            # Quality metrics
            if 'quality_metrics' in report['validation_results']:
                metrics = report['validation_results']['quality_metrics']
                f.write("## Quality Scores\n\n")
                f.write(f"- **Stability Score:** {metrics['stability_score']:.3f}\n")
                f.write(f"- **Population Continuity:** {metrics['population_continuity_score']:.3f}\n")
                f.write(f"- **Crosswalk Quality:** {metrics['crosswalk_quality_score']:.3f}\n")
                f.write(f"- **Geographic Consistency:** {metrics['geographic_consistency_score']:.3f}\n")
                f.write(f"- **Overall Score:** {metrics['overall_quality_score']:.3f}\n\n")

                # Critical issues
                if metrics['critical_issues']:
                    f.write("## Critical Issues\n\n")
                    for issue in metrics['critical_issues']:
                        f.write(f"- {issue}\n")
                    f.write("\n")

                # Recommendations
                if metrics['recommendations']:
                    f.write("## Recommendations\n\n")
                    for rec in metrics['recommendations']:
                        f.write(f"- {rec}\n")
                    f.write("\n")

if __name__ == "__main__":
    # Example usage
    validator = TractBoundaryValidator()

    # Would need actual tract data to run validation
    # validator.validate_tract_stability(tract_data)
    # validator.validate_population_continuity(tract_data)
    # validator.calculate_overall_quality_score()
    # validator.generate_validation_report()

    logger.info("Tract boundary validator initialized and ready for use")