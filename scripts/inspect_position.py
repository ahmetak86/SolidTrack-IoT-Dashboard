import requests
import json

API_USERNAME = "s.ozsarac@hkm.com.tr"
API_PASSWORD = "Solid_2023"
GROUP_ID = 7153 

def inspect_live_data():
    print("🔍 Canlı Sensör Verisi Aranıyor...")
    
    # 1. Token
    payload = {'grant_type': 'password', 'username': API_USERNAME, 'password': API_PASSWORD}
    token = requests.post("https://api.trusted.dk/Token", data=payload).json()['access_token']
    
    # 2. GroupCurrentPosition Çek (Altın madeni burası)
    headers = {'Authorization': f'Bearer {token}'}
    url = f"https://api.trusted.dk/api/Units/GroupCurrentPosition?groupid={GROUP_ID}"
    
    resp = requests.get(url, headers=headers)
    data = resp.json()
    
    if data:
        unit = data[0] # İlk cihaz
        print(f"\n📦 Cihaz: {unit.get('Unit', {}).get('UnitName')}")
        
        # CurrentPosition İçine Bakalım
        pos = unit.get("CurrentPosition", {})
        print("\n📍 CurrentPosition İçeriği:")
        print(json.dumps(pos, indent=4))
        
    else:
        print("Veri yok.")

if __name__ == "__main__":
    inspect_live_data()