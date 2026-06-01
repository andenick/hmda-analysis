#!/usr/bin/env python3
"""
HMDA Stakeholder Dashboard - Production Version
==============================================
Enhanced for public deployment with additional security, performance, and monitoring features.
"""

import os
import sys
from pathlib import Path
from datetime import datetime
import logging
import json
import secrets
from functools import wraps

# Add project root to path for imports
BASE_PATH = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(BASE_PATH))

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from flask import Flask, render_template, jsonify, request, send_file, session, make_response
from flask_caching import Cache
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib import colors
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment

# Production Configuration
class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or secrets.token_hex(32)
    CACHE_TYPE = os.environ.get('CACHE_TYPE', 'SimpleCache')
    CACHE_DEFAULT_TIMEOUT = int(os.environ.get('CACHE_DEFAULT_TIMEOUT', 300))

    # Security settings
    SESSION_COOKIE_SECURE = os.environ.get('SECURE_SSL', 'False').lower() == 'true'
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'

    # Rate limiting
    RATELIMIT_ENABLED = os.environ.get('RATE_LIMIT_ENABLED', 'True').lower() == 'true'
    RATELIMIT_DEFAULT = os.environ.get('RATE_LIMIT_PER_MINUTE', '60') + " per minute"

# Configure logging for production
def setup_logging():
    log_level = os.environ.get('LOG_LEVEL', 'INFO')
    log_file = os.environ.get('LOG_FILE', 'logs/dashboard.log')

    # Create logs directory if it doesn't exist
    Path(log_file).parent.mkdir(parents=True, exist_ok=True)

    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(sys.stdout)
        ]
    )
    return logging.getLogger(__name__)

logger = setup_logging()

# Initialize Flask app
app = Flask(__name__)
app.config.from_object(Config)

# Initialize extensions
cache = Cache(app)

# Rate limiting (if enabled)
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=[app.config['RATELIMIT_DEFAULT']] if app.config['RATELIMIT_ENABLED'] else []
)

# Security headers decorator
def security_headers(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        response = make_response(f(*args, **kwargs))

        # Add security headers
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'

        if app.config['SESSION_COOKIE_SECURE']:
            response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'

        return response
    return decorated_function

# CORS handling (if needed)
@app.after_request
def after_request(response):
    allowed_origins = os.environ.get('ALLOWED_CORS_ORIGINS', '').split(',')
    origin = request.headers.get('Origin')

    if origin in allowed_origins:
        response.headers['Access-Control-Allow-Origin'] = origin
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'

    return response

# Base paths
BASE_PATH = Path(os.environ.get('DATA_PATH', BASE_PATH))
DATA_PATH = BASE_PATH / "Output" / "Data"
ENHANCED_PATH = DATA_PATH / "enhanced_analysis"

class ProductionDataManager:
    """Enhanced data manager with better error handling and monitoring"""

    def __init__(self):
        self.data_loaded = False
        self.datasets = {}
        self.load_time = None
        self.error_count = 0

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

    @cache.cached(timeout=600, key_prefix='load_all_data')
    def load_all_data(self):
        """Load all datasets with enhanced error handling"""
        start_time = datetime.now()
        logger.info("Loading production dashboard data...")

        try:
            datasets_to_load = [
                ('state_data', 'state_level.csv'),
                ('county_data', 'county_level.csv'),
                ('msa_data', 'msa_level.csv'),
                ('tract_data', 'tract_sample.csv'),
                ('race_data', 'race_analysis.csv'),
                ('ethnicity_data', 'ethnicity_analysis.csv'),
                ('lender_data', 'lender_rankings.csv')
            ]

            for key, filename in datasets_to_load:
                file_path = ENHANCED_PATH / filename
                try:
                    if file_path.exists():
                        self.datasets[key] = pd.read_csv(file_path, low_memory=False)
                        logger.info(f"✓ Loaded {key}: {len(self.datasets[key]):,} rows")
                    else:
                        logger.warning(f"⚠ File not found: {file_path}")
                        self.datasets[key] = pd.DataFrame()  # Empty DataFrame as fallback

                except Exception as e:
                    logger.error(f"✗ Error loading {filename}: {str(e)}")
                    self.error_count += 1
                    self.datasets[key] = pd.DataFrame()

            self.data_loaded = True
            self.load_time = datetime.now() - start_time
            logger.info(f"✓ Data loading completed in {self.load_time}")

        except Exception as e:
            logger.error(f"✗ Critical error loading data: {str(e)}")
            self.data_loaded = False

    def get_dataset(self, key):
        """Get dataset with validation"""
        if not self.data_loaded:
            self.load_all_data()

        dataset = self.datasets.get(key, pd.DataFrame())
        return dataset.copy() if not dataset.empty else pd.DataFrame()

# Initialize data manager
data_manager = ProductionDataManager()

# Routes with security and rate limiting
@app.route('/')
@security_headers
@limiter.limit("30 per minute")
def index():
    """Main dashboard page"""
    return render_template('stakeholder_dashboard.html')

@app.route('/api/state-data')
@security_headers
@cache.cached(timeout=300)
def get_state_data():
    """Get state-level data with caching"""
    try:
        data = data_manager.get_dataset('state_data')
        return jsonify({
            'success': True,
            'data': data.to_dict('records')[:1000],  # Limit for performance
            'total_rows': len(data)
        })
    except Exception as e:
        logger.error(f"Error in state data endpoint: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Unable to load state data'
        }), 500

