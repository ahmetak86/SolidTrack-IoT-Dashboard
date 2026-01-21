# backend/init_db.py (DÜZELTİLMİŞ)
import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os
import sys

# UtilizationLog olarak import ediyoruz çünkü models.py içinde öyle bıraktık
from models import (
    Base, User, Device, TelemetryLog, 
    UtilizationLog, UtilizationEvent, UtilizationProfile, 
    ReportSubscription, GeoSite, AlarmEvent, ShareLink
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_EXCEL_FILE = os.path.join(BASE_DIR, "SolidTrack_Master_DB_Final.xlsx")
SQL_DB_URL = f"sqlite:///{os.path.join(BASE_DIR, 'solidtrack.db')}"

engine = create_engine(SQL_DB_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
db = SessionLocal()

def seed_data():
    print(f"🚀 Veritabanı kurulumu başlatılıyor...")

    # 1. Excel Kontrol
    xls = None
    if os.path.exists(DB_EXCEL_FILE):
        try:
            xls = pd.ExcelFile(DB_EXCEL_FILE)
            print("📂 Excel dosyası bulundu.")
        except Exception as e:
            print(f"❌ Excel hatası: {e}")
            return
    
    # 2. Tabloları Oluştur
    try:
        Base.metadata.create_all(bind=engine)
        print("✅ Tablo yapısı doğrulandı.")
    except Exception as e:
        print(f"❌ Tablo hatası: {e}")
        return

    # --- 3. PROFİLLERİ YÜKLE ---
    print("🧠 Profiller yükleniyor...")
    profiles = [
        {"id": "PROF_BREAKER", "name": "Hidrolik Kırıcı", "mode": "Burst", "g": 20.0, "sec": 10, "color": "#FF0000"},
        {"id": "PROF_DRUM_CUTTER", "name": "Drum Cutter (Törpü)", "mode": "Motion Extended", "g": 4.0, "sec": 10, "color": "#0000FF"},
        {"id": "PROF_SHEAR", "name": "Shear / Cutter (Makas)", "mode": "Motion Extended", "g": 2.0, "sec": 10, "color": "#008000"},
        {"id": "PROF_TRANSPORT", "name": "Kamyon / Nakliye", "mode": "Standard", "g": 0.5, "sec": 60, "color": "#808080"}
    ]
    for p in profiles:
        if not db.query(UtilizationProfile).filter(UtilizationProfile.profile_id == p["id"]).first():
            db.add(UtilizationProfile(
                profile_id=p["id"], profile_name=p["name"], mode_name=p["mode"],
                motion_threshold_g=p["g"], min_active_time_sec=p["sec"], color_code=p["color"]
            ))
    db.commit()

    def clean_val(val, default=""):
        if pd.isna(val): return default
        val_str = str(val).strip()
        if val_str.endswith(".0"): val_str = val_str[:-2]
        return val_str

    # --- 4. KULLANICILARI YÜKLE (ESKİ SÜTUNLARLA) ---
    if xls and "1_Users_Master" in xls.sheet_names:
        df_users = pd.read_excel(xls, "1_Users_Master")
        count = 0
        for _, row in df_users.iterrows():
            uid = clean_val(row['User_ID'])
            if not uid: continue
            if db.query(User).filter(User.id == uid).first(): continue

            user = User(
                id=uid,
                username=clean_val(row['Username']),
                email=clean_val(row['Email_Login']),
                password_hash=clean_val(row['Password']),
                role=clean_val(row['User_Role']),
                company_name=clean_val(row.get('Company_Name')),
                full_name=f"{clean_val(row.get('First_Name'))} {clean_val(row.get('Last_Name'))}",
                phone=clean_val(row.get('Phone_Raw')),
                company_address=clean_val(row.get('Address_Line')),
                tax_office=clean_val(row.get('Tax_Office')),
                tax_number=clean_val(row.get('Tax_Number')),
                logo_url=clean_val(row.get('Logo_Url')),
                language=clean_val(row.get('Reg_Language'), 'Turkish'),
                timezone=clean_val(row.get('Reg_TimeZone'), 'Europe/Istanbul'),
                
                # İŞTE BURASI PATLIYORDU, ARTIK PATLAMAZ ÇÜNKÜ MODELS'E GERİ EKLEDİK
                notification_email_enabled=True,
                notify_low_battery=True,
                notify_shock=True
            )
            db.add(user)
            count += 1
        db.commit()
        print(f"👤 {count} Kullanıcı eklendi.")

    # --- 5. CİHAZLARI YÜKLE (ESKİ SÜTUNLARLA) ---
    if xls and "2_Device_Inventory" in xls.sheet_names:
        df_devices = pd.read_excel(xls, "2_Device_Inventory")
        count = 0
        for _, row in df_devices.iterrows():
            did = clean_val(row['Device_ID'])
            if not did: continue
            if db.query(Device).filter(Device.device_id == did).first(): continue

            def get_float(val, default=0.0):
                try: return float(val)
                except: return default
            
            def get_int(val, default=0):
                try: return int(float(val))
                except: return default

            u_name = clean_val(row.get('Unit_Name'), '').lower()
            prof_id = "PROF_TRANSPORT"
            if "kırıcı" in u_name or "r250" in u_name or "breaker" in u_name: prof_id = "PROF_BREAKER"
            elif "drum" in u_name or "cutter" in u_name: prof_id = "PROF_DRUM_CUTTER"
            elif "makas" in u_name or "shear" in u_name: prof_id = "PROF_SHEAR"

            device = Device(
                device_id=did,
                owner_id=clean_val(row['Owner_User_ID']),
                unit_name=clean_val(row.get('Unit_Name'), 'Adsız Cihaz'),
                asset_model=clean_val(row.get('Asset_Model'), 'Unknown'),
                profile_id=prof_id,
                initial_hours_offset=get_float(row.get('Initial_Hours_Offset')),
                is_active=str(row.get('Is_Active')).lower() in ['true', '1', 'yes'],
                maintenance_interval_hours=get_int(row.get('Limit_Service_Hours'), 200),
                next_service_hours=get_int(row.get('Limit_Service_Hours'), 200),
                
                # BURASI DA ARTIK PATLAMAZ
                min_battery_threshold=get_int(row.get('Min_Battery_Threshold'), 20),
                notification_email=clean_val(row.get('Notification_Email')),
                limit_shock_g=get_float(row.get('Limit_Shock_G'), 8.0),
                limit_temp_c=get_int(row.get('Limit_Temp_C'), 80)
            )
            db.add(device)
            count += 1
        
        db.commit()
        print(f"🚜 {count} Cihaz eklendi.")

    print("\n🎉 Veritabanı (Eski + Yeni Özellikler) Hazır!")

if __name__ == "__main__":
    seed_data()