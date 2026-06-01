#!/usr/bin/env python3
"""
HMDA Stakeholder Dashboard - Streamlit Version
==============================================
Easy deployment on Streamlit Cloud with all the same features as the Flask version.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from pathlib import Path
import json
import time
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Set page config
st.set_page_config(
    page_title="HMDA Community Dashboard",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better accessibility and styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #2c3e50;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-card {
        background: #f8f9fa;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #3498db;
    }
    .info-box {
        background: #e8f4fd;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #3498db;
        margin: 1rem 0;
    }
    .warning-box {
        background: #fff3cd;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #ffc107;
        margin: 1rem 0;
    }
    .help-text {
        font-size: 0.9rem;
        color: #6c757d;
        font-style: italic;
    }
</style>
""", unsafe_allow_html=True)

class StreamlitDataManager:
    """Data manager optimized for Streamlit"""

    def __init__(self):
        self.base_path = Path(".")
        self.data_path = self.base_path / "Output" / "Data"
        self.enhanced_path = self.data_path / "enhanced_analysis"
        self.comprehensive_path = self.data_path / "comprehensive_hmda_results"

        # Plain language dictionary
        self.plain_language = {
            'action_taken': 'Loan Decision',
            'derived_race': 'Applicant Race',
            'derived_ethnicity': 'Applicant Ethnicity',
            'loan_amount': 'Loan Amount',
            'interest_rate': 'Interest Rate',
            'loan_to_income_ratio': 'Debt-to-Income Ratio',
            'origination_rate': 'Approval Rate',
            'denial_rate': 'Denial Rate',
            'high_cost_loan': 'High-Cost Loan',
            'lei': 'Lender',
            'fips': 'County Code',
            'state_code': 'State',
            'msa': 'Metro Area'
        }

    def load_data(self):
        """Load data with caching and error handling"""
        @st.cache_data(ttl=3600)  # Cache for 1 hour
        def _load_datasets():
            datasets = {}

            # Try enhanced analysis first
            datasets_to_load = [
                ('state_data', self.enhanced_path / "state_level.csv"),
                ('county_data', self.enhanced_path / "county_level.csv"),
                ('msa_data', self.enhanced_path / "msa_level.csv"),
                ('race_data', self.enhanced_path / "race_analysis.csv"),
                ('ethnicity_data', self.enhanced_path / "ethnicity_analysis.csv"),
                ('lender_data', self.enhanced_path / "lender_rankings.csv")
            ]

            for key, file_path in datasets_to_load:
                if file_path.exists():
                    try:
                        datasets[key] = pd.read_csv(file_path, low_memory=False)
                        logger.info(f"✓ Loaded {key}: {len(datasets[key]):,} rows")
                    except Exception as e:
                        logger.error(f"✗ Error loading {key}: {str(e)}")
                        datasets[key] = pd.DataFrame()
                else:
                    logger.warning(f"⚠ File not found: {file_path}")
                    datasets[key] = pd.DataFrame()

            return datasets

        return _load_datasets()

    def get_available_years(self):
        """Get list of available years from comprehensive results"""
        years = []
        if self.comprehensive_path.exists():
            for file_path in self.comprehensive_path.glob("*_hmda_final_aggregated.csv"):
                year = file_path.name.split('_')[0]
                try:
                    years.append(int(year))
                except ValueError:
                    continue
        return sorted(years)

# Initialize data manager
@st.cache_resource
def get_data_manager():
    return StreamlitDataManager()

data_manager = get_data_manager()

# Header and Introduction
st.markdown('<h1 class="main-header">🏠 HMDA Community Lending Dashboard</h1>',
           unsafe_allow_html=True)

st.markdown("""
Explore mortgage lending patterns in your community using data from the Home Mortgage Disclosure Act (HMDA).
This tool helps community organizations, researchers, and policymakers understand lending trends and identify potential fair lending concerns.
""")

# Sidebar for navigation and filters
st.sidebar.markdown("## 🗺️ Navigate")

# Page selection
page = st.sidebar.selectbox(
    "Choose a view:",
    ["Overview", "State Analysis", "County Details", "Demographic Analysis", "Lender Rankings", "About"]
)

# Data loading indicator
if st.sidebar.button("🔄 Reload Data"):
    st.cache_data.clear()
    st.success("Data cache cleared! Reloading...")