@app.route('/api/county-data')
@security_headers
@limiter.limit("20 per minute")
def get_county_data():
    """Get county-level data with caching and rate limiting"""
    try:
        state = request.args.get('state', '')
        data = data_manager.get_dataset('county_data')

        if state:
            data = data[data['state_code'] == state]

        return jsonify({
            'success': True,
            'data': data.to_dict('records')[:2000],  # Limit for performance
            'total_rows': len(data)
        })
    except Exception as e:
        logger.error(f"Error in county data endpoint: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Unable to load county data'
        }), 500

@app.route('/api/race-analysis')
@security_headers
@cache.cached(timeout=600)
def get_race_analysis():
    """Get race-based analysis data"""
    try:
        data = data_manager.get_dataset('race_data')
        return jsonify({
            'success': True,
            'data': data.to_dict('records')
        })
    except Exception as e:
        logger.error(f"Error in race analysis endpoint: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Unable to load race analysis data'
        }), 500

@app.route('/api/health')
@security_headers
def health_check():
    """Enhanced health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'data_loaded': data_manager.data_loaded,
        'load_time': str(data_manager.load_time) if data_manager.load_time else None,
        'error_count': data_manager.error_count,
        'datasets_loaded': len([k for k, v in data_manager.datasets.items() if not v.empty()]),
        'timestamp': datetime.now().isoformat(),
        'version': '1.0.0-production'
    })

@app.route('/api/metrics')
@security_headers
def get_metrics():
    """Application metrics for monitoring"""
    return jsonify({
        'data_loaded': data_manager.data_loaded,
        'load_time': str(data_manager.load_time) if data_manager.load_time else None,
        'error_count': data_manager.error_count,
        'available_datasets': {
            key: len(df) if not df.empty else 0
            for key, df in data_manager.datasets.items()
        },
        'cache_info': cache.get().get('cache_info', {}),
        'timestamp': datetime.now().isoformat()
    })

# Error handlers
@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal server error: {str(error)}")
    return jsonify({'error': 'Internal server error'}), 500

@app.errorhandler(429)
def ratelimit_handler(e):
    return jsonify({'error': 'Rate limit exceeded'}), 429

if __name__ == '__main__':
    logger.info("="*60)
    logger.info("Starting HMDA Stakeholder Dashboard (Production)")
    logger.info("="*60)

    # Load data on startup
    data_manager.load_all_data()

    # Start server
    host = os.environ.get('HOST', '0.0.0.0')
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'

    logger.info(f"Server starting on http://{host}:{port}")
    logger.info(f"Debug mode: {debug}")
    logger.info(f"Rate limiting enabled: {app.config['RATELIMIT_ENABLED']}")
    logger.info("="*60)

    app.run(host=host, port=port, debug=debug)