import requests
import pandas as pd
import json

# --- AYARLAR ---
# PDF'teki Endpoint: Get the total number of minutes in use
API_ENDPOINT = "https://api.trusted.dk/api/Utilization/GetUnitInUseMinutes"
USERNAME = "s.ozsarac@hkm.com.tr"
PASSWORD = "Solid_2023"

# Hedef Cihaz
DEVICE_SERIAL = "865456056700519"

# Tarih Aralığı (16-22 Aralık - Karşılaştırma için)
START_DATE = "2024-12-16T00:00:00"
END_DATE = "2024-12-22T23:59:59"

def get_token():
    print("🔑 Token alınıyor...")
    payload = {'grant_type': 'password', 'username': USERNAME, 'password': PASSWORD}
    try:
        resp = requests.post("https://api.trusted.dk/token", data=payload)
        if resp.status_code == 200:
            print("✅ Token alındı.")
            return resp.json()['access_token']
        else:
            print(f"❌ Token Hatası: {resp.text}")
            return None
    except Exception as e:
        print(f"💥 Bağlantı Hatası: {e}")
        return None

def fetch_total_minutes(token):
    print(f"📡 API İsteği Yapılıyor: {API_ENDPOINT}")
    
    headers = {'Authorization': f'Bearer {token}'}
    
    # PDF'teki Parametreler
    params = {
        "SerialNumber": DEVICE_SERIAL,
        "AfterDate": START_DATE,
        "BeforeDate": END_DATE
    }
    
    try:
        response = requests.get(API_ENDPOINT, headers=headers, params=params)
        
        if response.status_code != 200:
            print("❌ API Hata Döndürdü:")
            print(response.text)
            return

        json_data = response.json()
        print("✅ Veri çekildi.")
        print("-" * 30)
        
        # Gelen Cevabı Görelim
        # PDF'e göre cevap: {"SerialNumber": "...", "InUseMinutes": 123, "InUseSeconds": 7380, ...}
        print("API CEVABI:")
        print(json.dumps(json_data, indent=4))
        
        # Excel'e Basalım (Tek satırlık özet bilgi)
        df = pd.json_normalize(json_data)
        filename = "API_Toplam_Sure_Ozeti.xlsx"
        df.to_excel(filename, index=False)
        
        print("-" * 30)
        
        # Hızlı Analiz
        if "InUseMinutes" in json_data and "InUseSeconds" in json_data:
            minutes = json_data["InUseMinutes"]
            seconds = json_data["InUseSeconds"]
            hours = minutes / 60
            
            print(f"🕒 API'nin Hesapladığı Toplam Çalışma:")
            print(f"   ► {minutes} Dakika")
            print(f"   ► {seconds} Saniye")
            print(f"   ► {hours:.2f} Saat")
            
            print(f"\n🎉 Sonuç '{filename}' dosyasına kaydedildi.")
        else:
            print("⚠️ Beklenen 'InUseMinutes' alanı cevapta yok.")

    except Exception as e:
        print(f"💥 Kod Hatası: {e}")

if __name__ == "__main__":
    token_str = get_token()
    if token_str:
        fetch_total_minutes(token_str)