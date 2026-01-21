import requests
import json

# --- AYARLAR ---
API_BASE_URL = "https://api.trusted.dk/api"
TOKEN_URL = "https://api.trusted.dk/Token"
API_USERNAME = "s.ozsarac@hkm.com.tr"
API_PASSWORD = "Solid_2023"

# Hedef Cihaz (Senin cihazın)
TARGET_SERIAL = "865456055312555"

def get_token():
    print("🔑 Token alınıyor...")
    payload = {'grant_type': 'password', 'username': API_USERNAME, 'password': API_PASSWORD}
    try:
        resp = requests.post(TOKEN_URL, data=payload)
        resp.raise_for_status()
        return resp.json()['access_token']
    except Exception as e:
        print(f"❌ Token Hatası: {e}")
        return None

def inspect_sensors():
    token = get_token()
    if not token: return

    print(f"📡 '{TARGET_SERIAL}' için SENSÖR verileri çekiliyor...")
    headers = {'Authorization': f'Bearer {token}'}
    
    # [cite_start]SensorData/GetLatest servisi cihazın son sensör durumunu verir [cite: 24]
    url = f"{API_BASE_URL}/SensorData/GetLatest?serialNumber={TARGET_SERIAL}&count=1"
    
    try:
        resp = requests.get(url, headers=headers)
        if resp.status_code == 200:
            data = resp.json()
            if data:
                print("\n📦 GELEN SENSÖR VERİSİ:")
                print("=" * 40)
                print(json.dumps(data[0], indent=4)) # İlk kaydı bas
                print("=" * 40)
                
                # Hızlı Kontrol
                item = data[0]
                print(f"\n🔋 Pil Adayları:")
                for k, v in item.items():
                    if any(x in k.lower() for x in ['batt', 'pow', 'volt', 'level']):
                        print(f"   👉 {k}: {v}")
            else:
                print("⚠️ Sensör verisi boş döndü.")
        else:
            print(f"❌ API Hatası: {resp.status_code} - {resp.text}")
            
    except Exception as e:
        print(f"❌ Hata: {e}")

if __name__ == "__main__":
    inspect_sensors()