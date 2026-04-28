import streamlit as st
from api_client import EMajorLeagueAPI
from processing import DataProcessor
from analysis import Analyzer
from impact_score import ImpactCalculator

st.set_page_config(page_title="eMajorLeague Analytics", layout="wide")

st.title("🏆 eMajorLeague Analytics Dashboard")
st.markdown("Verileri filtreleyerek, taktiksel rolleri analiz ederek tablo bazlı incelemelerde bulunun.")

# Cache the data load operations
@st.cache_data(ttl=3600)
def load_filters():
    api = EMajorLeagueAPI()
    return api.get_filter_options()

@st.cache_data
def load_data(limit=10000, season="", tournament="", position=""):
    api = EMajorLeagueAPI()
    records = api.fetch_players(limit=limit, season=season, tournament=tournament, position=position)
    processor = DataProcessor()
    return processor.process_player_records(records)

@st.cache_data(ttl=3600)
def load_team_player_cache():
    """Loads the team_player_cache.json for under-10-match players."""
    return DataProcessor.load_team_player_data(min_matches_threshold=10)

# Sidebar
st.sidebar.header("Filtreleme Seçenekleri")
st.sidebar.markdown("eMajorLeague arama motoru parametreleri:")

with st.sidebar.container():
    filters = load_filters()
    is_live = any(len(v) > 0 for v in filters.values())
    if not is_live:
        st.sidebar.caption("⚠️ Filtreler önbellekten yüklendi veya boş. Site geçici olarak ulaşılamaz olabilir.")

    season_opts = {"Tümü": ""}
    season_opts.update(filters.get('season', {}))
    s_label = st.sidebar.selectbox("Sezon Seçiniz", options=list(season_opts.keys()))
    sel_season = season_opts[s_label]

    tourn_opts = {"Tümü": ""}
    tourn_opts.update(filters.get('tournament', {}))
    t_label = st.sidebar.selectbox("Turnuva Seçiniz", options=list(tourn_opts.keys()))
    sel_tournament = tourn_opts[t_label]

    pos_opts = {"Tümü": ""}
    pos_opts.update(filters.get('position', {}))
    p_label = st.sidebar.selectbox("Pozisyon Seçiniz", options=list(pos_opts.keys()))
    sel_position = pos_opts[p_label]

st.sidebar.markdown("---")
view_mode = st.sidebar.radio("Görünüm Seçimi", ["Oyuncu Analizleri", "Takım Analizleri"])
st.sidebar.markdown("---")
show_low_match = st.sidebar.toggle(
    "📋 <10 Maç Oyuncularını Göster",
    value=False,
    help="team_player_cache.json baz alınarak takım sayfalarından çekilen, ana API limitini (10 maç) aşamamış oyuncuları gösterir."
)
include_low_in_radar = st.sidebar.toggle(
    "📊 Radar'a Dahil Et (<10 Maç)",
    value=False,
    help="10 maç altı oyuncuları oyuncu ve takım radar grafikleri ile ortalama hesaplamalarına ekler. Bu oyunculardan sadece Gol/Asist/Reyting mevcuttur; Tackle ve Pas boyutları bu oyuncular için boş bırakılır (ortalamalara dahil edilmez)."
)
st.sidebar.markdown("---")
st.sidebar.markdown("Yerel tablolama filtreleri:")

with st.spinner("eMajorLeague API üzerinden veriler çekiliyor (Sayfalanıyor)..."):
    df = load_data(limit=5000, season=sel_season, tournament=sel_tournament, position=sel_position)

if df.empty:
    st.error("Veri yüklenemedi veya gelen liste boş!")
