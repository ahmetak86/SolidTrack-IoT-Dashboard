import sqlite3
import os

# Veritabanı dosyasının yerini bulalım
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "backend", "solidtrack.db")

def fix_database_restore():
    print(f"🔧 Veritabanı Restorasyonu Başlıyor: {DB_PATH}")
    
    if not os.path.exists(DB_PATH):
        print("❌ Veritabanı dosyası bulunamadı! Önce init_db.py çalışmalıydı.")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # --- 1. USERS TABLOSUNU TAMİR ET ---
    print("\n👤 Users tablosuna eksik sütunlar ekleniyor...")
    user_columns = [
        ("date_format", "VARCHAR DEFAULT 'DD.MM.YYYY'"),
        ("unit_length", "VARCHAR DEFAULT 'Metre / Km'"),
        ("unit_temp", "VARCHAR DEFAULT 'Celsius (°C)'"),
        ("unit_pressure", "VARCHAR DEFAULT 'Bar'"),
        ("unit_volume", "VARCHAR DEFAULT 'Litre'"),
        ("notification_email_enabled", "BOOLEAN DEFAULT 1"),
        ("notify_low_battery", "BOOLEAN DEFAULT 1"),
        ("notify_shock", "BOOLEAN DEFAULT 1"),
        ("notify_geofence", "BOOLEAN DEFAULT 1"),
        ("notify_maintenance", "BOOLEAN DEFAULT 1"),
        ("notify_daily_report", "BOOLEAN DEFAULT 1")
    ]

    for col_name, col_def in user_columns:
        try:
            cursor.execute(f"ALTER TABLE users ADD COLUMN {col_name} {col_def}")
            print(f"   ✅ Eklendi: {col_name}")
        except sqlite3.OperationalError as e:
            if "duplicate column" in str(e):
                print(f"   ℹ️ Zaten var: {col_name}")
            else:
                print(f"   ❌ Hata ({col_name}): {e}")

    # --- 2. DEVICES TABLOSUNU TAMİR ET ---
    print("\n🚜 Devices tablosuna eksik sütunlar ekleniyor...")
    device_columns = [
        ("min_battery_threshold", "INTEGER DEFAULT 20"),
        ("notification_email", "VARCHAR"),
        ("limit_shock_g", "FLOAT DEFAULT 8.0"),
        ("limit_temp_c", "INTEGER DEFAULT 80")
    ]

    for col_name, col_def in device_columns:
        try:
            cursor.execute(f"ALTER TABLE devices ADD COLUMN {col_name} {col_def}")
            print(f"   ✅ Eklendi: {col_name}")
        except sqlite3.OperationalError as e:
            if "duplicate column" in str(e):
                print(f"   ℹ️ Zaten var: {col_name}")
            else:
                print(f"   ❌ Hata ({col_name}): {e}")

    # --- 3. KAYDET VE ÇIK ---
    conn.commit()
    conn.close()
    print("\n🎉 Veritabanı başarıyla onarıldı! Şimdi init_db.py çalıştırabilirsin.")

if __name__ == "__main__":
    fix_database_restore()