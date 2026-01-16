# scripts/explore_api.py
import requests
import json
import os

# --- AYARLAR ---
API_BASE_URL = "https://api.trusted.dk"
TOKEN_URL = "https://api.trusted.dk/Token"
API_USERNAME = "s.ozsarac@hkm.com.tr" 
API_PASSWORD = "Solid_2023"

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

def explore():
    token = get_token()
    if not token: return

    headers = {'Authorization': f'Bearer {token}'}
    
    # 1. Önce Cihaz Listesini (ID'leri) alalım
    print("📡 Cihaz listesi çekiliyor...")
    units_resp = requests.get(f"{API_BASE_URL}/api/Units/MyUnits", headers=headers)
    units = units_resp.json()
    
    if not units:
        print("⚠️ Cihaz bulunamadı.")
        return

    # İlk cihazı kobay olarak seçelim
    target_unit = units[0]
    serial_no = target_unit.get('SerialNumber')
    unit_name = target_unit.get('UnitName')
    
    print(f"🎯 Hedef Cihaz Seçildi: {unit_name} (S/N: {serial_no})")
    print("-" * 40)

    results = {}
    
    # --- TEST 1: Cihazın Temel Bilgileri ---
    results['1_BASIC_INFO'] = target_unit

    # --- TEST 2: DataLog (Genelde konum buradadır) ---
    # Trusted API'de en kritik veri "DataLog" içindedir.
    # Son 5 logu çekelim bakalım içinde ne var.
    print("🧪 Test 2: DataLog (Geçmiş Verisi) deneniyor...")
    try:
        log_url = f"{API_BASE_URL}/api/DataLog/Get?serialNumber={serial_no}&count=5"
        log_resp = requests.get(log_url, headers=headers)
        results['2_DATALOG_RESPONSE'] = log_resp.json()
    except Exception as e:
        results['2_DATALOG_ERROR'] = str(e)

    # --- TEST 3: Trips (Seyahatler) ---
    # Eğer API_2'de Trip/Sefer bilgisi varsa buradadır.
    print("🧪 Test 3: Trips (Seferler) deneniyor...")
    try:
        trip_url = f"{API_BASE_URL}/api/Trips/Get?serialNumber={serial_no}&count=2"
        trip_resp = requests.get(trip_url, headers=headers)
        results['3_TRIPS_RESPONSE'] = trip_resp.json()
    except Exception as e:
        results['3_TRIPS_ERROR'] = str(e)
        
    # --- SONUÇLARI DOSYAYA YAZ ---
    # Konsola basınca kayboluyor, dosyaya yazalım ki bana atabilesin.
    with open("api_result.txt", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=4, ensure_ascii=False)
        
    print("\n" + "="*40)
    print("✅ TARAMA TAMAMLANDI!")
    print(f"📂 Sonuçlar 'api_result.txt' dosyasına kaydedildi.")
    print("👉 Lütfen bu dosyayı aç ve içeriğini (veya bir kısmını) bana gönder.")
    print("="*40)

if __name__ == "__main__":
    explore()