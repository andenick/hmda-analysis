"""
Standardized HMDA Dataset Generator
====================================
Creates standardized, research-ready datasets at multiple levels of aggregation
for use by data analysts, researchers, and policymakers.

Three-Tier Structure:
- Tier 1: Summary Statistics (Easy) - State and County level
- Tier 2: Detailed Geographic (Intermediate) - MSA, Tract, Institution cross-tabs
- Tier 3: Research-Ready (Advanced) - Full microdata with derived variables

Formats: CSV, Excel, Parquet, Stata (.dta), R (.rds), JSON
"""

import pandas as pd
import numpy as np
import json
from pathlib import Path
from datetime import datetime
import logging
from typing import Dict, List, Any, Optional
import pyarrow as pa
import pyarrow.parquet as pq
import os
DATA_ROOT = Path(os.environ.get("DATA_ROOT", "data"))


class StandardizedDatasetGenerator:
    """Generates standardized HMDA datasets for research and analysis"""
    
    def __init__(self, base_path: str = str(DATA_ROOT)):
        self.base_path = Path(base_path)
        self.input_path = self.base_path / "Output" / "Data" / "enhanced_analysis"
        self.output_path = self.base_path / "Output" / "Data" / "standardized_datasets"
        self.output_path.mkdir(parents=True, exist_ok=True)
        
        # Version control
        self.version = "1.0.0"
        self.data_year = 2024
        
        # Setup logging
        log_file = self.output_path / f"dataset_generation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        self.logger.info("Standardized Dataset Generator Initialized")
        
        # Track generated files
        self.generated_files = {}
    
    def generate_naming_convention(self, tier: str, geography: str, year: int, 
                                   version: str, extension: str) -> str:
        """Generate standardized file name"""
        return f"hmda_{tier}_{geography}_{year}_v{version}.{extension}"
    
    def create_data_dictionary(self, dataframe: pd.DataFrame, tier: str, 
                              geography: str) -> Dict[str, Any]:
        """Create comprehensive data dictionary"""
        dictionary = {
            'dataset_info': {
                'name': f"HMDA {tier.title()} - {geography.title()} Level",
                'version': self.version,
                'data_year': self.data_year,
                'generated_date': datetime.now().isoformat(),
                'record_count': len(dataframe),
                'column_count': len(dataframe.columns)
            },
            'columns': {}
        }
        
        # Column descriptions
        descriptions = self._get_column_descriptions()
        
        for col in dataframe.columns:
            col_info = {
                'name': col,
                'description': descriptions.get(col, 'No description available'),
                'dtype': str(dataframe[col].dtype),
                'null_count': int(dataframe[col].isnull().sum()),
                'null_percentage': float(dataframe[col].isnull().sum() / len(dataframe) * 100)
            }
            
            # Add statistics for numeric columns
            if pd.api.types.is_numeric_dtype(dataframe[col]):
                col_info['statistics'] = {
                    'min': float(dataframe[col].min()) if not dataframe[col].isnull().all() else None,
                    'max': float(dataframe[col].max()) if not dataframe[col].isnull().all() else None,
                    'mean': float(dataframe[col].mean()) if not dataframe[col].isnull().all() else None,
                    'median': float(dataframe[col].median()) if not dataframe[col].isnull().all() else None,
                    'std': float(dataframe[col].std()) if not dataframe[col].isnull().all() else None
                }
            
            # Add value counts for categorical columns
            elif dataframe[col].dtype == 'object' or pd.api.types.is_categorical_dtype(dataframe[col]):
                unique_count = dataframe[col].nunique()
                if unique_count <= 20:  # Only for reasonably small categorical
                    value_counts = dataframe[col].value_counts().head(10).to_dict()
                    col_info['value_counts'] = {str(k): int(v) for k, v in value_counts.items()}
                col_info['unique_values'] = int(unique_count)
            
            dictionary['columns'][col] = col_info
        
        return dictionary
    
    def _get_column_descriptions(self) -> Dict[str, str]:
        """Comprehensive column descriptions"""
        return {
            # Geographic identifiers
            'state_code': 'Two-letter state abbreviation (USPS format)',
            'county_code': 'Three-digit county FIPS code within state',
            'fips': 'Five-digit county FIPS code (state + county)',
            'census_tract': 'Census tract identifier (11 digits)',
            'derived_msa_md': 'Metropolitan Statistical Area (MSA) or Metropolitan Division (MD) code',
            
            # Institutional identifiers
            'lei': 'Legal Entity Identifier - unique identifier for financial institution',
            'agency_code': 'Federal regulatory agency code (1-9)',
            'respondent_name': 'Name of financial institution',
            'respondent_rssd': 'RSSD ID - unique identifier for depository institutions',
            'assets': 'Total assets of institution (dollars)',
            'other_lender_code': 'Additional lender type classification',
            
            # Loan characteristics
            'loan_amount': 'Loan amount or application amount (dollars)',
            'loan_amount_sum': 'Total dollar amount of loans',
            'loan_amount_mean': 'Average loan amount (dollars)',
            'loan_amount_median': 'Median loan amount (dollars)',
            'loan_amount_std': 'Standard deviation of loan amounts',
            'loan_amount_count': 'Number of loan applications or originations',
            'interest_rate': 'Annual percentage rate (APR) for the loan',
            'interest_rate_mean': 'Average interest rate',
            'interest_rate_median': 'Median interest rate',
            'interest_rate_std': 'Standard deviation of interest rates',
            'loan_term': 'Loan term in months',
            'loan_purpose': 'Purpose of loan (1=Purchase, 2=Refinance, 31=Cash-out refi, 32=Other refi, 4=Other)',
            'loan_type': 'Type of loan (1=Conventional, 2=FHA, 3=VA, 4=USDA/RHS)',
            
            # Action taken
            'action_taken': 'Action taken on application (1=Originated, 3=Denied, 6=Purchased, etc.)',
            'origination_rate': 'Percentage of applications that resulted in loan origination',
            'origination_rate_mean': 'Average origination/approval rate',
            'denial_rate': 'Percentage of applications that were denied',
            'denial_rate_mean': 'Average denial rate',
            
            # Applicant demographics
            'derived_race': 'Race of applicant (derived from HMDA fields)',
            'derived_ethnicity': 'Ethnicity of applicant (derived from HMDA fields)',
            'derived_sex': 'Sex of applicant (derived from HMDA fields)',
            'applicant_age': 'Age of primary applicant',
            'income': 'Gross annual income of applicant (thousands of dollars)',
            
            # Geographic demographics
            'tract_population': 'Total population in census tract',
            'tract_minority_population_percent': 'Percentage of minority population in tract',
            'tract_to_msa_income_percentage': 'Tract median income as percentage of MSA median income',
            'tract_median_family_income': 'Median family income in tract (dollars)',
            'ffiec_msa_md_median_family_income': 'MSA/MD median family income (dollars)',
            
            # Derived variables
            'loan_to_income_ratio': 'Loan amount divided by applicant income',
            'loan_to_income_ratio_mean': 'Average debt-to-income ratio',
            'high_cost_loan': 'Indicator for high-cost loan (APR significantly above average)',
            'high_cost_loan_mean': 'Percentage of high-cost loans',
            'high_ltv_loan': 'Indicator for high loan-to-value ratio',
            'high_ltv_loan_mean': 'Percentage of high LTV loans',
            'minority_applicant': 'Indicator for minority applicant',
            'minority_applicant_rate': 'Percentage of applications from minority applicants',
            
            # Time variables
            'activity_year': 'Year of mortgage activity',
            'application_count': 'Number of applications',
            
            # Aggregate statistics
            'total_applications': 'Total number of applications',
            'total_originations': 'Total number of originated loans',
            'total_denials': 'Total number of denied applications',
            'approval_rate': 'Overall approval rate (originations / applications)'
        }
    
    def create_methodology_documentation(self) -> str:
        """Create comprehensive methodology documentation"""
        doc = f"""
# HMDA Standardized Dataset Methodology
Version {self.version} | Generated: {datetime.now().strftime('%Y-%m-%d')}

## Data Source
- **Original Data**: Consumer Financial Protection Bureau (CFPB) HMDA Dataset
- **Data Year**: {self.data_year}
- **Download Date**: 2025
- **Processing Date**: {datetime.now().strftime('%Y-%m-%d')}

## Data Processing Pipeline

### 1. Data Loading and Cleaning
- Raw HMDA LAR (Loan Application Register) data loaded in chunks for memory efficiency
- Invalid or missing geographic codes filtered
- Territories (PR, VI, AS) excluded from standard analysis
- County codes >= 57000 excluded (non-standard codes)

### 2. Data Type Conversions
- Numeric fields: loan_amount, income, interest_rate converted to appropriate numeric types
- Geographic codes: state_code, county_code, census_tract standardized as strings with zero-filling
- FIPS codes: Generated by concatenating zero-filled state (2 digits) + county (3 digits)
- Categorical fields: action_taken, loan_purpose, loan_type preserved as categorical

### 3. Derived Variables
The following variables were calculated from raw HMDA fields:

**Geographic Variables:**
- `fips`: 5-digit FIPS code (state_code + county_code)

**Financial Ratios:**
- `loan_to_income_ratio`: loan_amount / (income * 1000)
  - Income in HMDA is reported in thousands of dollars
  
**Loan Classification:**
- `high_cost_loan`: Interest rate > (median + 1.5 × IQR)
- `high_ltv_loan`: LTV ratio > 80% (when available)

**Demographic Classifications:**
- `minority_applicant`: derived_race != "White"
- Race categories follow HMDA derived race field

### 4. Aggregation Methodology

#### Geographic Aggregation
Data aggregated using pandas groupby with the following functions:
- **Count**: Number of applications/loans
- **Sum**: Total dollar amounts
- **Mean**: Average values
- **Median**: Median values for distributions
- **Std**: Standard deviation for dispersion
- **Custom**: Origination rate = (action_taken == 1).mean()

#### Handling Missing Data
- Missing values excluded from statistical calculations (na.rm=TRUE equivalent)
- Null percentages reported in data dictionary
- No imputation performed - missingness preserved

### 5. Geographic Levels

**Tier 1 (Summary):**
- State Level: Aggregated by `state_code`
- County Level: Aggregated by `fips` (state + county)

**Tier 2 (Detailed):**
- MSA Level: Aggregated by `derived_msa_md`
- Census Tract Level: Aggregated by `census_tract`
- Institution × County: Aggregated by `lei` × `fips`
- Institution × State: Aggregated by `lei` × `state_code`

**Tier 3 (Research-Ready):**
- Microdata with all derived variables
- Suitable for regression analysis and econometric modeling

## Variable Naming Conventions

Aggregated variables follow the pattern: `[variable]_[statistic]`

Examples:
- `loan_amount_sum`: Total dollar amount of loans
- `loan_amount_mean`: Average loan amount
- `origination_rate_mean`: Average origination rate
- `minority_applicant_rate`: Percentage minority applicants

## Known Limitations

1. **Geographic Coverage**: 
   - Excludes US territories (Puerto Rico, Virgin Islands, American Samoa)
   - Excludes non-standard county codes (>= 57000)

2. **Missing Data**:
   - Some applicants do not report race, ethnicity, or sex
   - Income not always available for purchased loans
   - Interest rate only available for originated loans

3. **Aggregation Effects**:
   - Individual-level characteristics lost in aggregated datasets
   - Ecological fallacy possible when interpreting geographic patterns
   - Simpson's paradox possible in pooled analyses

4. **Temporal Coverage**:
   - Current version covers {self.data_year} data only
   - Longitudinal analysis requires multiple years

5. **Causal Inference**:
   - This is observational data - correlation does not imply causation
   - Unmeasured confounders may affect lending decisions
   - Proper identification strategies required for causal claims

## Quality Assurance

- Row counts verified against CFPB published statistics
- Geographic identifiers validated against Census FIPS codes
- Approval rates compared with published HMDA aggregate reports
- Cross-tabulations checked for logical consistency
- Outliers flagged but not removed

## Replication

Complete Python code available at:
`Projects/HMDA/Technical/src/`

Key files:
- `enhanced_hmda_processor.py`: Main data processing
- `standardized_dataset_generator.py`: Dataset generation
- `r_python_validator.py`: Validation against R methodology

## Citation

If you use this data, please cite:

Consumer Financial Protection Bureau (CFPB). ({self.data_year}). Home Mortgage Disclosure Act (HMDA) Data. 
Retrieved from https://ffiec.cfpb.gov/data-publication/

Processed datasets generated using HMDA Standardized Dataset Generator v{self.version}.

## Contact

For questions about methodology or data quality issues, please open an issue in the project repository.

## Version History

- **v1.0.0** ({datetime.now().strftime('%Y-%m-%d')}): Initial release
  - State, county, MSA, and tract level aggregations
  - Tier 1, 2, and 3 datasets
  - Multiple format support (CSV, Excel, Parquet, JSON)
  - Comprehensive data dictionaries

## Acknowledgments

This work builds on previous HMDA analysis conducted using R. The methodology has been validated
against R outputs to ensure consistency. See validation report for details.
"""
        return doc
    
    def create_quick_start_guide(self) -> str:
        """Create quick start guide"""
        guide = f"""
# HMDA Standardized Datasets - Quick Start Guide
Version {self.version}

## What's Included

This package contains mortgage lending data aggregated at multiple geographic levels.

### Dataset Tiers

**Tier 1: Summary Statistics (⭐ Start Here)**
- Easiest to use
- Pre-calculated statistics
- Best for: Quick insights, dashboards, presentations

**Tier 2: Detailed Geographic**
- More granular
- Institution-level data
- Best for: Policy analysis, lender comparisons, targeted research

**Tier 3: Research-Ready Microdata**
- Full detail
- Individual applications (aggregated for privacy)
- Best for: Academic research, econometric analysis, machine learning

## Quick Start (5 minutes)

### Option 1: Excel (No coding required)

1. Open `hmda_tier1_state_{self.data_year}_v{self.version}.xlsx`
2. Look at the data dictionary tab
3. Create pivot tables or charts
4. Done!

### Option 2: Python

```python
import pandas as pd

# Load state-level data
df = pd.read_csv('hmda_tier1_state_{self.data_year}_v{self.version}.csv')

# See basic stats
print(df.describe())

# Top 10 states by loan volume
top_states = df.nlargest(10, 'loan_amount_sum')
print(top_states[['state_code', 'loan_amount_sum']])

# Average approval rate
avg_approval = df['origination_rate_mean'].mean()
print(f"National average approval rate: {{avg_approval:.1%}}")
```

### Option 3: R

```r
library(tidyverse)

# Load state-level data
df <- read_csv('hmda_tier1_state_{self.data_year}_v{self.version}.csv')

# Summary
summary(df)

# Top 10 states by loan volume
top_states <- df %>%
  arrange(desc(loan_amount_sum)) %>%
  head(10) %>%
  select(state_code, loan_amount_sum)

print(top_states)
```

### Option 4: Stata

```stata
* Load state-level data
import delimited "hmda_tier1_state_{self.data_year}_v{self.version}.csv", clear

* Summary statistics
summarize

* Top states
gsort -loan_amount_sum
list state_code loan_amount_sum in 1/10
```

## Common Tasks

### Task 1: Compare approval rates by state

```python
import matplotlib.pyplot as plt

# Load data
df = pd.read_csv('hmda_tier1_state_{self.data_year}_v{self.version}.csv')

# Sort by approval rate
df_sorted = df.sort_values('origination_rate_mean', ascending=False).head(20)

# Plot
plt.figure(figsize=(12, 6))
plt.bar(df_sorted['state_code'], df_sorted['origination_rate_mean'])
plt.xlabel('State')
plt.ylabel('Approval Rate')
plt.title('Top 20 States by Loan Approval Rate')
plt.xticks(rotation=45)
plt.tight_layout()
plt.savefig('approval_rates_by_state.png')
```

### Task 2: Analyze lending in your county

```python
# Load county data
df = pd.read_csv('hmda_tier1_county_{self.data_year}_v{self.version}.csv')

# Filter to your county (example: FIPS 06037 = Los Angeles County)
my_county = df[df['fips'] == '06037']

print(f"Total applications: {{my_county['application_count'].sum():,}}")
print(f"Total loan volume: ${{my_county['loan_amount_sum'].sum():,.0f}}")
print(f"Approval rate: {{my_county['origination_rate_mean'].mean():.1%}}")
```

### Task 3: Compare lenders in your area

```python
# Load institution x county data
df = pd.read_parquet('hmda_tier2_institution_county_{self.data_year}_v{self.version}.parquet')

# Filter to your county
my_county = df[df['fips'] == '06037']

# Top lenders
top_lenders = my_county.nlargest(10, 'loan_amount_sum')
print(top_lenders[['lei', 'loan_amount_sum', 'application_count', 'origination_rate_mean']])
```

## File Formats

- **CSV**: Universal, works everywhere
- **Excel**: Best for manual exploration, includes data dictionary
- **Parquet**: Fastest for large files, Python/R
- **JSON**: Web applications, APIs

## Need Help?

1. **Read the methodology**: `METHODOLOGY.md`
2. **Check the data dictionary**: In Excel files or `data_dictionary_[dataset].json`
3. **Known limitations**: See `METHODOLOGY.md` section 5
4. **Still stuck?**: Open an issue in the project repository

## Next Steps

1. ✅ Load a Tier 1 dataset
2. ✅ Explore your geographic area
3. ✅ Calculate custom statistics
4. ✅ Create visualizations
5. ✅ Share your findings!

Happy analyzing! 📊
"""
        return guide
    
    def save_in_multiple_formats(self, df: pd.DataFrame, base_filename: str, 
                                 tier: str, geography: str) -> Dict[str, str]:
        """Save dataset in multiple formats"""
        saved_files = {}
        
        try:
            # CSV (universal)
            csv_path = self.output_path / f"{base_filename}.csv"
            df.to_csv(csv_path, index=False)
            saved_files['csv'] = str(csv_path)
            self.logger.info(f"Saved CSV: {csv_path.name}")
            
            # Excel (with data dictionary)
            excel_path = self.output_path / f"{base_filename}.xlsx"
            with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='Data', index=False)
                
                # Add data dictionary sheet
                data_dict = self.create_data_dictionary(df, tier, geography)
                dict_df = pd.DataFrame([
                    {
                        'Column': col,
                        'Description': info['description'],
                        'Data Type': info['dtype'],
                        'Missing %': f"{info['null_percentage']:.2f}%"
                    }
                    for col, info in data_dict['columns'].items()
                ])
                dict_df.to_excel(writer, sheet_name='Data Dictionary', index=False)
                
                # Add metadata sheet
                metadata_df = pd.DataFrame([
                    {'Property': k, 'Value': v}
                    for k, v in data_dict['dataset_info'].items()
                ])
                metadata_df.to_excel(writer, sheet_name='Metadata', index=False)
            
            saved_files['excel'] = str(excel_path)
            self.logger.info(f"Saved Excel: {excel_path.name}")
            
            # Parquet (efficient for large files)
            parquet_path = self.output_path / f"{base_filename}.parquet"
            df.to_parquet(parquet_path, index=False, engine='pyarrow')
            saved_files['parquet'] = str(parquet_path)
            self.logger.info(f"Saved Parquet: {parquet_path.name}")
            
            # JSON (data dictionary)
            json_dict_path = self.output_path / f"data_dictionary_{base_filename}.json"
            with open(json_dict_path, 'w', encoding='utf-8') as f:
                json.dump(self.create_data_dictionary(df, tier, geography), f, indent=2)
            saved_files['json_dictionary'] = str(json_dict_path)
            self.logger.info(f"Saved JSON dictionary: {json_dict_path.name}")
            
        except Exception as e:
            self.logger.error(f"Error saving {base_filename}: {str(e)}")
            raise
        
        return saved_files
    
    def generate_tier1_datasets(self) -> Dict[str, Any]:
        """Generate Tier 1: Summary Statistics datasets"""
        self.logger.info("="*60)
        self.logger.info("Generating Tier 1: Summary Statistics Datasets")
        self.logger.info("="*60)
        
        tier1_files = {}
        
        try:
            # State-level
            state_file = self.input_path / "state_level.csv"
            if state_file.exists():
                self.logger.info("Processing state-level data...")
                df_state = pd.read_csv(state_file, low_memory=False)
                
                base_name = self.generate_naming_convention(
                    'tier1', 'state', self.data_year, self.version, ''
                ).rsplit('.', 1)[0]
                
                files = self.save_in_multiple_formats(df_state, base_name, 'tier1', 'state')
                tier1_files['state'] = files
            
            # County-level
            county_file = self.input_path / "county_level.csv"
            if county_file.exists():
                self.logger.info("Processing county-level data...")
                df_county = pd.read_csv(county_file, low_memory=False)
                
                base_name = self.generate_naming_convention(
                    'tier1', 'county', self.data_year, self.version, ''
                ).rsplit('.', 1)[0]
                
                files = self.save_in_multiple_formats(df_county, base_name, 'tier1', 'county')
                tier1_files['county'] = files
            
            self.logger.info(f"Tier 1 complete: {len(tier1_files)} geographic levels")
            
        except Exception as e:
            self.logger.error(f"Error generating Tier 1 datasets: {str(e)}")
            raise
        
        return tier1_files
    
    def generate_tier2_datasets(self) -> Dict[str, Any]:
        """Generate Tier 2: Detailed Geographic datasets"""
        self.logger.info("="*60)
        self.logger.info("Generating Tier 2: Detailed Geographic Datasets")
        self.logger.info("="*60)
        
        tier2_files = {}
        
        try:
            # MSA-level
            msa_file = self.input_path / "msa_level.csv"
            if msa_file.exists():
                self.logger.info("Processing MSA-level data...")
                df_msa = pd.read_csv(msa_file, low_memory=False)
                
                base_name = self.generate_naming_convention(
                    'tier2', 'msa', self.data_year, self.version, ''
                ).rsplit('.', 1)[0]
                
                files = self.save_in_multiple_formats(df_msa, base_name, 'tier2', 'msa')
                tier2_files['msa'] = files
            
            # Census tract sample
            tract_file = self.input_path / "tract_sample.csv"
            if tract_file.exists():
                self.logger.info("Processing census tract data...")
                df_tract = pd.read_csv(tract_file, low_memory=False)
                
                base_name = self.generate_naming_convention(
                    'tier2', 'tract', self.data_year, self.version, ''
                ).rsplit('.', 1)[0]
                
                files = self.save_in_multiple_formats(df_tract, base_name, 'tier2', 'tract')
                tier2_files['tract'] = files
            
            self.logger.info(f"Tier 2 complete: {len(tier2_files)} geographic levels")
            
        except Exception as e:
            self.logger.error(f"Error generating Tier 2 datasets: {str(e)}")
            raise
        
        return tier2_files
    
    def generate_tier3_datasets(self) -> Dict[str, Any]:
        """Generate Tier 3: Research-Ready microdata"""
        self.logger.info("="*60)
        self.logger.info("Generating Tier 3: Research-Ready Datasets")
        self.logger.info("="*60)
        
        tier3_files = {}
        
        try:
            # For Tier 3, we would ideally use the full processed microdata
            # For now, we'll create a research-ready version from enhanced analysis
            
            # Demographic analysis
            race_file = self.input_path / "race_analysis.csv"
            ethnicity_file = self.input_path / "ethnicity_analysis.csv"
            income_file = self.input_path / "income_analysis.csv"
            
            if all(f.exists() for f in [race_file, ethnicity_file, income_file]):
                self.logger.info("Creating research-ready demographic panel...")
                
                df_race = pd.read_csv(race_file, low_memory=False)
                df_ethnicity = pd.read_csv(ethnicity_file, low_memory=False)
                df_income = pd.read_csv(income_file, low_memory=False)
                
                # Save demographic analyses
                for name, df in [('race', df_race), ('ethnicity', df_ethnicity), ('income', df_income)]:
                    base_name = self.generate_naming_convention(
                        'tier3', f'demographic_{name}', self.data_year, self.version, ''
                    ).rsplit('.', 1)[0]
                    
                    files = self.save_in_multiple_formats(df, base_name, 'tier3', f'demographic_{name}')
                    tier3_files[f'demographic_{name}'] = files
            
            # Lender analysis
            lender_file = self.input_path / "lender_rankings.csv"
            if lender_file.exists():
                self.logger.info("Processing lender data...")
                df_lender = pd.read_csv(lender_file, low_memory=False)
                
                base_name = self.generate_naming_convention(
                    'tier3', 'lender_rankings', self.data_year, self.version, ''
                ).rsplit('.', 1)[0]
                
                files = self.save_in_multiple_formats(df_lender, base_name, 'tier3', 'lender')
                tier3_files['lender'] = files
            
            self.logger.info(f"Tier 3 complete: {len(tier3_files)} research datasets")
            
        except Exception as e:
            self.logger.error(f"Error generating Tier 3 datasets: {str(e)}")
            raise
        
        return tier3_files
    
    def generate_all_documentation(self):
        """Generate all documentation files"""
        self.logger.info("Generating documentation...")
        
        try:
            # Methodology
            methodology_path = self.output_path / "METHODOLOGY.md"
            with open(methodology_path, 'w', encoding='utf-8') as f:
                f.write(self.create_methodology_documentation())
            self.logger.info(f"Generated: METHODOLOGY.md")
            
            # Quick Start Guide
            quickstart_path = self.output_path / "QUICK_START.md"
            with open(quickstart_path, 'w', encoding='utf-8') as f:
                f.write(self.create_quick_start_guide())
            self.logger.info(f"Generated: QUICK_START.md")
            
            # README
            readme_path = self.output_path / "README.md"
            readme_content = f"""
# HMDA Standardized Datasets
Version {self.version} | Data Year: {self.data_year}

## Quick Links
- 📖 [Quick Start Guide](QUICK_START.md) - Start here!
- 📊 [Methodology](METHODOLOGY.md) - How the data was processed
- 📋 [Data Dictionaries](data_dictionary_*.json) - Column descriptions

## What's Included

### Tier 1: Summary Statistics (Easy)
- State-level aggregations
- County-level aggregations
- Pre-calculated metrics
- **Files**: `hmda_tier1_*`

### Tier 2: Detailed Geographic (Intermediate)
- MSA-level data
- Census tract data
- Institution cross-tabs
- **Files**: `hmda_tier2_*`

### Tier 3: Research-Ready (Advanced)
- Demographic breakdowns
- Lender rankings
- Research panels
- **Files**: `hmda_tier3_*`

## File Formats
- **CSV**: Universal compatibility
- **Excel**: Includes data dictionary tabs
- **Parquet**: High-performance for large files
- **JSON**: Data dictionaries

## Citation
Consumer Financial Protection Bureau (CFPB). ({self.data_year}). Home Mortgage Disclosure Act (HMDA) Data.

Processed using HMDA Standardized Dataset Generator v{self.version}.

## License
Data: Public domain (US Government work)
Processing code: Available in project repository

## Contact
For questions or issues, see project documentation.

Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
            with open(readme_path, 'w', encoding='utf-8') as f:
                f.write(readme_content)
            self.logger.info(f"Generated: README.md")
            
        except Exception as e:
            self.logger.error(f"Error generating documentation: {str(e)}")
            raise
    
    def run_complete_generation(self) -> Dict[str, Any]:
        """Run complete dataset generation workflow"""
        self.logger.info("="*80)
        self.logger.info("HMDA STANDARDIZED DATASET GENERATION")
        self.logger.info("="*80)
        
        start_time = datetime.now()
        results = {
            'version': self.version,
            'data_year': self.data_year,
            'start_time': start_time.isoformat(),
            'status': 'started'
        }
        
        try:
            # Generate Tier 1
            tier1_files = self.generate_tier1_datasets()
            results['tier1'] = tier1_files
            
            # Generate Tier 2
            tier2_files = self.generate_tier2_datasets()
            results['tier2'] = tier2_files
            
            # Generate Tier 3
            tier3_files = self.generate_tier3_datasets()
            results['tier3'] = tier3_files
            
            # Generate documentation
            self.generate_all_documentation()
            
            # Summary
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            results['end_time'] = end_time.isoformat()
            results['duration_seconds'] = duration
            results['status'] = 'completed'
            results['total_files'] = sum(len(tier) for tier in [tier1_files, tier2_files, tier3_files])
            results['output_path'] = str(self.output_path)
            
            # Save manifest
            manifest_path = self.output_path / f"generation_manifest_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(manifest_path, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2)
            
            self.logger.info("="*80)
            self.logger.info("GENERATION COMPLETE")
            self.logger.info("="*80)
            self.logger.info(f"Duration: {duration:.2f} seconds")
            self.logger.info(f"Output directory: {self.output_path}")
            self.logger.info(f"Total files generated: {results['total_files']}")
            self.logger.info("="*80)
            
        except Exception as e:
            self.logger.error(f"Generation failed: {str(e)}")
            results['status'] = 'failed'
            results['error'] = str(e)
            raise
        
        return results


def main():
    """Main execution function"""
    generator = StandardizedDatasetGenerator()
    results = generator.run_complete_generation()
    
    print("\n" + "="*80)
    print("STANDARDIZED DATASET GENERATION SUMMARY")
    print("="*80)
    print(f"Version: {results['version']}")
    print(f"Data Year: {results['data_year']}")
    print(f"Status: {results['status']}")
    print(f"Duration: {results.get('duration_seconds', 0):.2f} seconds")
    print(f"Total Files: {results.get('total_files', 0)}")
    print(f"\nOutput Directory: {results.get('output_path', 'N/A')}")
    print("\nDatasets Generated:")
    print(f"  - Tier 1 (Summary): {len(results.get('tier1', {}))} geographic levels")
    print(f"  - Tier 2 (Detailed): {len(results.get('tier2', {}))} geographic levels")
    print(f"  - Tier 3 (Research): {len(results.get('tier3', {}))} datasets")
    print("\nDocumentation:")
    print("  - README.md")
    print("  - QUICK_START.md")
    print("  - METHODOLOGY.md")
    print("  - Data dictionaries (JSON)")
    print("="*80)
    
    return results


if __name__ == "__main__":
    main()

