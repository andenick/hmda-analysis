#!/usr/bin/env python3
"""
HMDA Interactive Visualization Dashboard
Flask-based web application for exploring HMDA data
"""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import json
from pathlib import Path
from flask import Flask, render_template, jsonify, request
from datetime import datetime
import logging
import os
DATA_ROOT = Path(os.environ.get("DATA_ROOT", "data"))

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)

# Base path
BASE_PATH = DATA_ROOT
DATA_PATH = BASE_PATH / "Output" / "Data"

class HMDAVisualizer:
    """Class to handle HMDA data visualization"""
    
    def __init__(self):
        self.data_loaded = False
        self.state_data = None
        self.county_data = None
        self.disparity_data = None
        
    def load_aggregated_data(self):
        """Load pre-aggregated data"""
        try:
            # Load state-level data
            state_files = list((DATA_PATH / "geographic_aggregations").glob("state_aggregation.csv"))
            if state_files:
                self.state_data = pd.read_csv(state_files[0])
                logger.info(f"Loaded state data: {len(self.state_data)} rows")
            
            # Load county-level data
            county_files = list((DATA_PATH / "geographic_aggregations").glob("county_aggregation.csv"))
            if county_files:
                self.county_data = pd.read_csv(county_files[0])
                logger.info(f"Loaded county data: {len(self.county_data)} rows")
            
            # Load disparity data
            disparity_files = list((DATA_PATH / "disparity_analysis").glob("disparity_analysis_results.csv"))
            if disparity_files:
                self.disparity_data = pd.read_csv(disparity_files[0])
                logger.info(f"Loaded disparity data: {len(self.disparity_data)} rows")
            
            self.data_loaded = True
            logger.info("Data loading completed successfully")
            
        except Exception as e:
            logger.error(f"Error loading data: {str(e)}")
            self.data_loaded = False
    
    def create_state_map(self):
        """Create choropleth map of state-level metrics"""
        if self.state_data is None or self.state_data.empty:
            return {"error": "No state data available"}
        
        # Check for required columns
        if 'state_code' not in self.state_data.columns:
            return {"error": "State code column not found"}
        
        # Find loan amount count column
        count_cols = [col for col in self.state_data.columns if 'loan_amount_count' in col.lower() or 'count' in col.lower()]
        if not count_cols:
            return {"error": "No count column found"}
        
        count_col = count_cols[0]
        
        fig = px.choropleth(
            self.state_data,
            locations='state_code',
            locationmode='USA-states',
            color=count_col,
            scope='usa',
            title='Loan Applications by State',
            color_continuous_scale='Viridis',
            labels={count_col: 'Application Count'}
        )
        
        fig.update_layout(
            geo=dict(bgcolor='rgba(0,0,0,0)'),
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            margin=dict(l=0, r=0, t=40, b=0)
        )
        
        return fig.to_json()
    
    def create_approval_rate_chart(self):
        """Create bar chart of approval rates by state"""
        if self.state_data is None or self.state_data.empty:
            return {"error": "No state data available"}
        
        # Find action_taken column
        action_cols = [col for col in self.state_data.columns if 'action_taken' in col.lower()]
        if not action_cols:
            return {"error": "No action_taken column found"}
        
        action_col = action_cols[0]
        
        # Sort by approval rate
        df = self.state_data.sort_values(action_col, ascending=False).head(20)
        
        fig = px.bar(
            df,
            x='state_code',
            y=action_col,
            title='Top 20 States by Approval Rate',
            labels={action_col: 'Approval Rate', 'state_code': 'State'},
            color=action_col,
            color_continuous_scale='RdYlGn'
        )
        
        fig.update_layout(
            xaxis_title='State',
            yaxis_title='Approval Rate',
            showlegend=False,
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)'
        )
        
        return fig.to_json()
    
    def create_disparity_chart(self):
        """Create disparity comparison chart"""
        if self.disparity_data is None or self.disparity_data.empty:
            return {"error": "No disparity data available"}
        
        fig = px.bar(
            self.disparity_data.head(15),
            x='metric_name',
            y='disparity_ratio',
            title='Top 15 Lending Disparities',
            labels={'disparity_ratio': 'Disparity Ratio', 'metric_name': 'Metric'},
            color='disparity_ratio',
            color_continuous_scale='Reds'
        )
        
        fig.update_layout(
            xaxis_tickangle=-45,
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)'
        )
        
        return fig.to_json()
    
    def get_summary_stats(self):
        """Get summary statistics"""
        stats = {}
        
        if self.state_data is not None:
            count_cols = [col for col in self.state_data.columns if 'count' in col.lower()]
            if count_cols:
                stats['total_applications'] = int(self.state_data[count_cols[0]].sum())
                stats['states_covered'] = len(self.state_data)
        
        if self.county_data is not None:
            stats['counties_covered'] = len(self.county_data)
        
        if self.disparity_data is not None:
            stats['disparities_identified'] = len(self.disparity_data)
        
        return stats

# Initialize visualizer
visualizer = HMDAVisualizer()

@app.route('/')
def index():
    """Main dashboard page"""
    return render_template('dashboard.html')

@app.route('/api/load_data')
def load_data():
    """API endpoint to load data"""
    visualizer.load_aggregated_data()
    return jsonify({'status': 'success', 'loaded': visualizer.data_loaded})

@app.route('/api/state_map')
def state_map():
    """API endpoint for state map"""
    return jsonify(visualizer.create_state_map())

@app.route('/api/approval_rate_chart')
def approval_rate_chart():
    """API endpoint for approval rate chart"""
    return jsonify(visualizer.create_approval_rate_chart())

@app.route('/api/disparity_chart')
def disparity_chart():
    """API endpoint for disparity chart"""
    return jsonify(visualizer.create_disparity_chart())

@app.route('/api/summary_stats')
def summary_stats():
    """API endpoint for summary statistics"""
    return jsonify(visualizer.get_summary_stats())

@app.route('/api/health')
def health():
    """Health check endpoint"""
    return jsonify({'status': 'healthy', 'timestamp': datetime.now().isoformat()})

if __name__ == '__main__':
    logger.info("Starting HMDA Visualization Dashboard...")
    visualizer.load_aggregated_data()
    app.run(debug=True, host='0.0.0.0', port=5000)

