import pandas as pd
import json
import os

class DataProcessor:
    @staticmethod
    def process_player_records(raw_records):
        """
        Converts raw API JSON records into a cleaned Pandas DataFrame.
        """
        if not raw_records:
            return pd.DataFrame()
            
        df = pd.DataFrame(raw_records)
        
        # 'pp' column contains HTML or composite strings like '/media/...$$**$$username$$**$$id'
        def extract_username(pp_val):
            if isinstance(pp_val, str) and "$$**$$" in pp_val:
                parts = pp_val.split("$$**$$")
                if len(parts) > 1:
                    return parts[1]
            return pp_val
            
        if 'pp' in df.columns:
            df['Username'] = df['pp'].apply(extract_username)
            
        # Add user_id column from raw records if possible to map cache
        if 'player__user_id' in df.columns:
            df['player__user_id'] = df['player__user_id'].astype(str)
        else:
            df['player__user_id'] = None
            
        # Clean column names
        rename_map = {
            'total_matches': 'Matches',
            'total_mvp': 'MVP',
            'total_goals': 'Goals',
            'total_assists': 'Assists',
            'total_passes': 'Passes',
            'total_tackles': 'Tackles',
            'total_saves': 'Saves',
            'total_defence_clean_sheet': 'Def_CS',
            'total_keeper_clean_sheet': 'GK_CS',
            'avg_rating': 'Rating',
            'player__transfer_fee': 'Transfer_Fee'
        }
        df = df.rename(columns=rename_map)
        
        # Convert numeric columns safely
        numeric_cols = list(rename_map.values())
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
                
        # Select relevant columns
        cols_to_keep = ['Username', 'player__user_id'] + numeric_cols
        actual_cols = [c for c in cols_to_keep if c in df.columns]
        
        df_result = df[actual_cols].copy()
        
        # Merge Cache Data if available
        cache_file = "player_profiles_cache.json"
        if os.path.exists(cache_file) and 'player__user_id' in df_result.columns:
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    cache_data = json.load(f)
                    
                def get_cache_val(uid, key, default):
                    if uid and uid in cache_data:
                        return cache_data[uid].get(key, default)
                    return default
                    
                df_result['Team'] = df_result['player__user_id'].apply(lambda x: get_cache_val(x, 'team', 'Unknown'))
                df_result['Detailed_Position'] = df_result['player__user_id'].apply(lambda x: get_cache_val(x, 'detailed_position', 'Unknown'))
                df_result['Primary_Position'] = df_result['Detailed_Position'].apply(
                    lambda x: x.replace('/', ' ').split()[0].upper() if isinstance(x, str) and x.strip() and x != 'Unknown' else 'Unknown'
                )
                df_result['TOTW'] = df_result['player__user_id'].apply(lambda x: get_cache_val(x, 'totw', 0))
                df_result['POTM'] = df_result['player__user_id'].apply(lambda x: get_cache_val(x, 'potm', 0))
                df_result['TOTS'] = df_result['player__user_id'].apply(lambda x: get_cache_val(x, 'tots', 0))
                df_result['TOTY'] = df_result['player__user_id'].apply(lambda x: get_cache_val(x, 'toty', 0))
            except Exception as e:
                print(f"Error merging cache: {e}")
                
        # Drop player__user_id if not needed anymore, or keep it
        return df_result

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
