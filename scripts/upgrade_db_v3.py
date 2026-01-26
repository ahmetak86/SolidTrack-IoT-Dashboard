from sqlalchemy import create_engine, text
import os

# Veritabanı yolunu bul
CURRENT_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
# Olası yolları kontrol et
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
        # Ara tabloyu oluştur
        sql = text("""
        CREATE TABLE IF NOT EXISTS device_geosite_link (
            device_id VARCHAR NOT NULL,
            site_id INTEGER NOT NULL,
            PRIMARY KEY (device_id, site_id),
            FOREIGN KEY(device_id) REFERENCES devices(device_id),
            FOREIGN KEY(site_id) REFERENCES geosites(site_id)
        );
        """)
        conn.execute(sql)
        print("✅ 'device_geosite_link' tablosu başarıyla oluşturuldu.")
    except Exception as e:
        print(f"❌ Hata: {e}")