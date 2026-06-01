"""
Bhutta (2011) Regression Discontinuity Estimation

Implements RD estimation following Bhutta (2011):
- Local linear regression (narrow bandwidth h=0.05)
- Cubic polynomial (wide bandwidth h=0.30)
- MSA fixed effects
- Clustered standard errors at MSA level

Key equation:
    Y_i = α + β*D_i + f(TM_i) + X_i*γ + μ_m + ε_i

Where:
- Y_i = log(bank originations)
- D_i = 1(TM_i < 0.80)  [treatment indicator]
- f(TM_i) = control function (linear or cubic in TM-0.80)
- X_i = tract controls
- μ_m = MSA fixed effects
- ε_i = error (clustered by MSA)
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

# Try to import statsmodels for regression
try:
    import statsmodels.api as sm
    import statsmodels.formula.api as smf
    from statsmodels.regression.linear_model import OLS

    HAS_STATSMODELS = True
except ImportError:
    HAS_STATSMODELS = False

# Try to import linearmodels for panel/clustered regression
try:
    from linearmodels.panel import PanelOLS
    from linearmodels.iv import AbsorbingLS

    HAS_LINEARMODELS = True
except ImportError:
    HAS_LINEARMODELS = False


@dataclass
class RDConfig:
    """Configuration for RD estimation."""

    # Cutoff
    cutoff: float = 0.80

    # Bandwidths
    bandwidths: Dict[str, float] = field(
        default_factory=lambda: {
            "narrow": 0.05,
            "wide": 0.30,
        }
    )

    # Control function specification
    control_functions: Dict[str, str] = field(
        default_factory=lambda: {
            "narrow": "linear",  # Linear in (TM - 0.80)
            "wide": "cubic",  # Cubic in (TM - 0.80)
        }
    )

    # Default control variables (Bhutta specification)
    default_controls: List[str] = field(
        default_factory=lambda: [
            "ln_housing_units",
            "ln_owner_occ",
            "ln_home_value",
            "pct_black",
            "pct_hispanic",
            "pct_65_over",
            "pct_group_quarters",
            "pct_pre1940",
            "pct_1940_1969",
        ]
    )

    # Fixed effects
    fe_var: str = "msa_code"

    # Clustering
    cluster_var: str = "msa_code"

    # Outcome variable
    outcome_var: str = "ln_bank_orig"

    # Treatment variable
    treatment_var: str = "D"

    # Assignment variable (centered)
    running_var: str = "TM_centered"


@dataclass
class RDResult:
    """Results from RD estimation."""

    # Main estimate
    beta: float
    se: float
    t_stat: float
    p_value: float
    ci_lower: float
    ci_upper: float

    # Sample info
    n_obs: int
    n_clusters: int
    n_msas: int

    # Specification
    bandwidth: str
    bandwidth_value: float
    control_function: str
    controls: List[str]

    # R-squared
    r_squared: float
    r_squared_adj: float

    # Full coefficient table
    coef_table: Optional[pd.DataFrame] = None

    def __str__(self):
        sig = ""
        if self.p_value < 0.01:
            sig = "***"
        elif self.p_value < 0.05:
            sig = "**"
        elif self.p_value < 0.10:
            sig = "*"

        return (
            f"RD Estimate (h={self.bandwidth_value}):\n"
            f"  β = {self.beta:.4f}{sig} (SE = {self.se:.4f})\n"
            f"  95% CI: [{self.ci_lower:.4f}, {self.ci_upper:.4f}]\n"
            f"  N = {self.n_obs:,}, MSAs = {self.n_msas}, R² = {self.r_squared:.3f}"
        )


class BhuttaRDEstimator:
    """
    Regression Discontinuity estimator following Bhutta (2011).
    """

    def __init__(self, config: Optional[RDConfig] = None):
        self.config = config or RDConfig()

        if not HAS_STATSMODELS:
            raise ImportError(
                "statsmodels required for RD estimation. "
                "Install with: pip install statsmodels"
            )

    def estimate(
        self,
        df: pd.DataFrame,
        bandwidth: str = "narrow",
        controls: Optional[List[str]] = None,
        msa_size: Optional[str] = None,
    ) -> RDResult:
        """
        Estimate RD treatment effect.

        Args:
            df: Analysis sample from BhuttaSampleConstructor
            bandwidth: "narrow" (h=0.05) or "wide" (h=0.30)
            controls: List of control variable names (default: Bhutta's controls)
            msa_size: Filter to specific MSA size ("small", "medium", "large")

        Returns:
            RDResult with coefficient estimates and statistics
        """
        # Prepare data
        data = self._prepare_data(df, bandwidth, controls, msa_size)

        # Build formula
        formula = self._build_formula(bandwidth, controls)

        # Run regression
        result = self._run_regression(data, formula)

        return result

    def estimate_all_sizes(
        self,
        df: pd.DataFrame,
        bandwidth: str = "narrow",
        controls: Optional[List[str]] = None,
    ) -> Dict[str, RDResult]:
        """
        Estimate RD for each MSA size category.

        Returns dict with keys: "all", "small", "medium", "large"
        """
        results = {}

        # All MSAs
        results["all"] = self.estimate(df, bandwidth, controls, msa_size=None)

        # By MSA size
        for size in ["small", "medium", "large"]:
            if "msa_size" in df.columns and (df["msa_size"] == size).any():
                results[size] = self.estimate(df, bandwidth, controls, msa_size=size)

        return results

    def compare_specifications(
        self,
        df: pd.DataFrame,
        specifications: Optional[List[Dict]] = None,
    ) -> pd.DataFrame:
        """
        Compare results across different specifications.

        Default compares:
        - Narrow vs wide bandwidth
        - With and without controls
        - Different MSA sizes
        """
        if specifications is None:
            specifications = [
                {
                    "bandwidth": "narrow",
                    "controls": None,
                    "msa_size": None,
                    "label": "All MSAs, h=0.05",
                },
                {
                    "bandwidth": "narrow",
                    "controls": None,
                    "msa_size": "large",
                    "label": "Large MSAs, h=0.05",
                },
                {
                    "bandwidth": "wide",
                    "controls": None,
                    "msa_size": None,
                    "label": "All MSAs, h=0.30 (cubic)",
                },
                {
                    "bandwidth": "wide",
                    "controls": None,
                    "msa_size": "large",
                    "label": "Large MSAs, h=0.30 (cubic)",
                },
            ]

        results = []
        for spec in specifications:
            try:
                result = self.estimate(
                    df,
                    bandwidth=spec.get("bandwidth", "narrow"),
                    controls=spec.get("controls"),
                    msa_size=spec.get("msa_size"),
                )
                results.append(
                    {
                        "label": spec.get("label", ""),
                        "beta": result.beta,
                        "se": result.se,
                        "t_stat": result.t_stat,
                        "p_value": result.p_value,
                        "n_obs": result.n_obs,
                        "n_msas": result.n_msas,
                        "bandwidth": result.bandwidth_value,
                        "r_squared": result.r_squared,
                    }
                )
            except Exception as e:
                results.append(
                    {
                        "label": spec.get("label", ""),
                        "error": str(e),
                    }
                )

        return pd.DataFrame(results)

    def _prepare_data(
        self,
        df: pd.DataFrame,
        bandwidth: str,
        controls: Optional[List[str]],
        msa_size: Optional[str],
    ) -> pd.DataFrame:
        """Prepare data for regression."""
        data = df.copy()

        # Filter by bandwidth
        h = self.config.bandwidths[bandwidth]
        lower = self.config.cutoff - h
        upper = self.config.cutoff + h
        data = data[(data["TM"] >= lower) & (data["TM"] <= upper)]

        # Filter by MSA size
        if msa_size is not None and "msa_size" in data.columns:
            data = data[data["msa_size"] == msa_size]

        # Ensure required columns
        required = [
            self.config.outcome_var,
            self.config.treatment_var,
            self.config.running_var,
            self.config.fe_var,
        ]
        missing = [c for c in required if c not in data.columns]
        if missing:
            raise ValueError(f"Missing required columns: {missing}")

        # Add polynomial terms for cubic specification
        if bandwidth == "wide":
            data["TM_centered_2"] = data[self.config.running_var] ** 2
            data["TM_centered_3"] = data[self.config.running_var] ** 3
            # Interactions with treatment
            data["TM_D"] = (
                data[self.config.running_var] * data[self.config.treatment_var]
            )
            data["TM2_D"] = data["TM_centered_2"] * data[self.config.treatment_var]
            data["TM3_D"] = data["TM_centered_3"] * data[self.config.treatment_var]

        # Handle controls
        ctrl_vars = controls or self.config.default_controls
        ctrl_vars = [c for c in ctrl_vars if c in data.columns]

        # Drop rows with missing values
        all_vars = (
            required
            + ctrl_vars
            + (["TM_centered_2", "TM_centered_3"] if bandwidth == "wide" else [])
        )
        data = data.dropna(subset=all_vars)

        return data

    def _build_formula(
        self,
        bandwidth: str,
        controls: Optional[List[str]],
    ) -> str:
        """Build regression formula."""
        # Outcome
        formula = f"{self.config.outcome_var} ~ "

        # Treatment
        formula += f"{self.config.treatment_var}"

        # Control function
        if bandwidth == "narrow":
            # Linear
            formula += f" + {self.config.running_var}"
            # Allow different slopes on each side
            formula += f" + {self.config.running_var}:{self.config.treatment_var}"
        else:
            # Cubic
            formula += f" + {self.config.running_var}"
            formula += f" + TM_centered_2 + TM_centered_3"
            # Allow different polynomials on each side
            formula += f" + TM_D + TM2_D + TM3_D"

        # Controls
        ctrl_vars = controls or self.config.default_controls
        ctrl_vars = [
            c
            for c in ctrl_vars
            if c not in [self.config.outcome_var, self.config.treatment_var]
        ]
        if ctrl_vars:
            formula += " + " + " + ".join(ctrl_vars)

        # Fixed effects (handled separately)
        formula += f" + C({self.config.fe_var})"

        return formula

    def _run_regression(self, data: pd.DataFrame, formula: str) -> RDResult:
        """Run OLS regression with clustered standard errors."""
        # Fit model
        model = smf.ols(formula, data=data)

        # Clustered standard errors
        results = model.fit(
            cov_type="cluster",
            cov_kwds={"groups": data[self.config.cluster_var]},
        )

        # Extract treatment coefficient
        treatment_var = self.config.treatment_var
        beta = results.params[treatment_var]
        se = results.bse[treatment_var]
        t_stat = results.tvalues[treatment_var]
        p_value = results.pvalues[treatment_var]
        ci = results.conf_int().loc[treatment_var]

        # Build coefficient table
        coef_table = pd.DataFrame(
            {
                "coef": results.params,
                "se": results.bse,
                "t": results.tvalues,
                "p": results.pvalues,
            }
        )

        # Determine bandwidth
        bandwidth = "narrow" if "TM_centered_2" not in data.columns else "wide"
        h = self.config.bandwidths[bandwidth]
        cf = self.config.control_functions[bandwidth]

        return RDResult(
            beta=beta,
            se=se,
            t_stat=t_stat,
            p_value=p_value,
            ci_lower=ci[0],
            ci_upper=ci[1],
            n_obs=int(results.nobs),
            n_clusters=data[self.config.cluster_var].nunique(),
            n_msas=data[self.config.fe_var].nunique(),
            bandwidth=bandwidth,
            bandwidth_value=h,
            control_function=cf,
            controls=list(self.config.default_controls),
            r_squared=results.rsquared,
            r_squared_adj=results.rsquared_adj,
            coef_table=coef_table,
        )


def run_bhutta_rd(
    sample_df: pd.DataFrame,
    bandwidth: str = "narrow",
    msa_size: str = "large",
) -> RDResult:
    """
    Convenience function to run Bhutta RD estimation.

    Args:
        sample_df: Output from BhuttaSampleConstructor
        bandwidth: "narrow" (h=0.05) or "wide" (h=0.30)
        msa_size: "all", "small", "medium", "large"

    Returns:
        RDResult object

    Example:
        >>> result = run_bhutta_rd(sample_df, bandwidth="narrow", msa_size="large")
        >>> print(result)
        RD Estimate (h=0.05):
          β = 0.0764** (SE = 0.0274)
          95% CI: [0.0227, 0.1301]
          N = 1,800, MSAs = 47, R² = 0.654
    """
    estimator = BhuttaRDEstimator()

    msa_filter = None if msa_size == "all" else msa_size

    return estimator.estimate(
        sample_df,
        bandwidth=bandwidth,
        msa_size=msa_filter,
    )


def replicate_bhutta_table2(sample_df: pd.DataFrame) -> pd.DataFrame:
    """
    Replicate Bhutta (2011) Table 2 results.

    Returns DataFrame with estimates comparable to Table 2:
    - All MSAs
    - Small MSAs
    - Medium MSAs
    - Large MSAs
    For both narrow (h=0.05) and wide (h=0.30) bandwidths.
    """
    estimator = BhuttaRDEstimator()

    results = []

    for bw in ["narrow", "wide"]:
        for size in [None, "small", "medium", "large"]:
            try:
                result = estimator.estimate(sample_df, bandwidth=bw, msa_size=size)
                size_label = size or "all"

                # Significance stars
                sig = ""
                if result.p_value < 0.01:
                    sig = "***"
                elif result.p_value < 0.05:
                    sig = "**"
                elif result.p_value < 0.10:
                    sig = "*"

                results.append(
                    {
                        "MSA Size": size_label.title(),
                        "Bandwidth": f"h={result.bandwidth_value}",
                        "β": f"{result.beta:.4f}{sig}",
                        "SE": f"({result.se:.4f})",
                        "N": result.n_obs,
                        "MSAs": result.n_msas,
                        "R²": f"{result.r_squared:.3f}",
                    }
                )
            except Exception as e:
                results.append(
                    {
                        "MSA Size": (size or "all").title(),
                        "Bandwidth": bw,
                        "Error": str(e)[:50],
                    }
                )

    return pd.DataFrame(results)
