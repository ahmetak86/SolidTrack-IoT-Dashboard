# scheduler.py (FİNAL ROBOT YÖNETİCİSİ)
import time
import schedule
import logging
from datetime import datetime
import sys
import os

# --- 1. SETTINGS & PATHS ---
# Proje ana dizinini bul
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(BASE_DIR)

# Scripts klasörünü yola ekle (Robotlar burada)
SCRIPTS_DIR = os.path.join(BASE_DIR, "scripts")
sys.path.append(SCRIPTS_DIR)

# --- 2. LOGLAMA AYARLARI ---
logging.basicConfig(
    filename='solidtrack_robot.log',
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# --- 3. ROBOTLARI ÇAĞIRMA ---
try:
    # HIZLI ROBOT (Canlı Veri + Geofence + Pil)
    from sync_trusted import TrustedClient
    print(f"✅ Canlı Takip Modülü Yüklendi: {SCRIPTS_DIR}")
except ImportError as e:
    print(f"\n❌ KRİTİK HATA: 'scripts/sync_trusted.py' bulunamadı veya hatalı!")
    print(f"Hata Detayı: {e}")
    time.sleep(10)
    exit(1)

# AKILLI ROBOT (Opsiyonel - Eğer dosya varsa yükler)
try:
    from sync_utilization_smart import UtilizationSyncSmart
    has_analysis_module = True
except ImportError:
    has_analysis_module = False
    print("ℹ️ Detaylı analiz modülü bulunamadı, sadece canlı takip çalışacak.")

# --- 4. GÖREV TANIMLARI ---

def job_live_tracking():
    """Her 5 dakikada bir: Canlı Konum, Alarm, Pil, Geofence"""
    print(f"\n📡 [CANLI TAKİP] Başlıyor... ({datetime.now().strftime('%H:%M:%S')})")
    try:
        client = TrustedClient()
        if client.login():
            # 1. Kullanıcıları güncelle (Yeni admin var mı?)
            client.sync_users()
            # 2. Filo ve Sensör verilerini çek, Alarmları kontrol et
            client.sync_fleet_and_sensors()
            client.close()
            logging.info("Canlı takip turu tamamlandı.")
        else:
            print("❌ Giriş Hatası: Trusted API'ye bağlanılamadı.")
            logging.error("Giriş Hatası")
    except Exception as e:
        print(f"⚠️ Canlı Takip Hatası: {e}")
        logging.error(f"Canlı Takip Hatası: {e}")

def job_detailed_analysis():
    """Her 1 saatte bir: Geçmişe dönük verimlilik analizi"""
    if not has_analysis_module: return

    print(f"\n🧠 [DETAYLI ANALİZ] Başlıyor... ({datetime.now().strftime('%H:%M:%S')})")
    try:
        # Analiz sınıfını başlat (Varsa)
        robot = UtilizationSyncSmart()
        # Eğer sınıfın içinde login/run metodları varsa çağır
        if hasattr(robot, 'run'):
            robot.run()
        logging.info("Detaylı analiz tamamlandı.")
    except Exception as e:
        print(f"⚠️ Analiz Hatası: {e}")
        logging.error(f"Analiz Hatası: {e}")

# --- 5. ZAMANLAYICIYI BAŞLAT ---
print(f"🤖 SolidTrack Otomasyon Robotu Başlatıldı.")
print(f"📂 Çalışma Yeri: {BASE_DIR}")
print(f"⏱️  Canlı Takip: Her 5 dakikada bir")
if has_analysis_module:
    print(f"⏱️  Detaylı Analiz: Her 60 dakikada bir")

print("\n🚀 İLK KONTROL BAŞLIYOR (Beklememek için)...")
job_live_tracking() # İlk açılışta hemen çalıştır

# Programlanmış görevler
schedule.every(5).minutes.do(job_live_tracking)
if has_analysis_module:
    schedule.every(60).minutes.do(job_detailed_analysis)

print("\n✅ Robot devrede. Çıkmak için CTRL+C yapabilirsiniz.")
print("-" * 50)

while True:
    try:
        schedule.run_pending()
        time.sleep(1)
    except KeyboardInterrupt:
        print("\n🛑 Robot elle durduruldu.")
        break
    except Exception as e:
        print(f"💥 Beklenmeyen Hata: {e}")
        time.sleep(60) # Hata olursa 1 dk dinlenip devam et