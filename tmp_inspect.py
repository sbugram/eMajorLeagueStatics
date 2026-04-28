from api_client import EMajorLeagueAPI
import json

if __name__ == "__main__":
    api = EMajorLeagueAPI()
    records = api.fetch_players(limit=1)
    if records:
        print("Keys available in JSON:")
        for k, v in records[0].items():
            print(f"- {k}: {v}")
