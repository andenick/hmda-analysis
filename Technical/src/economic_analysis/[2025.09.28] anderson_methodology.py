"""
Anderson Methodology Implementation
==================================

Implements Nicholas Anderson's methodology from "Evaluating the Community
Reinvestment Act: Utilizing a Regression Discontinuity Design to Assess
the Effectiveness of Exam-based Banking Regulation" (2025).

Key Features:
- No data filtering (unlike Bhutta)
- Modern HMDA processing pipeline
- Temporal focus (1994-2002)
- Comprehensive control specifications
"""

import pandas as pd
import numpy as np
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import statsmodels.api as sm
from statsmodels.formula.api import ols
import warnings

warnings.filterwarnings('ignore')


class AndersonMethodology:
    """
    Implementation of Anderson's CRA evaluation methodology.

    Key differences from Bhutta:
    - No group quarters filtering
    - No outlier lending filtering
    - Includes all census tracts
    - Focus on specification sensitivity
    """

    def __init__(self, data_path: Path, output_path: Path):
        """
        Initialize Anderson methodology module.

        Parameters:
        -----------
        data_path : Path
            Path to HMDA data
        output_path : Path
            Path for analysis outputs
        """
        self.data_path = data_path
        self.output_path = output_path
        self.logger = logging.getLogger('AndersonMethodology')

        # Anderson's specifications
        self.ANDERSON_YEARS = list(range(1994, 2003))  # 1994-2002
        self.CRA_CUTOFF = 0.80  # 80% MSA median income
        self.GSE_CUTOFF = 0.90  # Government Sponsored Enterprise cutoff

        # Metropolitan area size classifications (consistent with Bhutta for comparison)
        self.MSA_CLASSIFICATIONS = {
            'small': (0, 500_000),      # < 500K
            'medium': (500_000, 2_000_000),  # 500K - 2M
            'large': (2_000_000, float('inf'))  # > 2M
        }

        self.logger.info("📊 Anderson Methodology initialized")

    def run_full_analysis(self,
                         data_dict: Dict[int, pd.DataFrame],
                         years: List[int] = None,
                         bandwidth: float = 0.05) -> Dict:
        """
        Execute complete Anderson methodology analysis.

        Parameters:
        -----------
        data_dict : Dict[int, pd.DataFrame]
            Dictionary mapping years to HMDA dataframes
        years : List[int], optional
            Years to analyze (defaults to Anderson's 1994-2002)
        bandwidth : float
            RD bandwidth parameter

        Returns:
        --------
        Dict
            Complete Anderson methodology results
        """
        if years is None:
            years = self.ANDERSON_YEARS

        self.logger.info(f"📊 Starting Anderson methodology for years: {years}")

        results = {
            'specification': self._get_anderson_specification(),
            'data_summary': {},
            'regression_results': {},
            'sensitivity_analysis': {},
            'figures': {}
        }

        # Step 1: Apply minimal Anderson filters (no restrictive filtering)
        processed_data = {}
        for year in years:
            if year in data_dict:
                self.logger.info(f"📋 Processing {year} with Anderson methodology")
                processed_data[year] = self._apply_anderson_processing(data_dict[year], year)

                # Summary statistics
                results['data_summary'][year] = self._generate_data_summary(
                    processed_data[year], year
                )

        # Step 2: Create pooled dataset
        pooled_data = self._create_pooled_dataset(processed_data, years)
        self.logger.info(f"📊 Anderson pooled dataset: {len(pooled_data):,} observations")

        # Step 3: Run Anderson's regression specifications
        results['regression_results'] = self._run_anderson_regressions(
            pooled_data, bandwidth
        )

        # Step 4: Specification sensitivity analysis
        results['sensitivity_analysis'] = self._run_sensitivity_analysis(pooled_data)

        # Step 5: Generate Anderson's tables
        results['tables'] = self._generate_anderson_tables(results['regression_results'])

        # Step 6: Compare with/without controls (Anderson's key finding)
        results['control_sensitivity'] = self._analyze_control_sensitivity(pooled_data)

        self.logger.info("✅ Anderson methodology completed")
        return results

    def _apply_anderson_processing(self, df: pd.DataFrame, year: int) -> pd.DataFrame:
        """
        Apply Anderson's minimal data processing.

        Key difference: NO restrictive filtering like Bhutta
        - Keep all census tracts
        - No group quarters filter
        - No outlier lending filter
        - Minimal requirements only
        """
        self.logger.info(f"🔍 Applying Anderson processing to {year} data")

        original_count = len(df)

        # Step 1: Basic data quality requirements only
        # Remove tracts with missing key variables
        required_vars = ['HL_Loan_Orig_Total_All', 'tract_median_family_income',
                        'msa_median_family_income']

        for var in required_vars:
            if var in df.columns:
                df = df.dropna(subset=[var])

        # Step 2: Minimal housing unit filter (same as original R processing)
        if 'total_housing_units' in df.columns:
            df = df[df['total_housing_units'] >= 100]

        # Step 3: Create Anderson variables
        df = self._create_anderson_variables(df)

        # Step 4: No additional filtering (key difference from Bhutta)
        # - Keep all group quarters percentages
        # - Keep all lending levels (no outlier removal)

        processed_count = len(df)
        pct_remaining = (processed_count / original_count) * 100

        self.logger.info(f"   📊 Anderson processing: {original_count:,} → {processed_count:,} "
                        f"({pct_remaining:.1f}% retained)")

        return df

    def _create_anderson_variables(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Create variables for Anderson analysis.
        """
        # Tract Median Ratio (TM) - key assignment variable
        if 'tract_median_family_income' in df.columns and 'msa_median_family_income' in df.columns:
            df['TM'] = df['tract_median_family_income'] / df['msa_median_family_income']
        else:
            self.logger.warning("Cannot create TM variable - income data missing")

        # CRA eligibility indicator
        df['CRA_eligible'] = (df['TM'] < self.CRA_CUTOFF).astype(int)

        # GSE eligibility indicator (for control)
        df['GSE_eligible'] = (df['TM'] < self.GSE_CUTOFF).astype(int)

        # Log transformations for regression
        lending_var = 'HL_Loan_Orig_Total_All'
        if lending_var in df.columns:
            df['log_originations'] = np.log(df[lending_var].clip(lower=1))

        # Log control variables
        for var in ['total_housing_units', 'owner_occupied_units', 'median_home_value']:
            if var in df.columns:
                df[f'log_{var}'] = np.log(df[var].clip(lower=1))

        # Metropolitan area size classification
        df = self._classify_msa_size(df)

        return df

    def _classify_msa_size(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Classify MSAs by size (consistent with Bhutta for comparison).
        """
        # Placeholder classification - would use actual MSA population data
        df['msa_size'] = 'medium'  # Default classification

        # TODO: Implement actual MSA population-based classification
        return df

    def _create_pooled_dataset(self, data_dict: Dict[int, pd.DataFrame], years: List[int]) -> pd.DataFrame:
        """
        Create pooled dataset for Anderson analysis.
        """
        self.logger.info("🔗 Creating Anderson pooled dataset")

        pooled_frames = []
        for year in years:
            if year in data_dict and len(data_dict[year]) > 0:
                df_year = data_dict[year].copy()
                df_year['year'] = year
                pooled_frames.append(df_year)

        if not pooled_frames:
            raise ValueError("No valid data for Anderson pooled analysis")

        pooled = pd.concat(pooled_frames, ignore_index=True)

        self.logger.info(f"📊 Anderson pooled dataset: {len(pooled):,} observations, "
                        f"{len(years)} years")

        return pooled

    def _run_anderson_regressions(self, data: pd.DataFrame, bandwidth: float) -> Dict:
        """
        Run Anderson's regression specifications.

        Anderson tests both with and without controls to show sensitivity.
        """
        self.logger.info("📈 Running Anderson regression specifications")

        results = {}

        # Specification 1: With controls (Table 2 in Anderson paper)
        results['with_controls'] = {}
        results['with_controls']['all_msas'] = self._run_rd_regression(
            data, 'all', bandwidth, include_controls=True
        )

        for size in ['small', 'medium', 'large']:
            results['with_controls'][f'{size}_msas'] = self._run_rd_regression(
                data, size, bandwidth, include_controls=True
            )

        # Large MSAs with cubic control (wider bandwidth)
        results['with_controls']['large_msas_cubic'] = self._run_rd_regression(
            data, 'large', 0.30, include_controls=True, control_function='cubic'
        )

        # Specification 2: Without controls (Table 3 in Anderson paper)
        results['without_controls'] = {}
        results['without_controls']['all_msas'] = self._run_rd_regression(
            data, 'all', bandwidth, include_controls=False
        )

        for size in ['small', 'medium', 'large']:
            results['without_controls'][f'{size}_msas'] = self._run_rd_regression(
                data, size, bandwidth, include_controls=False
            )

        # Large MSAs without controls (cubic)
        results['without_controls']['large_msas_cubic'] = self._run_rd_regression(
            data, 'large', 0.30, include_controls=False, control_function='cubic'
        )

        return results

    def _run_rd_regression(self,
                          data: pd.DataFrame,
                          msa_size: str,
                          bandwidth: float,
                          include_controls: bool = True,
                          control_function: str = 'linear') -> Dict:
        """
        Run individual Anderson RD regression specification.
        """
        # Filter by MSA size
        if msa_size != 'all':
            reg_data = data[data['msa_size'] == msa_size].copy()
        else:
            reg_data = data.copy()

        # Apply bandwidth filter
        reg_data = reg_data[
            (reg_data['TM'] >= self.CRA_CUTOFF - bandwidth) &
            (reg_data['TM'] <= self.CRA_CUTOFF + bandwidth)
        ].copy()

        if len(reg_data) == 0:
            return {'error': 'No observations in bandwidth', 'n_obs': 0}

        # Create control function
        reg_data = self._create_control_function(reg_data, control_function)

        # Build regression formula
        formula = self._build_anderson_formula(include_controls, control_function)

        try:
            # Run regression with clustered standard errors
            model = ols(formula, data=reg_data).fit(
                cov_type='cluster',
                cov_kwds={'groups': reg_data['msa_code']} if 'msa_code' in reg_data.columns else None
            )

            result = {
                'coefficient': model.params.get('CRA_eligible', np.nan),
                'std_error': model.bse.get('CRA_eligible', np.nan),
                'p_value': model.pvalues.get('CRA_eligible', np.nan),
                't_stat': model.tvalues.get('CRA_eligible', np.nan),
                'n_obs': len(reg_data),
                'r_squared': model.rsquared,
                'r_squared_adj': model.rsquared_adj,
                'formula': formula,
                'model_summary': str(model.summary()),
                'bandwidth': bandwidth,
                'msa_size': msa_size,
                'control_function': control_function,
                'include_controls': include_controls
            }

            # Calculate significance levels
            p_val = result['p_value']
            if p_val <= 0.001:
                result['significance'] = '***'
            elif p_val <= 0.01:
                result['significance'] = '**'
            elif p_val <= 0.05:
                result['significance'] = '*'
            elif p_val <= 0.10:
                result['significance'] = '+'
            else:
                result['significance'] = ''

            return result

        except Exception as e:
            self.logger.error(f"Anderson regression failed: {str(e)}")
            return {'error': str(e), 'n_obs': len(reg_data)}

    def _create_control_function(self, data: pd.DataFrame, control_type: str) -> pd.DataFrame:
        """
        Create control function for Anderson RD regression.
        """
        # Center TM around cutoff
        data['TM_centered'] = data['TM'] - self.CRA_CUTOFF

        if control_type == 'linear':
            data['TM_control'] = data['TM_centered']
        elif control_type == 'cubic':
            data['TM_control'] = data['TM_centered']
            data['TM_control_2'] = data['TM_centered'] ** 2
            data['TM_control_3'] = data['TM_centered'] ** 3

        return data

    def _build_anderson_formula(self, include_controls: bool, control_function: str) -> str:
        """
        Build Anderson regression formula.
        """
        # Base formula
        formula = "log_originations ~ CRA_eligible + TM_control"

        # Add polynomial terms for cubic
        if control_function == 'cubic':
            formula += " + TM_control_2 + TM_control_3"

        # Add tract controls if specified
        if include_controls:
            controls = [
                'minority_pct',
                'log_total_housing_units',
                'log_median_home_value',
                'poverty_rate',
                'housing_built_before_1940_pct',
                'housing_built_1940_1969_pct'
            ]

            for control in controls:
                formula += f" + {control}"

        # Add GSE control for wider bandwidth specifications
        formula += " + GSE_eligible"

        return formula

    def _run_sensitivity_analysis(self, data: pd.DataFrame) -> Dict:
        """
        Run comprehensive sensitivity analysis.
        """
        self.logger.info("🔧 Running Anderson sensitivity analysis")

        sensitivity = {
            'bandwidth_sensitivity': {},
            'control_sensitivity': {},
            'temporal_sensitivity': {}
        }

        # Bandwidth sensitivity
        bandwidths = [0.025, 0.05, 0.075, 0.10, 0.15, 0.20, 0.30]
        for bw in bandwidths:
            sensitivity['bandwidth_sensitivity'][bw] = self._run_rd_regression(
                data, 'large', bw, include_controls=True
            )

        return sensitivity

    def _analyze_control_sensitivity(self, data: pd.DataFrame) -> Dict:
        """
        Analyze sensitivity to control variables (Anderson's key finding).
        """
        self.logger.info("🎯 Analyzing control sensitivity")

        # Compare with/without controls for each specification
        control_analysis = {}

        specifications = [
            ('all_msas', 'all', 0.05),
            ('small_msas', 'small', 0.05),
            ('medium_msas', 'medium', 0.05),
            ('large_msas', 'large', 0.05),
            ('large_msas_cubic', 'large', 0.30)
        ]

        for spec_name, msa_size, bandwidth in specifications:
            with_controls = self._run_rd_regression(
                data, msa_size, bandwidth, include_controls=True
            )
            without_controls = self._run_rd_regression(
                data, msa_size, bandwidth, include_controls=False
            )

            if 'error' not in with_controls and 'error' not in without_controls:
                control_analysis[spec_name] = {
                    'with_controls': {
                        'coefficient': with_controls['coefficient'],
                        'std_error': with_controls['std_error'],
                        'significance': with_controls['significance']
                    },
                    'without_controls': {
                        'coefficient': without_controls['coefficient'],
                        'std_error': without_controls['std_error'],
                        'significance': without_controls['significance']
                    },
                    'difference': {
                        'coefficient_change': (without_controls['coefficient'] -
                                             with_controls['coefficient']),
                        'significance_change': (without_controls['significance'] !=
                                              with_controls['significance'])
                    }
                }

        return control_analysis

    def _generate_anderson_tables(self, regression_results: Dict) -> Dict:
        """
        Generate tables matching Anderson's paper.
        """
        self.logger.info("📋 Generating Anderson methodology tables")

        tables = {}

        # Table 2: Results with controls
        tables['table_2_with_controls'] = self._create_anderson_table(
            regression_results['with_controls'], "With Controls"
        )

        # Table 3: Results without controls
        tables['table_3_without_controls'] = self._create_anderson_table(
            regression_results['without_controls'], "Without Controls"
        )

        # Comparison table
        tables['control_comparison'] = self._create_control_comparison_table(
            regression_results
        )

        return tables

    def _create_anderson_table(self, results: Dict, table_type: str) -> pd.DataFrame:
        """
        Create Anderson regression results table.
        """
        rows = []

        specifications = [
            ('All MSAs', 'all_msas'),
            ('Small MSAs', 'small_msas'),
            ('Medium MSAs', 'medium_msas'),
            ('Large MSAs', 'large_msas'),
            ('Large MSAs (cubic)', 'large_msas_cubic')
        ]

        for spec_name, spec_key in specifications:
            if spec_key in results and 'error' not in results[spec_key]:
                result = results[spec_key]

                row = {
                    'Specification': spec_name,
                    'Coefficient': f"{result['coefficient']:.4f}{result['significance']}",
                    'Std_Error': f"({result['std_error']:.4f})",
                    'R_Squared': f"{result['r_squared']:.3f}",
                    'N': result['n_obs'],
                    'Bandwidth': result['bandwidth'],
                    'Controls': table_type
                }
                rows.append(row)

        return pd.DataFrame(rows)

    def _create_control_comparison_table(self, results: Dict) -> pd.DataFrame:
        """
        Create table comparing with/without controls (Anderson's key finding).
        """
        rows = []

        specifications = [
            ('All MSAs', 'all_msas'),
            ('Small MSAs', 'small_msas'),
            ('Medium MSAs', 'medium_msas'),
            ('Large MSAs', 'large_msas')
        ]

        for spec_name, spec_key in specifications:
            with_controls = results['with_controls'].get(spec_key, {})
            without_controls = results['without_controls'].get(spec_key, {})

            if ('error' not in with_controls and 'error' not in without_controls and
                with_controls and without_controls):

                row = {
                    'Specification': spec_name,
                    'With_Controls_Coef': f"{with_controls['coefficient']:.4f}{with_controls['significance']}",
                    'With_Controls_SE': f"({with_controls['std_error']:.4f})",
                    'Without_Controls_Coef': f"{without_controls['coefficient']:.4f}{without_controls['significance']}",
                    'Without_Controls_SE': f"({without_controls['std_error']:.4f})",
                    'Difference': f"{without_controls['coefficient'] - with_controls['coefficient']:.4f}",
                    'Sign_Change': without_controls['coefficient'] * with_controls['coefficient'] < 0
                }
                rows.append(row)

        return pd.DataFrame(rows)

    def _get_anderson_specification(self) -> Dict:
        """
        Document Anderson's methodology specification.
        """
        return {
            'paper': 'Anderson, Nicholas (2025). Evaluating the Community Reinvestment Act: Utilizing a Regression Discontinuity Design to Assess the Effectiveness of Exam-based Banking Regulation.',
            'time_period': '1994-2002',
            'data_source': 'HMDA Loan Application Register (Python processed)',
            'geographic_scope': 'Metropolitan areas (excluding Hawaii, Alaska)',
            'key_differences_from_bhutta': [
                'No group quarters filtering (includes all tracts)',
                'No outlier lending filtering',
                'Shorter time period (1994-2002 vs 1994-2006)',
                'Focus on specification sensitivity'
            ],
            'assignment_variable': 'Tract median family income / MSA median family income',
            'cutoff': 0.80,
            'outcome_variable': 'Log(mortgage originations)',
            'control_function': 'Linear and cubic polynomials in assignment variable',
            'standard_errors': 'Clustered at MSA level',
            'key_finding': 'Results highly sensitive to control variable inclusion - opposite signs with/without controls'
        }

    def _generate_data_summary(self, df: pd.DataFrame, year: int) -> Dict:
        """
        Generate summary statistics for Anderson processed data.
        """
        summary = {
            'year': year,
            'n_observations': len(df),
            'n_cra_eligible': df['CRA_eligible'].sum() if 'CRA_eligible' in df.columns else 0,
            'pct_cra_eligible': df['CRA_eligible'].mean() * 100 if 'CRA_eligible' in df.columns else 0,
            'mean_originations': df['HL_Loan_Orig_Total_All'].mean() if 'HL_Loan_Orig_Total_All' in df.columns else 0,
            'median_tm': df['TM'].median() if 'TM' in df.columns else 0,
            'methodology': 'Anderson (no restrictive filtering)'
        }

        # MSA size distribution
        if 'msa_size' in df.columns:
            size_dist = df['msa_size'].value_counts()
            summary['msa_size_distribution'] = size_dist.to_dict()

        return summary


if __name__ == "__main__":
    # Example usage
    from pathlib import Path

    data_path = Path("../../data")
    output_path = Path("../../analysis_outputs")

    anderson = AndersonMethodology(data_path, output_path)

    print("📊 Anderson Methodology ready for use in main framework")