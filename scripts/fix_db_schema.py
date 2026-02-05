import sqlite3
import os

# Veritabanı yolu
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
DB_PATH = os.path.join(BASE_DIR, "backend", "solidtrack.db")

def add_column_if_not_exists(cursor, table, column, col_type):
    try:
        print(f"🛠️ '{table}' tablosuna '{column}' sütunu ekleniyor...")
        cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}")
        print(f"   ✅ Başarılı: {column} eklendi.")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e):
            print(f"   ℹ️ Zaten var: {column}")
        else:
            print(f"   ❌ Hata: {e}")

def fix_schema():
    if not os.path.exists(DB_PATH):
        print("❌ Veritabanı bulunamadı!")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    print("🚑 VERİTABANI TAMİRİ BAŞLADI...")

    # 1. TelemetryLog Tablosuna Eksikleri Ekle
    add_column_if_not_exists(cursor, "telemetry_logs", "speed", "REAL")
    add_column_if_not_exists(cursor, "telemetry_logs", "heading", "REAL")
    add_column_if_not_exists(cursor, "telemetry_logs", "temp_c", "REAL")
    add_column_if_not_exists(cursor, "telemetry_logs", "battery_v", "REAL")

    # 2. Değişiklikleri Kaydet
    conn.commit()
    conn.close()
    print("\n🎉 TAMİR TAMAMLANDI! Artık scriptleri çalıştırabilirsin.")

if __name__ == "__main__":
    fix_schema()