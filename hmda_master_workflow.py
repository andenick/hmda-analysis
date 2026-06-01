#!/usr/bin/env python3
"""
HMDA Master Workflow Script
Orchestrates the complete HMDA data analysis pipeline
"""

import subprocess
import sys
import time
import logging
from pathlib import Path
from datetime import datetime
import os
DATA_ROOT = Path(os.environ.get("DATA_ROOT", "data"))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f"hmda_master_workflow_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

BASE_PATH = DATA_ROOT

def run_script(script_path, description):
    """Run a Python script and log its execution"""
    logger.info(f"="*60)
    logger.info(f"Starting: {description}")
    logger.info(f"Script: {script_path}")
    logger.info(f"="*60)
    
    start_time = time.time()
    
    try:
        result = subprocess.run(
            [sys.executable, script_path],
            capture_output=True,
            text=True,
            check=True
        )
        
        duration = time.time() - start_time
        logger.info(f"✅ Completed: {description}")
        logger.info(f"Duration: {duration:.2f} seconds")
        logger.info(f"Output: {result.stdout[-500:]}")  # Last 500 chars
        
        return True, result.stdout
        
    except subprocess.CalledProcessError as e:
        duration = time.time() - start_time
        logger.error(f"❌ Failed: {description}")
        logger.error(f"Duration: {duration:.2f} seconds")
        logger.error(f"Error: {e.stderr[-500:]}")  # Last 500 chars
        
        return False, e.stderr

def check_file_exists(file_path, description):
    """Check if a file exists"""
    path = Path(file_path)
    exists = path.exists()
    
    if exists:
        logger.info(f"✅ Found: {description}")
        logger.info(f"   Path: {file_path}")
        logger.info(f"   Size: {path.stat().st_size / (1024*1024):.2f} MB")
    else:
        logger.warning(f"⚠️  Missing: {description}")
        logger.warning(f"   Path: {file_path}")
    
    return exists

def main():
    """Main workflow orchestration"""
    logger.info("="*60)
    logger.info("HMDA MASTER WORKFLOW - STARTING")
    logger.info(f"Timestamp: {datetime.now().isoformat()}")
    logger.info("="*60)
    
    workflow_start = time.time()
    
    # Step 1: Check prerequisites
    logger.info("\n📋 STEP 1: Checking Prerequisites")
    
    raw_data_path = BASE_PATH / "Technical" / "archive" / "new_input" / "2024_public_lar_csv"
    raw_data_found = check_file_exists(
        raw_data_path / "[2025.08.11] 2024_public_lar_csv.csv",
        "Raw HMDA 2024 LAR data"
    )
    
    if not raw_data_found:
        logger.error("❌ Raw data not found. Cannot proceed.")
        return False
    
    # Step 2: Enhanced HMDA Processing (if not already done)
    logger.info("\n📊 STEP 2: Enhanced HMDA Processing")
    
    metadata_path = BASE_PATH / "Output" / "Data" / "enhanced_analysis" / "processing_metadata.json"
    processing_done = check_file_exists(metadata_path, "Processing metadata")
    
    if not processing_done:
        logger.info("Processing not complete. Running enhanced processor...")
        success, output = run_script(
            BASE_PATH / "Technical" / "src" / "hmda" / "enhanced_hmda_processor.py",
            "Enhanced HMDA Processing"
        )
        
        if not success:
            logger.error("❌ Processing failed. Aborting workflow.")
            return False
    else:
        logger.info("✅ Processing already completed. Skipping...")
    
    # Step 3: Geographic Aggregation
    logger.info("\n🗺️  STEP 3: Geographic Aggregation")
    
    success, output = run_script(
        BASE_PATH / "Technical" / "src" / "analysis" / "comprehensive_geographic_aggregator.py",
        "Geographic Aggregation"
    )
    
    if not success:
        logger.warning("⚠️  Geographic aggregation failed. Continuing...")
    
    # Step 4: Disparity Analysis (if module exists)
    logger.info("\n📈 STEP 4: Disparity Analysis")
    
    disparity_script = BASE_PATH / "Technical" / "src" / "analysis" / "advanced_disparity_analysis.py"
    if disparity_script.exists():
        success, output = run_script(
            disparity_script,
            "Advanced Disparity Analysis"
        )
        
        if not success:
            logger.warning("⚠️  Disparity analysis failed. Continuing...")
    else:
        logger.info("ℹ️  Disparity analysis script not found. Skipping...")
    
    # Step 5: Generate Summary Report
    logger.info("\n📝 STEP 5: Summary Report")
    
    total_duration = time.time() - workflow_start
    
    logger.info("="*60)
    logger.info("HMDA MASTER WORKFLOW - COMPLETED")
    logger.info(f"Total Duration: {total_duration:.2f} seconds ({total_duration/60:.2f} minutes)")
    logger.info("="*60)
    
    # Print summary
    print("\n" + "="*60)
    print("HMDA ANALYSIS WORKFLOW - SUMMARY")
    print("="*60)
    print(f"Status: ✅ COMPLETED")
    print(f"Duration: {total_duration/60:.2f} minutes")
    print(f"\nOutput Directories:")
    print(f"  - Enhanced Analysis: {BASE_PATH / 'Output' / 'Data' / 'enhanced_analysis'}")
    print(f"  - Geographic Agg: {BASE_PATH / 'Output' / 'Data' / 'geographic_aggregations'}")
    print(f"  - Disparity Analysis: {BASE_PATH / 'Output' / 'Data' / 'disparity_analysis'}")
    print(f"\nNext Steps:")
    print(f"  1. Review output files in the directories above")
    print(f"  2. Run visualization dashboard: python {BASE_PATH / 'Technical' / 'src' / 'api' / 'hmda_visualization_dashboard.py'}")
    print(f"  3. Access dashboard at: http://localhost:5000")
    print(f"  4. Review research proposals: {BASE_PATH / 'Technical' / 'docs' / 'COMPREHENSIVE_REVIEW_AND_RESEARCH_PROPOSALS.md'}")
    print("="*60)
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

