# reset_daily_data.py
import sys
import os
from datetime import datetime, timedelta

# Backend yolunu ekle
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))
from database import SessionLocal
from models import UtilizationEvent, AlarmEvent, TelemetryLog

def clear_todays_data():
    db = SessionLocal()
    try:
        # Bugünü bul (UTC)
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        
        print(f"🧹 {today_start} tarihinden sonraki veriler temizleniyor...")
        
        # 1. Bugünün Utilization Verilerini Sil (Ki tekrar çeksin)
        deleted_util = db.query(UtilizationEvent).filter(UtilizationEvent.start_time >= today_start).delete()
        
        # 2. Bugünün Alarmlarını Sil (Ki tekrar alarm üretsin)
        deleted_alarms = db.query(AlarmEvent).filter(AlarmEvent.timestamp >= today_start).delete()
        
        db.commit()
        print(f"✅ Temizlendi:\n   - {deleted_util} Utilization Kaydı\n   - {deleted_alarms} Alarm Kaydı")
        print("\n👉 Şimdi 'scripts/sync_utilization_smart.py' dosyasını tekrar çalıştırabilirsin.")
        
    except Exception as e:
        print(f"❌ Hata: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    clear_todays_data()