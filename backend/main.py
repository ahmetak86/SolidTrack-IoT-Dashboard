from fastapi import FastAPI, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime, timedelta
import os
import sys
import logging

# --- YOL AYARLARI ---
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

from backend.database import SessionLocal, engine
from backend.models import Base, AlarmEvent, Device, TelemetryLog, UtilizationEvent
from backend.alarm_engine import (
    check_telemetry_alarms, 
    check_utilization_alarm, 
    check_work_hours_alarm
)

# Veritabanı tablolarını oluştur/güncelle
Base.metadata.create_all(bind=engine)

# --- LOGLAMA ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("SolidTrackAPI")

app = FastAPI(
    title="SolidTrack Global API",
    description="Real-time Webhook & Admin Management Service",
    version="1.2.0" # Sürüm atladık!
)

# --- DB OTURUMU ---
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- YARDIMCI MODELLER ---
class DashboardStats(BaseModel):
    total_active: int
    critical_count: int
    warning_count: int
    last_update: datetime

# --- ZEKA MOTORU: EVENT SINIFLANDIRMA ---
def classify_event_logic(duration, activity_val):
    """
    Push API'den gelen veriyi analiz eder.
    (sync_utilization_smart.py mantığının aynısı)
    """
    # Gelen veri bazen boolean, bazen 0/1, bazen string olabilir. Güvenli çevirim:
    is_active = str(activity_val).lower() in ['true', '1', 'on']
    
    if not is_active:
        return {"cat": "Boşta Bekleme (Idle)", "color": "#E0E0E0", "is_burst": False, "raw": 0}

    # Aktif ise süreye göre sınıflandır
    if duration > 180:
        return {"cat": "Nakliye / Uzun Hareket", "color": "#000000", "is_burst": True, "raw": 1}
    elif duration <= 20:
        return {"cat": "İdeal Çalışma (0-20s)", "color": "#00C853", "is_burst": True, "raw": 1} # YEŞİL
    elif 21 <= duration <= 40:
        return {"cat": "Kabul Edilebilir (21-40s)", "color": "#FFD600", "is_burst": True, "raw": 1} # SARI
    elif 41 <= duration <= 80:
        return {"cat": "Dikkat: Uzun Vuruş (41-80s)", "color": "#FF6D00", "is_burst": True, "raw": 1} # TURUNCU
    else: # 81-180 arası
        return {"cat": "HATA: Operatör Hatası (81s+)", "color": "#D50000", "is_burst": True, "raw": 1} # KIRMIZI

# --- WEBHOOK (PUSH API) ---
@app.post("/api/push/trusted")
async def trusted_webhook(request: Request, db: Session = Depends(get_db)):
    """
    Trusted Global'den gelen CANLI verileri (Konum + İş) yakalar.
    """
    try:
        payload = await request.json()
        logger.info(f"📡 Push Alındı: {payload}")

        records = payload if isinstance(payload, list) else [payload]
        processed_count = 0

        for data in records:
            serial_no = data.get("SerialNumber")
            if not serial_no: continue

            # --- ZAMAN DAMGASI DÜZELTME (UTC) ---
            ts = datetime.utcnow() # Varsayılan
            if "Timestamp" in data:
                try:
                    # Gelen: "2026-01-28T14:00:00Z" -> Timezone Aware
                    aware_dt = datetime.fromisoformat(data["Timestamp"].replace('Z', '+00:00'))
                    # DB için: Naive UTC
                    ts = aware_dt.replace(tzinfo=None)
                except:
                    pass
            # ------------------------------------

            # 1. TİP: KONUM VE TELEMETRİ (Latitude varsa)
            if "Latitude" in data:
                new_log = TelemetryLog(
                    log_id=f"PUSH_GPS_{int(ts.timestamp())}_{serial_no}",
                    device_id=serial_no,
                    timestamp=ts,
                    latitude=data.get("Latitude"),
                    longitude=data.get("Longitude"),
                    speed_kmh=data.get("Speed", 0),
                    battery_pct=data.get("BatteryLevel", 0),
                    temp_c=data.get("Temperature", 0),
                    max_shock_g=data.get("MaxAcceleration", 0)
                )
                db.merge(new_log) # Varsa güncelle, yoksa ekle
                
                # Alarm Kontrolü
                try:
                    check_telemetry_alarms(
                        device_id=serial_no,
                        battery_pct=new_log.battery_pct,
                        speed_kmh=new_log.speed_kmh,
                        shock_g=new_log.max_shock_g,
                        timestamp=ts
                    )
                except Exception as e:
                    logger.error(f"Telemetri Alarm Hatası: {e}")
                
                processed_count += 1

            # 2. TİP: KULLANIM / UTILIZATION (Duration varsa)
            # Trusted bazen "Duration" bazen "WorkTime" gönderebilir, API'ye göre Duration standarttır.
            elif "Duration" in data:
                duration_sec = data.get("Duration", 0)
                activity_val = data.get("Activity", 1) # Varsayılan aktif
                
                # Akıllı Sınıflandırma
                info = classify_event_logic(duration_sec, activity_val)
                
                # Bitiş zamanı Timestamp ise, başlangıcı hesapla
                end_ts = ts
                start_ts = end_ts - timedelta(seconds=duration_sec)

                new_event = UtilizationEvent(
                    device_id=serial_no,
                    start_time=start_ts,
                    end_time=end_ts,
                    duration_sec=duration_sec,
                    category=info["cat"],
                    color_code=info["color"],
                    is_burst=info["is_burst"],
                    raw_activity=info["raw"]
                )
                db.add(new_event)

                # Alarm Kontrolü (Sadece Çalışma Varsa)
                if info["raw"] == 1:
                    try:
                        # 1. Hatalı Kullanım (Uç Şişirme)
                        check_utilization_alarm(serial_no, duration_sec, end_ts)
                        # 2. Mesai Dışı (Hırsızlık)
                        check_work_hours_alarm(serial_no, start_ts)
                    except Exception as e:
                        logger.error(f"Utilization Alarm Hatası: {e}")
                
                processed_count += 1

        db.commit()
        return {"status": "success", "processed": processed_count}

    except Exception as e:
        logger.error(f"❌ Webhook Genel Hatası: {e}")
        # Hata olsa bile 200 dönüyoruz ki Trusted sürekli retry yapmasın
        return {"status": "error", "message": str(e)}

# --- DİĞER ENDPOINTLER ---

@app.get("/")
def health_check():
    return {"status": "Online", "mode": "Real-time Push Active", "utc_time": datetime.utcnow()}

@app.get("/api/dashboard/stats", response_model=DashboardStats)
def get_stats(db: Session = Depends(get_db)):
    active_q = db.query(AlarmEvent).filter(AlarmEvent.is_active == True)
    return {
        "total_active": active_q.count(),
        "critical_count": active_q.filter(AlarmEvent.severity == "Critical").count(),
        "warning_count": active_q.filter(AlarmEvent.severity == "Warning").count(),
        "last_update": datetime.utcnow()
    }