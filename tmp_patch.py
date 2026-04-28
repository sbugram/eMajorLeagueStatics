import pandas as pd
import os
import json

with open('processing.py', 'r', encoding='utf-8') as f:
    current = f.read()

# The new method to append
new_method = """
    @staticmethod
    def load_team_player_data(min_matches_threshold: int = 10):
        cache_file = "team_player_cache.json"
        if not os.path.exists(cache_file):
            return pd.DataFrame(), pd.DataFrame()
        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            print(f"Error loading team player cache: {e}")
            return pd.DataFrame(), pd.DataFrame()
        rows = []
        for key, p in data.items():
            username = p.get("username", key)
            team     = p.get("team", "Unknown")
            pos      = p.get("position", "Unknown")
            parts    = pos.replace("/", " ").split() if pos and pos.strip() not in ("", "Unknown") else []
            primary  = parts[0].upper() if parts else "Unknown"
            m_raw    = int(p.get("matches", 0))
            m        = max(m_raw, 1)
            g        = int(p.get("goals", 0))
            a        = int(p.get("assists", 0))
            rows.append({
                "Username":          username,
                "Team":              team,
                "Detailed_Position": pos,
                "Primary_Position":  primary,
                "Matches":           m_raw,
                "Goals":             g,
                "Assists":           a,
                "MOTM":              int(p.get("motm", 0)),
                "Rating":            float(p.get("rating", 0.0)),
                "Goals_Per_Match":   round(g / m, 3),
                "Assists_Per_Match": round(a / m, 3),
                "Source":            "team_page",
            })
        if not rows:
            return pd.DataFrame(), pd.DataFrame()
        full_df      = pd.DataFrame(rows)
        low_match_df = full_df[full_df["Matches"] < min_matches_threshold].copy()
        return full_df, low_match_df
"""

with open('processing.py', 'w', encoding='utf-8') as f:
    f.write(current.rstrip() + "\n" + new_method)

print("Done. Verifying...")
import importlib.util, sys
spec = importlib.util.spec_from_file_location("processing", "processing.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
print("processing.py loaded OK")
dp = mod.DataProcessor()
full, low = mod.DataProcessor.load_team_player_data()
print(f"full_df rows: {len(full)}, low_match rows: {len(low)}")
