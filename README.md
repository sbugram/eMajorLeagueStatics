# eMajorLeague İstatistik ve Analiz Aracı

Bu proje, **eMajorLeague** web sitesi üzerinden oyuncu istatistiklerini dinamik ve yapılandırılmış bir biçimde çeken, derleyen ve bu veriler üzerinden ileri düzey istatistiksel ve taktiksel analizler üretebilen bir Python komut satırı (CLI) uygulamasıdır.

## Mimari ve Prensipler

Proje, **Clean Code (Temiz Kod)** ve yapısal (modüler) tasarım prensiplerine sadık kalınarak inşa edilmiştir.
Veriler ağır ve yavaş çalışan tarayıcı simülasyonları yerine doğrudan sistemin arka planda yayınladığı `/player_statistics_data/` JSON uç noktasından çekilmektedir.

- **`api_client.py`:** HTTP/S isteklerini yöneterek veriyi çeker.
- **`processing.py`:** Gelen iç içe geçmiş (ör: görsel linkleri ve ID'lerin birleştiği metinler) formatları temizleyerek işlenebilir sayısal Pandas Dataframe formatına dönüştürür.
- **`analysis.py`:** Verinin üzerinde çalışarak filtreleme, korelasyon bulma, taktiksel rol çıkarma (Oyun Kurucu vs.) işlemlerini halleder.
- **`main.py`:** Kullanıcının tüm bu özellikleri terminalden pratik bayraklar (`--flag`) yardımıyla tetiklemesini sağlayan ana konsol giriş noktasıdır.

## Kurulum ve Çalıştırma

1. Python yüklü olduğundan emin olun.
2. Proje dizininde sanal ortama giriş yapın:
   ```bash
   # Windows için
   .\venv\Scripts\Activate
   ```
3. (İsteğe bağlı) Eğer ilk kez çalıştırıyorsanız kütüphaneleri kurduğunuzdan emin olun (Örn: `pip install requests pandas beautifulsoup4 lxml`).

## Kullanım Komutları (CLI Parametreleri)

Programı çalıştırmak için terminalden `python main.py` yazabilir ve sonrasına ekleyeceğiniz parametrelerle farklı analizlere ulaşabilirsiniz:

### 1. Genel İstatistikler ve Filtreleme
- **Genel Lig Özeti:**  
  `python main.py`  
  (Toplam goller, toplam asistler vb. özet bilgiler verir)
- **Gol Krallığı (En İyi Golcüler):**  
  `python main.py --top-scorers 5`
- **Asist Krallığı (En İyi Asist Yapanlar):**  
  `python main.py --top-assists 5`
- **Özel Oyuncu İncelemesi:**  
  `python main.py --player "KullaniciAdi"`  
  (Belirli bir kullanıcının mevcut tüm verilerini ekrana basar)
- **Detaylı Filtre Eklemeleri:**
  `python main.py --top-scorers 5 --min-matches 10 --min-rating 7.0`  
  (En az 10 maça çıkmış ve 7.0'ın üzerinde ortalaması olan en gollü 5 oyuncuyu getirir)

### 2. Gelişmiş Taktiksel Analizler ve Korelasyonlar
Uygulamanın gücü sadece genel bir okuma değil, aynı zamanda verilerden sonuç ve rol çıkarabilmesidir:

- **Taktiksel Rol Tespiti (Oyun Kurucular ve Belkemikleri):**  
  `python main.py --tactical-report 5`  
  Takım içerisinde pas dağılımlarını üstlenen *Playmaker* (Oyun Kurucu) profilindeki isimlerle, çok fazla top çalarak defansif kilit rol oynayan *Defensive Anchor* (Defansif Duvar) niteliğindeki isimleri çıkarıp listeler.
  
- **Toplam Gol Katkısı (Akış Yaratıcılar):**  
  `python main.py --top-contributors 5`  
  Gol veya asist ayrımı yapmaksızın takıma yapılan total (+G/A) katkıyı ölçer ve maç başına düşen oranı (Ratios per match) verir.

- **Fiyat/Performans Verimliliği (Value Efficiency):**  
  `python main.py --value-efficiency 5 --min-matches 10`  
  Transfer bedeli (`Transfer_Fee`) karşılığında oyuncunun ortaya koyduğu skor reytingini matematiğe dökerek kimin aslında en "ucuz ve verimli" performans sergilediğini bulur. Kulüp yatırım değerlendirmelerinde kullanılabilir.

- **Pearson Veri Korelasyonu:**  
  `python main.py --correlations`  
  Veri setindeki değişkenlerin (Örn. Atılan Pas) doğrudan bitiş Notuyla (Reyting) olan matematiksel bağını çıkarır.
