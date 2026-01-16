# scripts/debug_trusted.py
import requests
import json

# --- AYARLAR ---
API_BASE_URL = "https://api.trusted.dk"
TOKEN_URL = "https://api.trusted.dk/Token"
API_USERNAME = "s.ozsarac@hkm.com.tr"  # <-- DOLDUR
API_PASSWORD = "Solid_2023"          # <-- DOLDUR
DATA_ENDPOINT = "/api/Units/MyUnits"

def debug_api():
    print("🔍 API Röntgeni Başlıyor...")
    
    # 1. Token Al
    payload = {'grant_type': 'password', 'username': API_USERNAME, 'password': API_PASSWORD}
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    
    try:
        resp_token = requests.post(TOKEN_URL, data=payload, headers=headers)
        resp_token.raise_for_status()
        token = resp_token.json()['access_token']
        print("✅ Token OK.")
    except Exception as e:
        print(f"❌ Token Hatası: {e}")
        return

    # 2. Veriyi Çek ve Ham Halini Göster
    headers_api = {'Authorization': f'Bearer {token}'}
    try:
        url = f"{API_BASE_URL}{DATA_ENDPOINT}"
        resp = requests.get(url, headers=headers_api)
        
        print(f"📡 İstek Yapıldı: {url}")
        print(f"Status Code: {resp.status_code}")
        
        units = resp.json()
        print(f"📦 Gelen Cihaz Sayısı: {len(units)}")
        
        print("\n" + "="*40)
        print("🛑 İŞTE CİHAZIN HAM VERİSİ (BUNU KOPYALA)")
        print("="*40)
        
        # Sadece ilk cihazın tüm verisini ekrana basalım ki yapıyı görelim
        if units:
            first_unit = units[0]
            print(json.dumps(first_unit, indent=4))
        else:
            print("⚠️ Cihaz listesi boş!")

        print("="*40)

    except Exception as e:
        print(f"❌ Hata: {e}")

if __name__ == "__main__":
    debug_api()