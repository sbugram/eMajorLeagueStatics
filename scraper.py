import requests
import json

def fetch_data():
    url = "https://www.emajorleague.com/player_statistics_data/"
    params = {
        "draw": "1",
        "start": "0",
        "length": "10",
        "season": "",
        "position": "",
        "tournament": ""
    }
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    
    print("Fetching API...")
    response = requests.get(url, params=params, headers=headers)
    
    if response.status_code == 200:
        try:
            data = response.json()
            print(f"Total records: {data.get('recordsTotal', 'Unknown')}")
            records = data.get('data', [])
            print(f"Returned records: {len(records)}")
            if len(records) > 0:
                print("First record structure:")
                print(json.dumps(records[0], indent=2))
        except Exception as e:
            print("Could not parse JSON:", e)
            print(response.text[:200])
    else:
        print(f"Failed with status: {response.status_code}")

if __name__ == "__main__":
    fetch_data()
