#!/usr/bin/env python3
"""
Real HMDA Data Quality Assessment

CRITICAL PRINCIPLE: NO DATA MODIFICATIONS
- Analyze actual HMDA data files
- Document ALL quality issues without removing or changing values
- Provide specific recommendations for handling each issue type
- Focus on geographic fields and missing value patterns

This assessment uses your actual HMDA data to identify specific quality concerns.
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

class RealHMDADataQualityAssessment:
    """
    CRITICAL PRINCIPLES:
    - Analyze REAL HMDA data without modifications
    - Document every quality issue found
    - Preserve all original values exactly
    - Provide actionable quality insights
    """

    def __init__(self, base_path: str = str(DATA_ROOT)):
        self.base_path = Path(base_path)
        self.output_path = self.base_path / "analysis_outputs" / "data_quality"
        self.output_path.mkdir(parents=True, exist_ok=True)

        # Configure logging
        logging.basicConfig(level=logging.INFO,
                          format='%(asctime)s - %(levelname)s - %(message)s')
        self.logger = logging.getLogger(__name__)

        self.logger.info("Initialized Real HMDA Data Quality Assessment")
        self.logger.info("CRITICAL: NO data modifications - analysis only")

    def assess_real_data_quality(self) -> Dict[str, Any]:
        """
        Comprehensive quality assessment of actual HMDA data files.

        CRITICAL: This function ONLY documents issues - no data changes made.
        """
        self.logger.info("Starting real HMDA data quality assessment")
        self.logger.info("CRITICAL: Preserving all original data - no modifications")

        # Load actual HMDA data files
        hmda_files = self._identify_hmda_files()

        quality_assessment = {
            'analysis_metadata': {
                'analysis_date': datetime.now().isoformat(),
                'principle': 'NO_DATA_MODIFICATIONS - Real data analysis only',
                'files_found': len(hmda_files),
                'assessment_scope': 'Actual HMDA data quality issues'
            }
        }

        if hmda_files:
            # Analyze each file
            for file_info in hmda_files:
                file_assessment = self._assess_single_file(file_info)
                quality_assessment[file_info['identifier']] = file_assessment

            # Create summary analysis
            quality_assessment['summary_findings'] = self._create_summary_findings(quality_assessment)
            quality_assessment['critical_recommendations'] = self._generate_recommendations(quality_assessment)

        else:
            quality_assessment['critical_issue'] = 'No HMDA data files found for analysis'

        # Save comprehensive assessment
        self._save_quality_assessment(quality_assessment)

        self.logger.info("Real data quality assessment completed")
        self.logger.info(f"Results saved to: {self.output_path}")

        return quality_assessment

    def _identify_hmda_files(self) -> List[Dict[str, Any]]:
        """Identify actual HMDA data files in the project."""
        self.logger.info("Identifying actual HMDA data files")

        hmda_files = []

        # Check for sample file
        sample_file = self.base_path / "analysis_outputs" / "lar_sample_100k.csv"
        if sample_file.exists():
            hmda_files.append({
                'path': sample_file,
                'identifier': 'lar_sample_100k',
                'type': 'sample_data',
                'description': '100K sample of LAR data'
            })

        # Check for 2024 data
        data_2024 = self.base_path / "data" / "hmda" / "raw" / "2024" / "2024_public_lar_csv" / "2024_public_lar_csv.csv"
        if data_2024.exists():
            hmda_files.append({
                'path': data_2024,
                'identifier': '2024_public_lar',
                'type': 'full_year_data',
                'description': '2024 complete public LAR data'
            })

        # Check for R replication data
        r_replication_path = self.base_path / "data" / "r_replication"
        if r_replication_path.exists():
            for csv_file in r_replication_path.glob("*.csv"):
                if "lar" in csv_file.name.lower():
                    hmda_files.append({
                        'path': csv_file,
                        'identifier': csv_file.stem,
                        'type': 'r_replication',
                        'description': f'R replication data: {csv_file.name}'
                    })

        self.logger.info(f"Found {len(hmda_files)} HMDA data files")
        return hmda_files

    def _assess_single_file(self, file_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Assess quality of a single HMDA data file WITHOUT modifications.
        """
        self.logger.info(f"Assessing file: {file_info['identifier']}")

        try:
            # Load file preserving all original values
            df = pd.read_csv(file_info['path'], dtype=str, na_filter=False)

            assessment = {
                'file_metadata': {
                    'total_records': len(df),
                    'total_columns': len(df.columns),
                    'file_size_mb': file_info['path'].stat().st_size / (1024 * 1024),
                    'column_names': list(df.columns)
                },
                'geographic_field_analysis': self._analyze_geographic_fields(df),
                'missing_value_patterns': self._analyze_missing_patterns(df),
                'data_type_issues': self._analyze_data_types(df),
                'value_distribution_analysis': self._analyze_value_distributions(df),
                'potential_outliers': self._identify_potential_outliers(df),
                'referential_integrity': self._check_referential_integrity(df)
            }

            self.logger.info(f"Completed assessment: {file_info['identifier']} - {len(df):,} records")
            return assessment

        except Exception as e:
            self.logger.error(f"Error assessing {file_info['identifier']}: {e}")
            return {'error': str(e)}

    def _analyze_geographic_fields(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Analyze geographic fields WITHOUT modifying any values.
        """
        geo_analysis = {
            'principle': 'Analyze geographic fields - no value modifications',
            'fields_found': [],
            'quality_issues': {}
        }

        # Common geographic field names in HMDA data
        geo_fields = {
            'state_code': 'State FIPS code',
            'county_code': 'County FIPS code',
            'census_tract': 'Census tract identifier',
            'derived_msa_md': 'MSA/MD code'
        }

        for field, description in geo_fields.items():
            if field in df.columns:
                geo_analysis['fields_found'].append(field)

                field_data = df[field].astype(str)

                # Analyze without modifying
                field_analysis = {
                    'description': description,
                    'unique_values': len(field_data.unique()),
                    'empty_values': (field_data == '').sum(),
                    'null_like_values': field_data.isin(['nan', 'NaN', 'NULL', 'None']).sum(),
                    'sample_values': field_data.unique()[:10].tolist(),
                    'value_length_stats': {
                        'min_length': field_data.str.len().min(),
                        'max_length': field_data.str.len().max(),
                        'mean_length': field_data.str.len().mean()
                    }
                }

                # Check for potential issues
                issues = []
                if field_analysis['empty_values'] > 0:
                    issues.append(f"{field_analysis['empty_values']:,} empty values")

                if field_analysis['null_like_values'] > 0:
                    issues.append(f"{field_analysis['null_like_values']:,} null-like values")

                # Check format consistency
                if field == 'state_code':
                    non_numeric = (~field_data.str.isnumeric() & (field_data != '')).sum()
                    if non_numeric > 0:
                        issues.append(f"{non_numeric:,} non-numeric state codes")

                if field == 'county_code':
                    # Check for decimal points (should be whole numbers)
                    has_decimals = field_data.str.contains(r'\.').sum()
                    if has_decimals > 0:
                        issues.append(f"{has_decimals:,} county codes with decimal points")

                field_analysis['quality_issues'] = issues
                geo_analysis['quality_issues'][field] = field_analysis

        return geo_analysis

    def _analyze_missing_patterns(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Analyze missing value patterns WITHOUT removing anything.
        """
        missing_analysis = {
            'principle': 'Document missing patterns - no value removal',
            'overall_stats': {},
            'column_missing_rates': {},
            'missing_value_types': {}
        }

        # Overall missing statistics
        total_cells = len(df) * len(df.columns)
        empty_strings = (df == '').sum().sum()

        missing_analysis['overall_stats'] = {
            'total_cells': total_cells,
            'empty_strings': int(empty_strings),
            'empty_string_rate': float(empty_strings / total_cells)
        }

        # Missing rates by column
        for col in df.columns:
            col_data = df[col].astype(str)

            missing_counts = {
                'empty_strings': (col_data == '').sum(),
                'null_like': col_data.isin(['nan', 'NaN', 'NULL', 'None', 'null']).sum(),
                'missing_codes': col_data.isin(['-1', '999', '9999', '99999']).sum()
            }

            total_missing = sum(missing_counts.values())
            missing_rate = total_missing / len(df)

            if missing_rate > 0.01:  # Only report columns with >1% missing
                missing_analysis['column_missing_rates'][col] = {
                    'missing_count': int(total_missing),
                    'missing_rate': float(missing_rate),
                    'missing_breakdown': missing_counts
                }

        # Identify different types of missing representations
        missing_types = set()
        for col in df.columns:
            unique_vals = df[col].astype(str).unique()
            for val in unique_vals:
                if val in ['', 'nan', 'NaN', 'NULL', 'None', 'null', '-1', '999', '9999']:
                    missing_types.add(val)

        missing_analysis['missing_value_types'] = {
            'types_found': list(missing_types),
            'recommendation': 'Document and preserve all missing value representations'
        }

        return missing_analysis

    def _analyze_data_types(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Analyze data type consistency WITHOUT converting anything.
        """
        type_analysis = {
            'principle': 'Analyze types - no automatic conversions',
            'column_characteristics': {},
            'type_consistency_issues': []
        }

        for col in df.columns:
            col_data = df[col].astype(str)

            # Analyze characteristics without converting
            characteristics = {
                'appears_numeric': float(col_data.str.isnumeric().mean()),
                'appears_decimal': float(col_data.str.match(r'^\d+\.\d+$').mean()),
                'appears_categorical': len(col_data.unique()) / len(col_data),
                'has_special_chars': float(col_data.str.contains(r'[^a-zA-Z0-9\s\.]').mean()),
                'unique_value_count': len(col_data.unique()),
                'sample_values': col_data.unique()[:5].tolist()
            }

            # Flag potential type issues
            issues = []
            if 'amount' in col.lower() and characteristics['appears_numeric'] < 0.9:
                issues.append('Amount field with non-numeric values')

            if 'code' in col.lower() and characteristics['appears_numeric'] < 0.8:
                issues.append('Code field with unexpected non-numeric values')

            if issues:
                characteristics['potential_issues'] = issues

            type_analysis['column_characteristics'][col] = characteristics

        return type_analysis

    def _analyze_value_distributions(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Analyze value distributions WITHOUT modifying data.
        """
        distribution_analysis = {
            'principle': 'Analyze distributions - no data modifications',
            'categorical_distributions': {},
            'numeric_field_analysis': {}
        }

        # Analyze key categorical fields
        categorical_fields = ['action_taken', 'loan_purpose', 'loan_type', 'derived_race', 'derived_ethnicity']

        for field in categorical_fields:
            if field in df.columns:
                value_counts = df[field].value_counts().head(10)
                distribution_analysis['categorical_distributions'][field] = {
                    'top_values': value_counts.to_dict(),
                    'unique_count': df[field].nunique(),
                    'most_common_value': value_counts.index[0] if len(value_counts) > 0 else None,
                    'most_common_percentage': float(value_counts.iloc[0] / len(df)) if len(value_counts) > 0 else 0
                }

        # Analyze numeric fields without conversion
        numeric_fields = ['loan_amount', 'income', 'property_value']

        for field in numeric_fields:
            if field in df.columns:
                field_data = df[field].astype(str)

                # Try to analyze numeric characteristics without converting
                numeric_mask = field_data.str.isnumeric() | field_data.str.match(r'^\d+\.\d+$')
                numeric_data = field_data[numeric_mask]

                if len(numeric_data) > 0:
                    try:
                        numeric_values = pd.to_numeric(numeric_data, errors='coerce')
                        distribution_analysis['numeric_field_analysis'][field] = {
                            'numeric_count': len(numeric_data),
                            'non_numeric_count': len(field_data) - len(numeric_data),
                            'numeric_percentage': float(len(numeric_data) / len(field_data)),
                            'min_value': float(numeric_values.min()) if not numeric_values.isna().all() else None,
                            'max_value': float(numeric_values.max()) if not numeric_values.isna().all() else None,
                            'mean_value': float(numeric_values.mean()) if not numeric_values.isna().all() else None
                        }
                    except:
                        distribution_analysis['numeric_field_analysis'][field] = {
                            'analysis_failed': 'Could not analyze numeric characteristics'
                        }

        return distribution_analysis

    def _identify_potential_outliers(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Identify potential outliers WITHOUT removing them.
        """
        outlier_analysis = {
            'principle': 'Identify outliers - no removal',
            'outlier_candidates': {},
            'extreme_values': {}
        }

        # Focus on key numeric fields
        numeric_fields = ['loan_amount', 'income', 'property_value']

        for field in numeric_fields:
            if field in df.columns:
                field_data = df[field].astype(str)

                # Try to identify outliers without modifying data
                numeric_mask = field_data.str.isnumeric() | field_data.str.match(r'^\d+\.\d+$')

                if numeric_mask.any():
                    try:
                        numeric_data = pd.to_numeric(field_data[numeric_mask], errors='coerce')

                        if not numeric_data.isna().all():
                            q1, q3 = numeric_data.quantile([0.25, 0.75])
                            iqr = q3 - q1
                            lower_bound = q1 - 1.5 * iqr
                            upper_bound = q3 + 1.5 * iqr

                            outliers = (numeric_data < lower_bound) | (numeric_data > upper_bound)

                            outlier_analysis['outlier_candidates'][field] = {
                                'total_outliers': int(outliers.sum()),
                                'outlier_percentage': float(outliers.sum() / len(numeric_data)),
                                'extreme_low': float(numeric_data.min()),
                                'extreme_high': float(numeric_data.max()),
                                'outlier_preservation_note': 'All outliers preserved - flagged for investigation'
                            }
                    except:
                        outlier_analysis['outlier_candidates'][field] = {
                            'analysis_failed': 'Could not analyze for outliers'
                        }

        return outlier_analysis

    def _check_referential_integrity(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Check referential integrity WITHOUT fixing issues.
        """
        integrity_analysis = {
            'principle': 'Document integrity issues - no fixes',
            'geographic_hierarchy': {},
            'consistency_checks': {}
        }

        # Check geographic hierarchy consistency
        geo_fields = ['state_code', 'county_code', 'census_tract']
        available_geo_fields = [field for field in geo_fields if field in df.columns]

        if len(available_geo_fields) >= 2:
            # Check state-county consistency
            if 'state_code' in df.columns and 'county_code' in df.columns:
                state_county_combos = df.groupby('state_code')['county_code'].nunique()
                integrity_analysis['geographic_hierarchy']['state_county'] = {
                    'states_with_data': len(state_county_combos),
                    'counties_per_state_range': [int(state_county_combos.min()), int(state_county_combos.max())],
                    'avg_counties_per_state': float(state_county_combos.mean())
                }

        # Check for duplicate records
        if len(df) > 0:
            # Check for completely identical rows
            duplicate_rows = df.duplicated().sum()
            integrity_analysis['consistency_checks']['duplicate_rows'] = {
                'total_duplicates': int(duplicate_rows),
                'duplicate_percentage': float(duplicate_rows / len(df)),
                'recommendation': 'Investigate duplicate records but preserve for transparency'
            }

        return integrity_analysis

    def _create_summary_findings(self, quality_assessment: Dict[str, Any]) -> Dict[str, Any]:
        """Create summary of key quality findings across all files."""
        summary = {
            'principle': 'Summarize findings - no data changes',
            'critical_issues': [],
            'moderate_issues': [],
            'minor_issues': [],
            'overall_recommendations': []
        }

        # Analyze findings across all files
        for key, assessment in quality_assessment.items():
            if key in ['analysis_metadata']:
                continue

            if isinstance(assessment, dict) and 'file_metadata' in assessment:
                # Check for critical issues
                if 'geographic_field_analysis' in assessment:
                    geo_analysis = assessment['geographic_field_analysis']
                    for field, field_analysis in geo_analysis.get('quality_issues', {}).items():
                        if field_analysis.get('quality_issues'):
                            for issue in field_analysis['quality_issues']:
                                if 'empty values' in issue:
                                    summary['critical_issues'].append(f"{key}: {field} has {issue}")

                # Check missing value rates
                if 'missing_value_patterns' in assessment:
                    missing_analysis = assessment['missing_value_patterns']
                    for col, missing_info in missing_analysis.get('column_missing_rates', {}).items():
                        if missing_info['missing_rate'] > 0.1:  # >10% missing
                            summary['critical_issues'].append(f"{key}: {col} has {missing_info['missing_rate']:.1%} missing values")
                        elif missing_info['missing_rate'] > 0.05:  # >5% missing
                            summary['moderate_issues'].append(f"{key}: {col} has {missing_info['missing_rate']:.1%} missing values")

        return summary

    def _generate_recommendations(self, quality_assessment: Dict[str, Any]) -> List[str]:
        """Generate specific recommendations for handling quality issues."""
        recommendations = [
            "CRITICAL: Do not remove or modify any data values - preserve all original data",
            "Document all missing value patterns and decide handling on case-by-case basis",
            "Use geographic field validation for boundary crossing analysis",
            "Investigate outliers but preserve all values for transparency",
            "Consider creating quality flags rather than excluding problematic records"
        ]

        # Add specific recommendations based on findings
        summary = quality_assessment.get('summary_findings', {})

        if summary.get('critical_issues'):
            recommendations.append("Address critical geographic field issues before longitudinal analysis")

        if summary.get('moderate_issues'):
            recommendations.append("Consider impact of moderate missing value rates on analysis conclusions")

        return recommendations

    def _save_quality_assessment(self, quality_assessment: Dict[str, Any]) -> None:
        """Save comprehensive quality assessment results."""

        # Save detailed JSON report
        json_file = self.output_path / "real_hmda_data_quality_assessment.json"
        with open(json_file, 'w') as f:
            json.dump(quality_assessment, f, indent=2, default=str)

        # Save readable summary
        summary_file = self.output_path / "real_data_quality_summary.md"
        with open(summary_file, 'w') as f:
            f.write("# Real HMDA Data Quality Assessment Summary\n\n")
            f.write(f"**Analysis Date**: {quality_assessment['analysis_metadata']['analysis_date']}\n")
            f.write(f"**Files Analyzed**: {quality_assessment['analysis_metadata']['files_found']}\n\n")

            f.write("## CRITICAL DATA INTEGRITY COMMITMENT\n")
            f.write("- NO DATA MODIFICATIONS MADE - All original values preserved\n")
            f.write("- All quality issues documented for transparency\n")
            f.write("- Missing values and outliers flagged but not removed\n")
            f.write("- Recommendations provided for handling each issue type\n\n")

            # Summary findings
            if 'summary_findings' in quality_assessment:
                summary = quality_assessment['summary_findings']

                f.write("## Critical Issues Requiring Attention\n")
                for issue in summary.get('critical_issues', []):
                    f.write(f"- {issue}\n")
                f.write("\n")

                f.write("## Moderate Issues for Consideration\n")
                for issue in summary.get('moderate_issues', []):
                    f.write(f"- {issue}\n")
                f.write("\n")

            # Recommendations
            if 'critical_recommendations' in quality_assessment:
                f.write("## Recommendations\n")
                for rec in quality_assessment['critical_recommendations']:
                    f.write(f"- {rec}\n")
                f.write("\n")

        self.logger.info(f"Quality assessment saved: {json_file}")
        self.logger.info(f"Summary saved: {summary_file}")

def main():
    """Execute real HMDA data quality assessment."""
    print("REAL HMDA DATA QUALITY ASSESSMENT")
    print("CRITICAL: NO data modifications - analysis only")

    assessor = RealHMDADataQualityAssessment()
    quality_assessment = assessor.assess_real_data_quality()

    print("\nDATA QUALITY ASSESSMENT COMPLETE")
    print("All original data preserved exactly as found")
    print(f"Results: ${OUTPUT_ROOT}/analysis_outputs/data_quality/")

if __name__ == "__main__":
    main()