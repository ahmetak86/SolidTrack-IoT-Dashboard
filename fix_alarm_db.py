# fix_alarm_db.py
from sqlalchemy import create_engine, text
import os

# DB Yolunu Bul
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "backend", "solidtrack.db")

print(f"📂 Veritabanı Yolu: {DB_PATH}")
engine = create_engine(f"sqlite:///{DB_PATH}")

with engine.connect() as conn:
    try:
        # Sütun ekleme komutu
        print("🛠️ 'geosite_id' sütunu ekleniyor...")
        conn.execute(text("ALTER TABLE alarm_events ADD COLUMN geosite_id INTEGER"))
        print("✅ Başarıyla eklendi!")
    except Exception as e:
        if "duplicate column name" in str(e):
            print("ℹ️ Sütun zaten varmış, sorun yok.")
        else:
            print(f"❌ Hata: {e}")