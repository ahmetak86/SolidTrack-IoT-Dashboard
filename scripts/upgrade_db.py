from sqlalchemy import create_engine, text
import os

# Scriptin nerede olduğunu bul
CURRENT_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# Olası veritabanı yolları (Önce backend içini, sonra ana dizini, sonra scriptin yanını kontrol et)
possible_paths = [
    os.path.join(CURRENT_SCRIPT_DIR, "..", "backend", "solidtrack.db"), # scripts klasöründeyse bir üstteki backend'e bak
    os.path.join(CURRENT_SCRIPT_DIR, "backend", "solidtrack.db"),       # Ana dizindeyse backend içine bak
    os.path.join(CURRENT_SCRIPT_DIR, "solidtrack.db"),                  # Yanında mı bak
]

DB_PATH = None
for path in possible_paths:
    if os.path.exists(path):
        DB_PATH = os.path.abspath(path)
        break

if not DB_PATH:
    # Hiçbir yerde bulamazsa varsayılan olarak backend içine oluşturmaya çalışmasın, hata versin
    print("❌ HATA: 'solidtrack.db' dosyası bulunamadı!")
    print("Lütfen bu scripti projenin ana dizininde (SolidTrack klasörü) çalıştırdığınızdan emin olun.")
    exit()

print(f"📂 Hedef Veritabanı: {DB_PATH}")
SQL_DB_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(SQL_DB_URL)

def add_column_if_not_exists(table, column, type_def):
    with engine.connect() as conn:
        try:
            # Sütun eklemeyi dene
            sql = text(f"ALTER TABLE {table} ADD COLUMN {column} {type_def}")
            conn.execute(sql)
            print(f"✅ {column} eklendi.")
        except Exception as e:
            # Hata verirse muhtemelen sütun zaten vardır
            if "duplicate column name" in str(e):
                print(f"ℹ️ {column} zaten mevcut.")
            elif "no such table" in str(e):
                print(f"❌ Kritik Hata: '{table}' tablosu bulunamadı! Yanlış DB dosyası seçilmiş olabilir.")
            else:
                print(f"❌ Hata ({column}): {e}")

# Eksik sütunları ekleyelim
print("--- Veritabanı Güncelleniyor ---")
add_column_if_not_exists("geosites", "visible_to_subgroups", "BOOLEAN DEFAULT 0")
add_column_if_not_exists("geosites", "apply_to_all_devices", "BOOLEAN DEFAULT 1")
add_column_if_not_exists("geosites", "auto_enable_new_devices", "BOOLEAN DEFAULT 1")
add_column_if_not_exists("geosites", "auto_enable_alarms", "BOOLEAN DEFAULT 1")
print("--- İşlem Tamamlandı ---")