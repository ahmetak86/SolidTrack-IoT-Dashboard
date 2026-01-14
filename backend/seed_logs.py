# backend/seed_logs.py (ALARMLAR DAHİL)
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Device, TelemetryLog, AlarmEvent
import random
from datetime import datetime, timedelta
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SQL_DB_URL = f"sqlite:///{os.path.join(BASE_DIR, 'solidtrack.db')}"
engine = create_engine(SQL_DB_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine)
db = SessionLocal()

def generate_logs():
    print("🧪 Veritabanına test verileri ve ALARMLAR basılıyor...")
    devices = db.query(Device).all()
    
    if not devices:
        print("❌ Cihaz bulunamadı! Önce init_db.py çalıştır.")
        return

    # Önce eski alarmları temizle
    db.query(TelemetryLog).delete()
    db.query(AlarmEvent).delete()
    
    start_date = datetime.utcnow() - timedelta(days=5)
    
    total_logs = 0
    total_alarms = 0

    for device in devices:
        current_time = start_date
        lat, lon = 39.9863, 32.7667
        
        while current_time < datetime.utcnow():
            # 1. Telemetri
            is_moving = random.choice([True, False])
            speed = random.randint(10, 80) if is_moving else 0
            if is_moving:
                lat += random.uniform(-0.01, 0.01)
                lon += random.uniform(-0.01, 0.01)

            log = TelemetryLog(
                log_id=f"LOG_{device.device_id}_{int(current_time.timestamp())}",
                device_id=device.device_id,
                timestamp=current_time,
                latitude=lat, longitude=lon, speed_kmh=speed,
                battery_pct=random.randint(15, 100),
                temp_c=random.randint(40, 95),
                max_shock_g=random.choice([0.5, 1.2, 9.5]),
                tilt_deg=random.randint(0, 15)
            )
            db.add(log)
            total_logs += 1
            
            # 2. Alarm Üretme Senaryosu (Rastgele)
            # %5 ihtimalle alarm oluşsun
            if random.random() < 0.05:
                alarm_types = [
                    ("Shock", "Critical", f"{log.max_shock_g} G", "Aşırı Darbe Algılandı"),
                    ("LowBattery", "Warning", f"%{int(log.battery_pct)}", "Pil Kritik Seviyede"),
                    ("Geofence", "Critical", "Bölge Dışı", "Şantiye Sınırı İhlali"),
                    ("Speed", "Warning", f"{speed} km/s", "Hız Limiti Aşıldı")
                ]
                sel_alarm = random.choice(alarm_types)
                
                # Alarm hala aktif mi olsun yoksa geçmişte mi kalsın?
                is_active = current_time > (datetime.utcnow() - timedelta(hours=4)) # Son 4 saattekiler aktif kalsın
                
                alarm = AlarmEvent(
                    device_id=device.device_id,
                    alarm_type=sel_alarm[0],
                    severity=sel_alarm[1],
                    value=sel_alarm[2],
                    description=sel_alarm[3],
                    is_active=is_active,
                    timestamp=current_time,
                    acknowledged_by="Sistem" if not is_active else None,
                    acknowledged_at=datetime.utcnow() if not is_active else None
                )
                db.add(alarm)
                total_alarms += 1

            current_time += timedelta(hours=3)
            
    db.commit()
    print(f"🎉 Bitti: {total_logs} Log ve {total_alarms} Alarm oluşturuldu.")

if __name__ == "__main__":
    generate_logs()