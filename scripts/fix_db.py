# backend/fix_db.py
from sqlalchemy import create_engine, text
import os

# Veritabanı yolunu tam garantiye alalım
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "solidtrack.db")
engine = create_engine(f"sqlite:///{DB_PATH}")

def fix_schema():
    print(f"🔧 Veritabanı onarılıyor... Yol: {DB_PATH}")
    
    with engine.connect() as con:
        try:
            # 1. Eksik sütunu eklemeye çalış
            print("1. 'icon_type' sütunu ekleniyor...")
            con.execute(text("ALTER TABLE devices ADD COLUMN icon_type VARCHAR DEFAULT 'truck'"))
            con.commit()
            print("   ✅ Sütun Başarıyla Eklendi!")
        except Exception as e:
            # Eğer sütun zaten varsa hata verir, önemli değil.
            print(f"   ℹ️ Bilgi: {e}")
            print("   (Muhtemelen sütun zaten var veya başka bir durum oluştu.)")

    print("\n🏁 Onarım tamamlandı.")

if __name__ == "__main__":
    fix_schema()