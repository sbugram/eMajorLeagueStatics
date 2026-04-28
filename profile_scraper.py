import os
import json
import time
import requests
import logging
from bs4 import BeautifulSoup
from api_client import EMajorLeagueAPI

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

CACHE_FILE = "player_profiles_cache.json"

class ProfileScraper:
    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        self.cache = self.load_cache()

    def load_cache(self):
        if os.path.exists(CACHE_FILE):
            try:
                with open(CACHE_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error loading cache: {e}")
        return {}

    def save_cache(self):
        try:
            with open(CACHE_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.cache, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Error saving cache: {e}")

    def scrape_profile(self, user_id):
        url = f"https://www.emajorleague.com/players/profile/{user_id}/"
        try:
            r = requests.get(url, headers=self.headers, timeout=10)
            if r.status_code == 200:
                soup = BeautifulSoup(r.text, 'html.parser')
                data = {
                    "detailed_position": "",
                    "team": "",
                    "totw": 0,
                    "potm": 0,
                    "tots": 0,
                    "toty": 0
                }
                
                # Parse Position
                for li in soup.find_all('li'):
                    text = li.get_text(separator=" ", strip=True)
                    if 'Position:' in text:
                        pos = text.replace('Position:', '').strip()
                        data['detailed_position'] = pos
                        
                # Parse Successes
                success_tags = soup.find_all(string=lambda t: t and ('x TOTW' in t or 'x POTM' in t or 'x TOTS' in t or 'x TOTY' in t))
                for s in success_tags:
                    s_str = str(s).strip()
                    try:
                        count = int(s_str.split('x')[0].strip())
                        if 'TOTW' in s_str: data['totw'] = count
                        elif 'POTM' in s_str: data['potm'] = count
                        elif 'TOTS' in s_str: data['tots'] = count
                        elif 'TOTY' in s_str: data['toty'] = count
                    except:
                        pass
                
                # Parse Team
                team_links = soup.find_all('a', href=lambda h: h and '/teams/team/' in h)
                if team_links:
                    data['team'] = team_links[0].get_text(strip=True)
                    
                return data
            else:
                logger.warning(f"Failed to fetch {url} (Status: {r.status_code})")
        except Exception as e:
            logger.error(f"Error scraping {url}: {e}")
            
        return None

    def run(self, limit=50, force_update=False):
        api = EMajorLeagueAPI()
        # Fetch a batch to start enriching. You can increase limit if you want to scrape everyone.
        records = api.fetch_players(limit=limit)
        
        updates = 0
        for i, rec in enumerate(records):
            user_id = str(rec.get("player__user_id"))
            username = rec.get("player__origin_id")
            if not user_id or user_id == "None":
                continue
                
            if not force_update and user_id in self.cache:
                continue
                
            logger.info(f"Scraping [{i+1}/{len(records)}] {username} (ID: {user_id})...")
            profile_data = self.scrape_profile(user_id)
            
            if profile_data:
                self.cache[user_id] = profile_data
                updates += 1
                
            time.sleep(0.5) # Be polite
            
            # Save every 10 updates so we don't lose progress
            if updates % 10 == 0:
                self.save_cache()
                
        if updates > 0:
            self.save_cache()
            logger.info(f"Scraping complete. Updated {updates} profiles.")
        else:
            logger.info("Scraping complete. No new profiles needed updating.")

if __name__ == "__main__":
    scraper = ProfileScraper()
    scraper.run(limit=5000) # Fetch up to 5000 players
