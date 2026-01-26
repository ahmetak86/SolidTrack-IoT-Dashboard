# scripts/upgrade_db_v4.py
from sqlalchemy import create_engine, text
import os

# Veritabanı yolunu bul
CURRENT_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
possible_paths = [
    os.path.join(CURRENT_SCRIPT_DIR, "..", "backend", "solidtrack.db"),
    os.path.join(CURRENT_SCRIPT_DIR, "backend", "solidtrack.db"),
    os.path.join(CURRENT_SCRIPT_DIR, "solidtrack.db"),
]

DB_PATH = None
for path in possible_paths:
    if os.path.exists(path):
        DB_PATH = os.path.abspath(path)
        break

if not DB_PATH:
    print("❌ HATA: 'solidtrack.db' bulunamadı!")
    exit()

print(f"📂 Veritabanı: {DB_PATH}")
engine = create_engine(f"sqlite:///{DB_PATH}")

with engine.connect() as conn:
    try:
        sql = text("ALTER TABLE geosites ADD COLUMN trusted_site_id INTEGER DEFAULT NULL")
        conn.execute(sql)
        print("✅ 'trusted_site_id' sütunu başarıyla eklendi.")
    except Exception as e:
        if "duplicate" in str(e): print("ℹ️ Sütun zaten var.")
        else: print(f"❌ Hata: {e}")