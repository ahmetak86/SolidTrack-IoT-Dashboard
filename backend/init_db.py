# backend/init_db.py (GARANTİ ÇALIŞAN VERSİYON)
import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base, User, Device, TelemetryLog, UtilizationLog, ReportSubscription
import os

# --- AKILLI ADRES SİSTEMİ (BU KISIM HATAYI ÇÖZER) ---
# Bu dosya (init_db.py) nerede? -> .../backend/
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Excel ve DB dosyasının tam adresini oluştur
DB_EXCEL_FILE = os.path.join(BASE_DIR, "SolidTrack_Master_DB_Final.xlsx")
SQL_DB_URL = f"sqlite:///{os.path.join(BASE_DIR, 'solidtrack.db')}"

# Veritabanı Bağlantısı
engine = create_engine(SQL_DB_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
db = SessionLocal()

def seed_data():
    print(f"🚀 Veritabanı kurulumu başlatılıyor...")
    print(f"📂 Çalışılan Klasör Yolu: {BASE_DIR}") # Yolu ekrana basalım ki görelim

    # 1. Dosya Kontrolü
    if not os.path.exists(DB_EXCEL_FILE):
        print(f"❌ HATA: '{DB_EXCEL_FILE}' dosyası bulunamadı!")
        print("   Excel dosyasının 'backend' klasöründe olduğundan emin ol.")
        return

    # 2. Excel Dosyasını Oku
    print("📂 Excel dosyası okunuyor...")
    try:
        xls = pd.ExcelFile(DB_EXCEL_FILE)
    except Exception as e:
        print(f"❌ Excel okuma hatası: {e}")
        return

    # 3. Veritabanını Sıfırla
    print("🧹 Eski tablolar temizleniyor...")
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    print("✅ Tablolar (yeni özelliklerle) sıfırdan oluşturuldu.")

    # --- YARDIMCI FONKSİYON ---
    def clean_val(val, default=""):
        if pd.isna(val): return default
        val_str = str(val).strip()
        if val_str.endswith(".0"): 
            val_str = val_str[:-2]
        return val_str

    # --- KULLANICILARI YÜKLE ---
    if "1_Users_Master" in xls.sheet_names:
        df_users = pd.read_excel(xls, "1_Users_Master")
        count = 0
        for _, row in df_users.iterrows():
            user = User(
                # Temel
                id=clean_val(row['User_ID']),
                username=clean_val(row['Username']),
                email=clean_val(row['Email_Login']),
                password_hash=clean_val(row['Password']),
                role=clean_val(row['User_Role']),
                
                # Profil
                company_name=clean_val(row.get('Company_Name')),
                full_name=f"{clean_val(row.get('First_Name'))} {clean_val(row.get('Last_Name'))}",
                phone=clean_val(row.get('Phone_Raw')),
                company_address=clean_val(row.get('Address_Line')),
                tax_office=clean_val(row.get('Tax_Office')),
                tax_number=clean_val(row.get('Tax_Number')),
                logo_url=clean_val(row.get('Logo_Url')), # Eğer excelde yoksa boş gelir

                # Ayarlar (Varsayılanlar)
                language=clean_val(row.get('Reg_Language'), 'Turkish'),
                timezone=clean_val(row.get('Reg_TimeZone'), 'Europe/Istanbul'),
                date_format='DD.MM.YYYY',
                
                # Birimler
                unit_length='Metre / Km',
                unit_temp='Celsius (°C)',
                unit_pressure='Bar',
                unit_volume='Litre',
                
                # Bildirimler
                notification_email_enabled=True,
                notify_low_battery=True,
                notify_shock=True,
                notify_geofence=True,
                notify_maintenance=True,
                notify_daily_report=True
            )
            db.add(user)
            count += 1
        print(f"👤 {count} Kullanıcı eklendi.")

    # --- CİHAZLARI YÜKLE ---
    if "2_Device_Inventory" in xls.sheet_names:
        df_devices = pd.read_excel(xls, "2_Device_Inventory")
        count = 0
        for _, row in df_devices.iterrows():
            try:
                def get_float(val, default=0.0):
                    try: return float(val)
                    except: return default
                
                def get_int(val, default=0):
                    try: return int(float(val))
                    except: return default

                device = Device(
                    device_id=clean_val(row['Device_ID']),
                    owner_id=clean_val(row['Owner_User_ID']),
                    unit_name=clean_val(row.get('Unit_Name'), 'Adsız Cihaz'),
                    asset_model=clean_val(row.get('Asset_Model'), 'Unknown'),
                    initial_hours_offset=get_float(row.get('Initial_Hours_Offset')),
                    min_battery_threshold=get_int(row.get('Min_Battery_Threshold'), 20),
                    notification_email=clean_val(row.get('Notification_Email')),
                    is_active=str(row.get('Is_Active')).lower() in ['true', '1', 'yes'],
                    limit_shock_g=get_float(row.get('Limit_Shock_G'), 8.0),
                    limit_temp_c=get_int(row.get('Limit_Temp_C'), 80),
                    maintenance_interval_hours=get_int(row.get('Limit_Service_Hours'), 200),
                    next_service_hours=get_int(row.get('Limit_Service_Hours'), 200)
                )
                db.add(device)
                count += 1
            except Exception as e:
                pass # Hata olursa geç
        
        print(f"🚜 {count} Cihaz eklendi.")

    db.commit()
    print("\n🎉 TEBRİKLER! Veritabanı başarıyla oluşturuldu.")

if __name__ == "__main__":
    seed_data()