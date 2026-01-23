import requests
import pandas as pd
import json

# --- AYARLAR ---
# PDF'teki Endpoint Adresi
API_ENDPOINT = "https://api.trusted.dk/api/Utilization/GetUnit"
USERNAME = "s.ozsarac@hkm.com.tr"
PASSWORD = "Solid_2023"

# Hedef Cihaz
DEVICE_SERIAL = "865456056700519"

# Tarih girmek zorundayız yoksa API hangi aralığı vereceğini bilemez.
# Veri olduğunu bildiğimiz aralığı giriyorum:
START_DATE = "2024-12-16T00:00:00"
END_DATE = "2024-12-22T23:59:59"

def get_token():
    print("🔑 Token alınıyor...")
    payload = {'grant_type': 'password', 'username': USERNAME, 'password': PASSWORD}
    try:
        # Token adresi standarttır
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

def fetch_raw_api_data(token):
    print(f"📡 API İsteği Yapılıyor: {API_ENDPOINT}")
    
    headers = {
        'Authorization': f'Bearer {token}'
    }
    
    # PDF Sayfa 1'deki "URI Parameters" kısmına göre hazırladım:
    params = {
        "SerialNumber": DEVICE_SERIAL,   # Required (String)
        "AfterDate": START_DATE,         # Optional (Date) - Başlangıç
        "BeforeDate": END_DATE,          # Optional (Date) - Bitiş
        "Count": 10000,                  # Optional (Int32) - Max kayıt sayısı
        "SortDescending": "false",       # Optional (Boolean) - Eskiden yeniye sırala
        "ActivityFilter": "All",         # Optional (Enum) - PDF Sayfa 2: Idle, In Use or Both. "All" diyerek hepsini istiyoruz.
        "SeparateByDay": "false"         # Optional (Boolean) - PDF Sayfa 2: Günlere bölme, ham süreyi ver.
    }
    
    try:
        response = requests.get(API_ENDPOINT, headers=headers, params=params)
        
        # HTTP Durum Kodunu Görelim
        print(f"📡 HTTP Durum Kodu: {response.status_code}")
        
        if response.status_code != 200:
            print("❌ API Hata Döndürdü:")
            print(response.text)
            return

        json_data = response.json()
        print("✅ Veri çekildi.")

        # PDF Sayfa 2 -> "Response Information" kısmına göre:
        # Ana obje içinde "Activities" adında bir koleksiyon dönmesi lazım.
        # Ama bazen "Activities", bazen direkt liste dönebilir. Kontrol edelim:
        
        data_list = []
        
        if isinstance(json_data, dict):
            # Sözlük geldiyse anahtarlara bakalım
            print(f"ℹ️ Gelen Ana Anahtarlar: {list(json_data.keys())}")
            
            if "Activities" in json_data:
                data_list = json_data["Activities"]
            elif "List" in json_data:
                data_list = json_data["List"]
            elif "Items" in json_data:
                data_list = json_data["Items"]
            else:
                # Hiçbiri yoksa ana objeyi olduğu gibi listeye çevirmeyi dene
                print("⚠️ Beklenen 'Activities' anahtarı yok, JSON kökünü inceliyorum.")
                # Belki tek bir objedir, liste yapalım
                data_list = [json_data]
                
        elif isinstance(json_data, list):
            print("ℹ️ Veri doğrudan Liste [] olarak geldi.")
            data_list = json_data

        print(f"📊 Toplam Kayıt Sayısı: {len(data_list)}")

        if len(data_list) == 0:
            print("⚠️ Liste boş geldi.")
            return

        # Pandas ile Excel'e basalım
        df = pd.json_normalize(data_list)
        
        filename = "Trusted_GetUnit_Raw_Response.xlsx"
        df.to_excel(filename, index=False)
        
        print(f"🎉 Tüm ham veri '{filename}' dosyasına kaydedildi.")
        print("-" * 40)
        print("Sütun İsimleri (API'den ne geldiyse):")
        print(df.columns.tolist())

    except Exception as e:
        print(f"💥 Kod Hatası: {e}")

if __name__ == "__main__":
    token_str = get_token()
    if token_str:
        fetch_raw_api_data(token_str)