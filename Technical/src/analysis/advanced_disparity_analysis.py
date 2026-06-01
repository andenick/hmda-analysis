#!/usr/bin/env python3
"""
Advanced Disparity Analysis Tool
Comprehensive statistical analysis of lending disparities
Implements sophisticated disparity metrics and statistical testing
"""

import pandas as pd
import numpy as np
import scipy.stats as stats
from scipy.stats import chi2_contingency, fisher_exact
import logging
from pathlib import Path
import json
from datetime import datetime
from typing import Dict, List, Any, Tuple
import warnings
from dataclasses import dataclass
import matplotlib.pyplot as plt
import seaborn as sns
import os
DATA_ROOT = Path(os.environ.get("DATA_ROOT", "data"))

warnings.filterwarnings('ignore')

@dataclass
class DisparityResult:
    """Container for disparity analysis results"""
    metric_name: str
    group1: str
    group2: str
    group1_value: float
    group2_value: float
    disparity_ratio: float
    statistical_test: str
    p_value: float
    is_significant: bool
    confidence_interval: Tuple[float, float]
    effect_size: str

class AdvancedDisparityAnalyzer:
    """
    Advanced disparity analysis with statistical rigor
    Implements multiple disparity metrics and significance testing
    """

    def __init__(self, base_path: str = str(DATA_ROOT)):
        self.base_path = Path(base_path)
        self.data_path = self.base_path / "Output" / "Data" / "streamlined_analysis"
        self.output_path = self.base_path / "Output" / "Data" / "disparity_analysis"
        self.output_path.mkdir(parents=True, exist_ok=True)

        # Configure logging
        log_file = self.output_path / f"disparity_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)

        self.logger.info("Advanced Disparity Analyzer Initialized")

        # Initialize results storage
        self.disparity_results = []
        self.analysis_summary = {}

        # Define protected groups for analysis
        self.protected_groups = {
            'race': {
                'minority': ['Black or African American', 'American Indian or Alaska Native',
                           'Asian', 'Native Hawaiian or Other Pacific Islander'],
                'reference': ['White'],
                'hispanic': ['Hispanic or Latino']
            },
            'ethnicity': {
                'hispanic': ['Hispanic or Latino'],
                'non_hispanic': ['Not Hispanic or Latino']
            },
            'gender': {
                'female': ['Female'],
                'male': ['Male']
            }
        }

    def load_analysis_data(self) -> Dict[str, pd.DataFrame]:
        """Load data from previous analysis"""
        self.logger.info("Loading analysis data...")

        data_files = {}
        required_files = [
            'race_analysis.csv',
            'ethnicity_analysis.csv',
            'gender_analysis.csv',
            'state_analysis.csv',
            'race_approval_disparity.csv',
            'race_interest_rate_disparity.csv'
        ]

        for file_name in required_files:
            file_path = self.data_path / file_name
            if file_path.exists():
                try:
                    data_files[file_name.replace('.csv', '')] = pd.read_csv(file_path)
                    self.logger.info(f"Loaded: {file_name}")
                except Exception as e:
                    self.logger.warning(f"Failed to load {file_name}: {str(e)}")

        return data_files

    def calculate_disparity_ratio(self, group1_value: float, group2_value: float) -> float:
        """Calculate disparity ratio between two groups"""
        if group2_value == 0:
            return float('inf') if group1_value > 0 else 1.0
        return group1_value / group2_value

    def calculate_statistical_significance(self,
                                         group1_success: int, group1_total: int,
                                         group2_success: int, group2_total: int) -> Tuple[str, float]:
        """Calculate statistical significance for rate comparisons"""

        # Create contingency table
        contingency = np.array([
            [group1_success, group1_total - group1_success],
            [group2_success, group2_total - group2_success]
        ])

        try:
            # Use Fisher's exact test for small samples, chi-square for larger
            if min(contingency.sum(axis=1)) < 5:
                # Fisher's exact test
                _, p_value = fisher_exact(contingency)
                test_type = "Fisher's Exact"
            else:
                # Chi-square test
                _, p_value, _, _ = chi2_contingency(contingency)
                test_type = "Chi-square"

            return test_type, p_value

        except Exception as e:
            self.logger.warning(f"Statistical test failed: {str(e)}")
            return "Failed", 1.0

    def calculate_confidence_interval(self,
                                    proportion: float,
                                    sample_size: int,
                                    confidence_level: float = 0.95) -> Tuple[float, float]:
        """Calculate confidence interval for proportion"""
        if sample_size == 0:
            return 0.0, 1.0

        # Wilson score interval
        z = stats.norm.ppf(1 - (1 - confidence_level) / 2)
        denominator = 1 + z**2 / sample_size
        centre_adjusted = (proportion + z**2 / (2 * sample_size)) / denominator
        margin = z * np.sqrt((proportion * (1 - proportion) / sample_size +
                             z**2 / (4 * sample_size**2)) / denominator)

        return max(0, centre_adjusted - margin), min(1, centre_adjusted + margin)

    def calculate_effect_size(self,
                            group1_rate: float,
                            group2_rate: float) -> str:
        """Calculate and categorize effect size (Cohen's h)"""
        # Cohen's h for difference in proportions
        h = 2 * np.arcsin(np.sqrt(group1_rate)) - 2 * np.arcsin(np.sqrt(group2_rate))

        if abs(h) < 0.2:
            return "Small"
        elif abs(h) < 0.5:
            return "Medium"
        elif abs(h) < 0.8:
            return "Large"
        else:
            return "Very Large"

    def analyze_approval_disparities(self, approval_data: pd.DataFrame) -> List[DisparityResult]:
        """Analyze approval rate disparities across demographic groups"""
        self.logger.info("Analyzing approval rate disparities...")

        results = []

        if 'approval_rate' not in approval_data.columns or 'race' not in approval_data.columns:
            self.logger.warning("Required columns not found in approval data")
            return results

        # Get White reference group
        white_data = approval_data[approval_data['race'] == 'White']
        if white_data.empty:
            self.logger.warning("White reference group not found")
            return results

        white_rate = white_data['approval_rate'].iloc[0]
        white_total = approval_data[approval_data['race'] == 'White']['total_applications'].iloc[0]
        white_approved = approval_data[approval_data['race'] == 'White']['approved_count'].iloc[0]

        # Compare each minority group to White
        for _, row in approval_data.iterrows():
            race = row['race']
            if race in ['White', 'Unknown']:
                continue

            group_rate = row['approval_rate']
            group_total = row['total_applications']
            group_approved = row['approved_count']

            # Calculate metrics
            disparity_ratio = self.calculate_disparity_ratio(group_rate, white_rate)
            test_type, p_value = self.calculate_statistical_significance(
                group_approved, group_total, white_approved, white_total
            )
            confidence_interval = self.calculate_confidence_interval(group_rate, group_total)
            effect_size = self.calculate_effect_size(group_rate, white_rate)

            result = DisparityResult(
                metric_name="Approval Rate",
                group1=race,
                group2="White",
                group1_value=group_rate,
                group2_value=white_rate,
                disparity_ratio=disparity_ratio,
                statistical_test=test_type,
                p_value=p_value,
                is_significant=p_value < 0.05,
                confidence_interval=confidence_interval,
                effect_size=effect_size
            )
            results.append(result)

        return results

    def analyze_interest_rate_disparities(self, rate_data: pd.DataFrame) -> List[DisparityResult]:
        """Analyze interest rate disparities across demographic groups"""
        self.logger.info("Analyzing interest rate disparities...")

        results = []

        if 'mean' not in rate_data.columns or 'race' not in rate_data.columns:
            self.logger.warning("Required columns not found in interest rate data")
            return results

        # Get White reference group
        white_data = rate_data[rate_data['race'] == 'White']
        if white_data.empty:
            self.logger.warning("White reference group not found")
            return results

        white_mean = white_data['mean'].iloc[0]
        white_count = white_data['count'].iloc[0]

        # Compare each minority group to White
        for _, row in rate_data.iterrows():
            race = row['race']
            if race in ['White', 'Unknown']:
                continue

            group_mean = row['mean']
            group_count = row['count']

            # Simple t-test for difference in means (simplified)
            if group_count > 0 and white_count > 0:
                pooled_se = np.sqrt((row['std']**2 / group_count + white_data['std'].iloc[0]**2 / white_count))
                if pooled_se > 0:
                    t_stat = (group_mean - white_mean) / pooled_se
                    p_value = 2 * (1 - stats.t.cdf(abs(t_stat), df=min(group_count, white_count) - 1))
                else:
                    p_value = 1.0
            else:
                p_value = 1.0

            # Calculate metrics
            disparity_ratio = self.calculate_disparity_ratio(group_mean, white_mean)
            effect_size = self.calculate_effect_size(group_mean / 100, white_mean / 100)  # Convert to rates

            result = DisparityResult(
                metric_name="Interest Rate (Mean)",
                group1=race,
                group2="White",
                group1_value=group_mean,
                group2_value=white_mean,
                disparity_ratio=disparity_ratio,
                statistical_test="t-test",
                p_value=p_value,
                is_significant=p_value < 0.05,
                confidence_interval=(group_mean - row['std'], group_mean + row['std']),
                effect_size=effect_size
            )
            results.append(result)

        return results

    def analyze_geographic_disparities(self, state_data: pd.DataFrame) -> List[DisparityResult]:
        """Analyze disparities across geographic regions"""
        self.logger.info("Analyzing geographic disparities...")

        results = []

        required_cols = ['state_code', 'origination_rate', 'minority_applicant_rate']
        if not all(col in state_data.columns for col in required_cols):
            self.logger.warning("Required columns not found in state data")
            return results

        # Calculate correlation between minority rate and origination rate
        correlation = state_data['minority_applicant_rate'].corr(state_data['origination_rate'])

        # Find states with highest and lowest disparity
        state_data['disparity_index'] = state_data['minority_applicant_rate'] - state_data['origination_rate']

        highest_disparity = state_data.loc[state_data['disparity_index'].idxmax()]
        lowest_disparity = state_data.loc[state_data['disparity_index'].idxmin()]

        # Create results for extreme cases
        for extreme_type, row in [('Highest Minority Application', highest_disparity),
                                 ('Lowest Minority Application', lowest_disparity)]:
            result = DisparityResult(
                metric_name=f"Geographic Disparity ({extreme_type})",
                group1=row['state_code'],
                group2="National Average",
                group1_value=row['minority_applicant_rate'],
                group2_value=state_data['minority_applicant_rate'].mean(),
                disparity_ratio=self.calculate_disparity_ratio(
                    row['minority_applicant_rate'], state_data['minority_applicant_rate'].mean()
                ),
                statistical_test="Descriptive",
                p_value=1.0,  # Not applicable for descriptive analysis
                is_significant=False,
                confidence_interval=(0, 1),
                effect_size="N/A"
            )
            results.append(result)

        return results

    def create_disparity_summary(self, all_results: List[DisparityResult]) -> Dict[str, Any]:
        """Create comprehensive summary of disparity analysis"""
        self.logger.info("Creating disparity analysis summary...")

        summary = {
            'analysis_timestamp': datetime.now().isoformat(),
            'total_disparities_analyzed': len(all_results),
            'significant_disparities': len([r for r in all_results if r.is_significant]),
            'disparities_by_metric': {},
            'key_findings': [],
            'statistical_power': {}
        }

        # Group results by metric
        metrics = set(r.metric_name for r in all_results)
        for metric in metrics:
            metric_results = [r for r in all_results if r.metric_name == metric]

            summary['disparities_by_metric'][metric] = {
                'total_comparisons': len(metric_results),
                'significant': len([r for r in metric_results if r.is_significant]),
                'average_disparity_ratio': np.mean([r.disparity_ratio for r in metric_results if np.isfinite(r.disparity_ratio)]),
                'largest_disparity': max(metric_results, key=lambda x: x.disparity_ratio if np.isfinite(x.disparity_ratio) else 0),
                'most_significant': min(metric_results, key=lambda x: x.p_value)
            }

        # Key findings
        if all_results:
            # Find most significant disparities
            most_significant = sorted(all_results, key=lambda x: x.p_value)[:5]
            summary['key_findings'] = [
                f"{r.group1} vs {r.group2} in {r.metric_name}: "
                f"ratio={r.disparity_ratio:.3f}, p={r.p_value:.4f}, effect={r.effect_size}"
                for r in most_significant
            ]

        # Statistical power analysis
        total_comparisons = len(all_results)
        significant_comparisons = len([r for r in all_results if r.is_significant])
        summary['statistical_power'] = {
            'power_rate': significant_comparisons / total_comparisons if total_comparisons > 0 else 0,
            'type_i_error_rate': 0.05,  # Standard alpha level
            'bonferroni_corrected_alpha': 0.05 / total_comparisons if total_comparisons > 0 else 0.05
        }

        return summary

    def save_results(self, all_results: List[DisparityResult], summary: Dict[str, Any]) -> None:
        """Save disparity analysis results"""
        self.logger.info("Saving disparity analysis results...")

        # Convert results to DataFrame for easy export
        results_data = []
        for result in all_results:
            results_data.append({
                'metric_name': result.metric_name,
                'group1': result.group1,
                'group2': result.group2,
                'group1_value': result.group1_value,
                'group2_value': result.group2_value,
                'disparity_ratio': result.disparity_ratio,
                'statistical_test': result.statistical_test,
                'p_value': result.p_value,
                'is_significant': result.is_significant,
                'ci_lower': result.confidence_interval[0],
                'ci_upper': result.confidence_interval[1],
                'effect_size': result.effect_size
            })

        results_df = pd.DataFrame(results_data)

        # Save as CSV
        csv_file = self.output_path / "disparity_analysis_results.csv"
        results_df.to_csv(csv_file, index=False)

        # Save as Excel (single sheet)
        excel_file = self.output_path / "disparity_analysis_results.xlsx"
        results_df.to_excel(excel_file, index=False, sheet_name='Disparity Results')

        # Save summary
        summary_file = self.output_path / "disparity_analysis_summary.json"
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2, default=str)

        # Create detailed report
        report_file = self.output_path / "disparity_analysis_report.txt"
        with open(report_file, 'w') as f:
            f.write(self.generate_text_report(all_results, summary))

        self.logger.info(f"Results saved to {self.output_path}")

    def generate_text_report(self, results: List[DisparityResult], summary: Dict[str, Any]) -> str:
        """Generate comprehensive text report"""
        report = []
        report.append("=" * 80)
        report.append("ADVANCED DISPARITY ANALYSIS REPORT")
        report.append("=" * 80)
        report.append(f"Analysis Date: {summary['analysis_timestamp']}")
        report.append(f"Total Disparities Analyzed: {summary['total_disparities_analyzed']}")
        report.append(f"Statistically Significant: {summary['significant_disparities']}")
        report.append(f"Significance Rate: {summary['significant_disparities']/summary['total_disparities_analyzed']:.1%}")
        report.append("")

        # Disparities by metric
        report.append("DISPARITIES BY METRIC:")
        report.append("-" * 40)
        for metric, data in summary['disparities_by_metric'].items():
            report.append(f"\n{metric}:")
            report.append(f"  Total comparisons: {data['total_comparisons']}")
            report.append(f"  Significant findings: {data['significant']}")
            report.append(f"  Average disparity ratio: {data['average_disparity_ratio']:.3f}")
            if data['largest_disparity']:
                largest = data['largest_disparity']
                report.append(f"  Largest disparity: {largest.group1} vs {largest.group2} (ratio={largest.disparity_ratio:.3f})")

        # Key findings
        if summary['key_findings']:
            report.append("\nKEY FINDINGS:")
            report.append("-" * 40)
            for finding in summary['key_findings']:
                report.append(f"• {finding}")

        # Statistical significance summary
        report.append("\nSTATISTICAL SIGNIFICANCE SUMMARY:")
        report.append("-" * 40)
        power = summary['statistical_power']
        report.append(f"Statistical power: {power['power_rate']:.1%}")
        report.append(f"Type I error rate: {power['type_i_error_rate']}")
        report.append(f"Bonferroni corrected alpha: {power['bonferroni_corrected_alpha']:.6f}")

        # Detailed results table
        report.append("\nDETAILED RESULTS:")
        report.append("-" * 40)
        report.append(f"{'Metric':<25} {'Group1':<20} {'Group2':<10} {'Ratio':<8} {'P-value':<10} {'Significant':<10} {'Effect':<8}")
        report.append("-" * 90)

        for result in sorted(results, key=lambda x: x.p_value):
            sig_marker = "*" if result.is_significant else ""
            report.append(f"{result.metric_name:<25} {result.group1:<20} {result.group2:<10} "
                         f"{result.disparity_ratio:<8.3f} {result.p_value:<10.4f} "
                         f"{'Yes' + sig_marker:<10} {result.effect_size:<8}")

        report.append("\n" + "=" * 80)
        report.append("* Significant at p < 0.05")
        report.append("=" * 80)

        return "\n".join(report)

    def run_comprehensive_disparity_analysis(self) -> Dict[str, Any]:
        """Run complete disparity analysis"""
        self.logger.info("Starting comprehensive disparity analysis...")

        start_time = datetime.now()
        results = {
            'start_time': start_time,
            'status': 'started'
        }

        try:
            # Load data
            data_files = self.load_analysis_data()
            if not data_files:
                raise ValueError("No data files available for analysis")

            all_results = []

            # Analyze approval disparities
            if 'race_approval_disparity' in data_files:
                approval_results = self.analyze_approval_disparities(data_files['race_approval_disparity'])
                all_results.extend(approval_results)

            # Analyze interest rate disparities
            if 'race_interest_rate_disparity' in data_files:
                rate_results = self.analyze_interest_rate_disparities(data_files['race_interest_rate_disparity'])
                all_results.extend(rate_results)

            # Analyze geographic disparities
            if 'state_analysis' in data_files:
                geo_results = self.analyze_geographic_disparities(data_files['state_analysis'])
                all_results.extend(geo_results)

            # Create summary
            summary = self.create_disparity_summary(all_results)

            # Save results
            self.save_results(all_results, summary)

            end_time = datetime.now()
            results.update({
                'end_time': end_time,
                'duration_seconds': (end_time - start_time).total_seconds(),
                'status': 'completed',
                'total_disparities_found': len(all_results),
                'significant_disparities': len([r for r in all_results if r.is_significant]),
                'summary': summary
            })

            self.logger.info(f"Disparity analysis completed in {results['duration_seconds']:.2f} seconds")
            self.logger.info(f"Found {len(all_results)} disparities, {len([r for r in all_results if r.is_significant])} statistically significant")

        except Exception as e:
            self.logger.error(f"Disparity analysis failed: {str(e)}")
            results['status'] = 'failed'
            results['error'] = str(e)
            raise

        return results

def main():
    """Main execution function"""
    analyzer = AdvancedDisparityAnalyzer()
    results = analyzer.run_comprehensive_disparity_analysis()

    print("\n" + "=" * 80)
    print("ADVANCED DISPARITY ANALYSIS RESULTS")
    print("=" * 80)
    print(f"Status: {results['status']}")
    print(f"Total disparities analyzed: {results.get('total_disparities_found', 0)}")
    print(f"Statistically significant: {results.get('significant_disparities', 0)}")
    print(f"Processing time: {results.get('duration_seconds', 0):.2f} seconds")

    if results['status'] == 'completed':
        summary = results.get('summary', {})
        print(f"\nAnalysis Summary:")
        print(f"  Significance rate: {summary.get('significant_disparities', 0)/summary.get('total_disparities_analyzed', 1):.1%}")
        print(f"  Metrics analyzed: {len(summary.get('disparities_by_metric', {}))}")
        print(f"\nResults saved to: {analyzer.output_path}")

    return results

if __name__ == "__main__":
    main()