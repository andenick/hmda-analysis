#!/usr/bin/env python3
"""
Census Tract Boundary Crosswalk Analysis for HMDA Data
=====================================================

This script analyzes census tract boundary changes across decennial periods
and creates comprehensive crosswalk tables for ensuring longitudinal
data comparability in HMDA analysis.

Key Features:
- Identifies tract boundary changes across 1990, 2000, 2010, 2020 censuses
- Creates crosswalk tables for tract-to-tract relationships
- Validates data continuity and identifies problematic boundary changes
- Generates documentation for tract comparability issues
- Downloads and processes official crosswalk files where available

Critical for:
- Longitudinal HMDA analysis
- Time series trend analysis
- Geographic consistency validation
- Research data quality assurance
"""

import pandas as pd
import numpy as np
import logging
import json
import requests
import zipfile
import io
from pathlib import Path
from datetime import datetime
from collections import defaultdict, Counter
import matplotlib.pyplot as plt
import seaborn as sns
from typing import Dict, List, Set, Tuple, Optional
import warnings
import os
DATA_ROOT = Path(os.environ.get("DATA_ROOT", "data"))
warnings.filterwarnings('ignore')

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class TractBoundaryCrosswalkAnalyzer:
    """
    Comprehensive analyzer for census tract boundary changes and crosswalks.
    """

    def __init__(self, base_path: str = str(DATA_ROOT)):
        self.base_path = Path(base_path)
        self.output_dir = self.base_path / "analysis_outputs" / "tract_boundary_analysis"
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Key decennial years for boundary analysis
        self.decennial_years = [1990, 2000, 2010, 2020]
        self.analysis_years = list(range(1990, 2024))

        # Data containers
        self.tract_data = {}
        self.boundary_changes = {}
        self.crosswalk_tables = {}
        self.problematic_tracts = defaultdict(list)

        # Official crosswalk sources
        self.crosswalk_sources = {
            'census_bureau': 'https://www.census.gov/geographies/reference-files/time-series/geo/relationship-files.html',
            'hud_usps': 'https://www.huduser.gov/portal/datasets/census_tract_crosswalk.html',
            'nhgis': 'https://www.nhgis.org/geographic-crosswalks',
            'ltdb': 'https://s4.ad.brown.edu/projects/diversity/researcher/bridging.htm'
        }

        logger.info("Initialized TractBoundaryCrosswalkAnalyzer")

    def load_hmda_census_data(self) -> None:
        """Load HMDA census data files across all available years."""
        logger.info("Loading HMDA census data files")

        # Census data files from HMDA archive
        census_files_pattern = self.base_path / "Old" / "CRA_code" / "_Archive" / "hmda-census-master" / "output" / "census_data_extract_*.csv"
        census_files = list(self.base_path.glob("Old/CRA_code/_Archive/hmda-census-master/output/census_data_extract_*.csv"))

        for file_path in sorted(census_files):
            year = int(file_path.stem.split('_')[-1])
            if year in self.analysis_years:
                try:
                    df = pd.read_csv(file_path)

                    # Standardize column names
                    df.columns = df.columns.str.strip()

                    # Create unique tract identifier
                    if 'Census Tract' in df.columns:
                        df['tract_id'] = df['State'].astype(str).str.zfill(2) + \
                                       df['County'].astype(str).str.zfill(3) + \
                                       df['Census Tract'].astype(str).str.zfill(6)

                    self.tract_data[year] = df
                    logger.info(f"Loaded {len(df)} tracts for year {year}")

                except Exception as e:
                    logger.error(f"Error loading census data for {year}: {e}")

        logger.info(f"Successfully loaded data for {len(self.tract_data)} years")

    def analyze_tract_boundary_evolution(self) -> None:
        """Analyze how tract boundaries have evolved across decennial periods."""
        logger.info("Analyzing tract boundary evolution across decennial periods")

        boundary_analysis = {
            'tract_counts_by_year': {},
            'tract_appearances': defaultdict(list),
            'stable_tracts': set(),
            'split_tracts': defaultdict(list),
            'merged_tracts': defaultdict(list),
            'new_tracts': defaultdict(list),
            'discontinued_tracts': defaultdict(list)
        }

        # Track tract appearances across years
        all_tracts = set()
        for year, df in self.tract_data.items():
            if 'tract_id' in df.columns:
                year_tracts = set(df['tract_id'].unique())
                boundary_analysis['tract_counts_by_year'][year] = len(year_tracts)
                all_tracts.update(year_tracts)

                for tract in year_tracts:
                    boundary_analysis['tract_appearances'][tract].append(year)

        # Analyze tract stability and changes
        for tract_id, appearances in boundary_analysis['tract_appearances'].items():
            appearance_span = max(appearances) - min(appearances) + 1
            expected_years = len([y for y in self.analysis_years if min(appearances) <= y <= max(appearances)])

            if len(appearances) == expected_years:
                boundary_analysis['stable_tracts'].add(tract_id)
            else:
                # Identify type of change
                gaps = []
                sorted_appearances = sorted(appearances)
                for i in range(1, len(sorted_appearances)):
                    if sorted_appearances[i] - sorted_appearances[i-1] > 1:
                        gaps.append((sorted_appearances[i-1], sorted_appearances[i]))

                if gaps:
                    self.problematic_tracts['discontinuous'].append({
                        'tract_id': tract_id,
                        'appearances': appearances,
                        'gaps': gaps
                    })

        # Identify boundary changes at decennial transitions
        for i in range(len(self.decennial_years) - 1):
            prev_year = self.decennial_years[i]
            curr_year = self.decennial_years[i + 1]

            if prev_year in self.tract_data and curr_year in self.tract_data:
                prev_tracts = set(self.tract_data[prev_year]['tract_id'].unique())
                curr_tracts = set(self.tract_data[curr_year]['tract_id'].unique())

                # New tracts in current period
                new_tracts = curr_tracts - prev_tracts
                boundary_analysis['new_tracts'][f"{prev_year}-{curr_year}"] = list(new_tracts)

                # Discontinued tracts from previous period
                discontinued = prev_tracts - curr_tracts
                boundary_analysis['discontinued_tracts'][f"{prev_year}-{curr_year}"] = list(discontinued)

                # Potential splits (new tracts with similar IDs to discontinued ones)
                for disc_tract in discontinued:
                    base_tract = disc_tract[:10]  # First 10 digits (state + county + base tract)
                    potential_splits = [t for t in new_tracts if t.startswith(base_tract)]
                    if len(potential_splits) > 1:
                        boundary_analysis['split_tracts'][f"{prev_year}-{curr_year}"].append({
                            'original': disc_tract,
                            'splits': potential_splits
                        })

        self.boundary_changes = boundary_analysis
        logger.info(f"Boundary analysis complete: {len(boundary_analysis['stable_tracts'])} stable tracts identified")

    def create_tract_crosswalk_tables(self) -> None:
        """Create comprehensive crosswalk tables for tract-to-tract relationships."""
        logger.info("Creating tract-to-tract crosswalk tables")

        crosswalks = {}

        # Create crosswalks between consecutive decennial periods
        for i in range(len(self.decennial_years) - 1):
            prev_year = self.decennial_years[i]
            curr_year = self.decennial_years[i + 1]

            if prev_year in self.tract_data and curr_year in self.tract_data:
                period_key = f"{prev_year}_to_{curr_year}"
                crosswalk = self._create_period_crosswalk(prev_year, curr_year)
                crosswalks[period_key] = crosswalk

                # Save individual crosswalk table
                crosswalk_file = self.output_dir / f"tract_crosswalk_{period_key}.csv"
                crosswalk.to_csv(crosswalk_file, index=False)
                logger.info(f"Created crosswalk for {period_key}: {len(crosswalk)} relationships")

        # Create comprehensive master crosswalk
        master_crosswalk = self._create_master_crosswalk(crosswalks)
        master_file = self.output_dir / "tract_crosswalk_master.csv"
        master_crosswalk.to_csv(master_file, index=False)

        self.crosswalk_tables = crosswalks
        logger.info("Crosswalk table creation complete")

    def _create_period_crosswalk(self, prev_year: int, curr_year: int) -> pd.DataFrame:
        """Create crosswalk table between two specific years."""
        prev_df = self.tract_data[prev_year].copy()
        curr_df = self.tract_data[curr_year].copy()

        # Prepare geographic and demographic data for matching
        prev_geo = prev_df.groupby('tract_id').agg({
            'State': 'first',
            'County': 'first',
            'Census Tract': 'first',
            'Population': 'first',
            'MSA/MD': 'first'
        }).reset_index()

        curr_geo = curr_df.groupby('tract_id').agg({
            'State': 'first',
            'County': 'first',
            'Census Tract': 'first',
            'Population': 'first',
            'MSA/MD': 'first'
        }).reset_index()

        # Create crosswalk relationships
        crosswalk_records = []

        # Direct matches (same tract ID)
        common_tracts = set(prev_geo['tract_id']) & set(curr_geo['tract_id'])
        for tract_id in common_tracts:
            prev_pop = prev_geo[prev_geo['tract_id'] == tract_id]['Population'].iloc[0]
            curr_pop = curr_geo[curr_geo['tract_id'] == tract_id]['Population'].iloc[0]

            crosswalk_records.append({
                f'tract_id_{prev_year}': tract_id,
                f'tract_id_{curr_year}': tract_id,
                'relationship_type': 'identical',
                'confidence': 1.0,
                f'population_{prev_year}': prev_pop,
                f'population_{curr_year}': curr_pop,
                'population_change_ratio': curr_pop / prev_pop if prev_pop > 0 else np.nan
            })

        # Handle splits and merges
        prev_only = set(prev_geo['tract_id']) - common_tracts
        curr_only = set(curr_geo['tract_id']) - common_tracts

        # Identify potential splits (one prev -> multiple curr)
        for prev_tract in prev_only:
            base_tract = prev_tract[:10]  # State + County + base tract code
            potential_successors = [t for t in curr_only if t.startswith(base_tract)]

            if len(potential_successors) > 1:
                # This appears to be a split
                prev_pop = prev_geo[prev_geo['tract_id'] == prev_tract]['Population'].iloc[0]
                total_curr_pop = sum([
                    curr_geo[curr_geo['tract_id'] == t]['Population'].iloc[0]
                    for t in potential_successors
                ])

                for succ_tract in potential_successors:
                    succ_pop = curr_geo[curr_geo['tract_id'] == succ_tract]['Population'].iloc[0]
                    weight = succ_pop / total_curr_pop if total_curr_pop > 0 else 1.0 / len(potential_successors)

                    crosswalk_records.append({
                        f'tract_id_{prev_year}': prev_tract,
                        f'tract_id_{curr_year}': succ_tract,
                        'relationship_type': 'split',
                        'confidence': 0.8,
                        'weight': weight,
                        f'population_{prev_year}': prev_pop,
                        f'population_{curr_year}': succ_pop,
                        'population_change_ratio': succ_pop / prev_pop if prev_pop > 0 else np.nan
                    })

        # Identify potential merges (multiple prev -> one curr)
        for curr_tract in curr_only:
            base_tract = curr_tract[:10]
            potential_predecessors = [t for t in prev_only if t.startswith(base_tract)]

            if len(potential_predecessors) > 1:
                # This appears to be a merge
                curr_pop = curr_geo[curr_geo['tract_id'] == curr_tract]['Population'].iloc[0]
                total_prev_pop = sum([
                    prev_geo[prev_geo['tract_id'] == t]['Population'].iloc[0]
                    for t in potential_predecessors
                ])

                for pred_tract in potential_predecessors:
                    pred_pop = prev_geo[prev_geo['tract_id'] == pred_tract]['Population'].iloc[0]
                    weight = pred_pop / total_prev_pop if total_prev_pop > 0 else 1.0 / len(potential_predecessors)

                    crosswalk_records.append({
                        f'tract_id_{prev_year}': pred_tract,
                        f'tract_id_{curr_year}': curr_tract,
                        'relationship_type': 'merge',
                        'confidence': 0.8,
                        'weight': weight,
                        f'population_{prev_year}': pred_pop,
                        f'population_{curr_year}': curr_pop,
                        'population_change_ratio': curr_pop / pred_pop if pred_pop > 0 else np.nan
                    })

        return pd.DataFrame(crosswalk_records)

    def _create_master_crosswalk(self, period_crosswalks: Dict) -> pd.DataFrame:
        """Create a master crosswalk table linking all periods."""
        # This would create a comprehensive table linking tracts across all periods
        # For now, return a summary of all period crosswalks
        master_records = []

        for period, crosswalk in period_crosswalks.items():
            for _, row in crosswalk.iterrows():
                master_records.append({
                    'period': period,
                    'relationship_type': row['relationship_type'],
                    'confidence': row.get('confidence', 1.0),
                    **{k: v for k, v in row.items() if k not in ['relationship_type', 'confidence']}
                })

        return pd.DataFrame(master_records)

    def validate_longitudinal_comparability(self) -> None:
        """Validate data comparability issues for longitudinal analysis."""
        logger.info("Validating longitudinal data comparability")

        validation_results = {
            'tract_consistency_issues': [],
            'population_anomalies': [],
            'geographic_discontinuities': [],
            'data_quality_flags': []
        }

        # Check for extreme population changes that might indicate boundary issues
        for period, crosswalk in self.crosswalk_tables.items():
            if 'population_change_ratio' in crosswalk.columns:
                extreme_changes = crosswalk[
                    (crosswalk['population_change_ratio'] > 5) |
                    (crosswalk['population_change_ratio'] < 0.2)
                ]

                for _, row in extreme_changes.iterrows():
                    validation_results['population_anomalies'].append({
                        'period': period,
                        'tract_prev': row[f'tract_id_{period.split("_to_")[0]}'],
                        'tract_curr': row[f'tract_id_{period.split("_to_")[1]}'],
                        'change_ratio': row['population_change_ratio'],
                        'relationship_type': row['relationship_type']
                    })

        # Identify tracts with complex boundary changes
        for tract_id, issues in self.problematic_tracts.items():
            for issue in issues:
                validation_results['geographic_discontinuities'].append(issue)

        # Save validation results
        validation_file = self.output_dir / "longitudinal_comparability_validation.json"
        with open(validation_file, 'w') as f:
            json.dump(validation_results, f, indent=2, default=str)

        logger.info(f"Validation complete: {len(validation_results['population_anomalies'])} anomalies identified")

    def download_official_crosswalks(self) -> None:
        """Download official crosswalk files from Census Bureau and other sources."""
        logger.info("Attempting to download official crosswalk files")

        # Create directory for official crosswalks
        official_dir = self.output_dir / "official_crosswalks"
        official_dir.mkdir(exist_ok=True)

        # Known direct download URLs for Census Bureau relationship files
        census_urls = {
            '2020_to_2010_tract': 'https://www2.census.gov/geo/docs/maps-data/data/rel2020/tract/tab20_tract20_tract10_natl.txt',
            '2010_to_2000_tract': 'https://www2.census.gov/geo/docs/maps-data/data/rel/tl_2010_tract00_tract10_natl.txt'
        }

        downloaded_files = []
        for file_key, url in census_urls.items():
            try:
                response = requests.get(url, timeout=30)
                if response.status_code == 200:
                    file_path = official_dir / f"{file_key}_crosswalk.txt"
                    with open(file_path, 'w') as f:
                        f.write(response.text)
                    downloaded_files.append(file_path)
                    logger.info(f"Downloaded {file_key} crosswalk")
                else:
                    logger.warning(f"Could not download {file_key}: HTTP {response.status_code}")
            except Exception as e:
                logger.error(f"Error downloading {file_key}: {e}")

        return downloaded_files

    def create_visualizations(self) -> None:
        """Create visualizations of tract boundary changes."""
        logger.info("Creating tract boundary change visualizations")

        # Set up the plotting style
        plt.style.use('default')
        fig, axes = plt.subplots(2, 2, figsize=(15, 12))
        fig.suptitle('Census Tract Boundary Evolution Analysis', fontsize=16, fontweight='bold')

        # Plot 1: Tract count by year
        years = sorted(self.boundary_changes['tract_counts_by_year'].keys())
        counts = [self.boundary_changes['tract_counts_by_year'][y] for y in years]

        axes[0, 0].plot(years, counts, marker='o', linewidth=2, markersize=6)
        axes[0, 0].set_title('Total Census Tracts by Year')
        axes[0, 0].set_xlabel('Year')
        axes[0, 0].set_ylabel('Number of Census Tracts')
        axes[0, 0].grid(True, alpha=0.3)

        # Plot 2: Boundary changes by decennial period
        periods = []
        new_counts = []
        discontinued_counts = []

        for period, new_tracts in self.boundary_changes['new_tracts'].items():
            periods.append(period)
            new_counts.append(len(new_tracts))
            discontinued_counts.append(len(self.boundary_changes['discontinued_tracts'][period]))

        x = np.arange(len(periods))
        width = 0.35

        axes[0, 1].bar(x - width/2, new_counts, width, label='New Tracts', alpha=0.8)
        axes[0, 1].bar(x + width/2, discontinued_counts, width, label='Discontinued Tracts', alpha=0.8)
        axes[0, 1].set_title('Tract Changes by Decennial Period')
        axes[0, 1].set_xlabel('Period')
        axes[0, 1].set_ylabel('Number of Tracts')
        axes[0, 1].set_xticks(x)
        axes[0, 1].set_xticklabels(periods, rotation=45)
        axes[0, 1].legend()

        # Plot 3: Distribution of tract appearance spans
        appearance_spans = []
        for tract_id, appearances in self.boundary_changes['tract_appearances'].items():
            span = max(appearances) - min(appearances) + 1
            appearance_spans.append(span)

        axes[1, 0].hist(appearance_spans, bins=20, alpha=0.7, edgecolor='black')
        axes[1, 0].set_title('Distribution of Tract Appearance Spans')
        axes[1, 0].set_xlabel('Years Active')
        axes[1, 0].set_ylabel('Number of Tracts')

        # Plot 4: Relationship types in crosswalks
        if self.crosswalk_tables:
            relationship_counts = Counter()
            for period, crosswalk in self.crosswalk_tables.items():
                relationship_counts.update(crosswalk['relationship_type'])

            types = list(relationship_counts.keys())
            counts = list(relationship_counts.values())

            axes[1, 1].pie(counts, labels=types, autopct='%1.1f%%', startangle=90)
            axes[1, 1].set_title('Distribution of Tract Relationships')

        plt.tight_layout()

        # Save the plot
        plot_file = self.output_dir / "tract_boundary_evolution_analysis.png"
        plt.savefig(plot_file, dpi=300, bbox_inches='tight')
        plt.close()

        logger.info(f"Visualizations saved to {plot_file}")

    def generate_comprehensive_report(self) -> None:
        """Generate comprehensive report on tract boundary analysis."""
        logger.info("Generating comprehensive boundary analysis report")

        report = {
            'metadata': {
                'analysis_date': datetime.now().isoformat(),
                'analyzer': 'TractBoundaryCrosswalkAnalyzer',
                'version': '1.0',
                'scope': 'HMDA Census Tract Boundary Evolution Analysis'
            },
            'executive_summary': {
                'total_years_analyzed': len(self.tract_data),
                'decennial_periods_covered': len(self.decennial_years) - 1,
                'total_unique_tracts': len(self.boundary_changes['tract_appearances']),
                'stable_tracts_count': len(self.boundary_changes['stable_tracts']),
                'problematic_tracts_count': sum(len(issues) for issues in self.problematic_tracts.values())
            },
            'boundary_changes': self.boundary_changes,
            'crosswalk_summary': {
                period: {
                    'total_relationships': len(crosswalk),
                    'relationship_types': crosswalk['relationship_type'].value_counts().to_dict()
                }
                for period, crosswalk in self.crosswalk_tables.items()
            },
            'data_quality_assessment': {
                'continuity_issues': len(self.problematic_tracts['discontinuous']),
                'population_anomalies': len([
                    issue for crosswalk in self.crosswalk_tables.values()
                    for _, issue in crosswalk.iterrows()
                    if issue.get('population_change_ratio', 1) > 5 or issue.get('population_change_ratio', 1) < 0.2
                ])
            },
            'recommendations': {
                'high_priority': [
                    "Implement tract boundary validation in all longitudinal HMDA analysis",
                    "Use crosswalk tables for any analysis spanning decennial boundaries",
                    "Flag and investigate extreme population changes between periods"
                ],
                'medium_priority': [
                    "Download and integrate official Census Bureau relationship files",
                    "Develop automated boundary change detection systems",
                    "Create validation procedures for tract-level time series"
                ],
                'documentation_needs': [
                    "Document all known boundary changes for research use",
                    "Create user guides for proper crosswalk table usage",
                    "Maintain updated boundary change documentation"
                ]
            }
        }

        # Save detailed JSON report
        report_file = self.output_dir / "tract_boundary_comprehensive_report.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2, default=str)

        # Save human-readable summary
        summary_file = self.output_dir / "tract_boundary_analysis_summary.md"
        self._save_markdown_summary(report, summary_file)

        logger.info(f"Comprehensive report saved to {report_file}")

    def _save_markdown_summary(self, report: dict, file_path: Path) -> None:
        """Save a human-readable markdown summary of the analysis."""
        with open(file_path, 'w') as f:
            f.write("# Census Tract Boundary Crosswalk Analysis Summary\n\n")
            f.write(f"**Analysis Date:** {report['metadata']['analysis_date']}\n\n")

            f.write("## Executive Summary\n\n")
            exec_summary = report['executive_summary']
            f.write(f"- **Years Analyzed:** {exec_summary['total_years_analyzed']}\n")
            f.write(f"- **Decennial Periods:** {exec_summary['decennial_periods_covered']}\n")
            f.write(f"- **Total Unique Tracts:** {exec_summary['total_unique_tracts']:,}\n")
            f.write(f"- **Stable Tracts:** {exec_summary['stable_tracts_count']:,}\n")
            f.write(f"- **Problematic Tracts:** {exec_summary['problematic_tracts_count']:,}\n\n")

            f.write("## Key Findings\n\n")

            # Boundary changes summary
            f.write("### Tract Count Evolution\n")
            for year, count in sorted(report['boundary_changes']['tract_counts_by_year'].items()):
                f.write(f"- **{year}:** {count:,} tracts\n")
            f.write("\n")

            # Crosswalk summaries
            f.write("### Crosswalk Table Summary\n")
            for period, summary in report['crosswalk_summary'].items():
                f.write(f"#### {period.replace('_', ' → ')}\n")
                f.write(f"- **Total Relationships:** {summary['total_relationships']:,}\n")
                f.write("- **Relationship Types:**\n")
                for rel_type, count in summary['relationship_types'].items():
                    f.write(f"  - {rel_type}: {count:,}\n")
                f.write("\n")

            # Recommendations
            f.write("## Recommendations\n\n")
            f.write("### High Priority\n")
            for rec in report['recommendations']['high_priority']:
                f.write(f"- {rec}\n")
            f.write("\n")

            f.write("### Medium Priority\n")
            for rec in report['recommendations']['medium_priority']:
                f.write(f"- {rec}\n")
            f.write("\n")

            f.write("### Documentation Needs\n")
            for rec in report['recommendations']['documentation_needs']:
                f.write(f"- {rec}\n")
            f.write("\n")

    def run_comprehensive_analysis(self) -> None:
        """Run the complete tract boundary crosswalk analysis."""
        logger.info("Starting comprehensive tract boundary crosswalk analysis")

        try:
            # Step 1: Load data
            self.load_hmda_census_data()

            # Step 2: Analyze boundary evolution
            self.analyze_tract_boundary_evolution()

            # Step 3: Create crosswalk tables
            self.create_tract_crosswalk_tables()

            # Step 4: Validate comparability
            self.validate_longitudinal_comparability()

            # Step 5: Download official crosswalks
            self.download_official_crosswalks()

            # Step 6: Create visualizations
            self.create_visualizations()

            # Step 7: Generate comprehensive report
            self.generate_comprehensive_report()

            logger.info("Tract boundary crosswalk analysis completed successfully")
            logger.info(f"Results saved to: {self.output_dir}")

        except Exception as e:
            logger.error(f"Error in comprehensive analysis: {e}")
            raise

if __name__ == "__main__":
    # Run the comprehensive analysis
    analyzer = TractBoundaryCrosswalkAnalyzer()
    analyzer.run_comprehensive_analysis()