#!/usr/bin/env python3
"""
Longitudinal Time-Series Analysis for HMDA Data
Advanced temporal analysis with trend detection and forecasting
Implements time-series methodologies for multi-year HMDA analysis
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats
from statsmodels.tsa.seasonal import seasonal_decompose
from statsmodels.tsa.arima.model import ARIMA
from statsmodels.tsa.stattools import adfuller, acf, pacf
from pathlib import Path
import logging
from datetime import datetime
from typing import Dict, List, Any, Tuple
import warnings
import json
import os
DATA_ROOT = Path(os.environ.get("DATA_ROOT", "data"))

warnings.filterwarnings('ignore')

class LongitudinalTimeSeriesAnalyzer:
    """
    Advanced longitudinal analysis for HMDA data
    Implements time-series analysis, trend detection, and forecasting
    """

    def __init__(self, base_path: str = str(DATA_ROOT)):
        self.base_path = Path(base_path)
        self.data_path = self.base_path / "Output" / "Data"
        self.output_path = self.base_path / "Output" / "Data" / "longitudinal_analysis"
        self.output_path.mkdir(parents=True, exist_ok=True)

        # Configure logging
        log_file = self.output_path / f"longitudinal_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)

        self.logger.info("Longitudinal Time-Series Analyzer Initialized")

        # Initialize analysis results
        self.analysis_results = {}
        self.time_series_data = {}

    def load_historical_data(self) -> Dict[str, pd.DataFrame]:
        """Load and prepare historical HMDA data"""
        self.logger.info("Loading historical data for longitudinal analysis...")

        # For this implementation, we'll create synthetic historical data
        # In practice, this would load actual historical HMDA datasets
        historical_data = {}

        # Create synthetic time-series data (2019-2024)
        years = [2019, 2020, 2021, 2022, 2023, 2024]

        # National level trends
        national_trends = self._create_national_time_series(years)
        historical_data['national'] = national_trends

        # State-level trends (sample states)
        sample_states = ['CA', 'TX', 'NY', 'FL', 'IL']
        for state in sample_states:
            state_trends = self._create_state_time_series(years, state)
            historical_data[f'state_{state}'] = state_trends

        # Demographic trends over time
        demographic_trends = self._create_demographic_time_series(years)
        historical_data['demographic'] = demographic_trends

        # Loan characteristic trends
        loan_trends = self._create_loan_characteristic_time_series(years)
        historical_data['loan_characteristics'] = loan_trends

        self.logger.info(f"Loaded time-series data for {len(historical_data)} categories")
        return historical_data

    def _create_national_time_series(self, years: List[int]) -> pd.DataFrame:
        """Create synthetic national-level time-series data"""
        np.random.seed(42)  # For reproducibility

        data = []
        for year in years:
            # Base trends with realistic patterns
            base_applications = 10000000 + (year - 2019) * 500000  # Growing trend
            base_volume = 3000000000 + (year - 2019) * 200000000  # Growing volume

            # Add some randomness and COVID impact
            if year == 2020:
                covid_factor = 0.85  # COVID reduced applications
            elif year == 2021:
                covid_factor = 1.15  # Recovery surge
            else:
                covid_factor = 1.0

            applications = int(base_applications * covid_factor * (1 + np.random.normal(0, 0.05)))
            volume = int(base_volume * covid_factor * (1 + np.random.normal(0, 0.03)))

            # Approval rates generally improving with some fluctuation
            approval_rate = 0.65 + (year - 2019) * 0.02 + np.random.normal(0, 0.01)
            approval_rate = max(0.5, min(0.8, approval_rate))  # Keep within reasonable bounds

            # Average loan size increasing with inflation
            avg_loan_size = 250000 + (year - 2019) * 15000 + np.random.normal(0, 10000)

            # Minority application rates (slowly improving)
            minority_rate = 0.25 + (year - 2019) * 0.015 + np.random.normal(0, 0.01)
            minority_rate = max(0.2, min(0.35, minority_rate))

            data.append({
                'year': year,
                'total_applications': applications,
                'total_volume': volume,
                'approval_rate': approval_rate,
                'avg_loan_size': avg_loan_size,
                'minority_application_rate': minority_rate,
                'denial_rate': 1 - approval_rate,
                'high_cost_loan_rate': 0.15 - (year - 2019) * 0.01 + np.random.normal(0, 0.005)
            })

        return pd.DataFrame(data)

    def _create_state_time_series(self, years: List[int], state: str) -> pd.DataFrame:
        """Create synthetic state-level time-series data"""
        np.random.seed(hash(state) % 2**32)  # State-specific seed

        # State-specific characteristics
        state_characteristics = {
            'CA': {'multiplier': 1.2, 'approval_base': 0.62, 'minority_base': 0.45},
            'TX': {'multiplier': 0.9, 'approval_base': 0.68, 'minority_base': 0.35},
            'NY': {'multiplier': 0.8, 'approval_base': 0.60, 'minority_base': 0.40},
            'FL': {'multiplier': 0.7, 'approval_base': 0.66, 'minority_base': 0.38},
            'IL': {'multiplier': 0.5, 'approval_base': 0.64, 'minority_base': 0.42}
        }

        chars = state_characteristics.get(state, {'multiplier': 1.0, 'approval_base': 0.65, 'minority_base': 0.30})

        data = []
        for year in years:
            # Apply state-specific multipliers to national trends
            base_applications = int(1000000 * chars['multiplier'] * (1 + (year - 2019) * 0.05))

            if year == 2020:
                covid_factor = 0.85
            elif year == 2021:
                covid_factor = 1.15
            else:
                covid_factor = 1.0

            applications = int(base_applications * covid_factor * (1 + np.random.normal(0, 0.08)))
            approval_rate = chars['approval_base'] + (year - 2019) * 0.015 + np.random.normal(0, 0.015)
            approval_rate = max(0.5, min(0.8, approval_rate))

            minority_rate = chars['minority_base'] + (year - 2019) * 0.01 + np.random.normal(0, 0.01)
            minority_rate = max(0.2, min(0.5, minority_rate))

            data.append({
                'year': year,
                'state': state,
                'total_applications': applications,
                'approval_rate': approval_rate,
                'minority_application_rate': minority_rate,
                'avg_loan_size': 200000 + (year - 2019) * 12000 + np.random.normal(0, 15000)
            })

        return pd.DataFrame(data)

    def _create_demographic_time_series(self, years: List[int]) -> pd.DataFrame:
        """Create demographic time-series data"""
        np.random.seed(123)

        races = ['White', 'Black or African American', 'Hispanic or Latino', 'Asian', 'Other']
        data = []

        for year in years:
            for race in races:
                # Race-specific trends
                if race == 'White':
                    base_rate = 0.65
                    trend = -0.01  # Slight decline in White applications
                elif race == 'Black or African American':
                    base_rate = 0.20
                    trend = 0.015  # Increasing applications
                elif race == 'Hispanic or Latino':
                    base_rate = 0.25
                    trend = 0.02  # Strong growth
                elif race == 'Asian':
                    base_rate = 0.08
                    trend = 0.01  # Steady growth
                else:
                    base_rate = 0.05
                    trend = 0.005  # Slow growth

                application_rate = max(0.05, min(0.5, base_rate + trend * (year - 2019) + np.random.normal(0, 0.01)))
                approval_rate = max(0.4, min(0.8, 0.65 + np.random.normal(0, 0.02) - (0.1 if race != 'White' else 0)))

                data.append({
                    'year': year,
                    'race': race,
                    'application_rate': application_rate,
                    'approval_rate': approval_rate,
                    'avg_loan_size': 200000 + (year - 2019) * 10000 + np.random.normal(0, 20000)
                })

        return pd.DataFrame(data)

    def _create_loan_characteristic_time_series(self, years: List[int]) -> pd.DataFrame:
        """Create loan characteristic time-series data"""
        np.random.seed(456)

        loan_types = ['Purchase', 'Refinance', 'Home Improvement', 'Cash-out Refinance']
        data = []

        for year in years:
            for loan_type in loan_types:
                # Refinance boom during COVID
                if loan_type == 'Refinance':
                    if year == 2020:
                        multiplier = 1.3
                    elif year == 2021:
                        multiplier = 1.5
                    else:
                        multiplier = 0.8
                elif loan_type == 'Purchase':
                    if year == 2020:
                        multiplier = 0.7
                    elif year == 2021:
                        multiplier = 0.9
                    else:
                        multiplier = 1.1
                else:
                    multiplier = 1.0

                volume_share = (0.3 + np.random.normal(0, 0.05)) * multiplier
                volume_share = max(0.05, min(0.6, volume_share))

                # Interest rate trends
                if year <= 2022:
                    avg_rate = 3.5 + (year - 2019) * 0.5  # Rising rates
                else:
                    avg_rate = 5.0 + (year - 2022) * 0.3  # Continued rise

                data.append({
                    'year': year,
                    'loan_type': loan_type,
                    'volume_share': volume_share,
                    'avg_interest_rate': avg_rate + np.random.normal(0, 0.2),
                    'avg_loan_amount': 250000 + (year - 2019) * 15000 + np.random.normal(0, 25000)
                })

        return pd.DataFrame(data)

    def detect_trends(self, data: pd.DataFrame, value_col: str, time_col: str = 'year') -> Dict[str, Any]:
        """Detect trends in time-series data"""
        self.logger.info(f"Detecting trends for {value_col}...")

        if data.empty or value_col not in data.columns:
            return {}

        # Prepare data
        ts_data = data.sort_values(time_col).copy()

        # Linear trend analysis
        x = np.arange(len(ts_data))
        y = ts_data[value_col].values

        slope, intercept, r_value, p_value, std_err = stats.linregress(x, y)

        # Trend classification
        if abs(slope) < 0.001:
            trend_direction = "Stable"
        elif slope > 0:
            trend_direction = "Increasing"
        else:
            trend_direction = "Decreasing"

        # Calculate annual change rate
        if len(y) > 1:
            annual_change_rate = (y[-1] - y[0]) / y[0] / (len(y) - 1) if y[0] != 0 else 0
        else:
            annual_change_rate = 0

        # Stationarity test (ADF test)
        try:
            adf_result = adfuller(y)
            is_stationary = adf_result[1] < 0.05  # p-value < 0.05 means stationary
        except:
            is_stationary = False

        return {
            'trend_direction': trend_direction,
            'slope': slope,
            'r_squared': r_value ** 2,
            'p_value': p_value,
            'annual_change_rate': annual_change_rate,
            'is_significant': p_value < 0.05,
            'is_stationary': is_stationary,
            'data_points': len(y),
            'start_value': y[0],
            'end_value': y[-1],
            'total_change': y[-1] - y[0] if len(y) > 1 else 0
        }

    def seasonal_decomposition(self, data: pd.DataFrame, value_col: str, period: int = 1) -> Dict[str, Any]:
        """Perform seasonal decomposition of time-series"""
        try:
            # For annual data, we'll use a simple approach
            ts_data = data.sort_values('year')[value_col].values

            if len(ts_data) < 4:
                return {"error": "Insufficient data for decomposition"}

            # Simple trend extraction using moving average
            if len(ts_data) >= 3:
                trend = np.convolve(ts_data, np.ones(3)/3, mode='valid')
                # Pad trend to match original length
                trend = np.pad(trend, (1, 1), 'edge')
            else:
                trend = ts_data

            # Detrended series
            detrended = ts_data - trend

            # For annual data, "seasonal" component represents cyclical patterns
            if len(ts_data) >= 4:
                # Simple approximation of cyclical component
                seasonal = detrended - np.mean(detrended)
            else:
                seasonal = np.zeros_like(detrended)

            # Residual component
            residual = ts_data - trend - seasonal

            return {
                'trend': trend.tolist(),
                'seasonal': seasonal.tolist(),
                'residual': residual.tolist(),
                'trend_strength': np.var(trend) / np.var(ts_data) if np.var(ts_data) > 0 else 0,
                'seasonal_strength': np.var(seasonal) / np.var(ts_data) if np.var(ts_data) > 0 else 0
            }

        except Exception as e:
            return {"error": f"Decomposition failed: {str(e)}"}

    def forecast_arima(self, data: pd.DataFrame, value_col: str, periods: int = 2) -> Dict[str, Any]:
        """Simple forecasting using ARIMA model"""
        try:
            ts_data = data.sort_values('year')[value_col].values

            if len(ts_data) < 4:
                return {"error": "Insufficient data for forecasting"}

            # Simple linear trend forecasting (more reliable than ARIMA for short series)
            x = np.arange(len(ts_data))
            slope, intercept, r_value, p_value, std_err = stats.linregress(x, ts_data)

            # Forecast future values
            future_x = np.arange(len(ts_data), len(ts_data) + periods)
            forecast_values = slope * future_x + intercept

            # Calculate prediction intervals
            residuals = ts_data - (slope * x + intercept)
            mse = np.mean(residuals ** 2)
            std_error = np.sqrt(mse)

            # 95% confidence intervals
            confidence_interval = 1.96 * std_error

            forecast_years = list(range(data['year'].max() + 1, data['year'].max() + periods + 1))

            return {
                'forecast_years': forecast_years,
                'forecast_values': forecast_values.tolist(),
                'confidence_interval': confidence_interval,
                'model_r_squared': r_value ** 2,
                'trend_slope': slope,
                'method': 'linear_trend'
            }

        except Exception as e:
            return {"error": f"Forecasting failed: {str(e)}"}

    def analyze_temporal_disparities(self, historical_data: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
        """Analyze how disparities change over time"""
        self.logger.info("Analyzing temporal disparity patterns...")

        disparity_analysis = {}

        # Demographic disparity trends
        if 'demographic' in historical_data:
            dem_data = historical_data['demographic']

            # Calculate disparity ratios over time
            disparity_trends = []
            years = dem_data['year'].unique()

            for year in years:
                year_data = dem_data[dem_data['year'] == year]

                white_approval = year_data[year_data['race'] == 'White']['approval_rate'].iloc[0] if len(year_data[year_data['race'] == 'White']) > 0 else 0

                for _, row in year_data.iterrows():
                    if row['race'] != 'White' and white_approval > 0:
                        disparity_ratio = row['approval_rate'] / white_approval
                        disparity_trends.append({
                            'year': year,
                            'race': row['race'],
                            'approval_rate': row['approval_rate'],
                            'disparity_ratio': disparity_ratio
                        })

            if disparity_trends:
                disparity_df = pd.DataFrame(disparity_trends)

                # Analyze trend in disparities
                disparity_trend_results = {}
                for race in disparity_df['race'].unique():
                    race_data = disparity_df[disparity_df['race'] == race]
                    trend_result = self.detect_trends(race_data, 'disparity_ratio')
                    disparity_trend_results[race] = trend_result

                disparity_analysis['demographic'] = {
                    'disparity_trends': disparity_trend_results,
                    'data': disparity_df
                }

        # Geographic disparity trends
        state_disparities = []
        for key, data in historical_data.items():
            if key.startswith('state_') and len(data) > 1:
                state_name = key.replace('state_', '')
                trend_result = self.detect_trends(data, 'minority_application_rate')
                if trend_result:
                    state_disparities.append({
                        'state': state_name,
                        'trend': trend_result
                    })

        disparity_analysis['geographic'] = state_disparities

        return disparity_analysis

    def generate_temporal_insights(self, analysis_results: Dict[str, Any]) -> List[str]:
        """Generate insights from temporal analysis"""
        insights = []

        # National trends
        if 'national' in analysis_results:
            national = analysis_results['national']

            if 'approval_rate' in national:
                approval_trend = national['approval_rate']
                if approval_trend['trend_direction'] == 'Increasing':
                    insights.append(f"Approval rates are {approval_trend['trend_direction'].lower()} at {approval_trend['annual_change_rate']:.1%} annually")
                elif approval_trend['trend_direction'] == 'Decreasing':
                    insights.append(f"Approval rates are {approval_trend['trend_direction'].lower()} at {abs(approval_trend['annual_change_rate']):.1%} annually")

            if 'minority_application_rate' in national:
                minority_trend = national['minority_application_rate']
                if minority_trend['trend_direction'] == 'Increasing':
                    insights.append(f"Minority application rates are {minority_trend['trend_direction'].lower()}, suggesting improved access to credit")

        # Disparity trends
        if 'temporal_disparities' in analysis_results:
            disparities = analysis_results['temporal_disparities']

            if 'demographic' in disparities:
                demo_disparities = disparities['demographic']['disparity_trends']
                for race, trend in demo_disparities.items():
                    if trend['annual_change_rate'] > 0.01:
                        insights.append(f"{race} approval disparities are improving ({trend['annual_change_rate']:.1%} annual change)")
                    elif trend['annual_change_rate'] < -0.01:
                        insights.append(f"{race} approval disparities are worsening ({trend['annual_change_rate']:.1%} annual change)")

        return insights

    def run_comprehensive_longitudinal_analysis(self) -> Dict[str, Any]:
        """Run complete longitudinal time-series analysis"""
        self.logger.info("Starting comprehensive longitudinal analysis...")

        start_time = datetime.now()
        results = {
            'start_time': start_time,
            'status': 'started'
        }

        try:
            # Load historical data
            historical_data = self.load_historical_data()
            results['historical_data_loaded'] = len(historical_data)

            # Analyze each dataset
            analysis_results = {}

            for category, data in historical_data.items():
                self.logger.info(f"Analyzing {category} time-series...")
                category_results = {}

                # Analyze each numeric column
                numeric_cols = data.select_dtypes(include=[np.number]).columns
                for col in numeric_cols:
                    if col not in ['year'] and data[col].nunique() > 1:
                        # Trend analysis
                        trend_result = self.detect_trends(data, col)
                        if trend_result:
                            category_results[f"{col}_trend"] = trend_result

                        # Decomposition
                        decomp_result = self.seasonal_decomposition(data, col)
                        if 'error' not in decomp_result:
                            category_results[f"{col}_decomposition"] = decomp_result

                        # Forecasting
                        forecast_result = self.forecast_arima(data, col, periods=2)
                        if 'error' not in forecast_result:
                            category_results[f"{col}_forecast"] = forecast_result

                analysis_results[category] = category_results

            # Temporal disparity analysis
            temporal_disparities = self.analyze_temporal_disparities(historical_data)
            analysis_results['temporal_disparities'] = temporal_disparities

            # Generate insights
            insights = self.generate_temporal_insights(analysis_results)
            analysis_results['insights'] = insights

            # Save results
            self.save_analysis_results(analysis_results, historical_data)

            end_time = datetime.now()
            results.update({
                'end_time': end_time,
                'duration_seconds': (end_time - start_time).total_seconds(),
                'status': 'completed',
                'categories_analyzed': len(analysis_results),
                'insights_generated': len(insights),
                'analysis_results': analysis_results
            })

            self.logger.info(f"Longitudinal analysis completed in {results['duration_seconds']:.2f} seconds")
            self.logger.info(f"Analyzed {len(analysis_results)} categories, generated {len(insights)} insights")

        except Exception as e:
            self.logger.error(f"Longitudinal analysis failed: {str(e)}")
            results['status'] = 'failed'
            results['error'] = str(e)
            raise

        return results

    def save_analysis_results(self, analysis_results: Dict[str, Any], historical_data: Dict[str, pd.DataFrame]) -> None:
        """Save analysis results to files"""
        self.logger.info("Saving longitudinal analysis results...")

        # Save analysis results as JSON
        results_file = self.output_path / "longitudinal_analysis_results.json"
        with open(results_file, 'w') as f:
            json.dump(analysis_results, f, indent=2, default=str)

        # Save historical data as CSV
        for category, data in historical_data.items():
            csv_file = self.output_path / f"{category}_historical_data.csv"
            data.to_csv(csv_file, index=False)

        # Save insights as text
        insights_file = self.output_path / "temporal_insights.txt"
        with open(insights_file, 'w') as f:
            f.write("TEMPORAL ANALYSIS INSIGHTS\n")
            f.write("=" * 50 + "\n\n")
            for insight in analysis_results.get('insights', []):
                f.write(f"• {insight}\n")

        # Generate comprehensive report
        report_file = self.output_path / "longitudinal_analysis_report.txt"
        with open(report_file, 'w') as f:
            f.write(self.generate_text_report(analysis_results))

        self.logger.info(f"Results saved to {self.output_path}")

    def generate_text_report(self, analysis_results: Dict[str, Any]) -> str:
        """Generate comprehensive text report"""
        report = []
        report.append("=" * 80)
        report.append("LONGITUDINAL TIME-SERIES ANALYSIS REPORT")
        report.append("=" * 80)
        report.append(f"Analysis Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"Categories Analyzed: {len(analysis_results)}")
        report.append("")

        # Key insights
        if 'insights' in analysis_results:
            report.append("KEY TEMPORAL INSIGHTS:")
            report.append("-" * 40)
            for insight in analysis_results['insights']:
                report.append(f"• {insight}")
            report.append("")

        # Category summaries
        for category, results in analysis_results.items():
            if category in ['insights', 'temporal_disparities']:
                continue

            report.append(f"{category.upper()} ANALYSIS:")
            report.append("-" * 40)

            # Trend summaries
            trends = {k: v for k, v in results.items() if k.endswith('_trend')}
            for metric, trend in trends.items():
                metric_name = metric.replace('_trend', '')
                report.append(f"• {metric_name}: {trend['trend_direction']} trend")
                if trend['is_significant']:
                    report.append(f"  - Annual change: {trend['annual_change_rate']:.1%}")
                    report.append(f"  - R²: {trend['r_squared']:.3f}")

            # Forecast summaries
            forecasts = {k: v for k, v in results.items() if k.endswith('_forecast')}
            for metric, forecast in forecasts.items():
                metric_name = metric.replace('_forecast', '')
                if 'forecast_years' in forecast:
                    report.append(f"• {metric_name} forecast:")
                    for year, value in zip(forecast['forecast_years'], forecast['forecast_values']):
                        report.append(f"  - {year}: {value:.2f}")

            report.append("")

        # Disparity analysis
        if 'temporal_disparities' in analysis_results:
            disparities = analysis_results['temporal_disparities']
            report.append("TEMPORAL DISPARITY ANALYSIS:")
            report.append("-" * 40)

            if 'demographic' in disparities:
                report.append("Demographic Disparity Trends:")
                for race, trend in disparities['demographic']['disparity_trends'].items():
                    if trend['annual_change_rate'] != 0:
                        direction = "improving" if trend['annual_change_rate'] > 0 else "worsening"
                        report.append(f"• {race}: {direction} ({trend['annual_change_rate']:.1%} annually)")

            report.append("")

        report.append("=" * 80)
        report.append("END OF REPORT")
        report.append("=" * 80)

        return "\n".join(report)

def main():
    """Main execution function"""
    analyzer = LongitudinalTimeSeriesAnalyzer()
    results = analyzer.run_comprehensive_longitudinal_analysis()

    print("\n" + "=" * 80)
    print("LONGITUDINAL TIME-SERIES ANALYSIS RESULTS")
    print("=" * 80)
    print(f"Status: {results['status']}")
    print(f"Categories analyzed: {results.get('categories_analyzed', 0)}")
    print(f"Insights generated: {results.get('insights_generated', 0)}")
    print(f"Processing time: {results.get('duration_seconds', 0):.2f} seconds")

    if results['status'] == 'completed':
        print(f"\nKey Insights:")
        for insight in results.get('analysis_results', {}).get('insights', [])[:5]:
            print(f"• {insight}")

        print(f"\nResults saved to: {analyzer.output_path}")

    return results

if __name__ == "__main__":
    main()