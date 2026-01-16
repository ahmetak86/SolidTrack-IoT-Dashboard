# backend/fix_users_db.py (GÜNCELLENMİŞ)
from sqlalchemy import create_engine, text
import os

# --- AKILLI YOL AYARI (Bu dosya neredeyse DB oradadır) ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__)) 
DB_PATH = os.path.join(BASE_DIR, "solidtrack.db")

print(f"Hedef Veritabanı: {DB_PATH}")
engine = create_engine(f"sqlite:///{DB_PATH}")

def fix_users_schema():
    print(f"🔧 Kullanıcı Tablosu Onarılıyor...")
    
    columns_to_add = [
        ("date_format", "VARCHAR", "'DD.MM.YYYY'"),
        ("unit_length", "VARCHAR", "'Metre/Km'"),
        ("unit_temp", "VARCHAR", "'Celsius (°C)'"),
        ("unit_pressure", "VARCHAR", "'Bar'"),
        ("unit_volume", "VARCHAR", "'Litre'"),
        ("notification_email_enabled", "BOOLEAN", "1"),
        ("notify_low_battery", "BOOLEAN", "1"),
        ("notify_shock", "BOOLEAN", "1"),
        ("notify_geofence", "BOOLEAN", "1"),
        ("notify_maintenance", "BOOLEAN", "1"),
        ("notify_daily_report", "BOOLEAN", "1")
    ]

    with engine.connect() as con:
        for col_name, col_type, default_val in columns_to_add:
            try:
                # Sütun var mı kontrolü (Hata yönetimini daha sessiz yapalım)
                query = text(f"ALTER TABLE users ADD COLUMN {col_name} {col_type} DEFAULT {default_val}")
                con.execute(query)
                con.commit()
                print(f"   ✅ '{col_name}' eklendi.")
            except Exception as e:
                if "duplicate column" in str(e).lower():
                    print(f"   ℹ️ '{col_name}' zaten var.")
                else:
                    print(f"   ⚠️ Hata ({col_name}): {e}")

    print("\n🏁 Kullanıcı tablosu onarımı tamamlandı.")

if __name__ == "__main__":
    fix_users_schema()