# Load data
with st.spinner("Loading HMDA data... This may take a moment."):
    datasets = data_manager.load_data()

# Show data availability
available_years = data_manager.get_available_years()
st.sidebar.markdown(f"**📅 Data Years Available:** {', '.join(map(str, available_years))}")

if not any(datasets.values()):
    st.error("""
    ⚠️ **No Data Available**

    Please ensure that:
    1. HMDA data has been processed using the comprehensive processor
    2. Output files are in the `Output/Data/enhanced_analysis/` directory
    3. Files are named correctly (e.g., `state_level.csv`)

    See the deployment guide for data processing instructions.
    """)
    st.stop()

# Different pages
if page == "Overview":
    st.markdown("## 📊 National Overview")

    # Check if we have state data
    if datasets['state_data'].empty:
        st.warning("State-level data not available. Please run the data processor first.")
        st.stop()

    state_data = datasets['state_data']

    # Key metrics
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        total_applications = state_data['application_count'].sum()
        st.metric("Total Applications", f"{total_applications:,.0f}")

    with col2:
        avg_approval_rate = state_data['origination_rate_mean'].mean()
        st.metric("Average Approval Rate", f"{avg_approval_rate:.1f}%")

    with col3:
        total_loan_volume = state_data['loan_amount_sum'].sum()
        st.metric("Total Loan Volume", f"${total_loan_volume/1e9:.1f}B")

    with col4:
        num_states = len(state_data)
        st.metric("States Covered", num_states)

    # State map
    st.markdown("### 🗺️ State-Level Approval Rates")

    fig = px.choropleth(
        state_data,
        locations='state_code',
        color='origination_rate_mean',
        scope="usa",
        labels={'origination_rate_mean': 'Approval Rate (%)'},
        title='Mortgage Approval Rates by State',
        color_continuous_scale="RdYlGn",
        hover_data=['state_code', 'application_count', 'loan_amount_sum']
    )

    fig.update_layout(
        height=500,
        title_font_size=16
    )

    st.plotly_chart(fig, use_container_width=True)

    # Insights
    st.markdown("### 💡 Key Insights")

    # Find highest and lowest approval rates
    highest_state = state_data.loc[state_data['origination_rate_mean'].idxmax()]
    lowest_state = state_data.loc[state_data['origination_rate_mean'].idxmin()]

    col1, col2 = st.columns(2)

    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <h4>🟢 Highest Approval Rate</h4>
            <p><strong>{highest_state.get('state_name', highest_state.get('state_code', 'Unknown'))}</strong></p>
            <p>{highest_state['origination_rate_mean']:.1f}% approval rate</p>
            <p>{highest_state['application_count']:,.0f} applications</p>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown(f"""
        <div class="metric-card">
            <h4>🔴 Lowest Approval Rate</h4>
            <p><strong>{lowest_state.get('state_name', lowest_state.get('state_code', 'Unknown'))}</strong></p>
            <p>{lowest_state['origination_rate_mean']:.1f}% approval rate</p>
            <p>{lowest_state['application_count']:,.0f} applications</p>
        </div>
        """, unsafe_allow_html=True)

