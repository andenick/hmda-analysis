"""
Systemically Important Banks Analysis
====================================

This module identifies and analyzes systemically important US banks using HMDA data.
It provides tools to identify SIFIs (Systemically Important Financial Institutions)
and analyze their lending patterns across different demographic and geographic segments.
"""

import os
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import yaml

class SystemicBanksAnalyzer:
    """
    Analyzer for systemically important US banks using HMDA data.
    
    This class identifies and analyzes the largest, most systemically important
    banks based on their lending volume, geographic presence, and market share.
    """
    
    def __init__(self, config_path: str = "python_project.yaml"):
        """Initialize the analyzer with configuration."""
        self.config = self._load_config(config_path)
        self.sifi_data = None
        self.bank_rankings = None
        
    def _load_config(self, config_path: str) -> dict:
        """Load configuration from YAML file."""
        with open(config_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    
    def identify_systemic_banks(self, 
                              year: int = 2019, 
                              top_n: int = 50,
                              min_loans: int = 1000,
                              min_states: int = 5) -> pd.DataFrame:
        """
        Identify systemically important banks based on multiple criteria.
        
        Args:
            year: Year to analyze
            top_n: Number of top banks to identify
            min_loans: Minimum number of loans to be considered
            min_states: Minimum number of states where bank operates
            
        Returns:
            DataFrame with systemic bank rankings and metrics
        """
        print(f"Identifying systemic banks for {year}...")
        
        # Load HMDA data
        hmda_data = self._load_hmda_data(year)
        
        # Calculate bank-level metrics
        bank_metrics = self._calculate_bank_metrics(hmda_data)
        
        # Apply filters
        filtered_banks = bank_metrics[
            (bank_metrics['total_loans'] >= min_loans) &
            (bank_metrics['states_count'] >= min_states)
        ].copy()
        
        # Calculate systemic importance score
        filtered_banks = self._calculate_systemic_score(filtered_banks)
        
        # Rank and select top banks
        systemic_banks = filtered_banks.nlargest(top_n, 'systemic_score')
        
        print(f"Identified {len(systemic_banks)} systemic banks")
        return systemic_banks
    
    def _load_hmda_data(self, year: int) -> pd.DataFrame:
        """Load HMDA data for analysis."""
        hmda_path = f"data/hmda/hmda_race_agg_{year}.parquet"
        if not os.path.exists(hmda_path):
            raise FileNotFoundError(f"HMDA data not found: {hmda_path}")
        
        return pd.read_parquet(hmda_path)
    
    def _calculate_bank_metrics(self, hmda_data: pd.DataFrame) -> pd.DataFrame:
        """Calculate comprehensive metrics for each bank."""
        print("Calculating bank-level metrics...")
        
        # Group by LEI (bank identifier)
        bank_metrics = hmda_data.groupby('lei').agg({
            'county_code': ['count', 'nunique'],  # Total loans and counties
            # Sum all loan amounts (assuming these columns exist)
            **{col: 'sum' for col in hmda_data.columns if 'HL_Amt_' in col and 'Total' not in col}
        }).reset_index()
        
        # Flatten column names
        bank_metrics.columns = ['lei'] + [f"{col[0]}_{col[1]}" if col[1] else col[0] 
                                        for col in bank_metrics.columns[1:]]
        
        # Rename key columns
        bank_metrics = bank_metrics.rename(columns={
            'county_code_count': 'total_loans',
            'county_code_nunique': 'counties_count'
        })
        
        # Calculate states count from county codes (first 2 digits)
        hmda_data['state_code'] = hmda_data['county_code'].astype(str).str[:2]
        state_counts = hmda_data.groupby('lei')['state_code'].nunique().reset_index()
        state_counts.columns = ['lei', 'states_count']
        bank_metrics = bank_metrics.merge(state_counts, on='lei', how='left')
        
        # Calculate total loan amount
        amount_cols = [col for col in bank_metrics.columns if 'HL_Amt_' in col and 'Total' not in col]
        bank_metrics['total_loan_amount'] = bank_metrics[amount_cols].sum(axis=1)
        
        # Add placeholder columns for missing bank details
        bank_metrics['respondent_name'] = 'Unknown Bank'
        bank_metrics['assets'] = 0
        bank_metrics['agency_code'] = 0
        
        return bank_metrics
    
    def _calculate_systemic_score(self, bank_metrics: pd.DataFrame) -> pd.DataFrame:
        """Calculate systemic importance score for each bank."""
        print("Calculating systemic importance scores...")
        
        # Normalize metrics to 0-1 scale
        metrics_to_normalize = ['total_loans', 'counties_count', 'states_count', 'total_loan_amount']
        
        for metric in metrics_to_normalize:
            if metric in bank_metrics.columns:
                min_val = bank_metrics[metric].min()
                max_val = bank_metrics[metric].max()
                bank_metrics[f'{metric}_normalized'] = (bank_metrics[metric] - min_val) / (max_val - min_val)
        
        # Calculate weighted systemic score
        weights = {
            'total_loans_normalized': 0.3,
            'counties_count_normalized': 0.2,
            'states_count_normalized': 0.2,
            'total_loan_amount_normalized': 0.3
        }
        
        bank_metrics['systemic_score'] = 0
        for metric, weight in weights.items():
            if metric in bank_metrics.columns:
                bank_metrics['systemic_score'] += bank_metrics[metric] * weight
        
        return bank_metrics
    
    def analyze_lending_patterns(self, 
                               systemic_banks: pd.DataFrame, 
                               hmda_data: pd.DataFrame,
                               demographic_groups: List[str] = None) -> Dict:
        """
        Analyze lending patterns of systemic banks across demographic groups.
        
        Args:
            systemic_banks: DataFrame of systemic banks
            hmda_data: Full HMDA dataset
            demographic_groups: List of demographic groups to analyze
            
        Returns:
            Dictionary with analysis results
        """
        print("Analyzing lending patterns of systemic banks...")
        
        if demographic_groups is None:
            demographic_groups = ['race', 'income', 'geography']
        
        # Filter HMDA data to systemic banks only
        systemic_lei_list = systemic_banks['lei'].tolist()
        systemic_hmda = hmda_data[hmda_data['lei'].isin(systemic_lei_list)].copy()
        
        results = {}
        
        # Analyze by race
        if 'race' in demographic_groups:
            results['race_analysis'] = self._analyze_by_race(systemic_hmda)
        
        # Analyze by income
        if 'income' in demographic_groups:
            results['income_analysis'] = self._analyze_by_income(systemic_hmda)
        
        # Analyze by geography
        if 'geography' in demographic_groups:
            results['geography_analysis'] = self._analyze_by_geography(systemic_hmda)
        
        # Market concentration analysis
        results['market_concentration'] = self._analyze_market_concentration(systemic_hmda)
        
        return results
    
    def _analyze_by_race(self, hmda_data: pd.DataFrame) -> Dict:
        """Analyze lending patterns by race."""
        # This would analyze race-based lending patterns
        # Implementation depends on available race columns in HMDA data
        race_cols = [col for col in hmda_data.columns if any(race in col for race in 
                    ['Asian', 'Black', 'White', 'Indigenous', 'Other', 'NotAvail'])]
        
        race_analysis = {}
        for col in race_cols:
            if 'HL_Amt_' in col and 'Total' not in col:
                race_analysis[col] = {
                    'total_amount': hmda_data[col].sum(),
                    'avg_amount': hmda_data[col].mean(),
                    'count': (hmda_data[col] > 0).sum()
                }
        
        return race_analysis
    
    def _analyze_by_income(self, hmda_data: pd.DataFrame) -> Dict:
        """Analyze lending patterns by income level."""
        # Analyze by income buckets (BILow, BIMod, etc.)
        income_analysis = {}
        
        # This would analyze income-based patterns
        # Implementation depends on available income columns
        
        return income_analysis
    
    def _analyze_by_geography(self, hmda_data: pd.DataFrame) -> Dict:
        """Analyze lending patterns by geography."""
        geo_analysis = {}
        
        # Create state code from county code if not exists
        if 'state_code' not in hmda_data.columns:
            hmda_data['state_code'] = hmda_data['county_code'].astype(str).str[:2]
        
        # Analyze by state
        state_analysis = hmda_data.groupby('state_code').agg({
            'lei': 'nunique',
            **{col: 'sum' for col in hmda_data.columns if 'HL_Amt_' in col and 'Total' not in col}
        })
        
        geo_analysis['by_state'] = state_analysis
        
        # Analyze by county
        county_analysis = hmda_data.groupby('county_code').agg({
            'lei': 'nunique',
            **{col: 'sum' for col in hmda_data.columns if 'HL_Amt_' in col and 'Total' not in col}
        })
        
        geo_analysis['by_county'] = county_analysis
        
        return geo_analysis
    
    def _analyze_market_concentration(self, hmda_data: pd.DataFrame) -> Dict:
        """Analyze market concentration of systemic banks."""
        # Calculate HHI (Herfindahl-Hirschman Index) for market concentration
        total_amount = hmda_data[[col for col in hmda_data.columns if 'HL_Amt_' in col and 'Total' not in col]].sum().sum()
        
        bank_shares = hmda_data.groupby('lei').agg({
            col: 'sum' for col in hmda_data.columns if 'HL_Amt_' in col and 'Total' not in col
        }).sum(axis=1) / total_amount
        
        # Calculate HHI
        hhi = (bank_shares ** 2).sum()
        
        return {
            'hhi': hhi,
            'market_shares': bank_shares.to_dict(),
            'concentration_level': self._classify_concentration(hhi)
        }
    
    def _classify_concentration(self, hhi: float) -> str:
        """Classify market concentration based on HHI."""
        if hhi < 0.15:
            return "Unconcentrated"
        elif hhi < 0.25:
            return "Moderately Concentrated"
        else:
            return "Highly Concentrated"
    
    def generate_systemic_bank_report(self, 
                                    year: int = 2019,
                                    top_n: int = 50,
                                    output_dir: str = "data/banks") -> str:
        """
        Generate comprehensive report on systemic banks.
        
        Args:
            year: Year to analyze
            top_n: Number of top banks to include
            output_dir: Directory to save results
            
        Returns:
            Path to generated report
        """
        print(f"Generating systemic bank report for {year}...")
        
        # Create output directory
        os.makedirs(output_dir, exist_ok=True)
        
        # Identify systemic banks
        systemic_banks = self.identify_systemic_banks(year, top_n)
        
        # Load HMDA data for analysis
        hmda_data = self._load_hmda_data(year)
        
        # Analyze lending patterns
        patterns = self.analyze_lending_patterns(systemic_banks, hmda_data)
        
        # Save results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save systemic banks list
        banks_file = os.path.join(output_dir, f"systemic_banks_{year}_{timestamp}.csv")
        systemic_banks.to_csv(banks_file, index=False)
        
        # Save analysis results
        analysis_file = os.path.join(output_dir, f"systemic_analysis_{year}_{timestamp}.json")
        import json
        with open(analysis_file, 'w') as f:
            # Convert numpy types to Python types for JSON serialization
            json.dump(self._prepare_for_json(patterns), f, indent=2)
        
        # Generate summary report
        report_file = os.path.join(output_dir, f"systemic_bank_report_{year}_{timestamp}.md")
        self._generate_markdown_report(systemic_banks, patterns, report_file, year)
        
        print(f"Systemic bank report generated: {report_file}")
        return report_file
    
    def _prepare_for_json(self, data):
        """Prepare data for JSON serialization."""
        if isinstance(data, dict):
            return {k: self._prepare_for_json(v) for k, v in data.items()}
        elif isinstance(data, pd.DataFrame):
            return data.to_dict('records')
        elif isinstance(data, pd.Series):
            return data.to_dict()
        elif isinstance(data, (np.integer, np.floating)):
            return float(data)
        else:
            return data
    
    def _generate_markdown_report(self, 
                                systemic_banks: pd.DataFrame, 
                                patterns: Dict, 
                                output_path: str,
                                year: int):
        """Generate markdown report for systemic banks."""
        
        with open(output_path, 'w') as f:
            f.write(f"# Systemically Important Banks Analysis - {year}\n\n")
            f.write(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            # Executive Summary
            f.write("## Executive Summary\n\n")
            f.write(f"Analysis of {len(systemic_banks)} systemically important banks ")
            f.write(f"based on lending volume, geographic presence, and market concentration.\n\n")
            
            # Top Banks
            f.write("## Top Systemically Important Banks\n\n")
            f.write("| Rank | Bank Name | LEI | Total Loans | States | Counties | Systemic Score |\n")
            f.write("|------|-----------|-----|-------------|--------|----------|----------------|\n")
            
            for i, (_, bank) in enumerate(systemic_banks.head(20).iterrows(), 1):
                f.write(f"| {i} | {bank.get('respondent_name', 'N/A')} | {bank['lei']} | ")
                f.write(f"{bank.get('total_loans', 0):,} | {bank.get('states_count', 0)} | ")
                f.write(f"{bank.get('counties_count', 0)} | {bank.get('systemic_score', 0):.3f} |\n")
            
            # Market Concentration
            if 'market_concentration' in patterns:
                mc = patterns['market_concentration']
                f.write(f"\n## Market Concentration Analysis\n\n")
                f.write(f"**HHI (Herfindahl-Hirschman Index):** {mc.get('hhi', 0):.4f}\n")
                f.write(f"**Concentration Level:** {mc.get('concentration_level', 'Unknown')}\n\n")
            
            # Geographic Analysis
            if 'geography_analysis' in patterns:
                geo = patterns['geography_analysis']
                f.write("## Geographic Distribution\n\n")
                f.write("Analysis of lending patterns across different geographic regions.\n\n")
            
            # Race Analysis
            if 'race_analysis' in patterns:
                f.write("## Lending Patterns by Race\n\n")
                f.write("Analysis of lending patterns across different racial/ethnic groups.\n\n")
            
            f.write("\n---\n")
            f.write("*Report generated by Systemic Banks Analysis Library*\n")


def main():
    """Example usage of the SystemicBanksAnalyzer."""
    print("Systemically Important Banks Analysis")
    print("="*50)
    
    # Initialize analyzer
    analyzer = SystemicBanksAnalyzer()
    
    # Generate report for 2019
    try:
        report_path = analyzer.generate_systemic_bank_report(year=2019, top_n=50)
        print(f"Report generated successfully: {report_path}")
    except Exception as e:
        print(f"Error generating report: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
