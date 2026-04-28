"""
team_scraper.py - Scrapes player data from team pages on eMajorLeague.com
Supplements the main API (10+ matches only) with Goals/Assists/Matches/Rating
for ALL squad members including low-match players.

Anti-block strategy:
- Sequential requests only (no concurrent workers)
- Realistic browser headers + Referer chain
- Random delay between requests (1.0-2.5s)
- Exponential backoff retry on failures
- Guards against saving empty/bad cache results
"""
import os
import json
import re
import time
import random
import logging
import requests
from bs4 import BeautifulSoup

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

BASE_URL        = "https://www.emajorleague.com"
TEAM_CACHE_FILE = "team_player_cache.json"
TEAM_LIST_FILE  = "team_list_cache.json"

# Realistic browser headers
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "same-origin",
    "Referer": BASE_URL + "/",
}

COL_POS     = 0
COL_PLAYER  = 1
COL_MATCHES = 2
COL_GOALS   = 3
COL_ASSISTS = 4
COL_MOTM    = 5
COL_RATING  = 8

# Delay range between page requests (seconds) — mimics human browsing
MIN_DELAY = 0.8
MAX_DELAY = 2.0


def _polite_sleep():
    time.sleep(random.uniform(MIN_DELAY, MAX_DELAY))


def _safe_float(val):
    try:
        return float(val)
    except (ValueError, TypeError):
        return 0.0


def _safe_int(val):
    try:
        return int(val)
    except (ValueError, TypeError):
        return 0


def _get_with_retry(session: requests.Session, url: str,
                    retries: int = 3, backoff: float = 3.0) -> requests.Response | None:
    """GET via shared session with exponential-backoff retry."""
    for attempt in range(retries):
        try:
            resp = session.get(url, headers=HEADERS, timeout=20)
            if resp.status_code == 200:
                return resp
            if resp.status_code == 403:
                logger.error(f"403 Forbidden on {url} — IP may be blocked. Stopping.")
                return None
            logger.warning(f"HTTP {resp.status_code} on {url} (attempt {attempt+1}/{retries})")
        except Exception as e:
            logger.warning(f"Error on {url} (attempt {attempt+1}/{retries}): {e}")
        if attempt < retries - 1:
            wait = backoff * (2 ** attempt)
            logger.info(f"Retrying in {wait:.0f}s…")
            time.sleep(wait)
    logger.error(f"Giving up on {url} after {retries} attempts.")
    return None


# ---------------------------------------------------------------------------
# Team List Discovery
# ---------------------------------------------------------------------------

def scrape_team_list(session: requests.Session,
                     force_refresh: bool = False) -> list:
    """
    Returns all teams: [{"name": ..., "url": ...}, ...].
    Caches the list in team_list_cache.json to skip re-crawl on future runs.
    Only saves the cache if at least 10 teams were found (guards against
    saving an empty/partial result caused by temporary site issues).
    """
    if not force_refresh and os.path.exists(TEAM_LIST_FILE):
        try:
            with open(TEAM_LIST_FILE, "r", encoding="utf-8") as f:
                cached = json.load(f)
            if len(cached) >= 10:
                logger.info(f"Team list loaded from cache ({len(cached)} teams). "
                            f"Use --refresh-list to re-crawl.")
                return cached
            else:
                logger.warning("Cached team list looks incomplete — re-crawling.")
        except Exception as e:
            logger.warning(f"Could not read team list cache: {e}")

    # Discover last page
    resp = _get_with_retry(session, f"{BASE_URL}/teams/")
    if not resp:
        logger.error("Cannot reach /teams/ — aborting team list crawl.")
        return []

    nums = [int(m.group(1)) for a in BeautifulSoup(resp.text, "html.parser").find_all("a", href=True)
            if (m := re.search(r"/teams/(\d+)/?", a["href"]))]
    last_page = max(nums) if nums else 1
    logger.info(f"Teams listing has {last_page} pages — crawling sequentially…")

    seen_urls: set = set()
    teams: list = []

    for page_num in range(1, last_page + 1):
        url = f"{BASE_URL}/teams/{page_num}/"
        page_resp = _get_with_retry(session, url)
        if not page_resp:
            logger.warning(f"Skipping listing page {page_num}.")
            _polite_sleep()
            continue

        soup = BeautifulSoup(page_resp.text, "html.parser")
        for a in soup.find_all("a", href=lambda h: h and "/teams/team/" in h):
            href = a.get("href", "")
            name = a.get_text(strip=True)
            if not href or not name:
                continue
            if href.startswith("/"):
                href = f"{BASE_URL}{href}"
            if href not in seen_urls:
                seen_urls.add(href)
                teams.append({"name": name, "url": href})

        logger.info(f"  Page {page_num}/{last_page}: {len(teams)} teams so far.")
        _polite_sleep()

    teams.sort(key=lambda t: t["name"].lower())
    logger.info(f"Found {len(teams)} unique teams.")

    if len(teams) >= 10:
        try:
            with open(TEAM_LIST_FILE, "w", encoding="utf-8") as f:
                json.dump(teams, f, ensure_ascii=False, indent=2)
            logger.info(f"Team list cached → {TEAM_LIST_FILE}")
        except Exception as e:
            logger.error(f"Could not save team list cache: {e}")
    else:
        logger.warning(f"Only {len(teams)} teams found — NOT saving cache (possible block/error).")

    return teams


