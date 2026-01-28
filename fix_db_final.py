# fix_db_final.py
from sqlalchemy import create_engine, text
import os

# DB Yolunu Bul
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# Eğer backend klasörü içindeyse bir üste çık (Garanti olsun)
if BASE_DIR.endswith("backend") or BASE_DIR.endswith("scripts"):
    BASE_DIR = os.path.dirname(BASE_DIR)

DB_PATH = os.path.join(BASE_DIR, "backend", "solidtrack.db")

print(f"📂 Veritabanı Hedefi: {DB_PATH}")

if not os.path.exists(DB_PATH):
    print("❌ HATA: Veritabanı dosyası bulunamadı!")
    exit(1)

engine = create_engine(f"sqlite:///{DB_PATH}")

# Eklenecek Sütunlar Listesi (Sütun Adı, Veri Tipi)
columns_to_add = [
    ("value", "TEXT"),
    ("acknowledged_by", "TEXT"),
    ("acknowledged_at", "DATETIME"),
    ("resolution_note", "TEXT"),
    ("geosite_id", "INTEGER") # Bunu daha önce eklemiştik ama garanti olsun
]

with engine.connect() as conn:
    print("\n🛠️ Veritabanı Onarımı Başlıyor...")
    
    for col_name, col_type in columns_to_add:
        try:
            sql = f"ALTER TABLE alarm_events ADD COLUMN {col_name} {col_type}"
            conn.execute(text(sql))
            print(f"   ✅ '{col_name}' sütunu başarıyla eklendi.")
        except Exception as e:
            if "duplicate column name" in str(e):
                print(f"   ℹ️ '{col_name}' sütunu zaten var, atlandı.")
            else:
                print(f"   ❌ '{col_name}' eklenirken hata: {e}")

    print("\n🏁 İşlem Tamamlandı.")