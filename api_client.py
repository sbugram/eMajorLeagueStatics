import requests
import logging

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

class EMajorLeagueAPI:
    BASE_URL = "https://www.emajorleague.com/player_statistics_data/"

    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }

    def fetch_players(self, season="", position="", tournament="", limit=1000):
        """
        Fetches player statistics from the eMajorLeague API with auto-pagination.
        """
        params = {
            "draw": "1",
            "start": "0",
            "length": "100",
            "season": season,
            "position": position,
            "tournament": tournament
        }
        all_records = []
        try:
            logger.info("Fetching data from eMajorLeague API...")
            while len(all_records) < limit:
                params["start"] = str(len(all_records))
                response = requests.get(self.BASE_URL, params=params, headers=self.headers)
                response.raise_for_status()
                data = response.json()
                
                records = data.get("data", [])
                if not records:
                    break
                    
                all_records.extend(records)
                
                records_total = int(data.get("recordsFiltered", data.get("recordsTotal", 0)))
                logger.info(f"API Fetching Progress: {len(all_records)} / {records_total} (Limit: {limit})")
                if len(all_records) >= records_total:
                    break
                    
            logger.info(f"Successfully fetched {len(all_records)} records.")
            return all_records[:limit]
        except Exception as e:
            logger.error(f"Error fetching data: {e}")
            return all_records

    def get_filter_options(self):
        """ Scrapes the HTML page for select dropdown options """
        from bs4 import BeautifulSoup
        try:
            r = requests.get("https://www.emajorleague.com/statistics/", headers=self.headers)
            soup = BeautifulSoup(r.text, 'lxml') # Needs bs4 and lxml
            filters = {}
            for select_id in ['season', 'tournament', 'position']:
                select = soup.find('select', {'id': select_id})
                if select:
                    options = {}
                    for opt in select.find_all('option'):
                        val = opt.get('value', '').strip()
                        text = opt.text.strip()
                        if val:  # ignore empty 'Select' options
                            options[text] = val
                    filters[select_id] = options
            return filters
        except Exception as e:
            logger.error(f"Failed to scrape filters from HTML: {e}")
            return {}
