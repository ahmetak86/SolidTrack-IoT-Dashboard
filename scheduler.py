# scheduler.py (ANA DİZİN İÇİN ÖZEL AYAR)
import time
import schedule
import logging
from datetime import datetime
import sys
import os

# --- PATH AYARLARI (KÖPRÜLERİ KURUYORUZ) ---
# 1. Ana dizini (SolidTrack) belirle
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(BASE_DIR)

# 2. 'scripts' klasörünü yola ekle (Çünkü sync_trusted orada!)
SCRIPTS_DIR = os.path.join(BASE_DIR, "scripts")
sys.path.append(SCRIPTS_DIR)

# --- İMPORT ---
try:
    # Artık scripts klasörünü gördüğü için direkt çağırabiliriz
    from sync_trusted import TrustedClient
    print(f"✅ Modül 'scripts' klasöründen yüklendi: {SCRIPTS_DIR}")
except ImportError as e:
    print("\n❌ KRİTİK HATA: 'sync_trusted.py' bulunamadı!")
    print(f"Kontrol edilen klasör: {SCRIPTS_DIR}")
    print(f"Hata Detayı: {e}")
    # Klasörde ne var ne yok bakalım (Debug için)
    if os.path.exists(SCRIPTS_DIR):
        print(f"Klasördeki dosyalar: {os.listdir(SCRIPTS_DIR)}")
    else:
        print("Böyle bir klasör yok!")
    time.sleep(5)
    exit(1)

# --- LOGLAMA ---
logging.basicConfig(
    filename='scheduler.log',
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

def job_sync_fleet():
    """
    Filo verilerini ve sensörleri senkronize eden görev.
    """
    print(f"\n🔄 [OTOMASYON] Veri Senkronizasyonu Başlıyor... ({datetime.now().strftime('%H:%M:%S')})")
    try:
        client = TrustedClient()
        if client.login():
            # 1. Verileri Çek
            client.sync_fleet_and_sensors()
            client.close()
            logging.info("Senkronizasyon BASARILI.")
            print("✅ [OTOMASYON] Veriler başarıyla güncellendi.")
            
            # 2. ALARM KONTROLÜ (Geofence + Hareketsizlik)
            try:
                # Alarm motoru backend/alarm_engine.py içinde
                # Hareketsizlik fonksiyonunu da import ediyoruz
                from backend.alarm_engine import check_geofence_violations, check_inactivity_alarms
                
                check_geofence_violations() # Geofence İhlalleri
                check_inactivity_alarms()   # 3-7 Gün Sinyal Alamama Durumu
                
            except ImportError:
                print("⚠️ Uyarı: Alarm Motoru (backend/alarm_engine.py) bulunamadı.")
            except Exception as e:
                print(f"❌ Alarm Hatası: {e}")

        else:
            logging.error("Giriş Başarısız.")
            print("❌ [OTOMASYON] Giriş yapılamadı.")
    except Exception as e:
        logging.error(f"Hata: {e}")
        print(f"⚠️ [OTOMASYON] Bir hata oluştu: {e}")

# --- ZAMANLAMA ---
SCHEDULE_INTERVAL_MINUTES = 5

print(f"🤖 SolidTrack Otomasyon Robotu Başlatıldı.")
print(f"📂 Çalışma Yeri: {BASE_DIR}")
print(f"🔗 Bağlanan Script Klasörü: {SCRIPTS_DIR}")
print(f"⏱️  Periyot: Her {SCHEDULE_INTERVAL_MINUTES} dakikada bir çalışacak.")
print("Çıkmak için CTRL+C yapabilirsiniz.\n")

# İlk açılışta çalıştır
job_sync_fleet()

# Zamanlayıcı
schedule.every(SCHEDULE_INTERVAL_MINUTES).minutes.do(job_sync_fleet)

while True:
    try:
        schedule.run_pending()
        time.sleep(1)
    except KeyboardInterrupt:
        print("\n🛑 Robot durduruldu.")
        break