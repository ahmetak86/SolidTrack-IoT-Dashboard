# upgrade_db_v5.py
from sqlalchemy import create_engine, text
import os

# DB Yolunu Bul
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# Eğer scripts klasöründeysen bir üst klasöre çık, değilse direkt bak
if "scripts" in BASE_DIR:
    DB_PATH = os.path.join(os.path.dirname(BASE_DIR), "backend", "solidtrack.db")
else:
    DB_PATH = os.path.join(BASE_DIR, "backend", "solidtrack.db")

print(f"📂 Veritabanı Yolu: {DB_PATH}")
engine = create_engine(f"sqlite:///{DB_PATH}")

with engine.connect() as conn:
    try:
        # Sütun ekleme komutu
        conn.execute(text("ALTER TABLE geosites ADD COLUMN created_at DATETIME"))
        print("✅ 'created_at' sütunu başarıyla eklendi.")
    except Exception as e:
        print(f"ℹ️ Bilgi: {e}")