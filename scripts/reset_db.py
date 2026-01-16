import sys
import os

# Proje ana dizinini path'e ekle
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.database import engine, SessionLocal
from backend.models import Base, User

def reset_database():
    print("🧹 Veritabanı temizliği başlatılıyor...")
    
    # 1. Tüm tabloları sil (Drop)
    Base.metadata.drop_all(bind=engine)
    print("🗑️ Eski tablolar silindi.")

    # 2. Tabloları yeniden oluştur (Create)
    Base.metadata.create_all(bind=engine)
    print("✨ Tablolar sıfırdan oluşturuldu.")

    # 3. Özel Kullanıcıları (Demo & Admin) Geri Yükle
    db = SessionLocal()
    
    # Solidus Demo Kullanıcısı
    solidus_user = User(
        id="CUST_001",
        username="solidus_admin",
        email="info@solidus.com",
        password_hash="123456",
        role="Client",
        company_name="Solidus Mining Co.",
        full_name="Ahmet Yilmaz",
        company_address="Ivedik OSB 1453. Cad"
        # is_active satırı silindi çünkü User tablosunda böyle bir sütun yok
    )

    # HKM Default Admin (Yedek olarak dursun)
    hkm_admin = User(
        id="HKM_ADMIN",
        username="hkm_superadmin",
        email="admin@hkm.com",
        password_hash="123456",
        role="Admin",
        company_name="HKM Group",
        full_name="System Admin"
        # is_active satırı silindi
    )

    db.add(solidus_user)
    db.add(hkm_admin)
    
    db.commit()
    db.close()
    print("✅ Solidus ve Default Admin kullanıcıları eklendi.")
    print("🎉 Veritabanı tertemiz oldu!")

if __name__ == "__main__":
    reset_database()