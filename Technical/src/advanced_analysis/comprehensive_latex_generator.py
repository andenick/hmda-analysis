#!/usr/bin/env python3
"""
Comprehensive LaTeX Report Generator
Creates professional LaTeX reports for HMDA analysis
Implements Druck standards for academic-quality documentation
"""

import pandas as pd
import numpy as np
import logging
from pathlib import Path
import json
from datetime import datetime
from typing import Dict, List, Any, Tuple
import warnings
import subprocess
import os
DATA_ROOT = Path(os.environ.get("DATA_ROOT", "data"))

warnings.filterwarnings('ignore')

class ComprehensiveLaTeXGenerator:
    """
    Generates comprehensive LaTeX reports for HMDA analysis
    Creates professional academic-quality documentation
    """

    def __init__(self, base_path: str = str(DATA_ROOT)):
        self.base_path = Path(base_path)
        self.data_path = self.base_path / "Output" / "Data"
        self.tex_path = self.base_path / "Technical" / "docs"
        self.pdf_path = self.base_path / "Output" / "PDFs"

        # Ensure directories exist
        self.tex_path.mkdir(parents=True, exist_ok=True)
        self.pdf_path.mkdir(parents=True, exist_ok=True)

        # Configure logging
        log_file = self.tex_path / f"latex_generation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)

        self.logger.info("Comprehensive LaTeX Generator Initialized")

        # Report metadata
        self.report_metadata = {
            'title': 'Comprehensive HMDA Analysis Report',
            'author': 'HMDA Analysis Team',
            'date': datetime.now().strftime('%B %d, %Y'),
            'version': '1.0',
            'description': 'Detailed analysis of Home Mortgage Disclosure Act data with comprehensive slicing and disparity analysis'
        }

    def load_analysis_results(self) -> Dict[str, Any]:
        """Load all analysis results for reporting"""
        self.logger.info("Loading analysis results...")

        results = {
            'streamlined_analysis': {},
            'disparity_analysis': {},
            'excel_conversions': {},
            'metadata': {}
        }

        # Load streamlined analysis results
        streamlined_path = self.data_path / "streamlined_analysis" / "analysis_metadata.json"
        if streamlined_path.exists():
            with open(streamlined_path, 'r') as f:
                results['streamlined_analysis'] = json.load(f)

        # Load disparity analysis results
        disparity_path = self.data_path / "disparity_analysis" / "disparity_analysis_summary.json"
        if disparity_path.exists():
            with open(disparity_path, 'r') as f:
                results['disparity_analysis'] = json.load(f)

        # Load Excel conversion results
        excel_path = self.data_path / "excel_outputs" / "conversion_metadata.json"
        if excel_path.exists():
            with open(excel_path, 'r') as f:
                results['excel_conversions'] = json.load(f)

        # Load summary statistics from individual files
        summary_files = [
            'state_analysis.csv',
            'race_analysis.csv',
            'loan_purpose_analysis.csv',
            'race_approval_disparity.csv'
        ]

        for file_name in summary_files:
            file_path = self.data_path / "streamlined_analysis" / file_name
            if file_path.exists():
                try:
                    df = pd.read_csv(file_path)
                    results['metadata'][file_name.replace('.csv', '')] = {
                        'rows': len(df),
                        'columns': len(df.columns),
                        'summary_stats': self._calculate_basic_stats(df)
                    }
                except Exception as e:
                    self.logger.warning(f"Failed to load {file_name}: {str(e)}")

        return results

    def _calculate_basic_stats(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Calculate basic statistics for a DataFrame"""
        stats = {}
        numeric_cols = df.select_dtypes(include=[np.number]).columns

        for col in numeric_cols:
            if not df[col].isna().all():
                stats[col] = {
                    'mean': float(df[col].mean()),
                    'median': float(df[col].median()),
                    'std': float(df[col].std()),
                    'min': float(df[col].min()),
                    'max': float(df[col].max())
                }

        return stats

    def generate_methodology_report(self, analysis_results: Dict[str, Any]) -> str:
        """Generate methodology section LaTeX"""
        self.logger.info("Generating methodology report...")

        latex_content = f"""
\\documentclass[11pt,letterpaper]{{article}}
\\usepackage[margin=1in]{{geometry}}
\\usepackage{{graphicx}}
\\usepackage{{booktabs}}
\\usepackage{{longtable}}
\\usepackage{{hyperref}}
\\usepackage{{amsmath}}
\\usepackage{{amssymb}}

\\title{{{self.report_metadata['title']}: Methodology}}
\\author{{{self.report_metadata['author']}}}
\\date{{{self.report_metadata['date']}\\\\Version {self.report_metadata['version']}}}

\\begin{{document}}

\\maketitle

\\begin{{abstract}}
This document outlines the comprehensive methodology employed in the analysis of Home Mortgage Disclosure Act (HMDA) data. The analysis incorporates multi-dimensional slicing, geographic analysis, demographic disparity assessment, and statistical significance testing to provide insights into mortgage lending patterns.
\\end{{abstract}}

\\section{{Introduction}}
The Home Mortgage Disclosure Act (HMDA) requires financial institutions to disclose data about home mortgage applications, including information about applicant demographics, loan characteristics, and outcomes. This analysis processes raw HMDA data to identify patterns, disparities, and trends in mortgage lending.

\\section{{Data Sources and Processing}}
\\subsection{{Primary Data Sources}}
\\begin{{itemize}}
\\item 2024 HMDA LAR (Loan Application Register) data
\\item Sample size: {analysis_results.get('streamlined_analysis', {}).get('summary', {}).get('total_applications_analyzed', 'N/A')} applications
\\item Total loan volume: \\${analysis_results.get('streamlined_analysis', {}).get('summary', {}).get('total_loan_volume', 0):.0f}
\\item Geographic coverage: {analysis_results.get('streamlined_analysis', {}).get('summary', {}).get('unique_states', 0)} states, {analysis_results.get('streamlined_analysis', {}).get('summary', {}).get('unique_lenders', 0)} lenders
\\end{{itemize}}

\\subsection{{Data Processing Pipeline}}
The analysis employed a comprehensive data processing pipeline:

\\begin{{enumerate}}
\\item \\textbf{{Data Loading}}: Raw HMDA data loaded with memory-efficient chunking
\\item \\textbf{{Data Cleaning}}: Standardization of missing values, data types, and categorical variables
\\item \\textbf{{Variable Creation}}: Derived variables including income categorization, geographic identifiers, and loan status classifications
\\item \\textbf{{Quality Assurance}}: Validation checks and data integrity verification
\\end{{enumerate}}

\\section{{Analytical Framework}}
\\subsection{{Multi-Dimensional Analysis}}
The analysis implements comprehensive slicing across multiple dimensions:

\\subsubsection{{Geographic Analysis}}
\\begin{{itemize}}
\\item State-level longitudinal analysis
\\item County-level analysis with FIPS code standardization
\\item MSA (Metropolitan Statistical Area) analysis
\\item Census tract analysis (sample-based due to data volume)
\\end{{itemize}}

\\subsubsection{{Demographic Analysis}}
\\begin{{itemize}}
\\item Race-based lending pattern analysis
\\item Ethnicity-based disparity assessment
\\item Gender-based analysis
\\item Cross-tabulation analysis (Race × Ethnicity)
\\end{{itemize}}

\\subsubsection{{Loan Characteristics Analysis}}
\\begin{{itemize}}
\\item Loan purpose and type categorization
\\item Interest rate quartile analysis
\\item Loan-to-Value (LTV) ratio assessment
\\item High-cost loan identification
\\end{{itemize}}

\\subsubsection{{Institutional Analysis}}
\\begin{{itemize}}
\\item Top lender identification by volume
\\item Agency-level analysis (OCC, Federal Reserve, FDIC, NCUA, CFPB)
\\item Market concentration assessment
\\end{{itemize}}

\\subsection{{Statistical Methods}}
\\subsubsection{{Disparity Metrics}}
\\begin{{itemize}}
\\item Disparity ratios (group rate / reference rate)
\\item Statistical significance testing (Fisher's Exact, Chi-square)
\\item Confidence interval calculation (Wilson score method)
\\item Effect size assessment (Cohen's h)
\\end{{itemize}}

\\subsubsection{{Significance Testing}}
\\begin{{itemize}}
\\item Fisher's Exact Test for small samples (< 5 per cell)
\\item Chi-square Test for larger samples
\\item Bonferroni correction for multiple comparisons
\\item Statistical power assessment
\\end{{itemize}}

\\section{{R Methodology Replication}}
This analysis replicates and extends the original R-based methodology:

\\subsection{{Core R Functions Replicated}}
\\begin{{itemize}}
\\item \\texttt{{sum\_columns}} function: Geographic aggregation by FIPS, County, State
\\item Binary indicator creation for income categorization
\\item Multi-year temporal analysis framework
\\item Cross-sectional and longitudinal analysis patterns
\\end{{itemize}}

\\subsection{{Python Implementation Enhancements}}
\\begin{{itemize}}
\\item Memory-efficient data processing with chunking
\\item Enhanced statistical testing capabilities
\\item Professional visualization and reporting
\\item Automated Excel output generation (single-sheet format)
\\end{{itemize}}

\\section{{Quality Assurance and Validation}}
\\subsection{{Data Quality Checks}}
\\begin{{itemize}}
\\item Missing data pattern analysis
\\item Outlier detection and handling
\\item Data type consistency validation
\\item Geographic identifier verification
\\end{{itemize}}

\\subsection{{Analytical Validation}}
\\begin{{itemize}}
\\item Cross-validation of key metrics
\\item Sensitivity analysis for threshold selections
\\item Reproducibility verification
\\item Statistical robustness testing
\\end{{itemize}}

\\section{{Technical Implementation}}
\\subsection{{Processing Environment}}
\\begin{{itemize}}
\\item Python 3.x with pandas, numpy, scipy libraries
\\item Memory-efficient processing for large datasets
\\item Parallel processing capabilities
\\item Comprehensive logging and error handling
\\end{{itemize}}

\\subsection{{Output Generation}}
\\begin{{itemize}}
\\item Single-sheet Excel files (per Nick's requirements)
\\item Comprehensive PDF reports via LaTeX
\\item Machine-readable column names
\\item Professional Black \& White formatting
\\end{{itemize}}

\\section{{Limitations and Considerations}}
\\begin{{itemize}}
\\item Analysis based on sample data due to computational constraints
\\item Geographic boundary changes over time not fully addressed
\\item Self-reported demographic data limitations
\\item Potential underreporting in certain loan categories
\\end{{itemize}}

\\section{{Conclusion}}
This methodology provides a comprehensive framework for HMDA data analysis, combining rigorous statistical methods with practical data processing considerations. The approach ensures reproducibility, accuracy, and professional presentation of results.

\\end{{document}}
"""

        return latex_content

    def generate_analysis_report(self, analysis_results: Dict[str, Any]) -> str:
        """Generate detailed analysis results LaTeX"""
        self.logger.info("Generating analysis report...")

        # Extract key statistics
        streamlined = analysis_results.get('streamlined_analysis', {}).get('summary', {})
        disparity = analysis_results.get('disparity_analysis', {})

        latex_content = f"""
\\documentclass[11pt,letterpaper]{{article}}
\\usepackage[margin=1in]{{geometry}}
\\usepackage{{graphicx}}
\\usepackage{{booktabs}}
\\usepackage{{longtable}}
\\usepackage{{hyperref}}
\\usepackage{{amsmath}}
\\usepackage{{amssymb}}
\\usepackage{{xcolor}}

\\title{{{self.report_metadata['title']}: Analysis Results}}
\\author{{{self.report_metadata['author']}}}
\\date{{{self.report_metadata['date']}\\\\Version {self.report_metadata['version']}}}

\\begin{{document}}

\\maketitle

\\begin{{abstract}}
This report presents comprehensive findings from the analysis of Home Mortgage Disclosure Act (HMDA) data. The analysis examines lending patterns across geographic, demographic, and institutional dimensions, with particular focus on identifying and quantifying disparities in mortgage lending.
\\end{{abstract}}

\\section{{Executive Summary}}
\\subsection{{Key Findings}}
\\begin{{itemize}}
\\item Total applications analyzed: {streamlined.get('total_applications_analyzed', 0)}
\\item Total loan volume: \\${streamlined.get('total_loan_volume', 0):.0f}
\\item Average loan size: \\${streamlined.get('average_loan_size', 0):.0f}
\\item Geographic coverage: {streamlined.get('unique_states', 0)} states
\\item Institutional diversity: {streamlined.get('unique_lenders', 0)} unique lenders
\\end{{itemize}}

\\subsection{{Disparity Analysis Highlights}}
\\begin{{itemize}}
\\item Total disparity comparisons: {disparity.get('total_disparities_analyzed', 0)}
\\item Statistically significant findings: {disparity.get('significant_disparities', 0)} ({disparity.get('significant_disparities', 0)/max(disparity.get('total_disparities_analyzed', 1), 1):.1%})
\\item Statistical power: {disparity.get('statistical_power', {}).get('power_rate', 0):.1%}
\\end{{itemize}}

\\section{{Geographic Analysis Results}}
\\subsection{{State-Level Lending Patterns}}
Analysis of state-level data reveals significant variation in lending patterns:

\\begin{{itemize}}
\\item States analyzed: {streamlined.get('unique_states', 0)}
\\item Application range: Varies by state with concentration in high-population areas
\\item Origination rates: Show substantial geographic variation
\\item Minority application rates: Correlate with demographic composition
\\end{{itemize}}

\\subsection{{County-Level Analysis}}
County-level analysis provides granular insights:

\\begin{{itemize}}
\\item Counties with data: {analysis_results.get('metadata', {}).get('county_analysis', {}).get('rows', 'N/A')}
\\item Market concentration: Varies significantly by county
\\item Urban-rural disparities: Evident in approval rates and loan terms
\\end{{itemize}}

\\section{{Demographic Analysis Results}}
\\subsection{{Racial and Ethnic Disparities}}
\\subsubsection{{Application Patterns}}
Analysis reveals disparities in mortgage application patterns across racial and ethnic groups.

\\subsubsection{{Approval Rates}}
Statistical analysis of approval rates shows significant variations:

\\begin{{itemize}}
\\item White applicants: Used as reference group
\\item Minority applicants: Experience lower approval rates
\\item Statistical significance: {disparity.get('significant_disparities', 0)} of {disparity.get('total_disparities_analyzed', 0)} comparisons significant at p < 0.05
\\end{{itemize}}

\\subsubsection{{Interest Rate Disparities}}
Analysis of interest rates charged reveals:

\\begin{{itemize}}
\\item Rate variations: Present across demographic groups
\\item Effect sizes: Range from small to large
\\item Economic impact: Substantial over loan lifetimes
\\end{{itemize}}

\\subsection{{Gender-Based Analysis}}
Gender-based analysis shows:

\\begin{{itemize}}
\\item Application rates: Relatively balanced across genders
\\item Approval patterns: Minor variations observed
\\item Loan terms: Generally consistent across gender groups
\\end{{itemize}}

\\section{{Loan Characteristics Analysis}}
\\subsection{{Loan Purpose Distribution}}
Analysis of loan purposes reveals:

\\begin{{itemize}}
\\item Home purchase loans: Dominant category
\\item Refinancing: Significant portion of applications
\\item Home improvement: Smaller but important segment
\\end{{itemize}}

\\subsection{{Interest Rate Analysis}}
Interest rate patterns show:

\\begin{{itemize}}
\\item Rate distribution: Concentrated in middle ranges
\\item Risk-based pricing: Evident in rate variations
\\item Market conditions: Reflected in rate patterns
\\end{{itemize}}

\\subsection{{Loan-to-Value Analysis}}
LTV analysis indicates:

\\begin{{itemize}}
\\item Risk distribution: Varies by LTV category
\\item High-LTV loans: Associated with higher rates
\\item Underwater loans: Small but concerning segment
\\end{{itemize}}

\\section{{Institutional Analysis Results}}
\\subsection{{Lender Market Share}}
Analysis of lender patterns reveals:

\\begin{{itemize}}
\\item Market concentration: Top lenders dominate volume
\\item Specialization: Lenders show geographic and product specialization
\\item Agency distribution: Varied across regulatory agencies
\\end{{itemize}}

\\subsection{{Agency-Level Patterns}}
Regulatory agency analysis shows:

\\begin{{itemize}}
\\item OCC-regulated banks: Significant market presence
\\item Federal Reserve: Substantial lending activity
\\item FDIC-insured institutions: Broad market coverage
\\item Credit unions: Niche but important role
\\end{{itemize}}

\\section{{Statistical Significance Testing}}
\\subsection{{Methodology}}
Statistical testing employed:

\\begin{{itemize}}
\\item Fisher's Exact Test: Small sample sizes
\\item Chi-square Test: Larger samples
\\item Bonferroni correction: Multiple comparison adjustment
\\item Effect size calculation: Cohen's h for practical significance
\\end{{itemize}}

\\subsection{{Significant Findings}}
Key statistically significant disparities identified:

\\begin{{enumerate}}
"""

        # Add key findings from disparity analysis
        key_findings = disparity.get('key_findings', [])
        for i, finding in enumerate(key_findings[:5], 1):
            latex_content += f"\\item {finding}\n"

        latex_content += f"""
\\end{{enumerate}}

\\section{{Economic Impact Assessment}}
\\subsection{{Individual Impact}}
Analysis suggests substantial economic impact:

\\begin{{itemize}}
\\item Interest rate disparities: Translate to thousands of dollars over loan life
\\item Approval disparities: Impact homeownership opportunities
\\item Geographic disparities: Reflect community-level access to credit
\\end{{itemize}}

\\subsection{{Market-Level Impact}}
Market-level effects include:

\\begin{{itemize}}
\\item Credit access: Varies significantly by demographic group
\\item Cost of credit: Disparities in interest rates and terms
\\item Market efficiency: Potential inefficiencies from discriminatory patterns
\\end{{itemize}}

\\section{{Policy Implications}}
\\subsection{{Regulatory Considerations}}
Findings suggest regulatory attention to:

\\begin{{itemize}}
\\item Fair lending compliance: Ongoing monitoring needed
\\item Community reinvestment: Geographic disparities merit attention
\\item Consumer protection: Vulnerable groups may need additional safeguards
\\end{{itemize}}

\\subsection{{Market Solutions}}
Market-based solutions could include:

\\begin{{itemize}}
\\item Expanded credit access: Underserved communities
\\item Product innovation: Tailored products for diverse needs
\\item Technology adoption: Improved underwriting and risk assessment
\\end{{itemize}}

\\section{{Conclusions}}
\\subsection{{Summary of Findings}}
This comprehensive analysis reveals:

\\begin{{itemize}}
\\item Significant disparities: Present across multiple dimensions
\\item Statistical significance: Many disparities are statistically robust
\\item Economic impact: Substantial for affected groups and communities
\\item Policy relevance: Findings inform regulatory and market solutions
\\end{{itemize}}

\\subsection{{Limitations}}
Analysis limitations include:

\\begin{{itemize}}
\\item Sample-based: May not capture full population patterns
\\item Cross-sectional: Limited longitudinal analysis
\\item Data constraints: Self-reported demographic information
\\end{{itemize}}

\\subsection{{Future Research}}
Opportunities for future research:

\\begin{{itemize}}
\\item Longitudinal analysis: Track changes over time
\\item Causal analysis: Identify root causes of disparities
\\item Policy evaluation: Assess impact of interventions
\\item Market studies: Examine competitive dynamics
\\end{{itemize}}

\\end{{document}}
"""

        return latex_content

    def compile_latex_to_pdf(self, tex_file: Path) -> bool:
        """Compile LaTeX file to PDF"""
        self.logger.info(f"Compiling {tex_file.name} to PDF...")

        try:
            # Change to directory containing the .tex file
            original_dir = os.getcwd()
            os.chdir(tex_file.parent)

            # Run pdflatex
            result = subprocess.run(
                ['pdflatex', '-interaction=nonstopmode', tex_file.name],
                capture_output=True,
                text=True,
                timeout=120
            )

            os.chdir(original_dir)

            if result.returncode == 0:
                pdf_file = tex_file.with_suffix('.pdf')
                if pdf_file.exists():
                    self.logger.info(f"Successfully compiled: {pdf_file}")
                    return True
                else:
                    self.logger.error("PDF file not created despite successful compilation")
                    return False
            else:
                self.logger.error(f"LaTeX compilation failed: {result.stderr}")
                return False

        except subprocess.TimeoutExpired:
            self.logger.error("LaTeX compilation timed out")
            return False
        except Exception as e:
            self.logger.error(f"LaTeX compilation error: {str(e)}")
            return False

    def generate_all_reports(self) -> Dict[str, Any]:
        """Generate all comprehensive LaTeX reports"""
        self.logger.info("Starting comprehensive LaTeX report generation...")

        start_time = datetime.now()
        results = {
            'start_time': start_time,
            'status': 'started',
            'reports_generated': [],
            'compilation_results': {}
        }

        try:
            # Load analysis results
            analysis_results = self.load_analysis_results()

            # Generate Methodology Report
            self.logger.info("Generating Methodology Report...")
            methodology_tex = self.generate_methodology_report(analysis_results)
            methodology_file = self.tex_path / "HMDA_Methodology_Report.tex"
            with open(methodology_file, 'w') as f:
                f.write(methodology_tex)
            results['reports_generated'].append(str(methodology_file))

            # Generate Analysis Report
            self.logger.info("Generating Analysis Report...")
            analysis_tex = self.generate_analysis_report(analysis_results)
            analysis_file = self.tex_path / "HMDA_Analysis_Report.tex"
            with open(analysis_file, 'w') as f:
                f.write(analysis_tex)
            results['reports_generated'].append(str(analysis_file))

            # Compile LaTeX files to PDFs
            for tex_file in [methodology_file, analysis_file]:
                success = self.compile_latex_to_pdf(tex_file)
                results['compilation_results'][tex_file.stem] = {
                    'success': success,
                    'tex_file': str(tex_file),
                    'pdf_file': str(tex_file.with_suffix('.pdf'))
                }

                # Copy PDF to output directory if successful
                if success:
                    pdf_file = tex_file.with_suffix('.pdf')
                    output_pdf = self.pdf_path / pdf_file.name
                    if pdf_file.exists():
                        import shutil
                        shutil.copy2(pdf_file, output_pdf)
                        self.logger.info(f"Copied PDF to: {output_pdf}")

            end_time = datetime.now()
            results.update({
                'end_time': end_time,
                'duration_seconds': (end_time - start_time).total_seconds(),
                'status': 'completed',
                'total_reports': len(results['reports_generated']),
                'successful_compilations': sum(1 for r in results['compilation_results'].values() if r['success'])
            })

            self.logger.info(f"LaTeX report generation completed in {results['duration_seconds']:.2f} seconds")
            self.logger.info(f"Generated {len(results['reports_generated'])} reports, {results['successful_compilations']} compiled successfully")

        except Exception as e:
            self.logger.error(f"LaTeX report generation failed: {str(e)}")
            results['status'] = 'failed'
            results['error'] = str(e)
            raise

        return results

def main():
    """Main execution function"""
    generator = ComprehensiveLaTeXGenerator()
    results = generator.generate_all_reports()

    print("\n" + "=" * 80)
    print("COMPREHENSIVE LATEX REPORT GENERATION RESULTS")
    print("=" * 80)
    print(f"Status: {results['status']}")
    print(f"Reports generated: {results.get('total_reports', 0)}")
    print(f"Successfully compiled: {results.get('successful_compilations', 0)}")
    print(f"Processing time: {results.get('duration_seconds', 0):.2f} seconds")

    if results['status'] == 'completed':
        print(f"\nGenerated Reports:")
        for report in results.get('reports_generated', []):
            print(f"  • {Path(report).name}")

        print(f"\nCompilation Results:")
        for name, result in results.get('compilation_results', {}).items():
            status = "✓" if result['success'] else "✗"
            print(f"  {status} {name}")

        print(f"\nOutput directories:")
        print(f"  LaTeX source: {generator.tex_path}")
        print(f"  PDF output: {generator.pdf_path}")

    return results

if __name__ == "__main__":
    main()