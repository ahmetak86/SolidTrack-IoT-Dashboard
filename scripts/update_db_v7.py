import sys
import os
import sqlite3
from sqlalchemy import text

# 1. Proje ana dizinini yola ekle
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

print(f"📂 Çalışma Dizini: {parent_dir}")

from backend.database import engine, SQL_DB_URL
from backend.models import Base, Operator, DeviceShift, ServiceRecord, Alarm, AlarmRule, DeviceDocument

def add_column_if_not_exists(cursor, table, column, col_type, default=None):
    """
    Güvenli sütun ekleme fonksiyonu.
    Eğer sütun tabloda yoksa ekler, varsa pas geçer.
    """
    try:
        cursor.execute(f"SELECT {column} FROM {table} LIMIT 1")
    except sqlite3.OperationalError:
        # Sütun yok, ekleyelim
        print(f"🔧 ONARIM: '{table}' tablosuna '{column}' sütunu ekleniyor...")
        if default is not None:
            if isinstance(default, str):
                default_val = f"'{default}'"
            else:
                default_val = default
            cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_type} DEFAULT {default_val}")
        else:
            cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}")
        print(f"   ✅ Eklendi.")

def update_database():
    print("🔄 Veritabanı V7 sürümüne güncelleniyor...")

    # 1. YENİ TABLOLARI OLUŞTUR (create_all sadece olmayanları yaratır)
    # Operators, DeviceShifts, ServiceRecords vb. burada oluşacak.
    try:
        Base.metadata.create_all(bind=engine)
        print("✅ Tablo Yapıları Kontrol Edildi / Eksikler Oluşturuldu.")
    except Exception as e:
        print(f"❌ Tablo oluşturma hatası: {e}")

    # 2. MEVCUT TABLOLARA YENİ SÜTUNLARI EKLE (ALTER TABLE)
    # SQLAlchemy create_all, mevcut tablolara yeni eklenen sütunları OTOMATİK EKLEMEZ.
    # Bu yüzden manuel kontrol yapıyoruz.
    
    # SQLite bağlantısı aç (Raw SQL için)
    db_path = SQL_DB_URL.replace("sqlite:///", "")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # --- DEVICE TABLOSU GÜNCELLEMELERİ ---
        add_column_if_not_exists(cursor, "devices", "maintenance_interval_hours", "INTEGER", 250)
        add_column_if_not_exists(cursor, "devices", "last_maintenance_hour", "FLOAT", 0.0)
        add_column_if_not_exists(cursor, "devices", "last_service_date", "DATETIME", None)
        add_column_if_not_exists(cursor, "devices", "next_service_hours", "INTEGER", None)
        
        # --- USER TABLOSU GÜNCELLEMELERİ ---
        add_column_if_not_exists(cursor, "users", "parent_id", "VARCHAR", None)
        add_column_if_not_exists(cursor, "users", "tax_no", "VARCHAR", None)
        add_column_if_not_exists(cursor, "users", "tax_office", "VARCHAR", None)
        add_column_if_not_exists(cursor, "users", "billing_address", "VARCHAR", None)
        
        # --- UTILIZATION PROFILE GÜNCELLEMELERİ ---
        add_column_if_not_exists(cursor, "utilization_profiles", "motion_threshold_g", "FLOAT", 0.5)
        add_column_if_not_exists(cursor, "utilization_profiles", "min_active_time_sec", "INTEGER", 10)
        
        # --- GEOSITE GÜNCELLEMELERİ ---
        add_column_if_not_exists(cursor, "geosites", "auto_enable_entry_alarms", "BOOLEAN", 0)

        conn.commit()
        print("✅ Sütun Kontrolleri ve Eklemeler Tamamlandı.")

    except Exception as e:
        print(f"❌ Sütun ekleme hatası: {e}")
        conn.rollback()
    finally:
        conn.close()

    print("\n🚀 Veritabanı başarıyla V7 yapısına yükseltildi.")
    print("   (Operators, DeviceShifts, ServiceRecords tabloları hazır.)")

if __name__ == "__main__":
    update_database()