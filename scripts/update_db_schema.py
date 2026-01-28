# scripts/update_db_schema.py (GÜNCELLENMİŞ)
import sqlite3
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# DB yolunu hem backend hem ana dizinde ara
POSSIBLE_PATHS = [
    os.path.join(BASE_DIR, "solidtrack.db"),
    os.path.join(BASE_DIR, "backend", "solidtrack.db")
]

def migrate_db():
    db_path = None
    for path in POSSIBLE_PATHS:
        if os.path.exists(path):
            db_path = path
            break
            
    if not db_path:
        print("❌ DB Bulunamadı.")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        print("🛠️ 'users' tablosuna 'reset_token' ekleniyor...")
        cursor.execute("ALTER TABLE users ADD COLUMN reset_token TEXT")
        conn.commit()
        print("✅ BAŞARILI: reset_token eklendi.")
    except sqlite3.OperationalError as e:
        if "duplicate column" in str(e):
            print("ℹ️ Zaten ekli.")
        else:
            print(f"Hata: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    migrate_db()