elif page == "State Analysis":
    st.markdown("## 📈 Detailed State Analysis")

    if datasets['state_data'].empty:
        st.warning("State data not available.")
        st.stop()

    state_data = datasets['state_data']

    # State selector
    if 'state_name' in state_data.columns:
        state_options = ['All States'] + sorted(state_data['state_name'].unique())
        selected_state = st.selectbox("Select State:", state_options)

        if selected_state != 'All States':
            filtered_data = state_data[state_data['state_name'] == selected_state]
        else:
            filtered_data = state_data
    else:
        filtered_data = state_data
        st.info("State names not available in data. Showing all states.")

    # Detailed metrics for selected state
    if selected_state != 'All States' and len(filtered_data) == 1:
        st.markdown(f"### 📊 {selected_state} - Detailed Metrics")

        state_info = filtered_data.iloc[0]

        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric("Applications", f"{state_info['application_count']:,.0f}")
            st.metric("Approval Rate", f"{state_info['origination_rate_mean']:.1f}%")

        with col2:
            st.metric("Avg Loan Amount", f"${state_info['loan_amount_mean']:,.0f}")
            st.metric("Denial Rate", f"{state_info.get('denial_rate_mean', 0):.1f}%")

        with col3:
            st.metric("Total Volume", f"${state_info['loan_amount_sum']/1e6:.1f}M")
            st.metric("Lenders", f"{state_info.get('institution_count', 0):.0f}")

    # Comparison charts
    st.markdown("### 📊 State Comparisons")

    chart_type = st.selectbox("Select Chart Type:", ["Approval Rates", "Loan Amounts", "Application Volume"])

    if chart_type == "Approval Rates":
        fig = px.bar(
            filtered_data.head(20).sort_values('origination_rate_mean', ascending=True),
            x='origination_rate_mean',
            y='state_code' if 'state_code' in filtered_data.columns else filtered_data.index,
            orientation='h',
            title='Approval Rates by State (%)',
            labels={'origination_rate_mean': 'Approval Rate (%)', 'state_code': 'State'}
        )
    elif chart_type == "Loan Amounts":
        fig = px.bar(
            filtered_data.head(20).sort_values('loan_amount_mean', ascending=True),
            x='loan_amount_mean',
            y='state_code' if 'state_code' in filtered_data.columns else filtered_data.index,
            orientation='h',
            title='Average Loan Amounts by State ($)',
            labels={'loan_amount_mean': 'Average Loan Amount ($)', 'state_code': 'State'}
        )
    else:  # Application Volume
        fig = px.bar(
            filtered_data.head(20).sort_values('application_count', ascending=True),
            x='application_count',
            y='state_code' if 'state_code' in filtered_data.columns else filtered_data.index,
            orientation='h',
            title='Application Volume by State',
            labels={'application_count': 'Number of Applications', 'state_code': 'State'}
        )

    st.plotly_chart(fig, use_container_width=True)

elif page == "County Details":
    st.markdown("## 🏘️ County-Level Analysis")

    if datasets['county_data'].empty:
        st.warning("County data not available.")
        st.stop()

    county_data = datasets['county_data']

    # State selector for counties
    if 'state_code' in county_data.columns:
        states = sorted(county_data['state_code'].unique())
        selected_state = st.selectbox("Select State:", ['All States'] + states)

        if selected_state != 'All States':
            county_filtered = county_data[county_data['state_code'] == selected_state]
        else:
            county_filtered = county_data
    else:
        county_filtered = county_data

    # County selector
    if 'county_name' in county_filtered.columns:
        counties = ['All Counties'] + sorted(county_filtered['county_name'].unique()[:100])  # Limit to prevent UI issues
        selected_county = st.selectbox("Select County (showing first 100):", counties)

        if selected_county != 'All Counties':
            county_detail = county_filtered[county_filtered['county_name'] == selected_county]
            display_data = county_detail
        else:
            display_data = county_filtered.head(50)
    else:
        display_data = county_filtered.head(50)

    # Show county details or table
    if selected_county != 'All Counties' and len(county_detail) == 1:
        st.markdown(f"### 📊 {selected_county} County Details")

        county_info = county_detail.iloc[0]

        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric("Applications", f"{county_info['application_count']:,.0f}")
            st.metric("Approval Rate", f"{county_info['origination_rate_mean']:.1f}%")

        with col2:
            st.metric("Avg Loan Amount", f"${county_info['loan_amount_mean']:,.0f}")
            st.metric("Denial Rate", f"{county_info.get('denial_rate_mean', 0):.1f}%")

        with col3:
            st.metric("Total Volume", f"${county_info['loan_amount_sum']/1e6:.1f}M")
            st.metric("Lenders", f"{county_info.get('institution_count', 0):.0f}")

    # County table
    st.markdown("### 📋 County Data Table")
    st.dataframe(
        display_data[['state_code', 'county_name', 'application_count', 'origination_rate_mean', 'loan_amount_mean', 'denial_rate_mean']].round(2),
        use_container_width=True
    )

