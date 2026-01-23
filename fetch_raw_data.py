import requests
import pandas as pd
import json
from datetime import datetime

# --- AYARLAR ---
API_BASE_URL = "https://api.trusted.dk/api"

# DÜZELTME: Tırnak işaretleri eklendi
USERNAME = "s.ozsarac@hkm.com.tr"
PASSWORD = "Solid_2023"

# Hedef Cihaz ve Tarih
DEVICE_SERIAL = "865456055312555"
START_DATE = "2026-01-14T00:00:00"
END_DATE = "2026-01-21T23:59:59"

def get_token():
    print("🔑 Token alınıyor...")
    # DÜZELTME: Burada değişkenleri kullanıyoruz
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

def fetch_data_like_production(token):
    print(f"📡 Veri çekiliyor... (Endpoint: /Utilization/GetUnit)")
    
    url = f"{API_BASE_URL}/Utilization/GetUnit"
    
    headers = {
        'Authorization': f'Bearer {token}'
    }
    
    params = {
        "SerialNumber": DEVICE_SERIAL,
        "AfterDate": START_DATE,
        "BeforeDate": END_DATE,
        "Count": 10000 
    }
    
    try:
        resp = requests.get(url, headers=headers, params=params)
        
        if resp.status_code != 200:
            print(f"❌ HATA! Kod: {resp.status_code}")
            print(resp.text)
            return

        raw_data = resp.json()
        print("✅ Veri çekildi.")
        
        data_list = []
        if isinstance(raw_data, dict):
            if "Activities" in raw_data: 
                data_list = raw_data["Activities"]
                print("ℹ️ Veri 'Activities' anahtarı içinden alındı.")
            else:
                for key in ["Items", "List", "Data", "Result"]:
                    if key in raw_data: 
                        data_list = raw_data[key]
                        print(f"ℹ️ Veri '{key}' anahtarı içinden alındı.")
                        break
        elif isinstance(raw_data, list):
            data_list = raw_data
            print("ℹ️ Veri doğrudan liste olarak geldi.")

        if not data_list:
            print("⚠️ Liste boş veya format farklı.")
            print("Gelen Ham Cevap (İlk 500 karakter):", str(raw_data)[:500])
            return

        # Excel'e bas
        df = pd.json_normalize(data_list)
        filename = "Ham_Veri_Senin_Kodunla2.xlsx"
        df.to_excel(filename, index=False)
        print(f"🎉 Dosya oluşturuldu: {filename}")
        print(f"Toplam Satır: {len(df)}")
        
        # O problemli kolonlara bakalım
        cols_to_check = ['ActivityStart', 'Duration', 'Category', 'IsBurst', 'ActivityType', 'Name']
        existing_cols = [c for c in cols_to_check if c in df.columns]
        
        if existing_cols:
            print("\n--- İlk 5 Satır (Önemli Kolonlar) ---")
            print(df[existing_cols].head())
        else:
            print("\n--- İlk 5 Satır (Tüm Kolonlar) ---")
            print(df.head())

    except Exception as e:
        print(f"💥 Hata: {e}")

if __name__ == "__main__":
    token = get_token()
    if token:
        fetch_data_like_production(token)