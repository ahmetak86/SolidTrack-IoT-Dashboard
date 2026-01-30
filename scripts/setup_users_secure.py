# scripts/setup_users_secure.py
import sys
import os
from sqlalchemy import text

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.database import SessionLocal, get_password_hash # HASH FONKSİYONUNU ÇAĞIRDIK
from backend.models import User, Device

def setup_secure():
    db = SessionLocal()
    print("🧹 Temizlik ve Güvenli Kurulum Başlıyor...")

    # 1. Eski kullanıcıları sil
    try:
        db.execute(text("DELETE FROM users"))
        db.commit()
    except Exception as e:
        print(f"Silme hatası: {e}")
        db.rollback()

    # 2. Kullanıcı Listesi (Şifreler Hash'lenecek)
    users = [
        # SUPER ADMINLER
        {"id": "s.ozsarac", "email": "s.ozsarac@hkm.com.tr", "ad": "Serkan Özsaraç", "rol": "Admin", "grup": 7153, "firma": "HKM (HQ)"},
        {"id": "a.akkaya", "email": "a.akkaya@hkm.com.tr", "ad": "Ahmet Akkaya", "rol": "Admin", "grup": 7153, "firma": "HKM (HQ)"},
        
        # MÜŞTERİLER
        {"id": "ahmet", "email": "akkaya.ahmet1986@gmail.com", "ad": "Ahmet (Grup)", "rol": "User", "grup": 7153, "firma": "HKM Ops"},
        {"id": "chris", "email": "chris@feltech.com.tr", "ad": "Chris (Müşteri)", "rol": "User", "grup": 9840, "firma": "Fel-Tech"},
        {"id": "akkaya", "email": "a@a.com", "ad": "Akkaya (Tek Cihaz)", "rol": "User", "grup": None, "firma": "Özel"}
    ]

    print("🔐 Kullanıcılar şifrelenerek oluşturuluyor...")
    for u in users:
        # ŞİFREYİ KRİPTOLA: "1" -> "$2b$12$K8H..."
        secure_pass = get_password_hash("1") 
        
        new_user = User(
            id=u["id"],
            username=u["id"],
            email=u["email"],
            full_name=u["ad"],
            role=u["rol"],
            trusted_group_id=u["grup"],
            company_name=u["firma"],
            password_hash=secure_pass # Şifreli halini kaydet
        )
        db.add(new_user)
        print(f"✅ Eklendi: {u['id']} (Şifre: '1' olarak ayarlandı ama DB'de şifreli)")

    db.commit()

    # 3. Özel Cihaz Ataması
    dev = db.query(Device).filter(Device.unit_name == "TRÇAN BIG R250 #1").first()
    if dev:
        dev.owner_id = "akkaya"
        db.commit()
        print("🎯 TRÇAN cihazı 'akkaya' kullanıcısına zimmetlendi.")

    db.close()
    print("\n🎉 GÜVENLİ KURULUM TAMAMLANDI.")

if __name__ == "__main__":
    setup_secure()