import sys
import os

# Proje ana dizinini yola ekle
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.database import SessionLocal, User, get_password_hash

def reset_and_create_users():
    db = SessionLocal()
    print("\n🧨 VERİTABANI KULLANICILARI SIFIRLANIYOR...")
    
    # 1. TÜM KULLANICILARI SİL (Delete All)
    try:
        num_deleted = db.query(User).delete()
        db.commit()
        print(f"🗑️  Eski {num_deleted} kullanıcı silindi. Tablo tertemiz.")
    except Exception as e:
        print(f"❌ Silme hatası: {e}")
        return

    print("\n🏗️  YENİ KULLANICILAR OLUŞTURULUYOR...")

    # --- KULLANICI LİSTESİ ---
    users_to_create = [
        # 1. SUPER ADMIN 1 (Serkan Bey)
        {
            "id": "admin_01",
            "username": "s.ozsarac",
            "email": "s.ozsarac@hkm.com.tr",
            "password": "1",
            "role": "Admin",
            "trusted_group_id": 7153, # HKM ID
            "company": "HKM Hidrolik (HQ)",
            "name": "Serkan Özsaraç"
        },
        # 2. SUPER ADMIN 2 (Ahmet Akkaya - Kurumsal)
        {
            "id": "admin_02",
            "username": "a.akkaya",
            "email": "a.akkaya@hkm.com.tr",
            "password": "1",
            "role": "Admin",
            "trusted_group_id": 7153, # HKM ID
            "company": "HKM Hidrolik (HQ)",
            "name": "Ahmet Akkaya"
        },
        # 3. GROUP ADMIN (Ahmet - Gmail)
        {
            "id": "group_admin_01",
            "username": "ahmet",
            "email": "akkaya.ahmet1986@gmail.com",
            "password": "1",
            "role": "Admin", # Grup Admini olduğu için rolü Admin kalabilir, ID ile kısıtlayacağız
            "trusted_group_id": 7153, # Sadece HKM Cihazları
            "company": "HKM Operasyon",
            "name": "Ahmet (Grup Yöneticisi)"
        },
        # 4. CLIENT (Chris - Feltech)
        {
            "id": "client_01",
            "username": "chris",
            "email": "abc@feltech.com.tr",
            "password": "1",
            "role": "Client",
            "trusted_group_id": 9840, # Feltech ID (Sadece kendi cihazları)
            "company": "Feltech",
            "name": "Chris (Müşteri)"
        }
    ]

    for u in users_to_create:
        new_user = User(
            id=u["id"],
            username=u["username"],
            email=u["email"],
            password_hash=get_password_hash(u["password"]),
            role=u["role"],
            trusted_group_id=u["trusted_group_id"],
            company_name=u["company"],
            full_name=u["name"]
        )
        db.add(new_user)
        print(f"✅ OLUŞTURULDU: {u['username']} ({u['role']}) -> Grup: {u['trusted_group_id']}")

    db.commit()
    db.close()
    print("\n🚀 İŞLEM TAMAMLANDI! Yeni kadro hazır.")

if __name__ == "__main__":
    reset_and_create_users()