elif page == "Demographic Analysis":
    st.markdown("## 👥 Demographic Analysis")

    # Race analysis
    if not datasets['race_data'].empty:
        st.markdown("### 🏃‍♂️ Race-Based Lending Patterns")

        race_data = datasets['race_data']

        if 'derived_race' in race_data.columns and 'origination_rate_mean' in race_data.columns:
            # Race approval rates chart
            fig = px.bar(
                race_data,
                x='derived_race',
                y='origination_rate_mean',
                title='Approval Rates by Race/Ethnicity',
                labels={'origination_rate_mean': 'Approval Rate (%)', 'derived_race': 'Race/Ethnicity'},
                color='origination_rate_mean',
                color_continuous_scale="RdYlGn"
            )

            fig.update_layout(xaxis_tickangle=-45)
            st.plotly_chart(fig, use_container_width=True)

            # Detailed table
            st.markdown("#### Detailed Race Analysis")
            display_cols = ['derived_race', 'application_count', 'origination_rate_mean', 'denial_rate_mean', 'loan_amount_mean']
            available_cols = [col for col in display_cols if col in race_data.columns]
            st.dataframe(race_data[available_cols].round(2), use_container_width=True)
        else:
            st.warning("Race data columns not in expected format.")

    # Ethnicity analysis
    if not datasets['ethnicity_data'].empty:
        st.markdown("### 🌎 Ethnicity-Based Lending Patterns")

        ethnicity_data = datasets['ethnicity_data']

        if 'derived_ethnicity' in ethnicity_data.columns and 'origination_rate_mean' in ethnicity_data.columns:
            # Ethnicity approval rates chart
            fig = px.bar(
                ethnicity_data,
                x='derived_ethnicity',
                y='origination_rate_mean',
                title='Approval Rates by Ethnicity',
                labels={'origination_rate_mean': 'Approval Rate (%)', 'derived_ethnicity': 'Ethnicity'},
                color='origination_rate_mean',
                color_continuous_scale="RdYlGn"
            )

            fig.update_layout(xaxis_tickangle=-45)
            st.plotly_chart(fig, use_container_width=True)

            # Detailed table
            st.markdown("#### Detailed Ethnicity Analysis")
            display_cols = ['derived_ethnicity', 'application_count', 'origination_rate_mean', 'denial_rate_mean', 'loan_amount_mean']
            available_cols = [col for col in display_cols if col in ethnicity_data.columns]
            st.dataframe(ethnicity_data[available_cols].round(2), use_container_width=True)
        else:
            st.warning("Ethnicity data columns not in expected format.")

elif page == "Lender Rankings":
    st.markdown("## 🏦 Top Lenders Analysis")

    if datasets['lender_data'].empty:
        st.warning("Lender data not available.")
        st.stop()

    lender_data = datasets['lender_data']

    # State selector for lender rankings
    if 'state_code' in lender_data.columns:
        states = ['All States'] + sorted(lender_data['state_code'].unique())
        selected_state = st.selectbox("Select State:", states)

        if selected_state != 'All States':
            lender_filtered = lender_data[lender_data['state_code'] == selected_state]
        else:
            lender_filtered = lender_data
    else:
        lender_filtered = lender_data

    # Top lenders table
    st.markdown("### 📊 Top Lenders by Application Volume")

    if 'application_count' in lender_filtered.columns:
        top_lenders = lender_filtered.nlargest(20, 'application_count')

        # Display metrics
        col1, col2 = st.columns(2)

        with col1:
            st.metric("Total Lenders", len(lender_filtered))
            st.metric("Applications in Selected Area", top_lenders['application_count'].sum())

        with col2:
            avg_approval = top_lenders['origination_rate_mean'].mean()
            st.metric("Average Approval Rate", f"{avg_approval:.1f}%")
            total_volume = top_lenders['loan_amount_sum'].sum()
            st.metric("Total Loan Volume", f"${total_volume/1e9:.1f}B")

        # Lender table
        display_cols = ['institution_name', 'application_count', 'origination_rate_mean', 'loan_amount_mean', 'denial_rate_mean']
        available_cols = [col for col in display_cols if col in top_lenders.columns]

        st.dataframe(
            top_lenders[available_cols].round(2),
            use_container_width=True
        )

        # Visualization
        if len(top_lenders) > 0:
            fig = px.bar(
                top_lenders.head(10),
                x='application_count',
                y='institution_name' if 'institution_name' in top_lenders.columns else top_lenders.index,
                orientation='h',
                title='Top 10 Lenders by Application Volume',
                labels={'application_count': 'Number of Applications', 'institution_name': 'Lender'}
            )

            fig.update_layout(height=400, yaxis={'categoryorder':'total ascending'})
            st.plotly_chart(fig, use_container_width=True)

