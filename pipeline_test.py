from api_client import EMajorLeagueAPI
from processing import DataProcessor

def test_pipeline():
    api = EMajorLeagueAPI()
    records = api.fetch_players(limit=5)
    
    processor = DataProcessor()
    df = processor.process_player_records(records)
    
    print("DataFrame Head:")
    print(df.to_string())

if __name__ == "__main__":
    test_pipeline()
