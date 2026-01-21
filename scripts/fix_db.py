import sqlite3
import os

# Veritabanı dosyasının yerini bulalım
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "backend", "solidtrack.db")

def fix_database():
    print(f"🔧 Veritabanı onarılıyor: {DB_PATH}")
    
    if not os.path.exists(DB_PATH):
        print("❌ Veritabanı dosyası bulunamadı! Önce init_db.py çalışmalıydı.")
        return

    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # 1. utilization_profiles tablosuna mode_name ekle
        print("👉 'utilization_profiles' tablosuna 'mode_name' sütunu ekleniyor...")
        try:
            cursor.execute("ALTER TABLE utilization_profiles ADD COLUMN mode_name VARCHAR DEFAULT 'Standard'")
            print("   ✅ Başarılı: mode_name eklendi.")
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e):
                print("   ℹ️ Zaten ekliymiş, pas geçildi.")
            else:
                print(f"   ❌ Hata: {e}")

        # 2. Değişiklikleri Kaydet
        conn.commit()
        conn.close()
        print("\n🎉 Veritabanı şeması güncellendi! Şimdi init_db.py çalıştırabilirsin.")

    except Exception as e:
        print(f"❌ Beklenmedik bir hata oluştu: {e}")

if __name__ == "__main__":
    fix_database()