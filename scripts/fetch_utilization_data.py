import requests
import json
from datetime import datetime, timedelta

API_USERNAME = "s.ozsarac@hkm.com.tr"
API_PASSWORD = "Solid_2023"
TARGET_SERIAL = "865456056700519" 

def get_token():
    payload = {'grant_type': 'password', 'username': API_USERNAME, 'password': API_PASSWORD}
    resp = requests.post("https://api.trusted.dk/Token", data=payload)
    return resp.json()['access_token']

def fetch_utilization():
    token = get_token()
    headers = {'Authorization': f'Bearer {token}'}
    
    # Son 7 günü çekelim
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=7)
    
    print(f"📊 {TARGET_SERIAL} için Utilization Verisi Çekiliyor...")
    
    url = f"https://api.trusted.dk/api/Utilization/GetUnit"
    params = {
        "SerialNumber": TARGET_SERIAL,
        "AfterDate": start_date.strftime("%Y-%m-%dT%H:%M:%S"),
        "BeforeDate": end_date.strftime("%Y-%m-%dT%H:%M:%S"),
        "Count": 100
    }
    
    resp = requests.get(url, headers=headers, params=params)
    data = resp.json()
    
    if data:
        print(f"📦 {len(data)} adet kayıt geldi. Örnek Veri:")
        print(json.dumps(data[0], indent=4))
        
        # Kategorileri kontrol et
        categories = set()
        for item in data:
            if "Category" in item:
                categories.add(item["Category"])
        print("\n🏷️ BULUNAN KATEGORİLER:", categories)
    else:
        print("⚠️ Veri gelmedi.")

if __name__ == "__main__":
    fetch_utilization()