import requests
import pandas as pd
import json

# --- AYARLAR ---
BASE_URL = "https://api.trusted.dk/api"
USERNAME = "s.ozsarac@hkm.com.tr"
PASSWORD = "Solid_2023"

# Sorunlu veriyi incelemek için o haftayı seçiyoruz (Mecburuz, yoksa o veriyi göremeyiz)
DEVICE_SERIAL = "865456056700519"
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

def fetch_from_pdf_endpoint(token):
    # PDF'teki Endpoint: GET api/Utilization/GetUnit
    url = f"{BASE_URL}/Utilization/GetUnit"
    
    print(f"📡 API'ye Bağlanılıyor: {url}")
    
    headers = {
        'Authorization': f'Bearer {token}'
    }
    
    # PDF Sayfa 1'deki Parametreler
    params = {
        "SerialNumber": DEVICE_SERIAL,
        "AfterDate": START_DATE,   # PDF: Only activity after this date
        "BeforeDate": END_DATE,    # PDF: Only activity before this date
        "Count": 10000,            # PDF: Max number of activities
        "SortDescending": "false", # PDF: Sort activities
        "SeparateByDay": "false",  # PDF: Activity that span across dates... (False yapalım ki bölmesin, bütün görelim)
        "ActivityFilter": "All"    # PDF: Filter by Idle, In Use or Both. (Hepsini görelim)
    }
    
    try:
        resp = requests.get(url, headers=headers, params=params)
        
        if resp.status_code != 200:
            print(f"❌ HATA! Kod: {resp.status_code}")
            print(resp.text)
            return

        raw_data = resp.json()
        print("✅ Veri başarıyla çekildi.")
        
        # PDF Sayfa 2 -> Response Information -> "Activities" koleksiyonu
        data_list = []
        if "Activities" in raw_data:
            data_list = raw_data["Activities"]
        else:
            print("⚠️ Beklenen 'Activities' anahtarı bulunamadı. Gelen anahtarlar:", raw_data.keys())
            # Yine de ne geldiyse onu basmaya çalışalım
            data_list = raw_data

        if not data_list:
            print("⚠️ Veri boş geldi.")
            return

        # Excel'e Dök
        df = pd.json_normalize(data_list)
        filename = "API_Yaniti_GetUnit.xlsx"
        df.to_excel(filename, index=False)
        
        print(f"🎉 Ham veri '{filename}' dosyasına kaydedildi.")
        print("-" * 30)
        print("Sütunlar:", df.columns.tolist())
        
        # Merak ettiğimiz kolonları ön izleyelim
        important_cols = ['ActivityStart', 'Duration', 'Activity', 'CategoryId', 'IsBurst']
        existing = [c for c in important_cols if c in df.columns]
        if existing:
            print(df[existing].head())

    except Exception as e:
        print(f"💥 Hata: {e}")

if __name__ == "__main__":
    token = get_token()
    if token:
        fetch_from_pdf_endpoint(token)