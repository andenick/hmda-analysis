
def process_historical_year(year: int, source_type: str = "auto"):
    """
    Process any historical year using the complete R methodology.

    Parameters:
    - year: Year to process (1990-2024)
    - source_type: "r_processed", "raw_lar", "historical_archive", "auto"
    """

    if source_type == "r_processed" or (source_type == "auto" and
                                       os.path.exists(f"data/r_replication/{year}_lar_race_step9.csv")):
        # Load existing R processed data
        return pd.read_csv(f"data/r_replication/{year}_lar_race_step9.csv")

    elif source_type == "raw_lar" or (source_type == "auto" and
                                     os.path.exists(f"data/hmda/raw/{year}")):
        # Process raw LAR data using R methodology
        from r_methodology_replication import RMethodologyReplicator
        replicator = RMethodologyReplicator()

        lar_path = f"data/hmda/raw/{year}/{year}_public_lar_csv/{year}_public_lar_csv.csv"
        lar_df = replicator._load_lar_efficiently(lar_path, sample_rate=0.1)
        result_df = replicator.create_institution_county_matrix(lar_df, year)
        result_df = replicator.add_statistical_functions(result_df)

        # Save processed result
        os.makedirs("data/r_replication", exist_ok=True)
        result_df.to_csv(f"data/r_replication/{year}_lar_race_step9_python.csv", index=False)

        return result_df

    elif source_type == "historical_archive":
        # Process historical archive data
        # This would require specific handling for pre-2017 data formats
        logger.warning(f"Historical archive processing for {year} not yet implemented")
        return pd.DataFrame()

    else:
        logger.error(f"No data source found for year {year}")
        return pd.DataFrame()

def create_temporal_analysis(years: List[int]):
    """Create temporal analysis across multiple years."""

    combined_data = []

    for year in years:
        year_data = process_historical_year(year)
        if not year_data.empty:
            combined_data.append(year_data)

    if combined_data:
        temporal_df = pd.concat(combined_data, ignore_index=True)

        # Add temporal analysis variables
        temporal_df['year_group'] = pd.cut(temporal_df['activity_year'],
                                         bins=[1989, 1999, 2009, 2019, 2025],
                                         labels=['1990s', '2000s', '2010s', '2020s'])

        # Calculate temporal trends for key variables
        trend_vars = ['HL_Loan_Orig_Black_BILow', 'HL_Loan_Orig_Total_BILow']
        for var in trend_vars:
            if var in temporal_df.columns:
                temporal_df[f'{var}_trend'] = temporal_df.groupby('id_rssd')[var].pct_change()

        return temporal_df

    return pd.DataFrame()
