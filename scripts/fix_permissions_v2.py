import sys
import os

# Proje ana dizinini yola ekle
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.database import SessionLocal, User, Device, get_password_hash

def fix_all_permissions():
    db = SessionLocal()
    print("\n🔧 YETKİ VE SAHİPLİK DÜZELTME OPERASYONU BAŞLADI...\n")

    # --- 1. KULLANICILARI GARANTİ ALTINA AL ---
    # Kullanıcı Listesi (Senin verdiğin net bilgiler)
    users_data = [
        # SUPER ADMIN 1
        {"u": "s.ozsarac", "e": "s.ozsarac@hkm.com.tr", "g": 7153, "r": "Admin", "n": "Serkan Özsaraç"},
        # SUPER ADMIN 2
        {"u": "a.akkaya",  "e": "a.akkaya@hkm.com.tr",  "g": 7153, "r": "Admin", "n": "Ahmet Akkaya"},
        # GROUP ADMIN
        {"u": "ahmet",     "e": "akkaya.ahmet1986@gmail.com", "g": 7153, "r": "Admin", "n": "Ahmet (Grup Yöneticisi)"},
        # CLIENT
        {"u": "chris",     "e": "abc@feltech.com.tr",   "g": 9840, "r": "Client", "n": "Chris (Feltech)"}
    ]

    user_map = {} # user objelerini saklamak için

    print("👤 Kullanıcılar Kontrol Ediliyor...")
    for data in users_data:
        user = db.query(User).filter(User.username == data["u"]).first()
        if not user:
            print(f"   ➕ Oluşturuluyor: {data['u']}")
            user = User(id=f"usr_{data['u']}", username=data["u"])
            db.add(user)
        
        # Bilgileri Zorla Güncelle (Fixle)
        user.email = data["e"]
        user.password_hash = get_password_hash("1")
        user.trusted_group_id = data["g"]
        user.role = data["r"]
        user.full_name = data["n"]
        
        user_map[data["u"]] = user
        print(f"   ✅ {data['u']} -> Grup: {data['g']} | Rol: {data['r']}")

    db.commit()

    # --- 2. CİHAZLARI SAHİPLENDİR ---
    print("\n🚜 Cihazlar Sahiplerine Zimmetleniyor...")
    
    devices = db.query(Device).all()
    admin_user = user_map["s.ozsarac"] # Varsayılan Sahip (HKM)
    client_user = user_map["chris"]    # Müşteri (Feltech)

    for dev in devices:
        # İsimde 'FEL' veya 'USAFEL' geçiyorsa Chris'e ver
        if "FEL" in dev.unit_name.upper():
            dev.owner_id = client_user.id
            print(f"   👤 [FELTECH] {dev.unit_name} -> {client_user.username} (Grup: 9840)")
        else:
            # Geri kalan her şey Serkan Bey'e (Böylece Ahmet de görür)
            dev.owner_id = admin_user.id
            print(f"   🏢 [HKM HQ]  {dev.unit_name} -> {admin_user.username} (Grup: 7153)")

    db.commit()
    db.close()
    
    print("\n🚀 İŞLEM TAMAMLANDI!")
    print("--------------------------------------------------")
    print("1. s.ozsarac -> TÜM Cihazları görecek.")
    print("2. a.akkaya  -> TÜM Cihazları görecek.")
    print("3. ahmet     -> Sadece HKM (Serkan Bey'in) cihazlarını görecek.")
    print("4. chris     -> Sadece Feltech (Kendi) cihazlarını görecek.")
    print("--------------------------------------------------")

if __name__ == "__main__":
    fix_all_permissions()