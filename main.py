import argparse
from api_client import EMajorLeagueAPI
from processing import DataProcessor
from analysis import Analyzer

def main():
    parser = argparse.ArgumentParser(description="eMajorLeague Data Analyzer")
    parser.add_argument("--limit", type=int, default=1000, help="Number of records to fetch")
    parser.add_argument("--top-scorers", type=int, help="Show top N scorers")
    parser.add_argument("--top-assists", type=int, help="Show top N assist providers")
    parser.add_argument("--top-contributors", type=int, help="Show top N players by combined Goal Contributions")
    parser.add_argument("--value-efficiency", type=int, help="Show top N most cost-efficient players based on Rating/Fee")
    parser.add_argument("--correlations", action="store_true", help="Print the correlation matrix between different stats")
    parser.add_argument("--tactical-report", type=int, help="Show N players for Playmakers and Defensive Anchors (Tactical insight)")
    parser.add_argument("--player", type=str, help="Search for a specific player by username")
    parser.add_argument("--min-matches", type=int, default=0, help="Filter out players with less than N matches")
    parser.add_argument("--min-rating", type=float, default=0.0, help="Filter out players with less than N average rating")
    
    args = parser.parse_args()
    
    print("Initiating data fetch...")
    api = EMajorLeagueAPI()
    records = api.fetch_players(limit=args.limit)
    
    processor = DataProcessor()
    df = processor.process_player_records(records)
    
    if df.empty:
        print("No data could be processed.")
        return
        
    # Apply flexible filters
    analyzer = Analyzer(df)
    filtered_df = analyzer.filter_data(min_matches=args.min_matches, min_rating=args.min_rating)
    analyzer_filtered = Analyzer(filtered_df)
    
    print(f"\n[Analyzed {len(filtered_df)} players after filters applied]")
    
    # Process actions
    if args.tactical_report:
        print("\n--- TACTICAL REPORT: PLAYMAKERS ---")
        playmakers = analyzer_filtered.find_playmakers(args.tactical_report)
        if not playmakers.empty:
            print(playmakers[['Username', 'Matches', 'Passes', 'Rating']].to_string(index=False))
            
        print("\n--- TACTICAL REPORT: DEFENSIVE ANCHORS ---")
        anchors = analyzer_filtered.find_defensive_anchors(args.tactical_report)
        if not anchors.empty:
            print(anchors[['Username', 'Matches', 'Tackles', 'Def_CS', 'Rating']].to_string(index=False))

    if args.correlations:
        print("\n--- STATISTICAL CORRELATIONS ---")
        corr_matrix = analyzer_filtered.calculate_correlations()
        # Keep only correlations related to Rating to avoid huge tables, or print all
        if not corr_matrix.empty and 'Rating' in corr_matrix.columns:
            print("Correlations with Player Rating:")
            print(corr_matrix['Rating'].sort_values(ascending=False).to_string())
        else:
            print("Could not compute correlations.")

    if args.value_efficiency:
        print("\n--- TRANSFER VALUE EFFICIENCY ---")
        print(analyzer_filtered.value_efficiency(args.value_efficiency, min_matches=args.min_matches).to_string(index=False))

    if args.top_contributors:
        print("\n--- TOP GOAL CONTRIBUTORS (G + A) ---")
        print(analyzer_filtered.top_contributors(args.top_contributors)[['Username', 'Matches', 'Goals', 'Assists', 'Goal_Contributions', 'Contributions_Per_Match']].to_string(index=False))

    if args.top_scorers:
        print("\n--- TOP SCORERS ---")
        print(analyzer_filtered.top_scorers(args.top_scorers)[['Username', 'Matches', 'Goals', 'Goals_Per_Match', 'Rating']].to_string(index=False))
        
    if args.top_assists:
        print("\n--- TOP ASSISTS ---")
        print(analyzer_filtered.top_assists(args.top_assists)[['Username', 'Matches', 'Assists', 'MVP_Ratio', 'Rating']].to_string(index=False))
        
    if args.player:
        print(f"\n--- PLAYER SUMMARY: {args.player} ---")
        summary = analyzer_filtered.player_summary(args.player)
        if summary is not None:
            for k, v in summary.items():
                print(f"{k}: {v}")
        else:
            print("Player not found.")
            
    if not any([args.top_scorers, args.top_assists, args.player, args.correlations, args.value_efficiency, args.top_contributors, args.tactical_report]):

        print("\n--- LEAGUE OVERVIEW ---")
        overview = analyzer_filtered.overall_stats()
        for k, v in overview.items():
            print(f"{k}: {v}")
            
if __name__ == "__main__":
    main()
