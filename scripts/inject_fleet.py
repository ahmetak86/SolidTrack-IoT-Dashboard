# backend/inject_fleet.py (GÜNCELLENMİŞ)
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base, User, Device, TelemetryLog
import random
import os
from datetime import datetime

# --- AKILLI YOL AYARI ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "solidtrack.db")
print(f"Hedef Veritabanı: {DB_PATH}")

engine = create_engine(f"sqlite:///{DB_PATH}")
Session = sessionmaker(bind=engine)
session = Session()

def inject_data():
    print("🚀 Filo Enjeksiyonu Başlıyor...")

    # Kullanıcı Kontrolü
    user = session.query(User).filter(User.company_name.like("%Solidus%")).first()
    if not user:
        print("⚠️ 'Solidus' bulunamadı, herhangi bir admin seçiliyor...")
        user = session.query(User).first()
        if not user:
            print("❌ HİÇ KULLANICI YOK! Önce init_db.py çalıştır.")
            return
    
    print(f"👤 Hedef Kullanıcı: {user.company_name}")

    fleet_config = [
        (2, "hydraulic_breaker", "Kırıcı", "Atlas Copco HB"),
        (50, "excavator", "Ekskavatör", "CAT 320 GC"),
        (6, "hydraulic_auger", "Burgu", "Auger Torque 50K"),
        (7, "mixer", "Mikser", "Mercedes Arocs"),
        (4, "truck", "Kamyon", "Ford Cargo 4142"),
        (2, "concrete_cutter", "Beton Kesme", "Husqvarna FS 400")
    ]

    total_added = 0
    base_lat, base_lon = 39.7800, 32.8000

    for count, icon, name_prefix, model_prefix in fleet_config:
        for i in range(count):
            dev_id = f"EQ-{icon[:3].upper()}-{random.randint(1000, 9999)}"
            
            # Cihaz var mı kontrol et (Tekrar tekrar eklemesin)
            existing = session.query(Device).filter(Device.device_id == dev_id).first()
            if existing: continue

            device = Device(
                device_id=dev_id,
                owner_id=user.id,
                unit_name=f"{name_prefix} #{i+1}",
                asset_model=f"{model_prefix}",
                icon_type=icon, 
                is_active=True,
                address="Şantiye Sahası",
                initial_hours_offset=random.randint(100, 5000)
            )
            session.add(device)

            # Log Ekle
            log = TelemetryLog(
                log_id=f"LOG_INIT_{dev_id}",
                device_id=dev_id,
                timestamp=datetime.utcnow(),
                latitude=base_lat + random.uniform(-0.05, 0.05),
                longitude=base_lon + random.uniform(-0.05, 0.05),
                speed_kmh=random.choice([0, 25, 40]),
                battery_pct=85, temp_c=75, max_shock_g=0.1, tilt_deg=0
            )
            session.add(log)
            total_added += 1

    session.commit()
    print(f"✅ Başarılı! {total_added} makine eklendi.")

if __name__ == "__main__":
    inject_data()