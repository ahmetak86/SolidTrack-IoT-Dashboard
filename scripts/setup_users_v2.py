# scripts/setup_users_v2.py (CSV BAZLI FİNAL KURULUM)
import sys
import os
from sqlalchemy import text

# Ana dizini tanıt
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.database import SessionLocal, get_password_hash
from backend.models import User, Device

def setup_users_from_csv():
    db = SessionLocal()
    print("🧹 [1/3] Eski kullanıcı tablosu temizleniyor...")
    
    try:
        # Önce kullanıcıları temizle
        db.execute(text("DELETE FROM users"))
        db.commit()
    except Exception as e:
        print(f"Silme hatası: {e}")
        db.rollback()

    print("🏗️ [2/3] Yeni kullanıcılar oluşturuluyor (CSV Bazlı)...")

    # CSV'den Gelen Tam Liste
    users_data = [
        {
            "rol": "Admin",
            "ad": "Serkan Özsaraç",
            "kullanici_adi": "s.ozsarac",
            "email": "s.ozsarac@hkm.com.tr",
            "sifre": "1",
            "grup_id": 7153,
            "sirket": "HKM Hidrolik (HQ)"
        },
        {
            "rol": "Admin",
            "ad": "Ahmet Akkaya",
            "kullanici_adi": "a.akkaya",
            "email": "a.akkaya@hkm.com.tr",
            "sifre": "1",
            "grup_id": 7153,
            "sirket": "HKM Hidrolik (HQ)"
        },
        {
            "rol": "User", # Müşteri statüsü
            "ad": "Ahmet Akkaya (Grup)",
            "kullanici_adi": "ahmet",
            "email": "akkaya.ahmet1986@gmail.com",
            "sifre": "1",
            "grup_id": 7153,
            "sirket": "HKM Operasyon"
        },
        {
            "rol": "User", # Özel Müşteri
            "ad": "Akkaya (Tek Cihaz)",
            "kullanici_adi": "akkaya",
            "email": "a@a.com",
            "sifre": "1",
            "grup_id": None, # Grubu yok, özel cihaz atanacak
            "sirket": "Özel Müşteri"
        },
        {
            "rol": "User", # Fel-Tech Müşterisi
            "ad": "Chris (Müşteri)",
            "kullanici_adi": "chris",
            "email": "chris@feltech.com.tr", # CSV'deki güncel mail
            "sifre": "1",
            "grup_id": 9840,
            "sirket": "Fel-Tech Ltd."
        }
    ]

    for u in users_data:
        try:
            # Şifreyi hashle
            hashed_pw = get_password_hash(u["sifre"])
            
            new_user = User(
                id=u["kullanici_adi"], # ID ve Username aynı olsun
                username=u["kullanici_adi"],
                email=u["email"],
                full_name=u["ad"],
                role=u["rol"],
                trusted_group_id=u["grup_id"],
                company_name=u["sirket"],
                password_hash=hashed_pw
            )
            db.add(new_user)
            print(f"✅ Oluşturuldu: {u['kullanici_adi']} ({u['rol']})")
        except Exception as e:
            print(f"❌ Hata ({u['kullanici_adi']}): {e}")

    db.commit()

    # --- ÖZEL CİHAZ ATAMASI (TRÇAN BIG R250 #1 -> akkaya) ---
    print("\n🔗 [3/3] Özel Cihaz Ataması Yapılıyor...")
    
    target_device_name = "TRÇAN BIG R250 #1"
    target_user = "akkaya"
    
    device = db.query(Device).filter(Device.unit_name == target_device_name).first()
    
    if device:
        # Cihazın sahibini 'akkaya' yapıyoruz.
        # Böylece 'akkaya' kullanıcısı sadece kendi sahibi olduğu bu cihazı görecek.
        device.owner_id = target_user
        db.commit()
        print(f"🎯 BAŞARILI: '{target_device_name}' cihazı '{target_user}' kullanıcısına zimmetlendi.")
    else:
        print(f"⚠️ UYARI: '{target_device_name}' veritabanında bulunamadı! Robotu çalıştırıp cihazları çektin mi?")

    db.close()
    print("\n🎉 KURULUM TAMAMLANDI!")

if __name__ == "__main__":
    setup_users_from_csv()