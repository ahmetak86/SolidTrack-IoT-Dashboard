# backend/worker.py
import time
import schedule
import logging
from datetime import datetime
import sys
import os

# Yolları Ayarla
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.sync_engine import SyncEngine

# Loglama
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("solidtrack_worker.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("Worker")

def job_live():
    """Canlı Takip Görevi"""
    logger.info("⏱️  [GÖREV] Canlı Takip Tetiklendi")
    try:
        engine = SyncEngine()
        engine.sync_live_fleet()
        engine.close()
    except Exception as e:
        logger.error(f"❌ Canlı Takip Hatası: {e}")

def job_history():
    """Geçmiş Analiz Görevi"""
    logger.info("⏱️  [GÖREV] Verimlilik Analizi Tetiklendi")
    try:
        engine = SyncEngine()
        engine.sync_utilization_history()
        engine.close()
    except Exception as e:
        logger.error(f"❌ Analiz Hatası: {e}")

def run_worker():
    print(f"""
    =========================================
      🚀 SOLIDTRACK OTOMASYON İŞÇİSİ (V2)
      -------------------------------------
      📡 Canlı Takip:  Her 5 Dakikada Bir
      📊 Detaylı Analiz: Her 30 Dakikada Bir
      🛡️ Alarm Motoru: Aktif
    =========================================
    """)
    
    # 1. İlk açılışta hemen bir tur çalıştır (Beklememek için)
    job_live()
    
    # 2. Zamanlayıcıları Kur
    schedule.every(5).minutes.do(job_live)
    schedule.every(30).minutes.do(job_history)
    
    # 3. Sonsuz Döngü
    while True:
        try:
            schedule.run_pending()
            time.sleep(1)
        except KeyboardInterrupt:
            print("\n🛑 İşçi durduruldu.")
            break
        except Exception as e:
            logger.critical(f"💥 İŞÇİ ÇÖKTÜ (Yeniden başlıyor): {e}")
            time.sleep(60)

if __name__ == "__main__":
    run_worker()