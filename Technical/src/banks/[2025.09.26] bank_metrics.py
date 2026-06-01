"""
Bank Metrics and Analysis
========================

This module provides comprehensive metrics and analysis tools for banks
using HMDA data, including market share analysis, lending patterns,
and regulatory compliance metrics.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
import warnings

class BankMetricsCalculator:
    """
    Calculator for comprehensive bank metrics using HMDA data.
    
    This class provides methods to calculate various banking metrics
    including market share, lending patterns, and regulatory indicators.
    """
    
    def __init__(self):
        """Initialize the metrics calculator."""
        self.metrics_cache = {}
    
    def calculate_market_share(self, 
                             hmda_data: pd.DataFrame, 
                             group_by: str = 'lei',
                             metric_cols: List[str] = None) -> pd.DataFrame:
        """
        Calculate market share for banks across different metrics.
        
        Args:
            hmda_data: HMDA dataset
            group_by: Column to group by (default: 'lei' for banks)
            metric_cols: List of metric columns to calculate shares for
            
        Returns:
            DataFrame with market share calculations
        """
        if metric_cols is None:
            metric_cols = [col for col in hmda_data.columns if 'HL_Amt_' in col and 'Total' not in col]
        
        # Calculate totals for each metric
        totals = hmda_data[metric_cols].sum()
        
        # Group by specified column and calculate shares
        market_shares = hmda_data.groupby(group_by)[metric_cols].sum()
        
        # Calculate percentage shares
        for col in metric_cols:
            market_shares[f'{col}_share'] = (market_shares[col] / totals[col] * 100).round(4)
        
        # Add total market share
        market_shares['total_share'] = market_shares[[f'{col}_share' for col in metric_cols]].mean(axis=1)
        
        return market_shares.reset_index()
    
    def calculate_hhi(self, 
                     market_shares: pd.DataFrame, 
                     share_col: str = 'total_share') -> float:
        """
        Calculate Herfindahl-Hirschman Index (HHI) for market concentration.
        
        Args:
            market_shares: DataFrame with market share data
            share_col: Column containing market share percentages
            
        Returns:
            HHI value (0-1 scale)
        """
        # Convert percentages to proportions
        shares = market_shares[share_col] / 100
        
        # Calculate HHI
        hhi = (shares ** 2).sum()
        
        return hhi
    
    def calculate_lending_diversity_index(self, 
                                        hmda_data: pd.DataFrame,
                                        bank_col: str = 'lei',
                                        demographic_cols: List[str] = None) -> pd.DataFrame:
        """
        Calculate lending diversity index for each bank.
        
        Args:
            hmda_data: HMDA dataset
            bank_col: Column identifying banks
            demographic_cols: Columns representing demographic groups
            
        Returns:
            DataFrame with diversity indices
        """
        if demographic_cols is None:
            # Find demographic columns (race, income, etc.)
            demographic_cols = [col for col in hmda_data.columns 
                              if any(demo in col for demo in 
                                   ['Asian', 'Black', 'White', 'Indigenous', 'Other', 'NotAvail', 
                                    'BILow', 'BIMod', 'TILow', 'TIMod'])]
        
        diversity_results = []
        
        for bank in hmda_data[bank_col].unique():
            bank_data = hmda_data[hmda_data[bank_col] == bank]
            
            # Calculate diversity for each demographic dimension
            bank_diversity = {'lei': bank}
            
            for demo_col in demographic_cols:
                if demo_col in bank_data.columns:
                    # Calculate proportion of lending to this demographic group
                    total_lending = bank_data[demo_col].sum()
                    if total_lending > 0:
                        # Calculate entropy-based diversity index
                        proportions = bank_data[demo_col] / total_lending
                        proportions = proportions[proportions > 0]  # Remove zeros
                        entropy = -(proportions * np.log(proportions)).sum()
                        bank_diversity[f'{demo_col}_diversity'] = entropy
                    else:
                        bank_diversity[f'{demo_col}_diversity'] = 0
            
            diversity_results.append(bank_diversity)
        
        return pd.DataFrame(diversity_results)
    
    def calculate_geographic_diversity(self, 
                                     hmda_data: pd.DataFrame,
                                     bank_col: str = 'lei',
                                     geo_col: str = 'county_code') -> pd.DataFrame:
        """
        Calculate geographic diversity of lending for each bank.
        
        Args:
            hmda_data: HMDA dataset
            bank_col: Column identifying banks
            geo_col: Column representing geographic units
            
        Returns:
            DataFrame with geographic diversity metrics
        """
        geo_diversity = []
        
        for bank in hmda_data[bank_col].unique():
            bank_data = hmda_data[hmda_data[bank_col] == bank]
            
            # Count unique geographic units
            unique_geos = bank_data[geo_col].nunique()
            total_loans = len(bank_data)
            
            # Calculate geographic concentration
            geo_counts = bank_data[geo_col].value_counts()
            geo_proportions = geo_counts / total_loans
            
            # Calculate entropy (higher = more diverse)
            entropy = -(geo_proportions * np.log(geo_proportions)).sum()
            
            # Calculate Gini coefficient (lower = more equal distribution)
            gini = self._calculate_gini(geo_proportions.values)
            
            geo_diversity.append({
                'lei': bank,
                'unique_geographies': unique_geos,
                'geographic_entropy': entropy,
                'geographic_gini': gini,
                'concentration_ratio': geo_counts.iloc[0] / total_loans if len(geo_counts) > 0 else 0
            })
        
        return pd.DataFrame(geo_diversity)
    
    def _calculate_gini(self, values: np.ndarray) -> float:
        """Calculate Gini coefficient for inequality measurement."""
        if len(values) == 0:
            return 0
        
        # Sort values
        sorted_values = np.sort(values)
        n = len(sorted_values)
        
        # Calculate Gini coefficient
        cumsum = np.cumsum(sorted_values)
        gini = (n + 1 - 2 * np.sum(cumsum) / cumsum[-1]) / n if cumsum[-1] > 0 else 0
        
        return gini
    
    def calculate_regulatory_metrics(self, 
                                   hmda_data: pd.DataFrame,
                                   bank_col: str = 'lei') -> pd.DataFrame:
        """
        Calculate regulatory compliance and risk metrics.
        
        Args:
            hmda_data: HMDA dataset
            bank_col: Column identifying banks
            
        Returns:
            DataFrame with regulatory metrics
        """
        regulatory_metrics = []
        
        for bank in hmda_data[bank_col].unique():
            bank_data = hmda_data[hmda_data[bank_col] == bank]
            
            # Calculate basic metrics
            total_loans = len(bank_data)
            total_amount = bank_data[[col for col in bank_data.columns if 'HL_Amt_' in col and 'Total' not in col]].sum().sum()
            
            # Calculate average loan size
            avg_loan_size = total_amount / total_loans if total_loans > 0 else 0
            
            # Calculate loan size distribution
            loan_amounts = bank_data[[col for col in bank_data.columns if 'HL_Amt_' in col and 'Total' not in col]].sum(axis=1)
            loan_size_std = loan_amounts.std() if len(loan_amounts) > 1 else 0
            loan_size_cv = loan_size_std / avg_loan_size if avg_loan_size > 0 else 0
            
            # Calculate geographic spread
            unique_counties = bank_data['county_code'].nunique()
            unique_states = bank_data['state_code'].nunique()
            
            regulatory_metrics.append({
                'lei': bank,
                'total_loans': total_loans,
                'total_amount': total_amount,
                'avg_loan_size': avg_loan_size,
                'loan_size_std': loan_size_std,
                'loan_size_cv': loan_size_cv,
                'unique_counties': unique_counties,
                'unique_states': unique_states,
                'geographic_spread': unique_counties * unique_states
            })
        
        return pd.DataFrame(regulatory_metrics)
    
    def calculate_peer_comparison(self, 
                                bank_metrics: pd.DataFrame,
                                target_bank: str,
                                comparison_banks: List[str] = None) -> Dict:
        """
        Compare a target bank against its peers.
        
        Args:
            bank_metrics: DataFrame with bank metrics
            target_bank: LEI of target bank
            comparison_banks: List of peer bank LEIs (if None, uses all others)
            
        Returns:
            Dictionary with peer comparison results
        """
        if target_bank not in bank_metrics['lei'].values:
            raise ValueError(f"Target bank {target_bank} not found in metrics")
        
        target_data = bank_metrics[bank_metrics['lei'] == target_bank].iloc[0]
        
        if comparison_banks is None:
            peer_data = bank_metrics[bank_metrics['lei'] != target_bank]
        else:
            peer_data = bank_metrics[bank_metrics['lei'].isin(comparison_banks)]
        
        comparison = {}
        
        # Compare each metric
        numeric_cols = bank_metrics.select_dtypes(include=[np.number]).columns
        numeric_cols = [col for col in numeric_cols if col != 'lei']
        
        for col in numeric_cols:
            if col in target_data and col in peer_data.columns:
                target_value = target_data[col]
                peer_mean = peer_data[col].mean()
                peer_median = peer_data[col].median()
                peer_std = peer_data[col].std()
                
                # Calculate percentile rank
                percentile = (peer_data[col] <= target_value).mean() * 100
                
                comparison[col] = {
                    'target_value': target_value,
                    'peer_mean': peer_mean,
                    'peer_median': peer_median,
                    'peer_std': peer_std,
                    'percentile_rank': percentile,
                    'vs_mean': (target_value - peer_mean) / peer_std if peer_std > 0 else 0
                }
        
        return comparison
    
    def generate_bank_profile(self, 
                            hmda_data: pd.DataFrame,
                            bank_lei: str,
                            bank_name: str = None) -> Dict:
        """
        Generate comprehensive profile for a specific bank.
        
        Args:
            hmda_data: HMDA dataset
            bank_lei: LEI of the bank
            bank_name: Name of the bank (optional)
            
        Returns:
            Dictionary with comprehensive bank profile
        """
        bank_data = hmda_data[hmda_data['lei'] == bank_lei]
        
        if len(bank_data) == 0:
            raise ValueError(f"Bank {bank_lei} not found in data")
        
        profile = {
            'lei': bank_lei,
            'name': bank_name or bank_data['respondent_name'].iloc[0] if 'respondent_name' in bank_data.columns else 'Unknown',
            'total_records': len(bank_data),
            'analysis_date': pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        # Basic metrics
        profile['basic_metrics'] = self.calculate_regulatory_metrics(hmda_data, 'lei')
        profile['basic_metrics'] = profile['basic_metrics'][profile['basic_metrics']['lei'] == bank_lei].iloc[0].to_dict()
        
        # Market share
        market_shares = self.calculate_market_share(hmda_data, 'lei')
        bank_market_share = market_shares[market_shares['lei'] == bank_lei]
        if len(bank_market_share) > 0:
            profile['market_share'] = bank_market_share.iloc[0].to_dict()
        
        # Geographic diversity
        geo_diversity = self.calculate_geographic_diversity(hmda_data, 'lei')
        bank_geo = geo_diversity[geo_diversity['lei'] == bank_lei]
        if len(bank_geo) > 0:
            profile['geographic_diversity'] = bank_geo.iloc[0].to_dict()
        
        # Lending diversity
        lending_diversity = self.calculate_lending_diversity_index(hmda_data, 'lei')
        bank_lending = lending_diversity[lending_diversity['lei'] == bank_lei]
        if len(bank_lending) > 0:
            profile['lending_diversity'] = bank_lending.iloc[0].to_dict()
        
        return profile


def main():
    """Example usage of BankMetricsCalculator."""
    print("Bank Metrics Calculator")
    print("="*30)
    
    # This would be used with actual HMDA data
    print("This module provides comprehensive bank metrics calculation.")
    print("Use with SystemicBanksAnalyzer for complete analysis.")


if __name__ == "__main__":
    main()
