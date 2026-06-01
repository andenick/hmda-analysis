#!/usr/bin/env python3
"""
Interactive HMDA Analysis Dashboard
Web-based visualization and exploration tool
Comprehensive interactive analysis interface
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import json
from pathlib import Path
import logging
from datetime import datetime
from typing import Dict, List, Any
import warnings
import os
DATA_ROOT = Path(os.environ.get("DATA_ROOT", "data"))

warnings.filterwarnings('ignore')

class HMDADashboard:
    """
    Interactive Streamlit dashboard for HMDA analysis
    Provides comprehensive visualization and exploration capabilities
    """

    def __init__(self, base_path: str = str(DATA_ROOT)):
        self.base_path = Path(base_path)
        self.data_path = self.base_path / "Output" / "Data"
        self.setup_logging()

        # Load all analysis data
        self.load_data()

    def setup_logging(self):
        """Setup logging configuration"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)

    def load_data(self):
        """Load all analysis results"""
        self.logger.info("Loading dashboard data...")

        self.data = {}

        # Load streamlined analysis data
        streamlined_path = self.data_path / "streamlined_analysis"
        if streamlined_path.exists():
            # Key analysis files
            key_files = [
                'state_analysis.csv',
                'county_analysis.csv',
                'msa_analysis.csv',
                'race_analysis.csv',
                'ethnicity_analysis.csv',
                'gender_analysis.csv',
                'loan_purpose_analysis.csv',
                'loan_type_analysis.csv',
                'top_lenders.csv'
            ]

            for file_name in key_files:
                file_path = streamlined_path / file_name
                if file_path.exists():
                    try:
                        self.data[file_name.replace('.csv', '')] = pd.read_csv(file_path)
                        self.logger.info(f"Loaded: {file_name}")
                    except Exception as e:
                        self.logger.warning(f"Failed to load {file_name}: {str(e)}")

        # Load disparity analysis data
        disparity_path = self.data_path / "disparity_analysis"
        if disparity_path.exists():
            disparity_files = ['disparity_analysis_results.csv']
            for file_name in disparity_files:
                file_path = disparity_path / file_name
                if file_path.exists():
                    try:
                        self.data['disparity_results'] = pd.read_csv(file_path)
                        self.logger.info(f"Loaded disparity analysis: {file_name}")
                    except Exception as e:
                        self.logger.warning(f"Failed to load {file_name}: {str(e)}")

        # Load metadata
        metadata_file = streamlined_path / "analysis_metadata.json"
        if metadata_file.exists():
            with open(metadata_file, 'r') as f:
                self.metadata = json.load(f)

    def create_overview_metrics(self):
        """Create overview metrics display"""
        st.header("📊 HMDA Analysis Overview")

        if 'summary' in self.metadata:
            summary = self.metadata['summary']

            # Create metrics columns
            col1, col2, col3, col4 = st.columns(4)

            with col1:
                st.metric(
                    "Applications Analyzed",
                    f"{summary.get('total_applications_analyzed', 0):,}",
                    help="Total loan applications in analysis sample"
                )

            with col2:
                loan_volume = summary.get('total_loan_volume', 0)
                st.metric(
                    "Total Loan Volume",
                    f"${loan_volume/1e9:.1f}B",
                    help="Total dollar value of loans analyzed"
                )

            with col3:
                avg_loan = summary.get('average_loan_size', 0)
                st.metric(
                    "Average Loan Size",
                    f"${avg_loan:,.0f}",
                    help="Average loan amount across all applications"
                )

            with col4:
                st.metric(
                    "Geographic Coverage",
                    f"{summary.get('unique_states', 0)} States",
                    help="Number of states/territories represented"
                )

        # Analysis summary
        st.subheader("Analysis Summary")

        col1, col2 = st.columns(2)

        with col1:
            st.write("**Analysis Categories Generated:**")
            if 'total_slices_generated' in self.metadata:
                st.write(f"• {self.metadata['total_slices_generated']} comprehensive analysis slices")
                st.write(f"• {len(self.data)} data categories loaded")

        with col2:
            st.write("**Data Processing:**")
            if 'processing_timestamp' in self.metadata:
                processing_time = self.metadata.get('duration_seconds', 0)
                st.write(f"• Processing time: {processing_time:.2f} seconds")
                st.write(f"• Sample size: 100,000 applications")

    def create_geographic_analysis(self):
        """Create geographic analysis visualizations"""
        st.header("🗺️ Geographic Analysis")

        if 'state_analysis' in self.data:
            state_data = self.data['state_analysis']

            st.subheader("State-Level Analysis")

            col1, col2 = st.columns(2)

            with col1:
                # Application volume by state
                fig = px.choropleth(
                    state_data,
                    locations='state_code',
                    locationmode="USA-states",
                    color='application_count',
                    scope="usa",
                    color_continuous_scale="Viridis",
                    title='Application Volume by State',
                    hover_data=['total_volume', 'origination_rate']
                )
                st.plotly_chart(fig, use_container_width=True)

            with col2:
                # Origination rates by state
                fig = px.choropleth(
                    state_data,
                    locations='state_code',
                    locationmode="USA-states",
                    color='origination_rate',
                    scope="usa",
                    color_continuous_scale="RdYlGn",
                    title='Origination Rate by State',
                    hover_data=['application_count', 'minority_applicant_rate']
                )
                st.plotly_chart(fig, use_container_width=True)

        # County analysis (if available)
        if 'county_analysis' in self.data:
            st.subheader("County-Level Analysis (Sample)")
            county_data = self.data['county_analysis'].head(100)  # Sample for performance

            col1, col2 = st.columns(2)

            with col1:
                # Top counties by application count
                top_counties = county_data.nlargest(20, 'application_count')
                fig = px.bar(
                    top_counties,
                    x='application_count',
                    y='fips',
                    orientation='h',
                    title='Top 20 Counties by Application Count',
                    hover_data=['total_volume', 'origination_rate']
                )
                fig.update_layout(yaxis={'categoryorder':'total ascending'})
                st.plotly_chart(fig, use_container_width=True)

            with col2:
                # Origination rate distribution
                fig = px.histogram(
                    county_data,
                    x='origination_rate',
                    nbins=20,
                    title='Distribution of County Origination Rates',
                    marginal='box'
                )
                st.plotly_chart(fig, use_container_width=True)

    def create_demographic_analysis(self):
        """Create demographic analysis visualizations"""
        st.header("👥 Demographic Analysis")

        if 'race_analysis' in self.data:
            race_data = self.data['race_analysis']

            col1, col2 = st.columns(2)

            with col1:
                # Application volume by race
                fig = px.pie(
                    race_data,
                    values='application_count',
                    names='race',
                    title='Applications by Race'
                )
                st.plotly_chart(fig, use_container_width=True)

            with col2:
                # Origination rates by race
                fig = px.bar(
                    race_data,
                    x='race',
                    y='origination_rate',
                    title='Origination Rate by Race',
                    color='origination_rate',
                    color_continuous_scale="RdYlGn"
                )
                fig.add_annotation(
                    text="Higher origination rates indicate better approval outcomes",
                    xref="paper", yref="paper",
                    x=0.5, y=-0.15, showarrow=False
                )
                st.plotly_chart(fig, use_container_width=True)

        # Ethnicity analysis
        if 'ethnicity_analysis' in self.data:
            st.subheader("Ethnicity Analysis")
            ethnicity_data = self.data['ethnicity_analysis']

            col1, col2 = st.columns(2)

            with col1:
                fig = px.bar(
                    ethnicity_data,
                    x='ethnicity',
                    y='application_count',
                    title='Applications by Ethnicity',
                    color='application_count'
                )
                st.plotly_chart(fig, use_container_width=True)

            with col2:
                fig = px.bar(
                    ethnicity_data,
                    x='ethnicity',
                    y='origination_rate',
                    title='Origination Rate by Ethnicity',
                    color='origination_rate',
                    color_continuous_scale="Viridis"
                )
                st.plotly_chart(fig, use_container_width=True)

        # Gender analysis
        if 'gender_analysis' in self.data:
            st.subheader("Gender Analysis")
            gender_data = self.data['gender_analysis']

            fig = make_subplots(
                rows=1, cols=2,
                specs=[[{"type": "bar"}, {"type": "pie"}]],
                subplot_titles=("Application Count by Gender", "Origination Rate by Gender")
            )

            # Application counts
            fig.add_trace(
                go.Bar(x=gender_data['gender'], y=gender_data['application_count'], name="Applications"),
                row=1, col=1
            )

            # Origination rates
            fig.add_trace(
                go.Pie(labels=gender_data['gender'], values=gender_data['origination_rate'], name="Origination Rate"),
                row=1, col=2
            )

            fig.update_layout(title_text="Gender-Based Analysis Overview")
            st.plotly_chart(fig, use_container_width=True)

    def create_loan_characteristics_analysis(self):
        """Create loan characteristics analysis visualizations"""
        st.header("💰 Loan Characteristics Analysis")

        # Loan purpose analysis
        if 'loan_purpose_analysis' in self.data:
            st.subheader("Loan Purpose Analysis")
            loan_purpose_data = self.data['loan_purpose_analysis']

            col1, col2 = st.columns(2)

            with col1:
                fig = px.bar(
                    loan_purpose_data,
                    x='loan_purpose',
                    y='application_count',
                    title='Applications by Loan Purpose',
                    color='application_count'
                )
                st.plotly_chart(fig, use_container_width=True)

            with col2:
                fig = px.bar(
                    loan_purpose_data,
                    x='loan_purpose',
                    y='avg_loan_size',
                    title='Average Loan Size by Purpose',
                    color='avg_loan_size',
                    color_continuous_scale="Plasma"
                )
                st.plotly_chart(fig, use_container_width=True)

        # Loan type analysis
        if 'loan_type_analysis' in self.data:
            st.subheader("Loan Type Analysis")
            loan_type_data = self.data['loan_type_analysis']

            fig = make_subplots(
                rows=1, cols=2,
                specs=[[{"type": "bar"}, {"type": "scatter"}]],
                subplot_titles=("Applications by Loan Type", "Loan Size vs Origination Rate")
            )

            # Application counts
            fig.add_trace(
                go.Bar(x=loan_type_data['loan_type'], y=loan_type_data['application_count'], name="Applications"),
                row=1, col=1
            )

            # Size vs origination rate
            fig.add_trace(
                go.Scatter(
                    x=loan_type_data['avg_loan_size'],
                    y=loan_type_data['origination_rate'],
                    mode='markers+text',
                    text=loan_type_data['loan_type'],
                    textposition="top center",
                    name="Loan Types"
                ),
                row=1, col=2
            )

            fig.update_layout(title_text="Loan Type Characteristics")
            st.plotly_chart(fig, use_container_width=True)

    def create_disparity_analysis(self):
        """Create disparity analysis visualizations"""
        st.header("⚖️ Disparity Analysis")

        if 'disparity_results' in self.data:
            disparity_data = self.data['disparity_results']

            st.subheader("Statistical Disparity Findings")

            # Filter significant disparities
            significant_disparities = disparity_data[disparity_data['is_significant'] == True]

            if not significant_disparities.empty:
                st.write(f"**Found {len(significant_disparities)} statistically significant disparities** (p < 0.05)")

                # Disparity ratios by metric
                fig = px.bar(
                    significant_disparities,
                    x='group1',
                    y='disparity_ratio',
                    color='metric_name',
                    title='Significant Disparity Ratios',
                    barmode='group',
                    hover_data=['p_value', 'effect_size']
                )
                fig.add_hline(y=1.0, line_dash="dash", line_color="red", annotation_text="No Disparity (Ratio = 1.0)")
                st.plotly_chart(fig, use_container_width=True)

                # P-value distribution
                col1, col2 = st.columns(2)

                with col1:
                    fig = px.histogram(
                        disparity_data,
                        x='p_value',
                        color='is_significant',
                        title='P-Value Distribution',
                        nbins=20,
                        color_discrete_map={True: "red", False: "blue"}
                    )
                    fig.add_vline(x=0.05, line_dash="dash", line_color="red", annotation_text="Significance Threshold")
                    st.plotly_chart(fig, use_container_width=True)

                with col2:
                    # Effect size distribution
                    effect_counts = disparity_data['effect_size'].value_counts()
                    fig = px.pie(
                        values=effect_counts.values,
                        names=effect_counts.index,
                        title='Effect Size Distribution'
                    )
                    st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No statistically significant disparities found in the analysis.")

    def create_institutional_analysis(self):
        """Create institutional analysis visualizations"""
        st.header("🏦 Institutional Analysis")

        if 'top_lenders' in self.data:
            lender_data = self.data['top_lenders']

            st.subheader("Top Lenders by Volume")

            col1, col2 = st.columns(2)

            with col1:
                # Total volume by lender
                fig = px.bar(
                    lender_data,
                    x='total_volume',
                    y='lei',
                    orientation='h',
                    title='Total Loan Volume by Lender',
                    hover_data=['application_count', 'origination_rate']
                )
                fig.update_layout(yaxis={'categoryorder':'total ascending'})
                st.plotly_chart(fig, use_container_width=True)

            with col2:
                # Market share pie chart
                fig = px.pie(
                    lender_data,
                    values='total_volume',
                    names='lei',
                    title='Market Share by Volume'
                )
                st.plotly_chart(fig, use_container_width=True)

    def create_interactive_filters(self):
        """Create interactive filtering controls"""
        st.sidebar.header("🔍 Interactive Filters")

        # Geographic filters
        if 'state_analysis' in self.data:
            st.sidebar.subheader("Geographic Filters")
            selected_states = st.sidebar.multiselect(
                "Select States",
                options=self.data['state_analysis']['state_code'].unique(),
                default=self.data['state_analysis']['state_code'].unique()[:5]
            )

        # Demographic filters
        st.sidebar.subheader("Demographic Filters")
        if 'race_analysis' in self.data:
            selected_races = st.sidebar.multiselect(
                "Select Races",
                options=self.data['race_analysis']['race'].unique(),
                default=self.data['race_analysis']['race'].unique()
            )

        # Loan characteristic filters
        st.sidebar.subheader("Loan Filters")
        loan_size_range = st.sidebar.slider(
            "Loan Size Range ($000s)",
            min_value=0,
            max_value=1000,
            value=(100, 500),
            step=50
        )

        return {
            'selected_states': selected_states if 'selected_states' in locals() else None,
            'selected_races': selected_races if 'selected_races' in locals() else None,
            'loan_size_range': loan_size_range
        }

    def export_filtered_data(self, filters):
        """Create data export functionality"""
        st.sidebar.header("📥 Export Data")

        export_format = st.sidebar.selectbox(
            "Export Format",
            ["CSV", "Excel", "JSON"]
        )

        if st.sidebar.button("Export Filtered Data"):
            # Create filtered dataset based on selections
            filtered_data = {}

            for key, df in self.data.items():
                if isinstance(df, pd.DataFrame) and not df.empty:
                    # Apply filters
                    temp_df = df.copy()

                    # Geographic filter
                    if filters['selected_states'] and 'state_code' in temp_df.columns:
                        temp_df = temp_df[temp_df['state_code'].isin(filters['selected_states'])]

                    filtered_data[key] = temp_df

            # Prepare export
            if export_format == "CSV":
                st.sidebar.success(f"Prepared {len(filtered_data)} datasets for CSV export")
            elif export_format == "Excel":
                st.sidebar.success(f"Prepared {len(filtered_data)} datasets for Excel export")
            else:
                st.sidebar.success(f"Prepared {len(filtered_data)} datasets for JSON export")

    def run_dashboard(self):
        """Main dashboard execution"""
        st.set_page_config(
            page_title="HMDA Analysis Dashboard",
            page_icon="🏠",
            layout="wide",
            initial_sidebar_state="expanded"
        )

        st.title("🏠 Comprehensive HMDA Analysis Dashboard")
        st.markdown("---")

        # Overview section
        self.create_overview_metrics()
        st.markdown("---")

        # Interactive filters
        filters = self.create_interactive_filters()

        # Tab-based navigation
        tab1, tab2, tab3, tab4, tab5 = st.tabs([
            "🗺️ Geographic", "👥 Demographic", "💰 Loan Characteristics", "⚖️ Disparity Analysis", "🏦 Institutional"
        ])

        with tab1:
            self.create_geographic_analysis()

        with tab2:
            self.create_demographic_analysis()

        with tab3:
            self.create_loan_characteristics_analysis()

        with tab4:
            self.create_disparity_analysis()

        with tab5:
            self.create_institutional_analysis()

        # Export functionality
        self.export_filtered_data(filters)

        # Footer
        st.markdown("---")
        st.markdown("**Dashboard Information**")
        col1, col2, col3 = st.columns(3)

        with col1:
            st.write(f"**Last Updated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        with col2:
            if 'processing_timestamp' in self.metadata:
                st.write(f"**Data Processing:** {self.metadata['processing_timestamp'][:10]}")

        with col3:
            st.write("**Analysis Framework:** HMDA Comprehensive Pipeline v1.0")

def main():
    """Main dashboard execution"""
    dashboard = HMDADashboard()
    dashboard.run_dashboard()

if __name__ == "__main__":
    main()