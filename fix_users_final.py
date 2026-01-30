# fix_users_final.py (TEK SEFERLİK KURULUM)
import sys
import os
from sqlalchemy import text

# Ana dizini tanıt
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from backend.database import SessionLocal, get_password_hash, engine
from backend.models import User

def reset_and_create_users():
    db = SessionLocal()
    print("🧹 Eski kullanıcılar temizleniyor...")
    
    # Tüm kullanıcı tablosunu temizle (Sıfırdan kurulum)
    try:
        db.execute(text("DELETE FROM users"))
        db.commit()
    except Exception as e:
        print(f"Silme hatası: {e}")
        db.rollback()

    print("🏗️ Yeni kullanıcılar oluşturuluyor...")

    # SENİN BELİRLEDİĞİN 4 KULLANICI
    users_to_create = [
        # 1. SUPER ADMIN (Serkan Bey)
        {
            "id": "s.ozsarac", # Username ile aynı yapıyoruz ID'yi
            "username": "s.ozsarac",
            "email": "s.ozsarac@hkm.com.tr",
            "full_name": "Serkan Özsaraç",
            "role": "Admin",
            "password": "1",
            "group_id": 7153, # Tümünü görür (Kodda Admin yetkisi var)
            "company": "HKM Hidrolik (HQ)"
        },
        # 2. SUPER ADMIN 2 (Ahmet Bey - Sen)
        {
            "id": "a.akkaya",
            "username": "a.akkaya",
            "email": "a.akkaya@hkm.com.tr",
            "full_name": "Ahmet Akkaya",
            "role": "Admin",
            "password": "1",
            "group_id": 7153, # Tümünü görür
            "company": "HKM Hidrolik (HQ)"
        },
        # 3. GROUP ADMIN (Sadece 7153)
        {
            "id": "ahmet",
            "username": "ahmet",
            "email": "akkaya.ahmet1986@gmail.com",
            "full_name": "Ahmet Akkaya (Grup)",
            "role": "User", # Admin değil, normal kullanıcı (Grup bazlı)
            "password": "1",
            "group_id": 7153, # Sadece 7153 cihazlarını görür
            "company": "HKM Operasyon"
        },
        # 4. CLIENT (Chris - Sadece 9840)
        {
            "id": "chris",
            "username": "chris",
            "email": "abc@feltech.com.tr",
            "full_name": "Chris (Müşteri)",
            "role": "User", # Müşteri
            "password": "1",
            "group_id": 9840, # Sadece 9840 cihazlarını görür
            "company": "Fel-Tech Ltd."
        }
    ]

    for u in users_to_create:
        try:
            new_user = User(
                id=u["id"],
                username=u["username"],
                email=u["email"],
                full_name=u["full_name"],
                role=u["role"],
                trusted_group_id=u["group_id"],
                company_name=u["company"],
                password_hash=get_password_hash(u["password"]) # Şifreyi '1' olarak ayarlar
            )
            db.add(new_user)
            print(f"✅ Oluşturuldu: {u['username']} (Grup: {u['group_id']})")
        except Exception as e:
            print(f"❌ Hata ({u['username']}): {e}")

    db.commit()
    db.close()
    print("\n🎉 İŞLEM TAMAM! Artık sadece bu 4 kullanıcı ile giriş yapabilirsin.")

if __name__ == "__main__":
    reset_and_create_users()