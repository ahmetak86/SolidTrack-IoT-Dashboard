# update_db.py (FULL GÜNCEL VERSİYON)
import sqlite3
import os

# Backend klasöründeki DB yolu
DB_PATH = os.path.join("backend", "solidtrack.db")

def migrate():
    if not os.path.exists(DB_PATH):
        print(f"❌ HATA: '{DB_PATH}' bulunamadı!")
        return

    print(f"🔧 Veritabanı CRM Özellikleri ile Güncelleniyor...")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Eklenecek Yeni Kolonlar
    new_columns = [
        ("admin_note", "TEXT"),
        ("subscription_end_date", "TIMESTAMP"),
        ("device_limit", "INTEGER DEFAULT 100"),
        ("last_login_at", "TIMESTAMP"),
        ("is_active", "BOOLEAN DEFAULT 1"), # Önceden yoksa diye
        ("trusted_group_id", "INTEGER")
    ]
    
    for col_name, col_type in new_columns:
        try:
            cursor.execute(f"ALTER TABLE users ADD COLUMN {col_name} {col_type}")
            print(f"✅ 'users' tablosuna '{col_name}' eklendi.")
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e):
                print(f"ℹ️ '{col_name}' zaten var.")
            else:
                print(f"⚠️ Hata ({col_name}): {e}")

    conn.commit()
    conn.close()
    print("\n🚀 Veritabanı Hazır! Şimdi panele geçebilirsin.")

if __name__ == "__main__":
    migrate()