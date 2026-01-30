# update_db.py
import sqlite3

# Veritabanı dosyanın tam adı neyse buraya yaz
DB_NAME = "solidtrack.db"  

def migrate():
    print(f"🔧 Veritabanı Güncelleniyor: {DB_NAME}...")
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        # 1. Users Tablosuna Eksikleri Ekle
        columns_to_add_user = [
            ("is_active", "BOOLEAN DEFAULT 1"),
            ("allowed_pages", "TEXT"),
            ("allowed_device_ids", "TEXT")
        ]
        
        for col_name, col_type in columns_to_add_user:
            try:
                cursor.execute(f"ALTER TABLE users ADD COLUMN {col_name} {col_type}")
                print(f"✅ 'users' tablosuna '{col_name}' eklendi.")
            except sqlite3.OperationalError:
                print(f"ℹ️ '{col_name}' zaten var.")

        # 2. Devices Tablosuna Eksikleri Ekle
        try:
            cursor.execute("ALTER TABLE devices ADD COLUMN created_at TIMESTAMP")
            print("✅ 'devices' tablosuna 'created_at' eklendi.")
        except sqlite3.OperationalError:
            print("ℹ️ 'created_at' zaten var.")

        conn.commit()
        conn.close()
        print("🚀 Veritabanı başarıyla güncellendi! Artık hata almayacaksın.")
        
    except Exception as e:
        print(f"❌ Hata: {e}")

if __name__ == "__main__":
    migrate()