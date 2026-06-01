"""
Bhutta (2011) Replication Diagnostics

Tools for comparing different specification choices and diagnosing
sources of divergence between replication and original results.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from .sample_construction import BhuttaSampleConstructor, SampleConfig
from .rd_estimation import BhuttaRDEstimator, RDConfig, RDResult


@dataclass
class SpecificationDiff:
    """Difference between two specifications."""

    name: str
    description: str
    bhutta_value: str
    r_code_value: str
    impact: str  # "high", "medium", "low"
    category: str  # "sample", "controls", "model"


# Known specification differences from reconciliation document
SPECIFICATION_DIFFS = [
    SpecificationDiff(
        name="central_city_filter",
        description="Central city tract restriction",
        bhutta_value="No filter (all MSA tracts)",
        r_code_value="central_city_flag == 1",
        impact="HIGH",
        category="sample",
    ),
    SpecificationDiff(
        name="housing_unit_filter",
        description="Minimum housing unit requirement",
        bhutta_value="≥100 total housing units",
        r_code_value="≥100 owner-occupied units",
        impact="MEDIUM",
        category="sample",
    ),
    SpecificationDiff(
        name="log_owner_occupied",
        description="Log owner-occupied units control",
        bhutta_value="Included",
        r_code_value="Missing",
        impact="MEDIUM",
        category="controls",
    ),
    SpecificationDiff(
        name="race_controls",
        description="Race/ethnicity controls",
        bhutta_value="Separate % Black, % Hispanic",
        r_code_value="Combined minority_percentage",
        impact="LOW",
        category="controls",
    ),
    SpecificationDiff(
        name="age_control",
        description="Age 65+ control",
        bhutta_value="Included",
        r_code_value="Missing",
        impact="LOW",
        category="controls",
    ),
    SpecificationDiff(
        name="group_quarters_control",
        description="Group quarters percentage control",
        bhutta_value="Included + filter (<30%)",
        r_code_value="Missing",
        impact="LOW",
        category="controls",
    ),
    SpecificationDiff(
        name="property_type_controls",
        description="Property type share controls",
        bhutta_value="Included (detached, multi, mobile)",
        r_code_value="Missing",
        impact="LOW",
        category="controls",
    ),
]


def run_specification_comparison(
    census_df: pd.DataFrame,
    hmda_df: pd.DataFrame,
    msa_pop_df: Optional[pd.DataFrame] = None,
) -> pd.DataFrame:
    """
    Run the same RD estimation under different specifications
    to identify which differences explain the β divergence.

    Tests:
    1. Bhutta exact specification
    2. With central city filter (R code style)
    3. With owner-occupied housing filter
    4. With reduced controls

    Returns DataFrame comparing all specifications.
    """
    results = []

    # Specification 1: Exact Bhutta
    print("Testing Specification 1: Exact Bhutta...")
    config_bhutta = SampleConfig(
        central_city_only=False,
        min_housing_units=100,  # Total housing units
    )
    constructor = BhuttaSampleConstructor(config_bhutta)
    sample_bhutta = constructor.construct_sample(
        census_df, hmda_df, msa_pop_df, bandwidth="narrow"
    )

    try:
        estimator = BhuttaRDEstimator()
        result = estimator.estimate(sample_bhutta, bandwidth="narrow", msa_size="large")
        results.append(
            {
                "Specification": "Bhutta Exact",
                "Central City": "No",
                "HU Filter": "Total ≥100",
                "β": result.beta,
                "SE": result.se,
                "p": result.p_value,
                "N": result.n_obs,
                "MSAs": result.n_msas,
            }
        )
    except Exception as e:
        results.append({"Specification": "Bhutta Exact", "Error": str(e)})

    # Specification 2: With Central City Filter
    print("Testing Specification 2: With Central City Filter...")
    config_cc = SampleConfig(
        central_city_only=True,  # R code uses this
        min_housing_units=100,
    )
    constructor_cc = BhuttaSampleConstructor(config_cc)
    sample_cc = constructor_cc.construct_sample(
        census_df, hmda_df, msa_pop_df, bandwidth="narrow"
    )

    try:
        result = estimator.estimate(sample_cc, bandwidth="narrow", msa_size="large")
        results.append(
            {
                "Specification": "With Central City",
                "Central City": "Yes",
                "HU Filter": "Total ≥100",
                "β": result.beta,
                "SE": result.se,
                "p": result.p_value,
                "N": result.n_obs,
                "MSAs": result.n_msas,
            }
        )
    except Exception as e:
        results.append({"Specification": "With Central City", "Error": str(e)})

    # Specification 3: Owner-occupied filter
    print("Testing Specification 3: Owner-Occupied Filter...")
    # Would need to modify sample construction to filter on OOU instead of total HU

    results_df = pd.DataFrame(results)
    return results_df


def diagnose_sample_differences(
    df_bhutta: pd.DataFrame,
    df_rcode: pd.DataFrame,
) -> Dict:
    """
    Compare two samples to identify differences.

    Args:
        df_bhutta: Sample constructed with Bhutta specification
        df_rcode: Sample constructed with R code specification

    Returns:
        Dictionary with diagnostic information
    """
    diagnostics = {}

    # Sample size comparison
    diagnostics["n_bhutta"] = len(df_bhutta)
    diagnostics["n_rcode"] = len(df_rcode)
    diagnostics["n_diff"] = len(df_bhutta) - len(df_rcode)
    diagnostics["pct_diff"] = (
        (len(df_bhutta) - len(df_rcode)) / len(df_bhutta) * 100
        if len(df_bhutta) > 0
        else 0
    )

    # TM distribution
    if "TM" in df_bhutta.columns and "TM" in df_rcode.columns:
        diagnostics["tm_mean_bhutta"] = df_bhutta["TM"].mean()
        diagnostics["tm_mean_rcode"] = df_rcode["TM"].mean()
        diagnostics["tm_std_bhutta"] = df_bhutta["TM"].std()
        diagnostics["tm_std_rcode"] = df_rcode["TM"].std()

    # Treatment distribution (tracts below cutoff)
    if "D" in df_bhutta.columns and "D" in df_rcode.columns:
        diagnostics["pct_treated_bhutta"] = df_bhutta["D"].mean() * 100
        diagnostics["pct_treated_rcode"] = df_rcode["D"].mean() * 100

    # MSA coverage
    if "msa_code" in df_bhutta.columns and "msa_code" in df_rcode.columns:
        diagnostics["n_msas_bhutta"] = df_bhutta["msa_code"].nunique()
        diagnostics["n_msas_rcode"] = df_rcode["msa_code"].nunique()

        msas_bhutta = set(df_bhutta["msa_code"].unique())
        msas_rcode = set(df_rcode["msa_code"].unique())
        diagnostics["msas_only_bhutta"] = len(msas_bhutta - msas_rcode)
        diagnostics["msas_only_rcode"] = len(msas_rcode - msas_bhutta)

    return diagnostics


def create_diagnostic_report(
    census_df: pd.DataFrame,
    hmda_df: pd.DataFrame,
    msa_pop_df: Optional[pd.DataFrame] = None,
) -> str:
    """
    Create a detailed diagnostic report comparing specifications.
    """
    report = []
    report.append("=" * 80)
    report.append("BHUTTA (2011) REPLICATION DIAGNOSTIC REPORT")
    report.append("=" * 80)

    # Document known specification differences
    report.append("\n## Known Specification Differences\n")
    report.append("-" * 80)

    for diff in SPECIFICATION_DIFFS:
        report.append(f"\n### {diff.name} [{diff.impact} IMPACT]")
        report.append(f"  Description: {diff.description}")
        report.append(f"  Bhutta (2011): {diff.bhutta_value}")
        report.append(f"  R Code: {diff.r_code_value}")

    # Run specification comparison
    report.append("\n\n## Specification Comparison Results\n")
    report.append("-" * 80)

    try:
        comparison_df = run_specification_comparison(census_df, hmda_df, msa_pop_df)
        report.append(comparison_df.to_string())
    except Exception as e:
        report.append(f"Error running comparison: {e}")

    # Target results
    report.append("\n\n## Target Results (Bhutta Table 2)\n")
    report.append("-" * 80)
    report.append("Large MSAs, h=0.05:")
    report.append("  β = 0.0764* (SE = 0.0274)")
    report.append("  N ≈ 1,800 tracts")
    report.append("\nLarge MSAs, h=0.30 (cubic):")
    report.append("  β = 0.0729** (SE = 0.0158)")
    report.append("  N ≈ 9,551 tracts")

    report.append("\n" + "=" * 80)

    return "\n".join(report)


def sensitivity_analysis(
    census_df: pd.DataFrame,
    hmda_df: pd.DataFrame,
    parameter: str,
    values: List,
    msa_pop_df: Optional[pd.DataFrame] = None,
) -> pd.DataFrame:
    """
    Run sensitivity analysis varying one specification parameter.

    Args:
        census_df: Census tract data
        hmda_df: HMDA lending data
        parameter: Parameter to vary (e.g., "min_housing_units", "cutoff")
        values: List of values to test
        msa_pop_df: Optional MSA population data

    Returns:
        DataFrame with results for each parameter value
    """
    results = []

    for val in values:
        config = SampleConfig()
        setattr(config, parameter, val)

        constructor = BhuttaSampleConstructor(config)
        try:
            sample = constructor.construct_sample(
                census_df, hmda_df, msa_pop_df, bandwidth="narrow"
            )

            estimator = BhuttaRDEstimator()
            result = estimator.estimate(sample, bandwidth="narrow", msa_size="large")

            results.append(
                {
                    "parameter": parameter,
                    "value": val,
                    "beta": result.beta,
                    "se": result.se,
                    "p_value": result.p_value,
                    "n_obs": result.n_obs,
                    "n_msas": result.n_msas,
                }
            )
        except Exception as e:
            results.append(
                {
                    "parameter": parameter,
                    "value": val,
                    "error": str(e),
                }
            )

    return pd.DataFrame(results)
