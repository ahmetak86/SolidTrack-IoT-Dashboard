import requests
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from backend.database import SessionLocal
from backend.models import Device, User

# API Ayarları
BASE_URL = "https://api.trusted.dk"
TOKEN_PAYLOAD = {"grant_type": "password", "username": "s.ozsarac@hkm.com.tr", "password": "Solid_2023"}

def sync_device_owners():
    # 1. Token Al
    token_res = requests.post(f"{BASE_URL}/token", data=TOKEN_PAYLOAD)
    if token_res.status_code != 200:
        print("❌ Token alınamadı!")
        return
    token = token_res.json().get("access_token")
    headers = {"Authorization": f"Bearer {token}"}

    db = SessionLocal()
    
    # 2. Tüm cihazları ve GRUP BİLGİLERİNİ çek
    print("🌍 Trusted API'den cihaz listesi çekiliyor...")
    res = requests.get(f"{BASE_URL}/api/Units/GetAllSerialnumbers", headers=headers)
    units = res.json()

    # 3. DB'deki kullanıcıları Gruplarına göre sözlüğe al
    # {9840: 'client_feltech', 7153: 'admin_hkm'} gibi
    group_map = {}
    users = db.query(User).filter(User.trusted_group_id != None).all()
    for u in users:
        group_map[u.trusted_group_id] = u.id

    print(f"👥 Grup-Kullanıcı Eşleşmesi: {group_map}")

    # 4. Cihazları Güncelle
    count = 0
    for unit in units:
        serial = unit.get("SerialNumber")
        group_id = unit.get("UserGroupId")
        
        # Bu grubun sahibi olan bir kullanıcımız var mı?
        if group_id in group_map:
            owner_id = group_map[group_id]
            
            # Cihazı bul veya yarat
            device = db.query(Device).filter(Device.device_id == serial).first()
            if not device:
                device = Device(device_id=serial, is_active=True)
            
            # Sahipliği Ata
            old_owner = device.owner_id
            device.owner_id = owner_id
            device.unit_name = unit.get("Name", serial) # İsmi de güncelle
            
            db.merge(device)
            if old_owner != owner_id:
                print(f"🔄 {serial} cihazı -> {owner_id} kullanıcısına atandı (Grup: {group_id})")
                count += 1
    
    db.commit()
    db.close()
    print(f"✅ Toplam {count} cihazın sahipliği güncellendi/doğrulandı.")

if __name__ == "__main__":
    sync_device_owners()