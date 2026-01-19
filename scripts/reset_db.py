import sys
import os

# Proje ana dizinini path'e ekle
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.database import engine, SessionLocal
from backend.models import Base, User, UtilizationProfile

def reset_database():
    print("🧹 Veritabanı temizliği ve V2 Kurulumu başlatılıyor...")
    
    # 1. Tabloları Sil ve Yeniden Oluştur
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    print("✨ Tablolar (V2 - Profilli Yapı) oluşturuldu.")

    db = SessionLocal()
    
    # 2. Varsayılan Kullanıcılar
    solidus_user = User(
        id="CUST_001",
        username="solidus_admin",
        email="info@solidus.com",
        password_hash="123456",
        role="Client",
        company_name="Solidus Mining Co.",
        full_name="Ahmet Yilmaz",
        company_address="Ivedik OSB 1453. Cad"
    )

    hkm_admin = User(
        id="HKM_ADMIN",
        username="hkm_superadmin",
        email="admin@hkm.com",
        password_hash="123456",
        role="Admin",
        company_name="HKM Group",
        full_name="System Admin"
    )

    db.add(solidus_user)
    db.add(hkm_admin)

    # 3. KULLANIM PROFİLLERİ (Standartları Gömüyoruz)
    # Referans: 6_Utilization_Profiles.csv
    profiles = [
        UtilizationProfile(
            profile_id="PROF_BREAKER",
            profile_name="Hidrolik Kırıcı (Standart)",
            description="Darbe ve Titreşim odaklı çalışma. Hassas algılama.",
            color_code="#FFC107", # Sarı
            motion_threshold_g=0.5,
            min_active_time_sec=10,
            burst_mode_enabled=True
        ),
        UtilizationProfile(
            profile_id="PROF_EXCAVATOR",
            profile_name="Ekskavatör / Kova",
            description="Sadece hareket ve dönüş odaklı.",
            color_code="#007BFF", # Mavi
            motion_threshold_g=0.2,
            min_active_time_sec=30,
            burst_mode_enabled=False
        ),
        UtilizationProfile(
            profile_id="PROF_TRANSPORT",
            profile_name="Nakliye / Kamyon",
            description="Yüksek G kuvveti gerektirir (Çukur vs. eler).",
            color_code="#28A745", # Yeşil
            motion_threshold_g=1.0,
            min_active_time_sec=60,
            burst_mode_enabled=False
        )
    ]

    for p in profiles:
        db.add(p)

    db.commit()
    db.close()
    print("✅ Kullanıcılar ve Standart Profiller (Kırıcı, Kova, Kamyon) eklendi.")
    print("🎉 Veritabanı V2 kullanıma hazır!")

if __name__ == "__main__":
    reset_database()