else:
    max_matches = int(df['Matches'].max()) if 'Matches' in df.columns and len(df) > 0 else 100
    min_matches = st.sidebar.slider("Minimum Maç Sayısı", 0, max_matches, 0)
    min_rating = st.sidebar.slider("Minimum Ort. Reyting", 0.0, 10.0, 0.0, step=0.1)
    
    # Process Filtered Data
    analyzer = Analyzer(df)
    filtered_df = analyzer.filter_data(min_matches=min_matches, min_rating=min_rating)
    analyzer_filtered = Analyzer(filtered_df)

    # Calculate Impact Score
    analyzer_filtered.df = ImpactCalculator.calculate_impact_score(analyzer_filtered.df)
    filtered_df = analyzer_filtered.df

    # -----------------------------------------------------------------------
    # Build radar_df: optionally merge in under-10-match team-page players
    # NaN is used for Tackles/Passes/Saves/MVP so pandas mean() skips them
    # and league averages for those dimensions remain accurate.
    # -----------------------------------------------------------------------
    import pandas as pd
    _full_tp_radar, _low_tp_radar = load_team_player_cache()
    if include_low_in_radar and not _low_tp_radar.empty:
        low_radar = _low_tp_radar.copy()
        # Derive Goal_Contributions like the main pipeline does
        if 'Goals' in low_radar.columns and 'Assists' in low_radar.columns:
            low_radar['Goal_Contributions'] = low_radar['Goals'] + low_radar['Assists']
        if 'Goals_Per_Match' in low_radar.columns and 'Assists_Per_Match' in low_radar.columns:
            low_radar['Contributions_Per_Match'] = low_radar['Goals_Per_Match'] + low_radar['Assists_Per_Match']
        # Columns ONLY in main df — leave as NaN so they don't bias averages
        for col in ['Tackles', 'Tackles_Per_Match', 'Passes', 'Passes_Per_Match',
                    'Saves', 'GK_CS', 'Def_CS', 'MVP', 'Impact_Score', 'Role_Badge']:
            if col not in low_radar.columns:
                low_radar[col] = float('nan')
        radar_df = pd.concat([filtered_df, low_radar], ignore_index=True, sort=False)
    else:
        radar_df = filtered_df
    
    # TAKIM ANALİZLERİ
    if view_mode == "Takım Analizleri":
        st.header("🛡️ Takım Analizleri ve Karşılaştırması")
        st.markdown("Takım istatistikleri, oyuncu istatistiklerinin takım bazında ortalaması/toplamı alınarak hesaplanır.")
        
        derived_df = analyzer_filtered.df
        if 'Team' in derived_df.columns:
            # Use radar_df for team stats so under-10 players are included when toggled on
            team_source = radar_df if (include_low_in_radar and not _low_tp_radar.empty) else derived_df
            team_source = team_source[team_source['Team'].notna() & (team_source['Team'] != 'Unknown')]

            agg_dict = {'Username': 'count', 'Goals_Per_Match': 'mean', 'Assists_Per_Match': 'mean', 'Rating': 'mean'}
            for col in ['Tackles_Per_Match', 'Passes_Per_Match', 'MVP']:
                if col in team_source.columns:
                    agg_dict[col] = 'mean'
            team_stats = team_source.groupby('Team').agg(agg_dict).reset_index()
            team_stats = team_stats.rename(columns={'Username': 'Oyuncu_Sayisi'})
            # Fill NaN means (all-NaN groups) with 0
            team_stats = team_stats.fillna(0)
            
            if not team_stats.empty:
                st.dataframe(team_stats.style.background_gradient(cmap='viridis'), use_container_width=True)
                
                st.markdown("---")
                st.subheader("⚖️ Takım Radar Karşılaştırması")
                
                with st.expander("🎨 Grafik Ayarları"):
                    ct1, ct2 = st.columns(2)
                    with ct1:
                        team_color_1 = st.color_picker("1. Takım Çizgi Rengi", "#f59e0b")
                        team_opac_1 = st.slider("1. Takım Dolgu Opaklığı", 0.0, 1.0, 0.55)
                    with ct2:
                        team_color_2 = st.color_picker("2. Karşılaştırma Çizgi Rengi", "#64748b")
                        team_opac_2 = st.slider("2. Karşılaştırma Dolgu Opaklığı", 0.0, 1.0, 0.3)
                        
                def hex_to_rgba(hex_color, opacity):
                    hex_color = hex_color.lstrip('#')
                    r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
                    return f'rgba({r}, {g}, {b}, {opacity})'
                
                team_list = team_stats['Team'].tolist()
                t1, t2 = st.columns(2)
                with t1:
                    team_1 = st.selectbox("1. Takım Seçimi", options=team_list, index=0)
                with t2:
                    team_2_options = ["Lig Ortalaması"] + team_list
                    idx = 1 if len(team_list) > 1 else 0
                    team_2 = st.selectbox("2. Karşılaştırılacak Takım (Veya Lig Ort.)", options=team_2_options, index=idx)
                    
                import plotly.graph_objects as go
                
                t1_row = team_stats[team_stats['Team'] == team_1].iloc[0]
                t1_vals = {
                    'Hücum': t1_row['Goals_Per_Match'] + t1_row['Assists_Per_Match'],
                    'Pas': t1_row['Passes_Per_Match'],
                    'Defans': t1_row['Tackles_Per_Match'],
                    'Reyting': t1_row['Rating']
                }
                
                if team_2 == "Lig Ortalaması":
                    t2_vals = {
                        'Hücum': derived_df['Goals_Per_Match'].mean() + derived_df['Assists_Per_Match'].mean(),
                        'Pas': derived_df['Passes_Per_Match'].mean(),
                        'Defans': derived_df['Tackles_Per_Match'].mean(),
                        'Reyting': derived_df['Rating'].mean()
                    }
                else:
                    t2_row = team_stats[team_stats['Team'] == team_2].iloc[0]
                    t2_vals = {
                        'Hücum': t2_row['Goals_Per_Match'] + t2_row['Assists_Per_Match'],
                        'Pas': t2_row['Passes_Per_Match'],
                        'Defans': t2_row['Tackles_Per_Match'],
                        'Reyting': t2_row['Rating']
                    }
                    
                max_vals = {
                    'Hücum': team_stats['Goals_Per_Match'].max() + team_stats['Assists_Per_Match'].max() if len(team_stats) > 0 else 1,
                    'Pas': team_stats['Passes_Per_Match'].max() if len(team_stats) > 0 else 1,
                    'Defans': team_stats['Tackles_Per_Match'].max() if len(team_stats) > 0 else 1,
                    'Reyting': 10.0
                }
                
                def norm(val, max_val):
                    return min(100, max(0, (val / max_val) * 100)) if max_val > 0 else 0
                    
                categories = ['Hücum (G+A)', 'Pas Dağıtımı', 'Takım Savunması', 'Team Reytingi']
                s1 = [norm(t1_vals['Hücum'], max_vals['Hücum']), norm(t1_vals['Pas'], max_vals['Pas']), norm(t1_vals['Defans'], max_vals['Defans']), norm(t1_vals['Reyting'], max_vals['Reyting'])]
                s2 = [norm(t2_vals['Hücum'], max_vals['Hücum']), norm(t2_vals['Pas'], max_vals['Pas']), norm(t2_vals['Defans'], max_vals['Defans']), norm(t2_vals['Reyting'], max_vals['Reyting'])]
                
                ps1 = s1 + [s1[0]]
                ps2 = s2 + [s2[0]]
                cat_closed = categories + [categories[0]]
                
                fig = go.Figure()
                fig.add_trace(go.Scatterpolar(r=ps2, theta=cat_closed, fill='toself', name=team_2, line=dict(color=team_color_2, width=2), fillcolor=hex_to_rgba(team_color_2, team_opac_2)))
                fig.add_trace(go.Scatterpolar(r=ps1, theta=cat_closed, fill='toself', name=team_1, line=dict(color=team_color_1, width=3), fillcolor=hex_to_rgba(team_color_1, team_opac_1)))
                fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 100], gridcolor='#334155'), angularaxis=dict(gridcolor='#334155')), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#e2e8f0'), showlegend=True, height=500)
                st.plotly_chart(fig, use_container_width=True)
                
                # AI INSIGHTS
                st.markdown("---")
                st.subheader(f"🤖 {team_1} - Yapay Zeka Takım Analizi")
                insights = analyzer_filtered.generate_team_insights(team_1)
                
                c1, c2, c3 = st.columns(3)
                with c1:
                    st.success("✅ Güçlü Yanlar")
                    for p in insights.get('pros', []): st.write(f"- {p}")
                with c2:
                    st.error("❌ Zayıf Yanlar")
                    for c in insights.get('cons', []): st.write(f"- {c}")
                with c3:
                    st.info("💡 Taktiksel Tavsiyeler")
                    for a in insights.get('advice', []): st.write(f"- {a}")
            else:
                st.warning("Elde edilen kayıtlarda takım verisi bulunamadı. Lütfen Scraper'ı çalıştırınız.")
        else:
            st.warning("Uygulama veri haritasında 'Team' sütununa ulaşılamadı.")
            
        st.stop()
        
    # PLAYERS STATS SUMMARY (If view_mode is 'Oyuncu Analizleri')
    st.write(f"### 📋 Toplam Filtrelenen Oyuncu: **{len(filtered_df)}**")
    
    # Exclude complex lists or unreadable stuff
    display_df = filtered_df.copy()
    if 'player__profile_photo' in display_df.columns:
        display_df = display_df.drop(columns=['player__profile_photo'])
    if 'player__user_id' in display_df.columns:
        display_df = display_df.drop(columns=['player__user_id'])
        
    st.dataframe(display_df, use_container_width=True)

    # UNDER-10 MATCH ROSTER (from team page scraper)
    if show_low_match and view_mode == "Oyuncu Analizleri":
        st.markdown("---")
        st.subheader("📋 Düşük Maç Sayılı Oyuncular (<10 Maç) — Takım Sayfası Verisi")
        st.caption(
            "Bu veriler `team_player_cache.json` içinden okunur. "
            "Sadece **Gol / Asist / Maç Sayısı / Reyting** sütunları güvenilirdir. "
            "Tackle & Pas istatistikleri takım sayfasında yer almadığı için dahil edilmemiştir."
        )
        _full_tp, _low_tp = load_team_player_cache()
        if _low_tp.empty:
            st.warning(
                "Henüz team_player_cache.json oluşturulmamış ya da içinde 10 maç altı oyuncu yok. "
                "Lütfen terminalde `python team_scraper.py` komutunu çalıştırın."
            )
        else:
            low_cols = [c for c in ['Username','Team','Primary_Position','Matches','Goals','Assists','MOTM','Rating'] if c in _low_tp.columns]
            st.dataframe(_low_tp[low_cols].sort_values('Rating', ascending=False), use_container_width=True)
            st.caption(f"Toplam {len(_low_tp)} oyuncu listelendi.")

    # TACTICAL INSIGHTS
    st.markdown("---")
    st.header("🧠 Gelişmiş Taktiksel Analizler")
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Oyun Kurucular (Playmakers)")
        st.caption("En yüksek pas sayısına ulaşan takım içi dağıtıcı oyuncular")
        st.dataframe(analyzer_filtered.find_playmakers(10)[['Username', 'Role_Badge', 'Matches', 'Passes', 'Passes_Per_Match', 'Assists_Per_Match', 'Rating']], use_container_width=True)
        
    with col2:
        st.subheader("Defansif Belkemiği (Anchors)")
        st.caption("En yüksek top çalan, savunma dominasyonu kuran isimler")
        st.dataframe(analyzer_filtered.find_defensive_anchors(10)[['Username', 'Role_Badge', 'Matches', 'Tackles', 'Tackles_Per_Match', 'Def_CS', 'Rating']], use_container_width=True)
        
    # IMPACT LEADERBOARD
    st.markdown("---")
    st.header("🌟 Gerçek Etki Liderlik Tablosu (Impact Score)")
    st.markdown("Oyuncuların maç başına gol, asist, savunma, kaleci istatistikleri ve MVP oranları üzerinden hesaplanan özel **Etki Puanı (0-100)** sıralaması.")
    
    if not analyzer_filtered.df.empty and 'Impact_Score' in analyzer_filtered.df.columns:
        impact_leaderboard = analyzer_filtered.df.sort_values(by='Impact_Score', ascending=False).head(15)
        
        cols_to_show = ['Username', 'Team', 'Detailed_Position', 'Role_Badge', 'Matches', 'Impact_Score', 'Rating', 'MVP']
        cols_to_show = [c for c in cols_to_show if c in impact_leaderboard.columns]
        
        # Also include some raw stats based on what type of players they are
        st.dataframe(
            impact_leaderboard[cols_to_show].style.background_gradient(subset=['Impact_Score'], cmap='viridis'),
            use_container_width=True
        )

    # GOAL CONTRIBUTIONS
    st.subheader("Akan Oyunda Skor Katkıları (G+A Oranları)")
    st.dataframe(analyzer_filtered.top_contributors(10)[['Username', 'Role_Badge', 'Matches', 'Goals', 'Goals_Per_Match', 'Assists', 'Assists_Per_Match', 'Goal_Contributions', 'Contributions_Per_Match', 'Rating']], use_container_width=True)

    # CORRELATIONS
    st.markdown("---")
    st.subheader("🔗 İstatistiksel Korelasyon Matrisi (Pearson)")
    col_check = st.columns([1,3])
    with col_check[0]:
        show_corr = st.checkbox("Korelasyon Haritasını Göster")
    
    if show_corr:
        corr = analyzer_filtered.calculate_correlations()
        st.dataframe(corr.style.background_gradient(cmap='coolwarm'), use_container_width=True)

    # Use the dataframe that contains derived metrics across all graphs below
    derived_df = analyzer_filtered.df

    # SCATTER PLOT
    st.markdown("---")
    st.header("📊 Oyun Kurucu vs. Savunmacı Dağılımı")
    st.markdown("Bu dağılım haritası (Scatter Plot), pas dağıtımlarını ve savunma aksiyonlarını analiz ederek oyuncuların oyun stillerini sınıflandırır. Her nokta bir oyuncuyu, **noktanın boyutu** ise oyuncunun genel reytingini ifade eder.")
    
    if not derived_df.empty and 'Passes_Per_Match' in derived_df.columns:
        import plotly.express as px
        color_col = 'Role_Badge' if 'Role_Badge' in derived_df.columns else None
        
        fig_scatter = px.scatter(
            derived_df, 
            x='Passes_Per_Match', 
            y='Tackles_Per_Match', 
            size='Rating', 
            color=color_col,
            hover_name='Username',
            hover_data={'Rating': True, 'Matches': True, 'Role_Badge': True},
            labels={
                "Passes_Per_Match": "Maç Başına Başarılı Pas",
                "Tackles_Per_Match": "Maç Başına Savunma Aksiyonu (Tackle)",
                "Role_Badge": "Oyun Tarzı Etiketi"
            },
            template="plotly_dark"
        )
        fig_scatter.update_layout(
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            xaxis=dict(gridcolor='#334155'),
            yaxis=dict(gridcolor='#334155'),
            height=500
        )
        st.plotly_chart(fig_scatter, use_container_width=True)

    # BAR CHART AND HISTOGRAM
    st.markdown("---")
    st.header("📈 İstatistiksel Genel Bakış")
    st.markdown("Filtrelenmiş oyuncu havuzunun genel Reyting dağılımı ve en fazla *Maçın Adamı* (MVP) seçilmiş oyuncular tablosu.")
    
    col3, col4 = st.columns(2)
    
    with col3:
        st.subheader("Reyting Dağılım Çanı")
        if not derived_df.empty and 'Rating' in derived_df.columns:
            fig_hist = px.histogram(
                derived_df, 
                x="Rating", 
                nbins=15, 
                template="plotly_dark",
                color_discrete_sequence=['#8b5cf6'],
            )
            fig_hist.update_layout(
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                xaxis_title="Reyting Puanı",
                yaxis_title="Oyuncu Sayısı"
            )
            st.plotly_chart(fig_hist, use_container_width=True)
            
    with col4:
        st.subheader("En Çok MVP Ödülü Alanlar (En İyi 10)")
        if not derived_df.empty and 'MVP' in derived_df.columns:
            top_mvps = derived_df.nlargest(10, 'MVP')
            fig_bar = px.bar(
                top_mvps, 
                x='MVP', 
                y='Username', 
                orientation='h',
                template="plotly_dark",
                color='Rating',
                color_continuous_scale='Bluered',
            )
            fig_bar.update_layout(
                yaxis={'categoryorder':'total ascending'},
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                xaxis_title="Alınan Toplam MVP",
                yaxis_title="Oyuncu"
            )
            st.plotly_chart(fig_bar, use_container_width=True)

    # PLAYER RADAR CHART
    st.markdown("---")
    st.header("🎯 Oyuncu Profili Radar Grafiği")
    st.markdown("Hedef oyuncuyu seçerek, ligin en iyilerine kıyasla (0-100 normalize skalası) ve lig ortalamasıyla örümcek ağı profilini çıkarın.")
    
    with st.expander("🎨 Grafik Ayarları"):
        c_set1, c_set2 = st.columns(2)
        with c_set1:
            p_color_1 = st.color_picker("1. Oyuncu Çizgi Rengi", "#0ea5e9")
            p_opac_1 = st.slider("1. Oyuncu Dolgu Opaklığı", 0.0, 1.0, 0.55)
        with c_set2:
            p_color_2 = st.color_picker("2. Hedef Çizgi Rengi", "#64748b")
            p_opac_2 = st.slider("2. Hedef Dolgu Opaklığı", 0.0, 1.0, 0.3)
            
    def hex_to_rgba_player(hex_color, opacity):
        hex_color = hex_color.lstrip('#')
        r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        return f'rgba({r}, {g}, {b}, {opacity})'
        
    player_list = [""] + sorted(radar_df['Username'].dropna().unique().tolist())

    cp1, cp2 = st.columns(2)
    with cp1:
        selected_player = st.selectbox("1. Oyuncu Seçimi:", options=player_list)
    with cp2:
        comp_opts = ["Lig Ortalaması", "Mevki Ortalaması", "Takım Ortalaması"] + sorted(radar_df['Username'].dropna().unique().tolist())
        compare_target = st.selectbox("2. Kıyaslanacak Hedef (Oyuncu / Ortalama):", options=comp_opts)
    
    if selected_player:
        import plotly.graph_objects as go
        
        # Max scale bounds to normalize 0-100%
        max_vals = {
            'Hücum': radar_df['Goal_Contributions'].max() if 'Goal_Contributions' in radar_df.columns else 1,
            'Pas': radar_df['Passes'].max() if 'Passes' in radar_df.columns else 1,
            'Defans': radar_df['Tackles'].max() if 'Tackles' in radar_df.columns else 1,
            'MVP': radar_df['MVP'].max() if 'MVP' in radar_df.columns else 1,
            'Reyting': 10.0
        }
        # Ensure max_vals are at least 1 to avoid division by zero
        max_vals = {k: max(v, 1) if not (v != v) else 1 for k, v in max_vals.items()}

        # Player Selection Data — look up in radar_df so under-10 players are found too
        try:
            p_row = radar_df[radar_df['Username'] == selected_player].iloc[0]
        except Exception:
            st.warning("Seçilen oyuncu geçerli filtrelere takıldı veya veri bulunamadı. Sol panel filtrelerini kontrol edin.")
            p_row = {}

        if len(p_row) > 0:
            if 'Team' in p_row and 'Detailed_Position' in p_row:
                team = p_row.get('Team', 'Bilinmiyor')
                pos = p_row.get('Detailed_Position', 'Bilinmiyor')
                st.info(f"🏟️ **Takım:** {team} | 🏃 **Pozisyon:** {pos}")
                
            # Filter base_df according to comparison choice
            if compare_target in ["Lig Ortalaması", "Mevki Ortalaması", "Takım Ortalaması"]:
                if compare_target == "Mevki Ortalaması" and 'Primary_Position' in derived_df.columns:
                    pos_val = p_row.get('Primary_Position', '')
                    base_df = derived_df[derived_df['Primary_Position'] == pos_val] if pos_val else derived_df
                elif compare_target == "Takım Ortalaması" and 'Team' in derived_df.columns:
                    team_val = p_row.get('Team', '')
                    base_df = derived_df[derived_df['Team'] == team_val] if team_val else derived_df
                else:
                    base_df = derived_df
                    
                target_vals = {
                    'Hücum': base_df['Goal_Contributions'].mean() if 'Goal_Contributions' in base_df.columns else 0,
                    'Pas': base_df['Passes'].mean() if 'Passes' in base_df.columns else 0,
                    'Defans': base_df['Tackles'].mean() if 'Tackles' in base_df.columns else 0,
                    'MVP': base_df['MVP'].mean() if 'MVP' in base_df.columns else 0,
                    'Reyting': base_df['Rating'].mean() if 'Rating' in base_df.columns else 0
                }
            else:
                try:
                    p2_row = derived_df[derived_df['Username'] == compare_target].iloc[0]
                    target_vals = {
                        'Hücum': p2_row.get('Goal_Contributions', 0),
                        'Pas': p2_row.get('Passes', 0),
                        'Defans': p2_row.get('Tackles', 0),
                        'MVP': p2_row.get('MVP', 0),
                        'Reyting': p2_row.get('Rating', 0)
                    }
                except Exception:
                    st.warning("Karşılaştırılacak hedef oyuncu listede (filtrelere takılmış olabilir) bulunamadı.")
                    target_vals = { 'Hücum':0, 'Pas':0, 'Defans':0, 'MVP':0, 'Reyting':0 }
        
            p_vals = {
                'Hücum': p_row.get('Goal_Contributions', 0),
                'Pas': p_row.get('Passes', 0),
                'Defans': p_row.get('Tackles', 0),
                'MVP': p_row.get('MVP', 0),
                'Reyting': p_row.get('Rating', 0)
            }
        
            def norm(val, max_val):
                return min(100, max(0, (val / max_val) * 100)) if max_val > 0 else 0
                
            categories = ['Hücum Katkısı (G+A)', 'Pas Dağıtımı', 'Defansif Direnç (Tackle)', 'MVP Etkisi', 'Bireysel Reyting']
            
            player_scores = [
                norm(p_vals['Hücum'], max_vals['Hücum']),
                norm(p_vals['Pas'], max_vals['Pas']),
                norm(p_vals['Defans'], max_vals['Defans']),
                norm(p_vals['MVP'], max_vals['MVP']),
                norm(p_vals['Reyting'], max_vals['Reyting'])
            ]
            
            avg_scores = [
                norm(target_vals['Hücum'], max_vals['Hücum']),
                norm(target_vals['Pas'], max_vals['Pas']),
                norm(target_vals['Defans'], max_vals['Defans']),
                norm(target_vals['MVP'], max_vals['MVP']),
                norm(target_vals['Reyting'], max_vals['Reyting'])
            ]
            
            # Connecting the endpoints to close the radar shape
            ps = player_scores + [player_scores[0]]
            b_scores = avg_scores + [avg_scores[0]]
            cat_closed = categories + [categories[0]]
            
            fig = go.Figure()
            
            fig.add_trace(go.Scatterpolar(
                r=b_scores,
                theta=cat_closed,
                fill='toself',
                name=f'{compare_target}',
                line=dict(color=p_color_2, width=2),
                fillcolor=hex_to_rgba_player(p_color_2, p_opac_2)
            ))
            
            fig.add_trace(go.Scatterpolar(
                r=ps,
                theta=cat_closed,
                fill='toself',
                name=selected_player,
                line=dict(color=p_color_1, width=3),
                fillcolor=hex_to_rgba_player(p_color_1, p_opac_1)
            ))
            
            fig.update_layout(
                polar=dict(
                    radialaxis=dict(visible=True, range=[0, 100], gridcolor='#334155'),
                    angularaxis=dict(gridcolor='#334155')
                ),
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                font=dict(color='#e2e8f0'),
                showlegend=True,
                height=500
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            # PROS / CONS / ADVICE
            st.markdown("---")
            st.subheader("🔍 Yapay Zeka Destekli Oyuncu Analizi")
            st.caption(f"{selected_player} istatistikleri ve taktiksel alışkanlıklarına göre kural tabanlı değerlendirmeler.")
            
            insights = analyzer_filtered.generate_player_insights(selected_player)
            
            c1, c2, c3 = st.columns(3)
            with c1:
                st.success("✅ Artılar")
                for p in insights.get('pros', []): st.write(f"- {p}")
            with c2:
                st.error("❌ Eksiler")
                for c in insights.get('cons', []): st.write(f"- {c}")
            with c3:
                st.info("💡 Taktiksel Odak ve Beklentiler")
                for a in insights.get('advice', []): st.write(f"- {a}")
                st.markdown("---")
                st.markdown("**🪄 Tercih Edilebilecek PlayStyle+ Türleri**")
                for ps in insights.get('playstyles', []): st.write(f"- {ps}")
