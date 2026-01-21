import requests
import json

API_USERNAME = "s.ozsarac@hkm.com.tr"
API_PASSWORD = "Solid_2023"
TARGET_SERIAL = "865456056700519" # Referans Cihaz (TRÇAN BIG R250 #1)

def get_token():
    payload = {'grant_type': 'password', 'username': API_USERNAME, 'password': API_PASSWORD}
    resp = requests.post("https://api.trusted.dk/Token", data=payload)
    return resp.json()['access_token']

def inspect_settings():
    token = get_token()
    headers = {'Authorization': f'Bearer {token}'}
    
    print(f"🕵️‍♀️ {TARGET_SERIAL} cihazının Utilization Ayarları Çekiliyor...")
    
    # 1. Mevcut Modu Çek
    url_mode = f"https://api.trusted.dk/api/Utilization/GetCurrentMode?SerialNumber={TARGET_SERIAL}"
    resp_mode = requests.get(url_mode, headers=headers)
    print("\n--- MEVCUT MOD VE AYARLAR ---")
    print(json.dumps(resp_mode.json(), indent=4))

    # 2. Profil Bilgisi
    url_profile = f"https://api.trusted.dk/api/Utilization/CurrentUtilizationProfile?serialNumber={TARGET_SERIAL}"
    resp_profile = requests.get(url_profile, headers=headers)
    print("\n--- KULLANILAN PROFİL ---")
    print(json.dumps(resp_profile.json(), indent=4))

if __name__ == "__main__":
    inspect_settings()