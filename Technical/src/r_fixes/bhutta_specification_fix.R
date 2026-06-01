# Bhutta (2011) Specification Fix
# This script modifies the R code to match Bhutta's paper methodology
#
# Key changes:
# 1. REMOVE central_city_flag == 1 filter (line 657 in original)
# 2. Use total housing units >= 100 (not owner-occupied)
# 3. Add group quarters filter (< 30% in group quarters)
#
# To use: Source this file before running the regression section
# Or modify HMDA_RDandGraphs_NA.Rmd directly

# ============================================================
# MODIFIED SECTION 2.12 - Filter down to analysis sample
# ============================================================

# ORIGINAL CODE (PROBLEMATIC):
# combined_data6 <- combined_data5 %>% filter(central_city_flag == 1)

# FIXED CODE (Match Bhutta):
# Skip the central city filter entirely
combined_data6 <- combined_data5

# Write to CSV for comparison
write.csv(combined_data6, paste0(e2outPath, "combined_lar_step16_bhutta_spec", sufPath), row.names = TRUE)

# ============================================================
# MODIFIED SECTION 2.13 - Additional filters
# ============================================================

# ORIGINAL CODE:
# combined_data7 <- combined_data6 %>%
#   mutate(state_code = state_code.x) %>%
#   mutate(county_code = county_code.x) %>%
#   filter(state_code != 2) %>%
#   filter(state_code != 15) %>%
#   filter(ownOcc_housingUnits >= 100) %>%  # <-- CHANGE THIS
#   ...

# FIXED CODE (Match Bhutta):
combined_data7 <- combined_data6 %>%
    mutate(state_code = state_code.x) %>%
    mutate(county_code = county_code.x) %>%
    filter(state_code != 2) %>%
    filter(state_code != 15) %>%
    # Use TOTAL housing units >= 100, not owner-occupied
    filter(totalHousingUnits >= 100) %>%
    # Add group quarters filter (< 30%)
    # Note: Requires group_quarters_pop and total_pop columns
    # filter(group_quarters_pop / population < 0.30) %>%
    select(
        -msamd.x,
        -state_code.x, -state_code.y,
        -county_code.x, -county_code.y,
        -...1, -...2,
        -loan_amount,
        -duplicate_tract_flag,
        -split_tract_flag
    )

# ============================================================
# Additional Control Variables (to match Bhutta's 12+ controls)
# ============================================================

# Bhutta uses these controls that may be missing:
# - % age 65+
# - Log owner-occupied units (not total)
# - % single-family housing
# - % 2-4 family housing
# - % 5+ family housing
# - % group quarters

# Add log owner-occupied if not present
if (!"ln_ownOcc_housingUnits" %in% names(combined_data7)) {
    combined_data7$ln_ownOcc_housingUnits <- log(combined_data7$ownOcc_housingUnits)
}

# Update control columns to match Bhutta
control_columns_bhutta <- c(
    "minority_percentage",
    "ln_ownOcc_housingUnits", # Changed from total to owner-occupied
    "ln_ownOcc_housingUnits_medianValue",
    "poverty_level_percentage",
    "prop_pre1940",
    "prop_1940_1969"
    # Add these if available in your data:
    # "pct_age_65_over",
    # "pct_single_family",
    # "pct_multifamily",
    # "pct_group_quarters"
)

# ============================================================
# SAMPLE SIZE CHECK
# ============================================================

# Print sample sizes to verify closer to Bhutta's counts
cat("\n====== SAMPLE SIZE CHECK ======\n")
cat("Total observations:", nrow(combined_data7), "\n")

# By MSA size (if msa_size variable exists)
if ("msa_size" %in% names(combined_data7)) {
    cat("\nBy MSA Size:\n")
    print(table(combined_data7$msa_size))
}

# By bandwidth (narrow h=0.05)
narrow_sample <- combined_data7 %>%
    filter(abs(decennial_msa_median_family_income_percentage - 0.80) <= 0.05)
cat("\nNarrow bandwidth (h=0.05):", nrow(narrow_sample), "\n")

# By bandwidth (wide h=0.30)
wide_sample <- combined_data7 %>%
    filter(abs(decennial_msa_median_family_income_percentage - 0.80) <= 0.30)
cat("Wide bandwidth (h=0.30):", nrow(wide_sample), "\n")

# Bhutta targets:
# - Large MSAs, h=0.05: ~1,800 tracts
# - Large MSAs, h=0.30: ~8,000 tracts

cat("\n====== EXPECTED BHUTTA TARGETS ======\n")
cat("Large MSAs, h=0.05: ~1,800 tracts\n")
cat("Large MSAs, h=0.30: ~8,000 tracts\n")
