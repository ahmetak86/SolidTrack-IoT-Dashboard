import requests
import json
import sys

# --- AYARLAR ---
API_BASE_URL = "https://api.trusted.dk"
TOKEN_URL = "https://api.trusted.dk/Token"
API_USERNAME = "s.ozsarac@hkm.com.tr"
API_PASSWORD = "Solid_2023"

# Çıktıda gördüğümüz cihazın seri numarasını kullanıyoruz
TARGET_SERIAL = "865456055312555"  # TRISP ÖZÇ R260 #2 (Tahmini ID, eğer hata verirse listeden başkasını deneriz)

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

def inspect_datalog():
    token = get_token()
    if not token: return

    print(f"📡 '{TARGET_SERIAL}' cihazının SON SİNYALİ (DataLog) inceleniyor...")
    
    headers = {'Authorization': f'Bearer {token}'}
    # Son 1 adet logu çekiyoruz
    url = f"{API_BASE_URL}/api/DataLog/Get?serialNumber={TARGET_SERIAL}&count=1"
    
    try:
        resp = requests.get(url, headers=headers)
        if resp.status_code == 200:
            logs = resp.json()
            if isinstance(logs, list) and len(logs) > 0:
                last_log = logs[0]
                print("\n📦 SON SİNYAL İÇERİĞİ:")
                print("-" * 40)
                print(json.dumps(last_log, indent=4))
                
                print("\n🔎 'BATTERY' KELİMESİ ARANIYOR...")
                found = False
                for key, val in last_log.items():
                    if any(x in key.lower() for x in ['batt', 'volt', 'pow', 'ext', 'level']):
                        print(f"👉 BULUNDU: {key} = {val}")
                        found = True
                
                if not found:
                    print("❌ Log içinde de pil verisi bulunamadı. Belki 'Input' veya 'Analog' altındadır?")
            else:
                print("⚠️ Bu cihaz hiç veri göndermemiş (Log listesi boş).")
        else:
            print(f"❌ API Hatası: {resp.status_code} - {resp.text}")
            
    except Exception as e:
        print(f"❌ Bağlantı Hatası: {e}")

if __name__ == "__main__":
    inspect_datalog()