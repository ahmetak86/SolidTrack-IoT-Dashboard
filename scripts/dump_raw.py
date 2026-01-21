import requests
import json

# --- AYARLAR ---
API_BASE_URL = "https://api.trusted.dk/api"
TOKEN_URL = "https://api.trusted.dk/Token"
API_USERNAME = "s.ozsarac@hkm.com.tr"
API_PASSWORD = "Solid_2023"

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

def dump_all_data():
    token = get_token()
    if not token: return

    print("📡 Cihaz verileri çekiliyor (MyUnits)...")
    headers = {'Authorization': f'Bearer {token}'}
    
    # Garanti çalışan adres
    url = f"{API_BASE_URL}/Units/MyUnits"
    
    try:
        resp = requests.get(url, headers=headers)
        if resp.status_code == 200:
            units = resp.json()
            if len(units) > 0:
                # Sadece ilk cihazın TÜM verisini dökelim
                first_unit = units[0]
                print(f"\n📦 Cihaz: {first_unit.get('UnitName')}")
                print("=" * 50)
                print(json.dumps(first_unit, indent=4))
                print("=" * 50)
                print("✅ Çıktı tamamlandı.")
            else:
                print("⚠️ Cihaz listesi boş geldi.")
        else:
            print(f"❌ API Hatası: {resp.status_code}")
    except Exception as e:
        print(f"❌ Hata: {e}")

if __name__ == "__main__":
    dump_all_data()