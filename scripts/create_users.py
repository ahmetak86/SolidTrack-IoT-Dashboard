import sys
import os

# Backend yolunu ekle
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.database import SessionLocal, get_password_hash
from backend.models import User

def create_scenario_a_users():
    db = SessionLocal()

    # 1. ADMIN (SEN) - Hepsini görür
    admin_user = User(
        id="admin_hkm",
        username="s.ozsarac",
        email="s.ozsarac@hkm.com.tr",
        password_hash=get_password_hash("1"),
        role="Admin",          # <--- KİLİT NOKTA: Admin rolü
        trusted_group_id=7153, # Ana grup
        company_name="HKM Hidrolik",
        full_name="Serkan Özsaraç"
    )

    # 2. MÜŞTERİ (Fel-Tech) - Sadece kendini görür
    client_user = User(
        id="client_feltech",
        username="feltech",
        email="info@feltech.com",
        password_hash=get_password_hash("1"),
        role="Client",         # <--- KİLİT NOKTA: Client rolü
        trusted_group_id=9840, # <--- Sadece bu grubun cihazları onun olacak
        company_name="Fel-Tech Construction",
        full_name="Fel-Tech Yöneticisi"
    )

    # 3. Group Admin - Sadece group'a air olanları görür
    ahmet_user = User(
        id="admin_ahmet",
        username="a.akkaya",
        email="a.akkaya@hkm.com.tr",
        password_hash=get_password_hash("1"),
        role="Admin",          # Sen de Adminsin, her şeyi görürsün
        trusted_group_id=7153, 
        company_name="HKM Hidrolik",
        full_name="Ahmet Akkaya"
    )
    db.merge(ahmet_user)

    try:
        db.merge(admin_user)
        db.merge(client_user)
        db.commit()
        print("✅ Kullanıcılar oluşturuldu: Admin (HKM) ve Client (Fel-Tech)")
    except Exception as e:
        print(f"❌ Hata: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    create_scenario_a_users()