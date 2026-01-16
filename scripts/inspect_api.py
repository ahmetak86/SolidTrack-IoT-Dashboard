import requests
import json
import sys

# AYARLAR
API_USERNAME = "s.ozsarac@hkm.com.tr"
API_PASSWORD = "Solid_2023" # <--- Şifreni buraya yaz
GROUP_ID = 7153 

def inspect_data():
    print("🔍 API Röntgeni Çekiliyor...")
    
    # 1. Token Al
    session = requests.Session()
    payload = {"grant_type": "password", "username": API_USERNAME, "password": API_PASSWORD}
    
    try:
        resp = session.post("https://api.trusted.dk/token", data=payload)
        if resp.status_code != 200:
            print(f"❌ Giriş Hatası: {resp.text}")
            return
        token = resp.json().get("access_token")
        session.headers.update({"Authorization": f"Bearer {token}"})
        print("✅ Token alındı.")
    except Exception as e:
        print(f"❌ Bağlantı hatası: {e}")
        return

    # 2. Veriyi Çek ve Ham Halini Göster
    url = f"https://api.trusted.dk/api/Units/GroupCurrentPosition?groupid={GROUP_ID}"
    print(f"📡 İstek atılıyor: {url}")
    
    resp = session.get(url)
    if resp.status_code == 200:
        data = resp.json()
        print(f"📦 Gelen Paket Boyutu: {len(data)} adet obje")
        
        if len(data) > 0:
            print("\n--- 1. CİHAZIN HAM VERİSİ ---")
            print(json.dumps(data[0], indent=4))
            
            if len(data) > 1:
                print("\n--- 2. CİHAZIN HAM VERİSİ ---")
                print(json.dumps(data[1], indent=4))
        else:
            print("⚠️ Liste boş geldi!")
    else:
        print(f"❌ API Hatası: {resp.status_code} - {resp.text}")

if __name__ == "__main__":
    inspect_data()