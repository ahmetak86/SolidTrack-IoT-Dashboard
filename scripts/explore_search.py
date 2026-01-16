# scripts/explore_search.py
import requests
import json

# --- AYARLAR ---
API_BASE_URL = "https://api.trusted.dk"
TOKEN_URL = "https://api.trusted.dk/Token"
API_USERNAME = "s.ozsarac@hkm.com.tr" 
API_PASSWORD = "Solid_2023"

# Hedef Cihazın Seri Numarası (Senin çıktından aldım)
TARGET_SERIAL = "865456055312555"

def get_token():
    print("🔑 Token alınıyor...")
    payload = {'grant_type': 'password', 'username': API_USERNAME, 'password': API_PASSWORD}
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    try:
        resp = requests.post(TOKEN_URL, data=payload, headers=headers)
        resp.raise_for_status()
        return resp.json()['access_token']
    except Exception as e:
        print(f"❌ Token Hatası: {e}")
        return None

def search_unit():
    token = get_token()
    if not token: return

    headers = {'Authorization': f'Bearer {token}'}
    
    # API_2.pdf'te önerilen adres: /api/Search/Units
    print(f"📡 '{TARGET_SERIAL}' cihazı aranıyor...")
    
    # search parametresi ile sorgu atıyoruz
    search_url = f"{API_BASE_URL}/api/Search/Units?search={TARGET_SERIAL}"
    
    try:
        resp = requests.get(search_url, headers=headers)
        
        print(f"Status Code: {resp.status_code}")
        
        if resp.status_code == 200:
            data = resp.json()
            
            # Sonucu dosyaya yaz
            with open("search_result.txt", "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
                
            print("\n✅ ARAMA BAŞARILI!")
            print("📂 Sonuç 'search_result.txt' dosyasına kaydedildi.")
            
            # Kısaca ekrana basalım, var mı yok mu görelim
            if isinstance(data, list) and len(data) > 0:
                unit = data[0]
                print(f"📦 Bulunan Cihaz: {unit.get('UnitName')}")
                
                # KONUM KONTROLÜ
                if 'Position' in unit:
                    print("📍 Position Objesi BULUNDU! (İşte aradığımız şey!)")
                    print(json.dumps(unit['Position'], indent=4))
                elif 'Latitude' in unit:
                     print(f"📍 Latitude Ana Dizinde Bulundu: {unit['Latitude']}")
                else:
                    print("⚠️ Hala Position objesi görünmüyor. Dosyayı incelememiz lazım.")
            else:
                print("⚠️ Cihaz bulunamadı veya liste boş.")
        else:
            print(f"❌ Hata: {resp.text}")

    except Exception as e:
        print(f"🔥 Kritik Hata: {e}")

if __name__ == "__main__":
    search_unit()