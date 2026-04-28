import pandas as pd

class Analyzer:
    def __init__(self, dataframe):
        self.df = dataframe.copy()
        
        # Add derived metrics
        if 'Goals' in self.df.columns and 'Assists' in self.df.columns:
            self.df['Goal_Contributions'] = self.df['Goals'] + self.df['Assists']
            
        if 'Matches' in self.df.columns:
            matches_safe = self.df['Matches'].replace(0, pd.NA) # avoid div by zero
            if 'Goals' in self.df.columns:
                self.df['Goals_Per_Match'] = (self.df['Goals'] / matches_safe).fillna(0).round(2)
            if 'Assists' in self.df.columns:
                self.df['Assists_Per_Match'] = (self.df['Assists'] / matches_safe).fillna(0).round(2)
            if 'Goal_Contributions' in self.df.columns:
                self.df['Contributions_Per_Match'] = (self.df['Goal_Contributions'] / matches_safe).fillna(0).round(2)
            if 'MVP' in self.df.columns:
                self.df['MVP_Ratio'] = (self.df['MVP'] / matches_safe).fillna(0).round(2)
            if 'Passes' in self.df.columns:
                self.df['Passes_Per_Match'] = (self.df['Passes'] / matches_safe).fillna(0).round(2)
            if 'Tackles' in self.df.columns:
                self.df['Tackles_Per_Match'] = (self.df['Tackles'] / matches_safe).fillna(0).round(2)
        self._assign_role_badges()

    def _assign_role_badges(self):
        """ Assigns automatic play style roles based on stat quantiles """
        if self.df.empty:
            return
            
        pass_p75 = self.df['Passes_Per_Match'].quantile(0.75) if 'Passes_Per_Match' in self.df.columns else 0
        ast_p75 = self.df['Assists_Per_Match'].quantile(0.75) if 'Assists_Per_Match' in self.df.columns else 0
        tcl_p75 = self.df['Tackles_Per_Match'].quantile(0.75) if 'Tackles_Per_Match' in self.df.columns else 0
        tcl_p90 = self.df['Tackles_Per_Match'].quantile(0.90) if 'Tackles_Per_Match' in self.df.columns else 0
        goal_p75 = self.df['Goals_Per_Match'].quantile(0.75) if 'Goals_Per_Match' in self.df.columns else 0
        
        roles = []
        for _, row in self.df.iterrows():
            g_pm = row.get('Goals_Per_Match', 0)
            p_pm = row.get('Passes_Per_Match', 0)
            a_pm = row.get('Assists_Per_Match', 0)
            t_pm = row.get('Tackles_Per_Match', 0)
            
            if g_pm >= goal_p75 and t_pm >= tcl_p75 and g_pm > 0 and t_pm > 0:
                roles.append("🔋 Box-to-Box")
            elif p_pm >= pass_p75 and a_pm >= ast_p75 and (p_pm > 0 or a_pm > 0):
                roles.append("🎩 Maestro")
            elif t_pm >= tcl_p90 and t_pm > 0:
                roles.append("🛡️ Kesici Dinamo")
            elif g_pm >= goal_p75 and g_pm > 0:
                roles.append("🎯 Keskin Nişancı")
            else:
                roles.append("⚙️ Görev Adamı")
                
        self.df['Role_Badge'] = roles
        
    def filter_data(self, min_matches=0, min_rating=0.0):
        """
        Filters the dataset flexibly based on minimum matches and rating.
        """
        filtered = self.df.copy()
        if 'Matches' in filtered.columns:
            filtered = filtered[filtered['Matches'] >= min_matches]
        if 'Rating' in filtered.columns:
            filtered = filtered[filtered['Rating'] >= min_rating]
            
        return filtered

    def top_scorers(self, top_n=5):
        if 'Goals' not in self.df.columns:
            return pd.DataFrame()
        return self.df.sort_values(by='Goals', ascending=False).head(top_n)

    def top_assists(self, top_n=5):
        if 'Assists' not in self.df.columns:
            return pd.DataFrame()
        return self.df.sort_values(by='Assists', ascending=False).head(top_n)

    def player_summary(self, username):
        if 'Username' not in self.df.columns:
            return None
        player_df = self.df[self.df['Username'].str.contains(username, case=False, na=False)]
        if player_df.empty:
            return None
        # Transpose single row for easier reading
        return player_df.iloc[0]
        
    def overall_stats(self):
        """ Returns some generic statistics about the league """
        stats = {}
        if 'Goals' in self.df.columns:
            stats['Total Goals'] = self.df['Goals'].sum()
        if 'Assists' in self.df.columns:
            stats['Total Assists'] = self.df['Assists'].sum()
        stats['Total Players'] = len(self.df)
        return dict(stats)

    def calculate_correlations(self):
        """ Returns a correlation matrix for numeric columns, measuring linear relationships """
        numeric_cols = self.df.select_dtypes(include='number').columns
        if len(numeric_cols) > 0:
            return self.df[numeric_cols].corr()
        return pd.DataFrame()
        
    def value_efficiency(self, top_n=5, min_matches=5):
        """ Finds the most efficient players based on Rating vs Transfer_Fee """
        filtered = self.df[self.df['Matches'] >= min_matches].copy()
        if 'Transfer_Fee' in filtered.columns and 'Rating' in filtered.columns:
            filtered['Rating_Per_Million'] = filtered['Rating'] / (filtered['Transfer_Fee'] + 1) # +1 to avoid div by zero
            return filtered.sort_values(by='Rating_Per_Million', ascending=False)[
                ['Username', 'Matches', 'Rating', 'Transfer_Fee', 'Rating_Per_Million']
            ].head(top_n)
        return pd.DataFrame()
        
    def top_contributors(self, top_n=5):
        """ Orders by Goal Contributions (Goals + Assists) """
        if 'Goal_Contributions' in self.df.columns:
            return self.df.sort_values(by='Goal_Contributions', ascending=False).head(top_n)
        return pd.DataFrame()

    def find_playmakers(self, top_n=5):
        """ Identifies pass distributors and playmakers (most Passes) """
        if 'Passes' in self.df.columns:
            return self.df.sort_values(by='Passes', ascending=False).head(top_n)
        return pd.DataFrame()

    def find_defensive_anchors(self, top_n=5):
        """ Identifies players who win the most tackles/struggles (most Tackles) """
        if 'Tackles' in self.df.columns:
            return self.df.sort_values(by='Tackles', ascending=False).head(top_n)
        return pd.DataFrame()

    def generate_player_insights(self, player_username):
        """
        Kural tabanlı (heuristic) analiz motoru. Seçilen oyuncunun istatistiklerini
        lig veya kendi alt grupları ile karşılaştırarak artılar, eksiler, hedefe yönelik tavsiyeler 
        ve FC 26 Clubs moduna uygun Playstyle+ önerileri üretir.
        """
        if self.df.empty or 'Username' not in self.df.columns:
            return {"pros": [], "cons": [], "advice": [], "playstyles": []}
            
        player_df = self.df[self.df['Username'] == player_username]
        if player_df.empty:
            return {"pros": [], "cons": [], "advice": [], "playstyles": []}
            
        p = player_df.iloc[0]
        
        pros = []
        cons = []
        advice = []
        playstyles = []
        
        # Calculate League Averages
        avg_r = self.df['Rating'].mean() if 'Rating' in self.df.columns else 0
        avg_g = self.df['Goals_Per_Match'].mean() if 'Goals_Per_Match' in self.df.columns else 0
        avg_a = self.df['Assists_Per_Match'].mean() if 'Assists_Per_Match' in self.df.columns else 0
        avg_t = self.df['Tackles_Per_Match'].mean() if 'Tackles_Per_Match' in self.df.columns else 0
        avg_p = self.df['Passes_Per_Match'].mean() if 'Passes_Per_Match' in self.df.columns else 0
        
        # Player Stats
        rating = p.get('Rating', 0)
        g_pm = p.get('Goals_Per_Match', 0)
        a_pm = p.get('Assists_Per_Match', 0)
        t_pm = p.get('Tackles_Per_Match', 0)
        p_pm = p.get('Passes_Per_Match', 0)
        matches = p.get('Matches', 0)
        pos = p.get('Primary_Position', p.get('Detailed_Position', 'Unknown'))
        
        pos_str = str(pos).upper()
        is_def = any(x in pos_str for x in ['CB', 'LB', 'RB', 'LWB', 'RWB'])
        is_cdm = 'CDM' in pos_str
        is_gk = 'GK' in pos_str
        is_mid = any(x in pos_str for x in ['CM', 'CAM', 'RM', 'LM'])
        is_att = any(x in pos_str for x in ['ST', 'CF', 'RW', 'LW'])
        
        # ATTACKING INSIGHTS
        if is_att or (is_mid and g_pm > 0.4):
            if g_pm >= avg_g * 1.8:
                pros.append(f"Olağanüstü bir gol makinesi, takımının skor yükünü tek başına sırtlayan bir Elit Forvet. (Gol Ort: {g_pm:.2f} | Lig Ort: {avg_g:.2f} ▲)")
                playstyles.append("🎯 Power Shot+ veya Finesse Shot+ (Ceza sahası çevresi bitiricilik için mecburi)")
                playstyles.append("🦊 Quick Step+ (Defans botlarının arkasına ani sızmalar için)")
            elif g_pm >= avg_g * 1.3:
                pros.append(f"Klinik bir Pro bitiricisi, yakaladığı fırsatları istikrarlı gole çeviriyor. (Gol Ort: {g_pm:.2f} | Lig Ort: {avg_g:.2f} ▲)")
                playstyles.append("🚀 Rapid+ veya Aerial+ (Akan oyunda fiziksel üstünlük kurmak için)")
            elif g_pm < avg_g * 0.5:
                cons.append(f"Hücum profilinde yer almasına rağmen tabelaya katkısı Clubs normlarına göre oldukça zayıf. (Gol Ort: {g_pm:.2f} | Lig Ort: {avg_g:.2f} ▼)")
                advice.append("Sanal Pro'sunun boy/kilo (Build) ayarlarını hafifletip, 'Call For Pass' (Top İsteme) yerine takım arkadaşlarıyla uyumlu çapraz koşulara (Creative Runs) odaklanmalı.")
                
            if a_pm >= avg_a * 1.5:
                pros.append(f"Dar alanda kilidi açabilen son pas/yaratıcılık ustası; hücum organizasyonlarında tam bir Maestro. (Asist Ort: {a_pm:.2f} | Lig Ort: {avg_a:.2f} ▲)")
                playstyles.append("💫 Incisive Pass+ veya Whipped Pass+ (İnsan oyuncuların koşu yollarına tam isabet kilit paslar için)")
                
        # PASSING & PLAYMAKING INSIGHTS
        if p_pm >= avg_p * 1.4:
            pros.append(f"Sahanın oyun kurucusu, takım arkadaşlarını ve Any (Herkes) rolündeki oyuncuyu çok rahatlatıyor. (Pas Ort: {p_pm:.1f} | Lig Ort: {avg_p:.1f} ▲)")
            playstyles.append("🏓 Pinged Pass+ veya Tiki Taka+ (Clubs modunun dar alan ping-pong paslaşmaları için mükemmel)")
            if a_pm < avg_a * 0.8:
                cons.append(f"Pas dağıtımı yüksek fakat bu paslar 3. bölgede kilit pasa veya asiste dönüşmüyor; top çevirme odaklı. (Asist Ort: {a_pm:.2f} | Lig Ort: {avg_a:.2f} ▼)")
                advice.append("Geriye dönük veya botlara verilen garanti paslardan vazgeçip, forvet hattındaki insan arkadaşlarına dikey, riskli ara pasları denemeli.")
        elif (is_mid or is_cdm) and p_pm < avg_p * 0.7:
            cons.append(f"Oyunun merkezinde oynamasına rağmen, takım arkadaşlarıyla top alışverişi çok düşük seviyede. (Pas Ort: {p_pm:.1f} | Lig Ort: {avg_p:.1f} ▼)")
            advice.append("11v11 sisteminde oyunun dışında kalıyor. Daha fazla alana yayılarak (Width) ve boşa çıkarak toplu oyuna dahil olmalı.")

        # DEFENDERS & TACKLES
        if t_pm >= avg_t * 1.5:
            pros.append(f"Kendi hattını adeta duvar ören elit bir savunma lideri. Botlara komuta edip atakları süpürüyor. (Müdahale Ort: {t_pm:.1f} | Lig Ort: {avg_t:.1f} ▲)")
            playstyles.append("🛡️ Anticipate+ (Ayağa temiz müdahale) veya Bruiser+ (Rakip Sanal Pro'ları devirmek için)")
            playstyles.append("🚫 Intercept+ (Botların yetersiz kaldığı kilit pas aralarını kapatmak için)")
        elif t_pm >= avg_t * 1.1:
            pros.append(f"Mevkisine uygun olarak pas arası yapma yetisiyle FC Clubs defansına insan aklının güvenini veriyor. (Müdahale Ort: {t_pm:.1f} | Lig Ort: {avg_t:.1f} ▲)")
            playstyles.append("🧱 Block+ veya Slide Tackle+ (Savunma hattı engelleyici aksiyonları)")
        elif (is_def or is_cdm) and t_pm < avg_t * 0.6:
            cons.append(f"Clubs savunma beklentisinin çok gerisinde, 1v1 savunmalarda aşırı pasif. (Müdahale Ort: {t_pm:.1f} | Lig Ort: {avg_t:.1f} ▼)")
            advice.append("Jockey (L2/LT hareketi) refleksleri üzerine pratik yapmalı; top çalma (Tackling) yetenek ağacındaki Puanlarını (Skill Points) maksimuma vermeli.")

        # GOALKEEPERS
        if is_gk:
            if t_pm >= avg_t * 1.2:
                pros.append(f"Clubs'ta bot savunmasının arkasını toplayan, kalesini zamanında terk eden harika bir modern GK performansı.")
                playstyles.append("🧤 Rush Out+ (Kaleyi çapraz paslara veya atılan uzun üçgenlere karşı erken terk etme) ve Far Reach+")
            elif rating < avg_r * 0.85:
                cons.append("Maç içinde kalesinde gördüğü tehlikelere karşı takımını kurtaramıyor; Clubs refleks reytingleri zayıf.")
                advice.append("VPRO GK boy/kilo (Build) metasına uyum sağlamalı, manuel pozisyon alışları (R3 Positioning / Analog) üzerine pratik yapmalı.")

        # GENERIC PATTERNS & HYBRID
        if is_def and a_pm >= avg_a * 1.5:
            pros.append(f"Hücuma bindiren ideal Clubs beki; topu taca atmak yerine atağa genişlik ve tehlike katıyor. (Asist Ort: {a_pm:.2f} | Lig Ort: {avg_a:.2f} ▲)")
            playstyles.append("🎯 Whipped Pass+ veya Relentless+ (Maç sonuna kadar o çizgide bitmeyen bir stamina ve orta açma gücü)")
            
        if rating >= avg_r * 1.15:
            pros.append(f"Divizyonları taşıyan ve Clubs takımının kaderini belirleyen tam bir yıldız / 'Carry' oyuncu. (Reyting: {rating:.2f} | Lig Ort: {avg_r:.2f} ▲)")
        elif rating > 0 and rating < avg_r * 0.8:
            cons.append(f"Performans grafiği ve maç puanları (AMR) tehlike çanları çalıyor. (Reyting: {rating:.2f} | Lig Ort: {avg_r:.2f} ▼)")
            advice.append("Takım içi iletişimini artırmalı, oynadığı role uygun Yetenek Ağacını (Skill Tree) sıfırlayıp 'Meta' bir yapılandırmaya (Build) geçmeli.")

        if matches < 10 and matches > 0:
            cons.append(f"Sadece {matches} el maç oynanmış. Sanal Pro'su henüz tam reytingine ulaşmamış veya form tutmamış olabilir. Analiz için yetersiz örneklem.")

        # Defaults
        if not pros:
            pros.append(f"Ligin sıradan standartlarında, takım kimyasını bozmadan görevini yerine getiren uyumlu bir Sanal Pro. (Reyting: {rating:.2f})")
        if not cons:
            cons.append("İstatistiksel tablolarda sırıtacak net bir defosu veya Clubs meta'sına aykırı bir durumu yok.")
        if len(advice) == 0:
            advice.append("Takım arkadaşlarıyla olan mevcut kimyasını bozmadan, oynadığı bölgenin taktiksel gereksinimlerini karşılamaya devam etmeli.")
        if len(playstyles) == 0:
            playstyles.append("🏃 Relentless+ (Clubs için hayati olan dayanıklılık) veya First Touch+ (İlk dokunuş kontrolü) önerilir.")
            
        return {"pros": pros, "cons": cons, "advice": advice, "playstyles": playstyles}


    def generate_team_insights(self, team_name):
        """
        Kural tabanlı (heuristic) analiz motoru. Seçilen takımın kadrosunun ortalamalarını
        lig geneliyle kıyaslayarak FC Clubs moduna uygun 11v11 takım dinamiklerini özetler.
        """
        if self.df.empty or 'Team' not in self.df.columns:
            return {"pros": [], "cons": [], "advice": []}
            
        team_df = self.df[self.df['Team'] == team_name]
        if team_df.empty:
            return {"pros": [], "cons": [], "advice": []}
            
        pros = []
        cons = []
        advice = []
        
        # Calculate League Averages
        avg_r = self.df['Rating'].mean() if 'Rating' in self.df.columns else 0
        l_g = self.df['Goals_Per_Match'].mean() if 'Goals_Per_Match' in self.df.columns else 0
        l_a = self.df['Assists_Per_Match'].mean() if 'Assists_Per_Match' in self.df.columns else 0
        l_t = self.df['Tackles_Per_Match'].mean() if 'Tackles_Per_Match' in self.df.columns else 0
        l_p = self.df['Passes_Per_Match'].mean() if 'Passes_Per_Match' in self.df.columns else 0
        
        # Calculate Team Averages
        t_r = team_df['Rating'].mean()
        t_g = team_df['Goals_Per_Match'].mean()
        t_a = team_df['Assists_Per_Match'].mean()
        t_t = team_df['Tackles_Per_Match'].mean()
        t_p = team_df['Passes_Per_Match'].mean()
        
        # OFFENSIVE
        if t_g >= l_g * 1.3:
            pros.append(f"Ligdeki rakiplerine nefes aldırmayan, her pozisyonu gole çeviren elit bir hücum formasyonları var. (Takım Gol Ort: {t_g:.2f} | Lig: {l_g:.2f} ▲)")
        elif t_g >= l_g * 1.1:
            pros.append(f"İnsan oyunculardan oluşan hücum hatları oldukça uyumlu; skor üretmede istikrarlı bir kimyaya sahipler. (Takım Gol Ort: {t_g:.2f} | Lig: {l_g:.2f} ▲)")
        elif t_g < l_g * 0.8:
            cons.append(f"Forvet hattı botlarla ve arka alanla tamamen kopuk; gol yollarında devasa bir üretememe sorunu çekiyorlar. (Takım Gol Ort: {t_g:.2f} | Lig: {l_g:.2f} ▼)")
            advice.append("Clubs hücum organizasyonlarında merkez forvetlerin Target Man (Hedef Adam) mi yoksa Get In Behind (Arka Koşucu) mu oynayacağına dair ekip içi net kararlar verilmeli.")
            
        # PLAYMAKING
        if t_p >= l_p * 1.2:
            pros.append(f"Botları ve insan oyuncuları muazzam koordine ederek yüksek pas trafiği (Tiki-Taka) kuruyor, oyunu domine ediyorlar. (Takım Pas Ort: {t_p:.1f} | Lig: {l_p:.1f} ▲)")
            if t_a >= l_a * 1.15:
                pros.append(f"Bu topa sahip olma oyunu doğrudan öldürücü asistlere dönüşüyor, mükemmel takım oyunu. (Takım Asist Ort: {t_a:.2f} | Lig: {l_a:.2f} ▲)")
            else:
                cons.append(f"Paslaşmalar genellikle yatay eksende; risk alınmadığı için tabelada asiste veya keskin ataklara dönüşemiyor. (Takım Asist: {t_a:.2f} | Lig: {l_a:.2f} ▼)")
                advice.append("Eğer 'Any' (Herkes) rolü kullanılıyorsa The ANY doğrudan 'Direct Passing' taktiğini aktifleştirmeli; yoksa merkezdeki takım arkadaşları uzun top özelliklerini artırmalı.")
        elif t_p < l_p * 0.8:
            cons.append(f"Hızlı set hücumlarına kalkarken orta sahada inanılmaz amatör pas hataları ve bağlantısızlıklar yaşanıyor. (Takım Pas Ort: {t_p:.1f} | Lig: {l_p:.1f} ▼)")
            advice.append("Oyuncular bireysel oynamayı bırakıp pas istasyonlarına güvenmeli. Ayrıca bot defansların pas hataları için savunmaya kadar destek gelinmeli.")
            
        # DEFENSE
        if l_t > 0 and t_t >= l_t * 1.2:
            pros.append(f"Botları başarılı şekilde öne çekebilen, rakip oyunculara boşluk bırakmayıp alan daraltan harika bir savunma anlayışı. (Takım Müdahale: {t_t:.1f} | Lig: {l_t:.1f} ▲)")
        elif l_t > 0 and t_t < l_t * 0.8:
            cons.append(f"Defans hattı oldukça dağınık, rakibin hızlı kanat akınlarında veya botların yerleşim hatalarında ağır çuvallıyorlar. (Takım Müdahale: {t_t:.1f} | Lig: {l_t:.1f} ▼)")
            advice.append("Kaptan, D-Pad (Yön tuşları) üzerinden takım presini (Team Press) maçın kritik anlarında doğru yönetmeli; savunmada mutlaka en azından bir insan Stoper/CDM görevlendirilmeli.")
            
        # Overall
        if t_r >= avg_r * 1.1:
            pros.append(f"Birbirini tanıyan, üst düzey bir 'Pro Club' sinerjisine sahip; liderliğe veya 1. Divizyona oynayan elit bir kulüp. (Takım Reyting: {t_r:.2f} | Lig: {avg_r:.2f} ▲)")
            
        if not pros:
            pros.append("Büyük dalgalanmalardan uzak, standart düzeyde performans gösteren ortalama bir 'Sunday League' takımı kıvamındalar.")
        if not cons:
            cons.append("Göze batan organize bir arızaları, veya botları yanlış konumlandıracak vahim bir taktik denemeleri bulunmuyor.")
        if not advice:
            advice.append("Kulübün oyun içindeki mevcut arkadaşlık ve taktik kimyasını değiştirmeden yollarına devam etmeleri önerilir.")
            
        return {"pros": pros, "cons": cons, "advice": advice}



