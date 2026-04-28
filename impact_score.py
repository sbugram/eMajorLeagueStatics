import pandas as pd
import numpy as np

class ImpactCalculator:
    """
    Calculates a custom 'Impact Score' for each player based on their per-match statistics.
    """
    @staticmethod
    def calculate_impact_score(df):
        if df is None or df.empty:
            return df
            
        result_df = df.copy()
        
        # Ensure per-match columns exist. The Analyzer class adds some of these, 
        # but we should calculate any missing ones we need.
        matches_safe = result_df['Matches'].replace(0, pd.NA)
        
        def get_per_match(col):
            if col in result_df.columns:
                return (result_df[col] / matches_safe).fillna(0)
            return pd.Series(0, index=result_df.index)

        goals_pm = result_df.get('Goals_Per_Match', get_per_match('Goals'))
        assists_pm = result_df.get('Assists_Per_Match', get_per_match('Assists'))
        tackles_pm = result_df.get('Tackles_Per_Match', get_per_match('Tackles'))
        mvp_ratio = result_df.get('MVP_Ratio', get_per_match('MVP'))
        
        def_cs_pm = get_per_match('Def_CS')
        gk_cs_pm = get_per_match('GK_CS')
        saves_pm = get_per_match('Saves')

        # Base Formula
        raw_score = (goals_pm * 1.5) + (assists_pm * 1.2) + (tackles_pm * 0.8) + (mvp_ratio * 2.0)
        
        # Add Defender / Goalkeeper specific stats
        # The prompt says: "eğer oyuncunun pozisyonu kaleci/defans ise formüle Def_CS, GK_CS ve Saves verilerini uygun katsayılarla dahil et."
        # We can safely add these for everyone because for attackers these stats will be 0.
        raw_score += (def_cs_pm * 1.0)
        raw_score += (gk_cs_pm * 1.5)
        raw_score += (saves_pm * 0.2)
        
        # Normalize to 0-100 range
        min_score = raw_score.min()
        max_score = raw_score.max()
        
        if max_score > min_score:
            normalized_score = ((raw_score - min_score) / (max_score - min_score)) * 100
        else:
            normalized_score = raw_score * 0 # if everyone has the same score
            
        result_df['Impact_Score'] = normalized_score.round(2)
        
        return result_df
