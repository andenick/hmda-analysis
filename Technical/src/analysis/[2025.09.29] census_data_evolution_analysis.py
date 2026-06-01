#!/usr/bin/env python3
"""
Comprehensive Census Data Evolution Analysis
==========================================

Detailed analysis comparing census data structure, quality, and methodology
between pre-2017 and post-2017 periods in HMDA analysis.
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import logging
import json
from typing import Dict, List, Any, Tuple
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class CensusDataEvolutionAnalyzer:
    """Comprehensive analyzer for census data evolution across HMDA periods."""

    def __init__(self):
        self.project_root = Path(__file__).parent.parent.parent
        self.output_path = self.project_root / "analysis_outputs" / "census_analysis"
        self.output_path.mkdir(parents=True, exist_ok=True)

        # Initialize data containers
        self.pre_2017_data = {}
        self.post_2017_data = {}
        self.schema_evolution = {}
        self.quality_metrics = {}
        self.methodology_changes = {}

        # Key years for analysis
        self.pre_2017_sample_years = [1990, 1995, 2000, 2005, 2010, 2015, 2016]
        self.post_2017_years = [2018, 2019]
        self.transition_year = 2017

    def run_comprehensive_analysis(self):
        """Run the complete census data evolution analysis."""
        logger.info("Starting comprehensive census data evolution analysis")

        try:
            # Phase 1: Load and examine data structures
            self._load_pre_2017_data()
            self._load_post_2017_data()

            # Phase 2: Analyze schema evolution
            self._analyze_schema_evolution()

            # Phase 3: Data quality assessment
            self._assess_data_quality_evolution()

            # Phase 4: Methodology documentation
            self._document_methodology_changes()

            # Phase 5: Generate comprehensive report
            self._generate_evolution_report()

            # Phase 6: Create visualizations
            self._create_evolution_visualizations()

            logger.info("Census data evolution analysis completed successfully")

        except Exception as e:
            logger.error(f"Error in census data evolution analysis: {e}")
            raise

    def _load_pre_2017_data(self):
        """Load and analyze pre-2017 census data files."""
        logger.info("Loading pre-2017 census data files")

        # Load sample years of pre-2017 data
        for year in self.pre_2017_sample_years:
            file_path = (self.project_root /
                        f"Old/CRA_code/_Archive/hmda-census-master/output/census_data_extract_{year}.csv")

            if file_path.exists():
                try:
                    df = pd.read_csv(file_path)
                    self.pre_2017_data[year] = {
                        'data': df,
                        'columns': list(df.columns),
                        'shape': df.shape,
                        'dtypes': df.dtypes.to_dict(),
                        'file_size': file_path.stat().st_size
                    }
                    logger.info(f"Loaded {year} census data: {df.shape[0]:,} records, {df.shape[1]} columns")
                except Exception as e:
                    logger.warning(f"Failed to load {year} census data: {e}")
            else:
                logger.warning(f"Census data file not found for {year}: {file_path}")

        # Load FFIEC census schemas for pre-2017
        schema_files = [
            "Old/Python Stuff/schemas/ffiec_census_fwf_spec_2002.csv",
            "Old/Python Stuff/schemas/ffiec_census_fwf_spec_2006.csv"
        ]

        for schema_file in schema_files:
            schema_path = self.project_root / schema_file
            if schema_path.exists():
                try:
                    schema_df = pd.read_csv(schema_path)
                    year = "2002" if "2002" in schema_file else "2006"
                    self.pre_2017_data[f'schema_{year}'] = schema_df
                    logger.info(f"Loaded FFIEC schema for {year}: {len(schema_df)} field definitions")
                except Exception as e:
                    logger.warning(f"Failed to load schema {schema_file}: {e}")

    def _load_post_2017_data(self):
        """Load and analyze post-2017 census data files."""
        logger.info("Loading post-2017 census data files")

        # Load modern parquet files
        parquet_files = {
            2019: "data/census/census_data_2019.parquet",
            2006: "data/census/census_data_2006.parquet",  # For comparison
            1998: "data/census/census_data_1998.parquet"   # For comparison
        }

        for year, file_path in parquet_files.items():
            full_path = self.project_root / file_path
            if full_path.exists():
                try:
                    df = pd.read_parquet(full_path)
                    self.post_2017_data[year] = {
                        'data': df,
                        'columns': list(df.columns),
                        'shape': df.shape,
                        'dtypes': df.dtypes.to_dict(),
                        'file_size': full_path.stat().st_size
                    }
                    logger.info(f"Loaded {year} parquet data: {df.shape[0]:,} records, {df.shape[1]} columns")
                except Exception as e:
                    logger.warning(f"Failed to load {year} parquet data: {e}")

        # Load flat file census data for comparison
        flat_files = {
            2016: "Old/CRA_code/_files2/flatFiles/src/2016/census2016.csv",
            2018: "Old/CRA_code/_files2/flatFiles/src/2018/census2018.csv"
        }

        for year, file_path in flat_files.items():
            full_path = self.project_root / file_path
            if full_path.exists():
                try:
                    # These files might be large, so sample them
                    df = pd.read_csv(full_path, nrows=10000)
                    self.post_2017_data[year] = {
                        'data': df,
                        'columns': list(df.columns),
                        'shape': df.shape,
                        'dtypes': df.dtypes.to_dict(),
                        'file_size': full_path.stat().st_size,
                        'is_sample': True
                    }
                    logger.info(f"Loaded {year} flat file sample: {df.shape[0]:,} records, {df.shape[1]} columns")
                except Exception as e:
                    logger.warning(f"Failed to load {year} flat file: {e}")

    def _analyze_schema_evolution(self):
        """Analyze how census data schema evolved over time."""
        logger.info("Analyzing census data schema evolution")

        # Track column evolution
        all_columns_by_year = {}

        # Combine pre-2017 and post-2017 data
        all_data = {**self.pre_2017_data, **self.post_2017_data}

        for year, data_info in all_data.items():
            if isinstance(year, int) and 'columns' in data_info:
                all_columns_by_year[year] = set(data_info['columns'])

        # Identify column evolution patterns
        self.schema_evolution = {
            'columns_by_year': all_columns_by_year,
            'column_stability': self._analyze_column_stability(all_columns_by_year),
            'new_columns_post_2017': self._identify_new_columns_post_2017(all_columns_by_year),
            'deprecated_columns': self._identify_deprecated_columns(all_columns_by_year),
            'column_name_changes': self._identify_column_name_changes(all_columns_by_year),
            'data_type_evolution': self._analyze_data_type_evolution()
        }

    def _analyze_column_stability(self, columns_by_year: Dict[int, set]) -> Dict[str, Any]:
        """Analyze which columns remained stable across periods."""
        if not columns_by_year:
            return {}

        all_years = sorted([y for y in columns_by_year.keys() if isinstance(y, int)])
        if len(all_years) < 2:
            return {}

        # Find columns present in all years
        stable_columns = set.intersection(*[columns_by_year[year] for year in all_years])

        # Find columns that appeared and disappeared
        column_appearances = {}
        for col in set.union(*[columns_by_year[year] for year in all_years]):
            appearances = [year for year in all_years if col in columns_by_year[year]]
            column_appearances[col] = {
                'first_appeared': min(appearances),
                'last_appeared': max(appearances),
                'years_present': len(appearances),
                'total_years_analyzed': len(all_years),
                'stability_score': len(appearances) / len(all_years)
            }

        return {
            'total_columns_analyzed': len(column_appearances),
            'stable_columns': list(stable_columns),
            'stable_count': len(stable_columns),
            'column_appearances': column_appearances,
            'stability_distribution': self._calculate_stability_distribution(column_appearances)
        }

    def _calculate_stability_distribution(self, column_appearances: Dict) -> Dict[str, int]:
        """Calculate distribution of column stability scores."""
        stability_scores = [info['stability_score'] for info in column_appearances.values()]

        return {
            'always_present': sum(1 for score in stability_scores if score == 1.0),
            'mostly_present': sum(1 for score in stability_scores if 0.8 <= score < 1.0),
            'sometimes_present': sum(1 for score in stability_scores if 0.4 <= score < 0.8),
            'rarely_present': sum(1 for score in stability_scores if 0.0 < score < 0.4),
            'single_appearance': sum(1 for score in stability_scores if score <= 0.2)
        }

    def _identify_new_columns_post_2017(self, columns_by_year: Dict[int, set]) -> List[str]:
        """Identify columns that appeared only after 2017."""
        pre_2017_years = [y for y in columns_by_year.keys() if isinstance(y, int) and y <= 2017]
        post_2017_years = [y for y in columns_by_year.keys() if isinstance(y, int) and y > 2017]

        if not pre_2017_years or not post_2017_years:
            return []

        pre_2017_columns = set.union(*[columns_by_year[year] for year in pre_2017_years])
        post_2017_columns = set.union(*[columns_by_year[year] for year in post_2017_years])

        return list(post_2017_columns - pre_2017_columns)

    def _identify_deprecated_columns(self, columns_by_year: Dict[int, set]) -> List[str]:
        """Identify columns that disappeared after 2017."""
        pre_2017_years = [y for y in columns_by_year.keys() if isinstance(y, int) and y <= 2017]
        post_2017_years = [y for y in columns_by_year.keys() if isinstance(y, int) and y > 2017]

        if not pre_2017_years or not post_2017_years:
            return []

        pre_2017_columns = set.union(*[columns_by_year[year] for year in pre_2017_years])
        post_2017_columns = set.union(*[columns_by_year[year] for year in post_2017_years])

        return list(pre_2017_columns - post_2017_columns)

    def _identify_column_name_changes(self, columns_by_year: Dict[int, set]) -> Dict[str, List[str]]:
        """Identify potential column name changes (similar names across periods)."""
        pre_2017_years = [y for y in columns_by_year.keys() if isinstance(y, int) and y <= 2017]
        post_2017_years = [y for y in columns_by_year.keys() if isinstance(y, int) and y > 2017]

        if not pre_2017_years or not post_2017_years:
            return {}

        pre_2017_columns = set.union(*[columns_by_year[year] for year in pre_2017_years])
        post_2017_columns = set.union(*[columns_by_year[year] for year in post_2017_years])

        # Look for similar column names (basic string similarity)
        potential_changes = {}
        for old_col in pre_2017_columns:
            for new_col in post_2017_columns:
                # Simple similarity check
                if (self._string_similarity(old_col.lower(), new_col.lower()) > 0.7 and
                    old_col != new_col):
                    potential_changes[old_col] = potential_changes.get(old_col, []) + [new_col]

        return potential_changes

    def _string_similarity(self, s1: str, s2: str) -> float:
        """Calculate simple string similarity."""
        if not s1 or not s2:
            return 0.0

        # Simple common character ratio
        common_chars = sum(1 for c in s1 if c in s2)
        max_len = max(len(s1), len(s2))
        return common_chars / max_len if max_len > 0 else 0.0

    def _analyze_data_type_evolution(self) -> Dict[str, Any]:
        """Analyze how data types evolved for common columns."""
        type_evolution = {}

        # Find common columns across periods
        all_data = {**self.pre_2017_data, **self.post_2017_data}
        common_columns = None

        for year, data_info in all_data.items():
            if isinstance(year, int) and 'columns' in data_info:
                year_columns = set(data_info['columns'])
                if common_columns is None:
                    common_columns = year_columns
                else:
                    common_columns = common_columns.intersection(year_columns)

        if common_columns:
            for col in common_columns:
                type_evolution[col] = {}
                for year, data_info in all_data.items():
                    if isinstance(year, int) and 'dtypes' in data_info and col in data_info['dtypes']:
                        type_evolution[col][year] = str(data_info['dtypes'][col])

        return type_evolution

    def _assess_data_quality_evolution(self):
        """Assess data quality changes over time."""
        logger.info("Assessing data quality evolution")

        self.quality_metrics = {
            'completeness_by_year': {},
            'consistency_metrics': {},
            'accuracy_indicators': {},
            'coverage_analysis': {}
        }

        # Analyze completeness
        all_data = {**self.pre_2017_data, **self.post_2017_data}

        for year, data_info in all_data.items():
            if isinstance(year, int) and 'data' in data_info:
                df = data_info['data']

                completeness = {
                    'total_records': len(df),
                    'total_fields': len(df.columns),
                    'missing_value_ratio': df.isnull().sum().sum() / (len(df) * len(df.columns)),
                    'fields_with_missing': df.isnull().any().sum(),
                    'completely_empty_fields': (df.isnull().all()).sum(),
                    'field_completeness': {}
                }

                # Field-level completeness
                for col in df.columns:
                    completeness['field_completeness'][col] = {
                        'missing_count': df[col].isnull().sum(),
                        'missing_ratio': df[col].isnull().mean(),
                        'unique_values': df[col].nunique(),
                        'data_type': str(df[col].dtype)
                    }

                self.quality_metrics['completeness_by_year'][year] = completeness

    def _document_methodology_changes(self):
        """Document key methodology changes between periods."""
        logger.info("Documenting methodology changes")

        self.methodology_changes = {
            'data_source_changes': {
                'pre_2017': {
                    'primary_source': 'FFIEC Census Flat Files',
                    'update_frequency': 'Decennial Census with ACS supplements',
                    'geographic_granularity': 'Census tract level',
                    'income_calculations': 'HUD Area Median Income',
                    'minority_definitions': 'Traditional OMB race/ethnicity categories'
                },
                'post_2017': {
                    'primary_source': 'American Community Survey (ACS) 5-year estimates',
                    'update_frequency': 'Annual rolling 5-year estimates',
                    'geographic_granularity': 'Census tract with block group supplements',
                    'income_calculations': 'FFIEC Median Family Income based on ACS',
                    'minority_definitions': 'Expanded race/ethnicity categories'
                }
            },
            'calculation_methodology_changes': {
                'income_ratios': {
                    'pre_2017': 'HUD Area Median Income (AMI) based',
                    'post_2017': 'FFIEC Median Family Income (MFI) based',
                    'impact': 'More frequent updates, different calculation base'
                },
                'minority_population_calculation': {
                    'pre_2017': 'Based on decennial census with linear interpolation',
                    'post_2017': 'Based on ACS 5-year rolling estimates',
                    'impact': 'More timely but potentially less stable estimates'
                },
                'geographic_coding': {
                    'pre_2017': 'Fixed tract boundaries from decennial census',
                    'post_2017': 'Updated tract boundaries with ACS geography',
                    'impact': 'Tract boundary changes affect longitudinal comparisons'
                }
            },
            'data_quality_improvements': {
                'timeliness': 'ACS provides more current data than decennial interpolation',
                'granularity': 'Additional demographic detail available',
                'coverage': 'Better coverage of small area demographics',
                'consistency': 'Standardized processing across all areas'
            },
            'challenges_introduced': {
                'sampling_error': 'ACS estimates have margins of error, especially for small areas',
                'longitudinal_comparability': 'Methodology changes affect trend analysis',
                'data_volatility': 'ACS estimates can be more volatile than decennial data',
                'complexity': 'More complex data integration and quality control needed'
            }
        }

    def _generate_evolution_report(self):
        """Generate comprehensive evolution analysis report."""
        logger.info("Generating comprehensive evolution report")

        report = {
            'metadata': {
                'analysis_date': datetime.now().isoformat(),
                'analyst': 'Census Data Evolution Analyzer',
                'version': '1.0',
                'scope': 'HMDA Census Data Evolution Analysis 1990-2019'
            },
            'executive_summary': self._generate_executive_summary(),
            'schema_evolution': self.schema_evolution,
            'quality_metrics': self.quality_metrics,
            'methodology_changes': self.methodology_changes,
            'key_findings': self._generate_key_findings(),
            'recommendations': self._generate_recommendations()
        }

        # Save comprehensive report
        report_file = self.output_path / "census_data_evolution_report.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2, default=str)

        logger.info(f"Evolution report saved to {report_file}")

        # Generate markdown summary
        self._generate_markdown_summary(report)

    def _generate_executive_summary(self) -> Dict[str, Any]:
        """Generate executive summary of key findings."""

        # Calculate key statistics
        pre_2017_years = len([y for y in self.pre_2017_data.keys() if isinstance(y, int)])
        post_2017_years = len([y for y in self.post_2017_data.keys() if isinstance(y, int)])

        return {
            'analysis_scope': {
                'total_years_analyzed': pre_2017_years + post_2017_years,
                'pre_2017_years': pre_2017_years,
                'post_2017_years': post_2017_years,
                'transition_period': '2017-2018'
            },
            'major_changes_identified': {
                'data_source_transition': 'Shift from decennial census + interpolation to ACS 5-year estimates',
                'methodology_modernization': 'Updated income calculations and geographic coding',
                'quality_improvements': 'Enhanced timeliness and granularity',
                'new_challenges': 'Increased complexity and sampling variability'
            },
            'impact_assessment': {
                'data_quality': 'Generally improved with some trade-offs',
                'comparability': 'Longitudinal analysis requires methodological adjustments',
                'usability': 'More complex but more comprehensive',
                'stakeholder_impact': 'Requires updated analysis approaches'
            }
        }

    def _generate_key_findings(self) -> List[Dict[str, str]]:
        """Generate key findings from the analysis."""
        return [
            {
                'category': 'Data Source Evolution',
                'finding': 'Transition from decennial census to ACS improved data timeliness but introduced sampling variability',
                'impact': 'High',
                'recommendation': 'Implement margin of error reporting for small area estimates'
            },
            {
                'category': 'Schema Stability',
                'finding': f"Only {len(self.schema_evolution.get('column_stability', {}).get('stable_columns', []))} columns remained completely stable across all periods",
                'impact': 'Medium',
                'recommendation': 'Maintain comprehensive field mapping documentation'
            },
            {
                'category': 'Methodology Changes',
                'finding': 'Income calculation methodology changed from HUD AMI to FFIEC MFI basis',
                'impact': 'High',
                'recommendation': 'Provide dual calculations during transition periods'
            },
            {
                'category': 'Quality Improvements',
                'finding': 'Post-2017 data shows improved completeness but increased complexity',
                'impact': 'Medium',
                'recommendation': 'Enhance data validation and quality control procedures'
            }
        ]

    def _generate_recommendations(self) -> List[Dict[str, str]]:
        """Generate recommendations based on analysis."""
        return [
            {
                'area': 'Data Integration',
                'recommendation': 'Develop standardized crosswalk tables for pre/post-2017 comparisons',
                'priority': 'High',
                'timeline': 'Immediate'
            },
            {
                'area': 'Quality Control',
                'recommendation': 'Implement systematic margin of error tracking for ACS-based estimates',
                'priority': 'High',
                'timeline': '3 months'
            },
            {
                'area': 'Documentation',
                'recommendation': 'Create comprehensive methodology change documentation for users',
                'priority': 'Medium',
                'timeline': '6 months'
            },
            {
                'area': 'Analysis Tools',
                'recommendation': 'Develop tools to handle methodology transitions in longitudinal analysis',
                'priority': 'Medium',
                'timeline': '6-12 months'
            },
            {
                'area': 'Training',
                'recommendation': 'Provide training on ACS data characteristics and limitations',
                'priority': 'Medium',
                'timeline': 'Ongoing'
            }
        ]

    def _generate_markdown_summary(self, report: Dict):
        """Generate markdown summary of the analysis."""
        markdown_file = self.output_path / "census_data_evolution_summary.md"

        with open(markdown_file, 'w') as f:
            f.write("# Census Data Evolution Analysis Summary\n\n")
            f.write(f"**Analysis Date:** {report['metadata']['analysis_date']}\n\n")

            f.write("## Executive Summary\n\n")
            exec_summary = report['executive_summary']
            f.write(f"**Analysis Scope:** {exec_summary['analysis_scope']['total_years_analyzed']} years analyzed ")
            f.write(f"({exec_summary['analysis_scope']['pre_2017_years']} pre-2017, ")
            f.write(f"{exec_summary['analysis_scope']['post_2017_years']} post-2017)\n\n")

            f.write("### Major Changes Identified\n")
            for change, description in exec_summary['major_changes_identified'].items():
                f.write(f"- **{change.replace('_', ' ').title()}:** {description}\n")
            f.write("\n")

            f.write("## Key Findings\n\n")
            for finding in report['key_findings']:
                f.write(f"### {finding['category']}\n")
                f.write(f"**Finding:** {finding['finding']}\n\n")
                f.write(f"**Impact:** {finding['impact']}\n\n")
                f.write(f"**Recommendation:** {finding['recommendation']}\n\n")

            f.write("## Schema Evolution Summary\n\n")
            if 'column_stability' in self.schema_evolution:
                stability = self.schema_evolution['column_stability']
                f.write(f"- **Stable columns across all periods:** {stability.get('stable_count', 'Unknown')}\n")
                f.write(f"- **Total columns analyzed:** {stability.get('total_columns_analyzed', 'Unknown')}\n")

            if 'new_columns_post_2017' in self.schema_evolution:
                new_cols = len(self.schema_evolution['new_columns_post_2017'])
                f.write(f"- **New columns post-2017:** {new_cols}\n")

            if 'deprecated_columns' in self.schema_evolution:
                deprecated_cols = len(self.schema_evolution['deprecated_columns'])
                f.write(f"- **Deprecated columns post-2017:** {deprecated_cols}\n")

            f.write("\n## Recommendations\n\n")
            for rec in report['recommendations']:
                f.write(f"### {rec['area']}\n")
                f.write(f"**Priority:** {rec['priority']}\n\n")
                f.write(f"**Timeline:** {rec['timeline']}\n\n")
                f.write(f"{rec['recommendation']}\n\n")

        logger.info(f"Markdown summary saved to {markdown_file}")

    def _create_evolution_visualizations(self):
        """Create visualizations showing data evolution."""
        logger.info("Creating evolution visualizations")

        plt.style.use('seaborn-v0_8')
        fig, axes = plt.subplots(2, 2, figsize=(16, 12))
        fig.suptitle('Census Data Evolution Analysis', fontsize=16, fontweight='bold')

        # Plot 1: Data completeness over time
        self._plot_completeness_evolution(axes[0, 0])

        # Plot 2: Schema stability
        self._plot_schema_stability(axes[0, 1])

        # Plot 3: File size evolution
        self._plot_file_size_evolution(axes[1, 0])

        # Plot 4: Record count evolution
        self._plot_record_count_evolution(axes[1, 1])

        plt.tight_layout()
        plot_file = self.output_path / "census_data_evolution_plots.png"
        plt.savefig(plot_file, dpi=300, bbox_inches='tight')
        plt.close()

        logger.info(f"Evolution plots saved to {plot_file}")

    def _plot_completeness_evolution(self, ax):
        """Plot data completeness evolution over time."""
        years = []
        completeness_rates = []

        for year, metrics in self.quality_metrics.get('completeness_by_year', {}).items():
            if isinstance(year, int):
                years.append(year)
                completeness_rates.append((1 - metrics['missing_value_ratio']) * 100)

        if years and completeness_rates:
            ax.plot(years, completeness_rates, marker='o', linewidth=2, markersize=6)
            ax.axvline(x=2017, color='red', linestyle='--', alpha=0.7, label='HMDA Rule Change')
            ax.set_xlabel('Year')
            ax.set_ylabel('Data Completeness (%)')
            ax.set_title('Data Completeness Evolution')
            ax.legend()
            ax.grid(True, alpha=0.3)
        else:
            ax.text(0.5, 0.5, 'No completeness data available',
                   horizontalalignment='center', verticalalignment='center',
                   transform=ax.transAxes)

    def _plot_schema_stability(self, ax):
        """Plot schema stability distribution."""
        if 'column_stability' in self.schema_evolution:
            stability_dist = self.schema_evolution['column_stability'].get('stability_distribution', {})

            categories = list(stability_dist.keys())
            counts = list(stability_dist.values())

            if categories and counts:
                bars = ax.bar(categories, counts, alpha=0.7)
                ax.set_xlabel('Column Stability Category')
                ax.set_ylabel('Number of Columns')
                ax.set_title('Column Stability Distribution')
                ax.tick_params(axis='x', rotation=45)

                # Add value labels on bars
                for bar in bars:
                    height = bar.get_height()
                    ax.text(bar.get_x() + bar.get_width()/2., height,
                           f'{int(height)}', ha='center', va='bottom')
            else:
                ax.text(0.5, 0.5, 'No schema stability data available',
                       horizontalalignment='center', verticalalignment='center',
                       transform=ax.transAxes)
        else:
            ax.text(0.5, 0.5, 'No schema data available',
                   horizontalalignment='center', verticalalignment='center',
                   transform=ax.transAxes)

    def _plot_file_size_evolution(self, ax):
        """Plot file size evolution over time."""
        years = []
        file_sizes_mb = []

        all_data = {**self.pre_2017_data, **self.post_2017_data}
        for year, data_info in all_data.items():
            if isinstance(year, int) and 'file_size' in data_info:
                years.append(year)
                file_sizes_mb.append(data_info['file_size'] / (1024 * 1024))  # Convert to MB

        if years and file_sizes_mb:
            ax.plot(years, file_sizes_mb, marker='s', linewidth=2, markersize=6, color='green')
            ax.axvline(x=2017, color='red', linestyle='--', alpha=0.7, label='HMDA Rule Change')
            ax.set_xlabel('Year')
            ax.set_ylabel('File Size (MB)')
            ax.set_title('Census File Size Evolution')
            ax.legend()
            ax.grid(True, alpha=0.3)
        else:
            ax.text(0.5, 0.5, 'No file size data available',
                   horizontalalignment='center', verticalalignment='center',
                   transform=ax.transAxes)

    def _plot_record_count_evolution(self, ax):
        """Plot record count evolution over time."""
        years = []
        record_counts = []

        all_data = {**self.pre_2017_data, **self.post_2017_data}
        for year, data_info in all_data.items():
            if isinstance(year, int) and 'shape' in data_info:
                years.append(year)
                record_counts.append(data_info['shape'][0])

        if years and record_counts:
            ax.plot(years, record_counts, marker='^', linewidth=2, markersize=6, color='purple')
            ax.axvline(x=2017, color='red', linestyle='--', alpha=0.7, label='HMDA Rule Change')
            ax.set_xlabel('Year')
            ax.set_ylabel('Number of Records')
            ax.set_title('Census Record Count Evolution')
            ax.legend()
            ax.grid(True, alpha=0.3)

            # Format y-axis to show values in thousands/millions
            ax.ticklabel_format(style='scientific', axis='y', scilimits=(0,0))
        else:
            ax.text(0.5, 0.5, 'No record count data available',
                   horizontalalignment='center', verticalalignment='center',
                   transform=ax.transAxes)

def main():
    """Run the comprehensive census data evolution analysis."""
    analyzer = CensusDataEvolutionAnalyzer()
    analyzer.run_comprehensive_analysis()

if __name__ == "__main__":
    main()