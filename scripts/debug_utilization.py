import requests
import json
from datetime import datetime, timedelta

API_USERNAME = "s.ozsarac@hkm.com.tr"
API_PASSWORD = "Solid_2023"
# Verisi olduğunu bildiğimiz cihaz
TARGET_SERIAL = "865456056700519" 

def get_token():
    payload = {'grant_type': 'password', 'username': API_USERNAME, 'password': API_PASSWORD}
    resp = requests.post("https://api.trusted.dk/Token", data=payload)
    return resp.json()['access_token']

def debug_api():
    print("🕵️‍♀️ API Yanıt Yapısı İnceleniyor...")
    token = get_token()
    headers = {'Authorization': f'Bearer {token}'}
    
    # Verisi olduğunu bildiğimiz 2024 sonuna odaklanalım
    url = "https://api.trusted.dk/api/Utilization/GetUnit"
    params = {
        "SerialNumber": TARGET_SERIAL,
        "AfterDate": "2024-10-01T00:00:00", 
        "BeforeDate": "2024-10-05T00:00:00", # Sadece 5 gün yeterli
        "Count": 10
    }
    
    resp = requests.get(url, headers=headers, params=params)
    
    if resp.status_code == 200:
        data = resp.json()
        print("\n📦 API YANITI (TÜRÜ):", type(data))
        
        if isinstance(data, dict):
            print("🔑 ANAHTARLAR (KEYS):", list(data.keys()))
            # İçindeki her bir anahtarın neye benzediğine bakalım
            for k, v in data.items():
                print(f"   👉 {k}: {type(v)} -> (Örnek: {str(v)[:50]}...)")
        elif isinstance(data, list):
            print(f"📏 LİSTE UZUNLUĞU: {len(data)}")
            if len(data) > 0:
                print("📝 İLK ÖĞE:", data[0])
    else:
        print(f"❌ API Hatası: {resp.status_code}")
        print(resp.text)

if __name__ == "__main__":
    debug_api()