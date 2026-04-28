import time
from team_scraper import scrape_team_list, scrape_team_squad

# Test 1: How fast does the list load from cache if it exists?
t0 = time.time()
teams = scrape_team_list(force_refresh=False)
t1 = time.time()
print(f"Team list load: {t1-t0:.2f}s, count={len(teams)}")

# Test 2: Force refresh the list (37 pages concurrently)
t0 = time.time()
teams2 = scrape_team_list(force_refresh=True, workers=12)
t1 = time.time()
print(f"Team list CONCURRENT refresh: {t1-t0:.2f}s, count={len(teams2)}")

# Test 3: Scrape 5 squads sequentially vs concurrently
from concurrent.futures import ThreadPoolExecutor, as_completed
sample = teams[:5]

t0 = time.time()
for t in sample:
    scrape_team_squad(t['name'], t['url'])
t_seq = time.time() - t0

t0 = time.time()
with ThreadPoolExecutor(max_workers=5) as pool:
    list(pool.map(lambda t: scrape_team_squad(t['name'], t['url']), sample))
t_con = time.time() - t0

print(f"\nSquad scrape (5 teams) - Sequential: {t_seq:.2f}s | Concurrent: {t_con:.2f}s | Speedup: {t_seq/t_con:.1f}x")
