# scripts/fix_ownership_final.py (ÇOKLU GRUP VE İSİM DÜZELTME)
import sys
import os
import requests

# Ana dizini tanıt
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.database import SessionLocal
from backend.models import Device

# --- API AYARLARI ---
API_BASE_URL = "https://api.trusted.dk/api"
API_USERNAME = "s.ozsarac@hkm.com.tr"
API_PASSWORD = "Solid_2023"

# TARANACAK GRUPLAR (Hem HKM hem Müşteri gruplarını buraya yazıyoruz)
TARGET_GROUPS = [7153, 9840] 

def get_token():
    print("🔑 Token alınıyor...")
    payload = {"grant_type": "password", "username": API_USERNAME, "password": API_PASSWORD}
    try:
        resp = requests.post("https://api.trusted.dk/token", data=payload)
        if resp.status_code == 200:
            return resp.json().get("access_token")
        else:
            print(f"❌ Token Hatası: {resp.status_code}")
    except Exception as e:
        print(f"❌ Bağlantı Hatası: {e}")
    return None

def fix_all_devices():
    print("🔧 Cihaz Sahiplikleri Düzeltiliyor (Geniş Kapsam)...")
    
    token = get_token()
    if not token: return

    headers = {"Authorization": f"Bearer {token}"}
    db = SessionLocal()
    
    total_fixed = 0

    for group_id in TARGET_GROUPS:
        print(f"\n📡 Grup Taranıyor: {group_id} ...")
        url = f"{API_BASE_URL}/Units/GroupCurrentPosition?groupid={group_id}"
        
        try:
            resp = requests.get(url, headers=headers)
            if resp.status_code != 200:
                print(f"   ⚠️ Grup {group_id} çekilemedi (Yetki yok veya boş).")
                continue

            api_data = resp.json()
            if not api_data:
                print("   ℹ️ Bu grupta cihaz yok.")
                continue

            print(f"   🔎 {len(api_data)} cihaz bulundu.")

            for item in api_data:
                unit = item.get("Unit", {})
                
                serial_no = str(unit.get("SerialNumber"))
                # İsim bazen Name, bazen UnitName olabiliyor, ikisini de dene
                name = unit.get("Name") or unit.get("UnitName") or "Bilinmiyor"
                
                # API'den gelen grup ID (Bazen Unit içinde UserGroupId olarak gelir)
                trusted_group = unit.get("UserGroupId", group_id) 
                
                if not serial_no: continue

                # Yerel veritabanındaki cihazı bul
                device = db.query(Device).filter(Device.device_id == serial_no).first()
                
                if device:
                    # İSMİ GÜNCELLE (Eğer 'Bilinmiyor' kalmışsa düzelsin)
                    if device.unit_name == "Bilinmiyor" or device.unit_name != name:
                        device.unit_name = name

                    new_owner = "s.ozsarac" # Varsayılan

                    # --- MANTIK KURALLARI ---
                    
                    # 1. ÖZEL İSTİSNA: TRÇAN -> akkaya
                    # (Büyük/küçük harf duyarsız kontrol)
                    if "TRÇAN" in name.upper() or "R250 #1" in name:
                        new_owner = "akkaya"
                    
                    # 2. CHRIS (FEL-TECH) GRUBU (9840) -> chris
                    elif trusted_group == 9840:
                        new_owner = "chris"
                    
                    # 3. DİĞERLERİ -> s.ozsarac
                    else:
                        new_owner = "s.ozsarac"

                    # Değişiklik varsa uygula
                    if device.owner_id != new_owner:
                        print(f"   ✅ DÜZELTİLDİ: {name} -> {new_owner}")
                        device.owner_id = new_owner
                        total_fixed += 1
                    else:
                        # print(f"   👍 Doğru: {name} -> {new_owner}")
                        pass
        except Exception as e:
            print(f"   ❌ Hata: {e}")

    db.commit()
    db.close()
    print(f"\n🎉 SONUÇ: Toplam {total_fixed} cihazın sahibi güncellendi.")

if __name__ == "__main__":
    fix_all_devices()