# ---------------------------------------------------------------------------
# Squad Scraping
# ---------------------------------------------------------------------------

def scrape_team_squad(session: requests.Session,
                      team_name: str, team_url: str) -> list:
    """
    Scrape squad table from a single team page.
    Returns per-player dicts with Goals/Assists/Matches/Rating/MOTM.
    Tackles/Passes/Saves intentionally omitted (not on team pages).
    """
    resp = _get_with_retry(session, team_url)
    if not resp:
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    tables = soup.find_all("table")

    squad_table = None
    max_ths = 0
    for t in tables:
        n = len(t.find_all("th"))
        if n > max_ths:
            max_ths = n
            squad_table = t

    if squad_table is None or max_ths < 5:
        logger.warning(f"No squad table for '{team_name}'")
        return []

    tbody = squad_table.find("tbody")
    if not tbody:
        return []

    players = []
    for row in tbody.find_all("tr"):
        cells = row.find_all("td")
        if len(cells) < 9:
            continue

        position = cells[COL_POS].get_text(strip=True)
        link = cells[COL_PLAYER].find("a")
        username    = link.get_text(strip=True) if link else cells[COL_PLAYER].get_text(strip=True)
        player_href = link.get("href", "") if link else ""

        players.append({
            "username":    username,
            "team":        team_name,
            "position":    position,
            "matches":     _safe_int(cells[COL_MATCHES].get_text(strip=True)),
            "goals":       _safe_int(cells[COL_GOALS].get_text(strip=True)),
            "assists":     _safe_int(cells[COL_ASSISTS].get_text(strip=True)),
            "motm":        _safe_int(cells[COL_MOTM].get_text(strip=True)),
            "rating":      _safe_float(cells[COL_RATING].get_text(strip=True)),
            "player_href": player_href,
            "source":      "team_page",
        })
    return players


# ---------------------------------------------------------------------------
# Cache Helpers
# ---------------------------------------------------------------------------

def load_team_cache() -> dict:
    if os.path.exists(TEAM_CACHE_FILE):
        try:
            with open(TEAM_CACHE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading player cache: {e}")
    return {}


def save_team_cache(cache: dict):
    try:
        with open(TEAM_CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(cache, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Error saving player cache: {e}")


# ---------------------------------------------------------------------------
# Main Run
# ---------------------------------------------------------------------------

def run(force_update: bool = False, refresh_list: bool = False):
    """
    Full sequential scrape pipeline.
    Uses a shared requests.Session for cookie persistence and keep-alive.
    """
    session = requests.Session()
    # Warm up the session with a visit to the main page (get cookies)
    logger.info("Warming up session…")
    try:
        session.get(BASE_URL + "/", headers=HEADERS, timeout=15)
        time.sleep(1.5)
    except Exception as e:
        logger.warning(f"Warm-up failed: {e}")

    cache = load_team_cache()
    teams = scrape_team_list(session, force_refresh=refresh_list)

    if not teams:
        logger.error("No teams found. The site may be temporarily blocking requests. "
                     "Wait a few minutes and try again.")
        return cache

    # Skip already-cached teams unless forcing
    if not force_update:
        cached_teams = {p["team"] for p in cache.values()}
        teams_to_scrape = [t for t in teams if t["name"] not in cached_teams]
        skip = len(teams) - len(teams_to_scrape)
        if skip:
            logger.info(f"Skipping {skip} already-cached teams. "
                        f"Scraping {len(teams_to_scrape)} new teams.")
    else:
        teams_to_scrape = teams

    if not teams_to_scrape:
        logger.info("All teams already cached. Use --force to re-scrape.")
        return cache

    logger.info(f"Scraping {len(teams_to_scrape)} team squad pages sequentially…")
    total_new = 0

    for i, team in enumerate(teams_to_scrape, 1):
        players = scrape_team_squad(session, team["name"], team["url"])
        for p in players:
            key = p["username"].lower()
            if not force_update and key in cache:
                continue
            cache[key] = p
            total_new += 1

        if i % 25 == 0 or i == len(teams_to_scrape):
            pct = i / len(teams_to_scrape) * 100
            logger.info(f"  [{i}/{len(teams_to_scrape)} — {pct:.0f}%] "
                        f"new entries so far: {total_new}")
            # Periodic save so progress isn't lost if interrupted
            save_team_cache(cache)

        _polite_sleep()

    save_team_cache(cache)
    logger.info(f"Done. New/updated: {total_new}. Total cached: {len(cache)}.")
    return cache


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(
        description="Scrape team pages for squad player data."
    )
    parser.add_argument("--force",        action="store_true",
                        help="Re-scrape every player even if already cached.")
    parser.add_argument("--refresh-list", action="store_true",
                        help="Re-crawl team listing pages (rebuilds team_list_cache.json).")
    args = parser.parse_args()
    run(force_update=args.force, refresh_list=args.refresh_list)