elif page == "About":
    st.markdown("## ℹ️ About This Dashboard")

    st.markdown("""
    ### 🎯 Purpose
    This dashboard makes Home Mortgage Disclosure Act (HMDA) data accessible to community organizations, policymakers, researchers, and the public to:

    - Monitor lending patterns in local communities
    - Identify potential fair lending concerns
    - Support housing advocacy and policy development
    - Promote transparency in mortgage lending

    ### 📊 Data Source
    - **Consumer Financial Protection Bureau (CFPB)**
    - **HMDA Public Data**: 2019-2024 (most recent available)
    - **Update Frequency**: Annually

    ### 🏛️ What is HMDA?
    The Home Mortgage Disclosure Act requires most mortgage lenders to report:
    - Who applies for mortgages
    - Who gets approved or denied
    - Loan amounts and terms
    - Applicant demographics (race, ethnicity, income, etc.)

    ### 💡 How to Use This Dashboard

    1. **Overview**: See national lending patterns
    2. **State Analysis**: Dive into state-specific data
    3. **County Details**: Explore local lending patterns
    4. **Demographic Analysis**: Compare lending across demographic groups
    5. **Lender Rankings**: See which lenders are most active in your area

    ### ⚠️ Important Notes

    - **Correlation vs. Causation**: Differences in approval rates don't prove discrimination
    - **Multiple Factors**: Many legitimate factors affect lending decisions
    - **Data Limitations**: HMDA data doesn't include credit scores or detailed financial information
    - **Context Matters**: Consider local economic conditions when interpreting results

    ### 🛠️ Technical Details

    - **Data Processing**: Follows strict R methodology replication
    - **Validation**: Extensive quality checks and validation procedures
    - **Updates**: Annual when new HMDA data is released

    ### 📞 Get Help

    **For Fair Housing Concerns:**
    - File a complaint: [consumerfinance.gov/complaint](https://www.consumerfinance.gov/complaint)
    - HUD Fair Housing: 1-800-669-9777

    **For Housing Counseling:**
    - HUD-approved counselors: [hud.gov/counseling](https://www.hud.gov/counseling)

    **For Data Questions:**
    - Technical support: [Contact Information]
    - Data documentation: Available in project repository

    ---

    *This dashboard is designed to promote transparency and fairness in mortgage lending. All data is public information from the CFPB.*
    """)

    st.markdown("---")
    st.markdown("### 📊 Data Summary")

    # Show data availability summary
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Years Available", len(available_years))
        if available_years:
            st.metric("Data Range", f"{min(available_years)}-{max(available_years)}")

    with col2:
        available_datasets = sum(1 for dataset in datasets.values() if not dataset.empty)
        st.metric("Datasets Loaded", f"{available_datasets}/6")

    with col3:
        total_records = 0
        for name, dataset in datasets.items():
            if not dataset.empty:
                total_records += len(dataset)
        st.metric("Total Records", f"{total_records:,.0f}")

# Footer
st.markdown("---")
st.markdown(f"""
<div style="text-align: center; color: #6c757d; font-size: 0.8rem;">
    <p>HMDA Community Dashboard | Data from CFPB | Last updated: {datetime.now().strftime('%B %Y')}</p>
    <p>This tool uses public HMDA data to promote transparency in mortgage lending.</p>
</div>
""", unsafe_allow_html=True)

# Data quality and help information
with st.expander("❓ Need Help?"):
    st.markdown("""
    ### Common Questions

    **Q: Why can't I see any data?**
    A: Make sure the HMDA data has been processed. Run `comprehensive_hmda_processor_fixed.py` first.

    **Q: What do approval rates mean?**
    A: Percentage of mortgage applications that were approved. Normal range is typically 70-85%.

    **Q: Should I be concerned about demographic differences?**
    A: Small differences (1-3%) are normal. Large differences (10%+) may warrant further investigation.

    **Q: How current is this data?**
    A: HMDA data is released annually with a one-year lag. 2024 data is typically available in late 2024.

    **Q: Can I download this data?**
    A: Yes! The processed data is available in the `Output/Data/` directories in CSV, Excel, and other formats.
    """)