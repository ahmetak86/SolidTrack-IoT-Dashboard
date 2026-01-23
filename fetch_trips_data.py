import requests
import pandas as pd
import json

# --- AYARLAR ---
# PDF'teki Endpoint: GET api/Utilization/Trips
API_ENDPOINT = "https://api.trusted.dk/api/Utilization/Trips"
USERNAME = "s.ozsarac@hkm.com.tr"
PASSWORD = "Solid_2023"

# Hedef Cihaz
DEVICE_SERIAL = "865456056700519"

# Hangi tarihten itibaren baksın? (16 Aralık ve sonrası)
FROM_DATE = "2024-12-16T00:00:00"

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

def fetch_trips(token):
    print(f"📡 API İsteği Yapılıyor: {API_ENDPOINT}")
    
    headers = {'Authorization': f'Bearer {token}'}
    
    # PDF'e göre sadece SerialNumber ve FromDate parametresi var.
    # ToDate yok, yani o tarihten bugüne kadar olan her şeyi getirecek.
    params = {
        "SerialNumber": DEVICE_SERIAL,
        "FromDate": FROM_DATE
    }
    
    try:
        response = requests.get(API_ENDPOINT, headers=headers, params=params)
        
        if response.status_code != 200:
            print("❌ API Hata Döndürdü:")
            print(response.text)
            return

        json_data = response.json()
        print("✅ Veri çekildi.")

        # TripModel yapısına göre liste dönmesini bekliyoruz
        # PDF Sayfa 2: Response Information -> TripModel
        
        data_list = []
        if isinstance(json_data, list):
            data_list = json_data
        elif isinstance(json_data, dict) and "List" in json_data:
            data_list = json_data["List"] # Bazı endpointlerde List wrapper olabiliyor
        
        print(f"📊 Toplam Seyahat (Trip) Sayısı: {len(data_list)}")

        if not data_list:
            print("⚠️ Hiç seyahat kaydı bulunamadı (Liste boş).")
            # Yine de boş Excel oluşturalım ki kolonları görelim
            pd.DataFrame().to_excel("Trusted_Trips_Analiz.xlsx", index=False)
            return

        # Excel'e aktar
        df = pd.json_normalize(data_list)
        
        filename = "Trusted_Trips_Analiz.xlsx"
        df.to_excel(filename, index=False)
        
        print(f"🎉 Rapor Hazır: {filename}")
        print("-" * 30)
        
        # Sütunları ve ilk 5 satırı görelim
        # Özellikle Duration ve Distance bizim için önemli
        cols_to_show = [c for c in ['TripId', 'FromGeocode', 'ToGeocode', 'Distance', 'Duration', 'DepartureDate', 'ArrivalDate'] if c in df.columns]
        
        print("🔍 İlk 5 Seyahat Kaydı:")
        print(df[cols_to_show].head())

    except Exception as e:
        print(f"💥 Kod Hatası: {e}")

if __name__ == "__main__":
    token_str = get_token()
    if token_str:
        fetch_trips(token_str)