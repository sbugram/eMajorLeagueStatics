import json, requests, re
from bs4 import BeautifulSoup

# 1. Check player_profiles_cache for team data
with open('player_profiles_cache.json', encoding='utf-8') as f:
    cache = json.load(f)

print("=== PLAYER PROFILES CACHE ===")
for uid, data in list(cache.items())[:3]:
    print(f"uid={uid}: keys={list(data.keys())}")
has_team = sum(1 for v in cache.values() if v.get('team') and v.get('team') != 'Unknown')
print(f"Total: {len(cache)}, with team: {has_team}")

# 2. Check if /teams/team/<id>/0/ URL pattern gives us team ID in a predictable range
# Extract all team IDs from team_player_cache if it exists
try:
    with open('team_player_cache.json', encoding='utf-8') as f:
        tc = json.load(f)
    print(f"\nteam_player_cache entries: {len(tc)}")
    sample = list(tc.items())[:2]
    for k, v in sample:
        print(f"  key={k}: {v}")
except FileNotFoundError:
    print("No team_player_cache yet")

# 3. Probe /teams/?letter=A, /teams/?search=, /teams/all  
print("\n=== PROBING ALTERNATIVE ENDPOINTS ===")
for u in [
    'https://www.emajorleague.com/teams/?letter=A',
    'https://www.emajorleague.com/teams/all/',
]:
    r = requests.get(u, timeout=5, allow_redirects=True)
    team_links = re.findall(r'/teams/team/(\d+)', r.text)
    print(f"{u} -> status={r.status_code}, team IDs count={len(set(team_links))}")

# 4. Measure concurrent vs sequential fetch time difference on 5 sample pages
import time, threading
sample_pages = [f'https://www.emajorleague.com/teams/{i}/' for i in range(1, 6)]
results_seq = {}
t0 = time.time()
for u in sample_pages:
    r = requests.get(u, timeout=10)
    results_seq[u] = len(re.findall(r'/teams/team/(\d+)', r.text))
t_seq = time.time() - t0

# Concurrent
results_con = {}
def fetch(u):
    r = requests.get(u, timeout=10)
    results_con[u] = len(re.findall(r'/teams/team/(\d+)', r.text))

t0 = time.time()
threads = [threading.Thread(target=fetch, args=(u,)) for u in sample_pages]
for t in threads: t.start()
for t in threads: t.join()
t_con = time.time() - t0

print(f"\nSequential 5 pages: {t_seq:.2f}s  |  Concurrent 5 pages: {t_con:.2f}s")
print(f"Speedup ratio: {t_seq/t_con:.1f}x")
