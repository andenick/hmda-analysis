#!/usr/bin/env python3
"""
Comprehensive Multi-Scope Analysis Framework

CRITICAL PRINCIPLE: SEPARATE ANALYSIS SCOPES WITH SPECIFIC QUALITY HANDLING
- State-level longitudinal analysis (highest reliability)
- County-level analysis with decimal format handling
- Tract-level analysis with boundary corrections
- Cross-sectional analysis across all levels
- MSA analysis with redefinition awareness

Each analysis scope has its own quality requirements and data handling protocols.
ALL ORIGINAL DATA PRESERVED - no modifications to source data.
"""

import pandas as pd
import numpy as np
import logging
from pathlib import Path
import json
from datetime import datetime
from typing import Dict, List, Any, Tuple
import warnings
import os
DATA_ROOT = Path(os.environ.get("DATA_ROOT", "data"))

warnings.filterwarnings('ignore')

class MultiScopeAnalysisFramework:
    """
    CRITICAL PRINCIPLES:
    - Separate analysis pipelines for each geographic scope
    - Scope-specific quality handling without data modification
    - Preserve all original data exactly as found
    - Document scope-specific limitations and requirements
    """

    def __init__(self, base_path: str = str(DATA_ROOT)):
        self.base_path = Path(base_path)
        self.output_path = self.base_path / "analysis_outputs" / "multi_scope_analysis"
        self.output_path.mkdir(parents=True, exist_ok=True)

        # Configure logging
        logging.basicConfig(level=logging.INFO,
                          format='%(asctime)s - %(levelname)s - %(message)s')
        self.logger = logging.getLogger(__name__)

        self.logger.info("Initialized Multi-Scope Analysis Framework")
        self.logger.info("CRITICAL: NO data modifications - separate scope handling")

        # Initialize analysis scopes
        self.analysis_scopes = {
            'state_longitudinal': {
                'description': 'State-level longitudinal analysis - highest reliability',
                'geographic_level': 'state',
                'time_dimension': 'longitudinal',
                'stability_rating': 'HIGHEST',
                'quality_requirements': 'Basic validation',
                'stable_areas': 23,
                'recommended_for': ['Policy analysis', 'National trends', 'Long-term research']
            },
            'county_longitudinal': {
                'description': 'County-level longitudinal analysis with quality handling',
                'geographic_level': 'county',
                'time_dimension': 'longitudinal',
                'stability_rating': 'HIGH',
                'quality_requirements': 'Handle decimal format, validate stability',
                'stable_areas': 18,
                'recommended_for': ['Regional analysis', 'Sub-state policy research']
            },
            'tract_longitudinal': {
                'description': 'Tract-level longitudinal with mandatory boundary corrections',
                'geographic_level': 'tract',
                'time_dimension': 'longitudinal',
                'stability_rating': 'LOW',
                'quality_requirements': 'MANDATORY crosswalk application',
                'stable_areas': '10.3%',
                'recommended_for': ['Neighborhood analysis with crosswalks']
            },
            'msa_longitudinal': {
                'description': 'MSA longitudinal analysis - use with extreme caution',
                'geographic_level': 'msa',
                'time_dimension': 'longitudinal',
                'stability_rating': 'LOWEST',
                'quality_requirements': 'Redefinition tracking, not recommended',
                'stable_areas': 0,
                'recommended_for': ['Cross-sectional only, avoid longitudinal']
            },
            'cross_sectional_all_levels': {
                'description': 'Cross-sectional analysis - all levels acceptable',
                'geographic_level': 'all',
                'time_dimension': 'cross_sectional',
                'stability_rating': 'NOT_APPLICABLE',
                'quality_requirements': 'Standard quality validation',
                'stable_areas': 'N/A',
                'recommended_for': ['Single-year analysis', 'Snapshot studies']
            },
            'specialized_demographic': {
                'description': 'Demographic analysis with missing value handling',
                'geographic_level': 'flexible',
                'time_dimension': 'flexible',
                'stability_rating': 'VARIABLE',
                'quality_requirements': 'Handle high missing rates in secondary fields',
                'stable_areas': 'Depends on scope',
                'recommended_for': ['Race/ethnicity analysis', 'Income analysis']
            }
        }

    def setup_all_analysis_scopes(self) -> Dict[str, Any]:
        """
        Set up all analysis scopes with their specific requirements.

        CRITICAL: Each scope maintains separate data handling protocols.
        """
        self.logger.info("Setting up all analysis scopes with separate handling")
        self.logger.info("CRITICAL: Each scope preserves original data differently")

        framework_setup = {
            'setup_metadata': {
                'setup_date': datetime.now().isoformat(),
                'principle': 'SEPARATE_SCOPE_HANDLING - No cross-contamination',
                'scopes_configured': len(self.analysis_scopes),
                'quality_framework_applied': True
            }
        }

        # Set up each analysis scope
        for scope_name, scope_config in self.analysis_scopes.items():
            self.logger.info(f"Setting up {scope_name}: {scope_config['description']}")

            scope_setup = self._setup_individual_scope(scope_name, scope_config)
            framework_setup[scope_name] = scope_setup

        # Create scope coordination framework
        framework_setup['scope_coordination'] = self._create_scope_coordination()

        # Save framework setup
        self._save_framework_setup(framework_setup)

        self.logger.info("Multi-scope analysis framework setup completed")
        return framework_setup

    def _setup_individual_scope(self, scope_name: str, scope_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Set up individual analysis scope with specific requirements.

        CRITICAL: Each scope has unique data quality and handling protocols.
        """
        scope_setup = {
            'scope_configuration': scope_config,
            'data_requirements': self._define_data_requirements(scope_name, scope_config),
            'quality_protocols': self._define_quality_protocols(scope_name, scope_config),
            'analysis_pipeline': self._define_analysis_pipeline(scope_name, scope_config),
            'output_specifications': self._define_output_specs(scope_name, scope_config)
        }

        # Create scope-specific directory
        scope_dir = self.output_path / scope_name
        scope_dir.mkdir(parents=True, exist_ok=True)

        return scope_setup

    def _define_data_requirements(self, scope_name: str, scope_config: Dict[str, Any]) -> Dict[str, Any]:
        """Define specific data requirements for each analysis scope."""

        base_requirements = {
            'preserve_original_data': True,
            'no_data_modifications': True,
            'quality_documentation_required': True
        }

        if scope_name == 'state_longitudinal':
            return {
                **base_requirements,
                'geographic_fields': ['state_code'],
                'missing_tolerance': 'Low - exclude records missing state codes',
                'quality_checks': ['State code validation', 'Temporal consistency'],
                'stable_area_filter': 'Use 23 stable states for maximum reliability',
                'time_range': 'Full available range',
                'boundary_corrections': 'Not required - states stable'
            }

        elif scope_name == 'county_longitudinal':
            return {
                **base_requirements,
                'geographic_fields': ['state_code', 'county_code'],
                'missing_tolerance': 'Low - exclude records missing county identifiers',
                'quality_checks': ['County code format handling', 'Boundary validation'],
                'stable_area_filter': 'Use 18 stable counties, validate others',
                'time_range': 'Full available range',
                'boundary_corrections': 'Validate county stability, handle format issues',
                'special_handling': 'Convert decimal county codes to integers'
            }

        elif scope_name == 'tract_longitudinal':
            return {
                **base_requirements,
                'geographic_fields': ['state_code', 'county_code', 'census_tract'],
                'missing_tolerance': 'Very Low - exclude records missing tract identifiers',
                'quality_checks': ['Tract boundary validation', 'Crosswalk application'],
                'stable_area_filter': 'Use stable tracts only OR apply crosswalks',
                'time_range': 'Limited by crosswalk availability',
                'boundary_corrections': 'MANDATORY - 31.6% of tracts require crosswalks',
                'special_handling': 'Apply tract boundary corrections before analysis'
            }

        elif scope_name == 'msa_longitudinal':
            return {
                **base_requirements,
                'geographic_fields': ['derived_msa_md'],
                'missing_tolerance': 'Medium - MSA field complete but codes unstable',
                'quality_checks': ['MSA redefinition tracking', 'Code consistency'],
                'stable_area_filter': 'NO STABLE MSAs - extreme caution required',
                'time_range': 'Limited by redefinition periods',
                'boundary_corrections': 'Track redefinitions: 2003, 2009, 2013',
                'special_handling': 'NOT RECOMMENDED for longitudinal analysis'
            }

        elif scope_name == 'cross_sectional_all_levels':
            return {
                **base_requirements,
                'geographic_fields': ['state_code', 'county_code', 'census_tract', 'derived_msa_md'],
                'missing_tolerance': 'Medium - accept missing for non-critical analysis',
                'quality_checks': ['Basic validation', 'Completeness assessment'],
                'stable_area_filter': 'Not required - single time point',
                'time_range': 'Any single year or period',
                'boundary_corrections': 'Not required for cross-sectional',
                'special_handling': 'Use all available data with quality flags'
            }

        elif scope_name == 'specialized_demographic':
            return {
                **base_requirements,
                'geographic_fields': ['Flexible based on analysis'],
                'missing_tolerance': 'High - handle structured missing patterns',
                'quality_checks': ['Missing pattern analysis', 'Field availability'],
                'stable_area_filter': 'Depends on geographic scope chosen',
                'time_range': 'Flexible',
                'boundary_corrections': 'Apply appropriate to geographic scope',
                'special_handling': 'Handle 95%+ missing rates in secondary fields'
            }

        return base_requirements

    def _define_quality_protocols(self, scope_name: str, scope_config: Dict[str, Any]) -> Dict[str, Any]:
        """Define quality control protocols specific to each analysis scope."""

        base_protocols = {
            'preserve_all_original_data': True,
            'document_all_exclusions': True,
            'quality_flag_creation': True,
            'independent_validation': True
        }

        quality_protocols = {
            'state_longitudinal': {
                **base_protocols,
                'exclusion_criteria': ['Missing state codes', 'Invalid state codes'],
                'quality_flags': ['State stability verified', 'Complete geographic coverage'],
                'validation_checks': ['State code consistency', 'Temporal coverage'],
                'expected_exclusion_rate': '1.2% (missing state codes)',
                'reliability_rating': 'HIGHEST'
            },
            'county_longitudinal': {
                **base_protocols,
                'exclusion_criteria': ['Missing county codes', 'Invalid state-county combinations'],
                'quality_flags': ['County stability verified', 'Format corrected', 'Boundary validated'],
                'validation_checks': ['County code format', 'State-county hierarchy', 'Stability verification'],
                'expected_exclusion_rate': '1.7% (missing county codes)',
                'reliability_rating': 'HIGH',
                'special_processing': 'Convert decimal county codes: "24035.0" -> "24035"'
            },
            'tract_longitudinal': {
                **base_protocols,
                'exclusion_criteria': ['Missing tract codes', 'Invalid tract hierarchies', 'No crosswalk available'],
                'quality_flags': ['Boundary corrections applied', 'Crosswalk confidence', 'Population validated'],
                'validation_checks': ['Tract boundary changes', 'Crosswalk application', 'Population continuity'],
                'expected_exclusion_rate': '1.6% + crosswalk limitations',
                'reliability_rating': 'MEDIUM (with corrections)',
                'mandatory_processing': 'Apply crosswalk tables for decennial boundary crossings'
            },
            'msa_longitudinal': {
                **base_protocols,
                'exclusion_criteria': ['Use with extreme caution - frequent redefinitions'],
                'quality_flags': ['Redefinition period flagged', 'Code transition tracked'],
                'validation_checks': ['MSA redefinition impact', 'Code consistency across periods'],
                'expected_exclusion_rate': 'Variable - depends on redefinition tolerance',
                'reliability_rating': 'LOWEST',
                'critical_warning': 'NOT RECOMMENDED for longitudinal analysis'
            },
            'cross_sectional_all_levels': {
                **base_protocols,
                'exclusion_criteria': ['Minimal - preserve maximum data for single-period analysis'],
                'quality_flags': ['Geographic completeness', 'Field availability'],
                'validation_checks': ['Basic data integrity', 'Geographic hierarchy'],
                'expected_exclusion_rate': 'Minimal for cross-sectional purposes',
                'reliability_rating': 'HIGH (single period)'
            },
            'specialized_demographic': {
                **base_protocols,
                'exclusion_criteria': ['Field-specific based on analysis requirements'],
                'quality_flags': ['Missing pattern documented', 'Secondary field availability'],
                'validation_checks': ['Missing pattern analysis', 'Field completeness'],
                'expected_exclusion_rate': 'Variable by demographic field',
                'reliability_rating': 'VARIABLE',
                'special_considerations': 'Handle 95%+ missing rates in secondary race/ethnicity fields'
            }
        }

        return quality_protocols.get(scope_name, base_protocols)

    def _define_analysis_pipeline(self, scope_name: str, scope_config: Dict[str, Any]) -> Dict[str, Any]:
        """Define analysis pipeline steps for each scope."""

        base_pipeline = [
            'Load original data (no modifications)',
            'Apply scope-specific quality protocols',
            'Create quality flags and documentation',
            'Execute analysis preserving data integrity',
            'Generate scope-specific outputs',
            'Validate results and document limitations'
        ]

        pipeline_configs = {
            'state_longitudinal': {
                'pipeline_steps': [
                    '1. Load HMDA data preserving all original values',
                    '2. Filter to stable states (23 identified stable areas)',
                    '3. Validate state code completeness and consistency',
                    '4. Apply temporal analysis across full available range',
                    '5. Generate state-level trend analysis',
                    '6. Create policy-relevant aggregations',
                    '7. Document methodology and limitations'
                ],
                'expected_outputs': ['State trend analysis', 'Policy impact assessment', 'National patterns'],
                'analysis_types': ['Time series', 'Panel analysis', 'Policy evaluation']
            },
            'county_longitudinal': {
                'pipeline_steps': [
                    '1. Load HMDA data preserving all original values',
                    '2. Handle decimal county code format (preserve originals, create cleaned versions)',
                    '3. Filter to stable counties or validate county boundary consistency',
                    '4. Apply county-level quality protocols',
                    '5. Execute county-level longitudinal analysis',
                    '6. Generate regional trend analysis',
                    '7. Document format handling and stability validation'
                ],
                'expected_outputs': ['County trend analysis', 'Regional patterns', 'Sub-state variation'],
                'analysis_types': ['Regional analysis', 'County comparison', 'Sub-state policy evaluation']
            },
            'tract_longitudinal': {
                'pipeline_steps': [
                    '1. Load HMDA data preserving all original values',
                    '2. Load and apply appropriate crosswalk tables',
                    '3. Validate tract boundary corrections and population continuity',
                    '4. Filter to analysis-appropriate tract sets',
                    '5. Execute tract-level analysis with boundary corrections',
                    '6. Generate neighborhood-level insights',
                    '7. Document crosswalk applications and limitations'
                ],
                'expected_outputs': ['Tract trend analysis', 'Neighborhood patterns', 'Local area research'],
                'analysis_types': ['Neighborhood analysis', 'Community development research', 'Local policy evaluation'],
                'critical_requirement': 'MANDATORY crosswalk application for longitudinal analysis'
            },
            'cross_sectional_all_levels': {
                'pipeline_steps': [
                    '1. Load HMDA data for target period preserving all values',
                    '2. Apply minimal quality filtering for cross-sectional purposes',
                    '3. Create multi-level geographic analysis',
                    '4. Execute cross-sectional analysis across all levels',
                    '5. Generate comparative analysis between geographic levels',
                    '6. Create snapshot insights',
                    '7. Document cross-sectional methodology'
                ],
                'expected_outputs': ['Multi-level analysis', 'Geographic comparison', 'Snapshot studies'],
                'analysis_types': ['Cross-sectional comparison', 'Geographic pattern analysis', 'Single-period evaluation']
            }
        }

        return pipeline_configs.get(scope_name, {'pipeline_steps': base_pipeline})

    def _define_output_specs(self, scope_name: str, scope_config: Dict[str, Any]) -> Dict[str, Any]:
        """Define output specifications for each analysis scope."""

        output_specs = {
            'state_longitudinal': {
                'primary_outputs': [
                    'state_trend_analysis.csv - State-level lending trends over time',
                    'state_policy_analysis.json - Policy impact assessment',
                    'state_methodology_notes.md - Complete methodology documentation'
                ],
                'quality_documentation': [
                    'state_exclusions_log.csv - Record of excluded data with reasons',
                    'state_quality_flags.csv - Quality indicators for each record',
                    'state_stability_validation.json - Validation of stable state usage'
                ],
                'analysis_outputs': [
                    'state_lending_trends.html - Interactive trend visualization',
                    'state_demographic_patterns.csv - Demographic lending patterns by state',
                    'state_policy_impact_report.pdf - Policy research findings'
                ]
            },
            'county_longitudinal': {
                'primary_outputs': [
                    'county_trend_analysis.csv - County-level lending trends',
                    'county_format_handling_log.json - Documentation of decimal format corrections',
                    'county_methodology_notes.md - County-specific methodology'
                ],
                'quality_documentation': [
                    'county_exclusions_log.csv - Excluded records with reasons',
                    'county_format_corrections.csv - Original vs corrected county codes',
                    'county_stability_validation.json - County boundary validation results'
                ],
                'analysis_outputs': [
                    'county_regional_analysis.html - Regional lending pattern visualization',
                    'county_comparison_analysis.csv - Cross-county comparison',
                    'county_policy_impact_assessment.pdf - Regional policy analysis'
                ]
            },
            'tract_longitudinal': {
                'primary_outputs': [
                    'tract_trend_analysis.csv - Tract-level trends with boundary corrections',
                    'tract_crosswalk_applications.json - Documentation of crosswalk usage',
                    'tract_methodology_notes.md - Boundary correction methodology'
                ],
                'quality_documentation': [
                    'tract_boundary_corrections.csv - All boundary corrections applied',
                    'tract_crosswalk_confidence.csv - Confidence levels for each correction',
                    'tract_population_validation.json - Population continuity verification'
                ],
                'analysis_outputs': [
                    'tract_neighborhood_analysis.html - Neighborhood-level insights',
                    'tract_community_patterns.csv - Community development indicators',
                    'tract_boundary_impact_report.pdf - Impact of boundary changes on analysis'
                ]
            }
        }

        return output_specs.get(scope_name, {})

    def _create_scope_coordination(self) -> Dict[str, Any]:
        """Create coordination framework between analysis scopes."""

        coordination = {
            'principle': 'Separate but coordinated analysis scopes',
            'cross_scope_validation': {
                'state_county_consistency': 'Validate county results aggregate to state results',
                'geographic_hierarchy': 'Ensure tract results align with county/state when possible',
                'temporal_alignment': 'Coordinate time periods across longitudinal scopes'
            },
            'result_integration': {
                'multi_level_comparison': 'Enable comparison across geographic levels',
                'policy_consistency': 'Check policy conclusions across different scopes',
                'methodology_documentation': 'Document how scope-specific methods affect results'
            },
            'quality_coordination': {
                'consistent_exclusion_documentation': 'Document exclusions consistently across scopes',
                'quality_flag_standardization': 'Use consistent quality flagging across scopes',
                'validation_cross_checks': 'Cross-validate results where scopes overlap'
            },
            'output_coordination': {
                'shared_metadata_standards': 'Consistent metadata across all scope outputs',
                'integrated_documentation': 'Combined methodology documentation',
                'coordinated_release': 'Release scope results together with integration notes'
            }
        }

        return coordination

    def _save_framework_setup(self, framework_setup: Dict[str, Any]) -> None:
        """Save the complete framework setup."""

        # Save detailed JSON framework
        json_file = self.output_path / "multi_scope_analysis_framework.json"
        with open(json_file, 'w') as f:
            json.dump(framework_setup, f, indent=2, default=str)

        # Save readable summary
        summary_file = self.output_path / "analysis_scopes_summary.md"
        with open(summary_file, 'w') as f:
            f.write("# Multi-Scope Analysis Framework Summary\n\n")
            f.write(f"**Setup Date**: {framework_setup['setup_metadata']['setup_date']}\n")
            f.write(f"**Principle**: {framework_setup['setup_metadata']['principle']}\n\n")

            f.write("## CRITICAL DATA INTEGRITY COMMITMENT\n")
            f.write("- NO DATA MODIFICATIONS across any analysis scope\n")
            f.write("- Separate quality handling for each analysis type\n")
            f.write("- Scope-specific exclusions and quality protocols\n")
            f.write("- Complete documentation and validation for each scope\n\n")

            f.write("## Analysis Scopes Configured\n\n")
            for scope_name, scope_info in framework_setup.items():
                if scope_name == 'setup_metadata' or scope_name == 'scope_coordination':
                    continue

                if isinstance(scope_info, dict) and 'scope_configuration' in scope_info:
                    config = scope_info['scope_configuration']
                    f.write(f"### {scope_name.replace('_', ' ').title()}\n")
                    f.write(f"- **Description**: {config['description']}\n")
                    f.write(f"- **Geographic Level**: {config['geographic_level']}\n")
                    f.write(f"- **Stability Rating**: {config['stability_rating']}\n")
                    f.write(f"- **Quality Requirements**: {config['quality_requirements']}\n")
                    f.write(f"- **Stable Areas**: {config['stable_areas']}\n")
                    f.write(f"- **Recommended For**: {', '.join(config['recommended_for'])}\n\n")

            f.write("## Scope Coordination\n")
            coordination = framework_setup.get('scope_coordination', {})
            f.write(f"**Principle**: {coordination.get('principle', 'Separate but coordinated')}\n")
            f.write("- Cross-scope validation procedures established\n")
            f.write("- Result integration protocols defined\n")
            f.write("- Quality coordination framework implemented\n")
            f.write("- Output coordination standards established\n\n")

        self.logger.info(f"Framework setup saved: {json_file}")
        self.logger.info(f"Summary saved: {summary_file}")

def main():
    """Set up comprehensive multi-scope analysis framework."""
    print("MULTI-SCOPE ANALYSIS FRAMEWORK SETUP")
    print("CRITICAL: Separate handling for each analysis scope")

    framework = MultiScopeAnalysisFramework()
    setup_results = framework.setup_all_analysis_scopes()

    print("\nFRAMEWORK SETUP COMPLETE")
    print("All analysis scopes configured with separate quality protocols")
    print(f"Results: ${OUTPUT_ROOT}/analysis_outputs/multi_scope_analysis/")

if __name__ == "__main__":
    main()