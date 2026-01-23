import requests
import pandas as pd
import json

# --- AYARLAR ---
API_ENDPOINT = "https://api.trusted.dk/api/Utilization/GetUnit"
USERNAME = "s.ozsarac@hkm.com.tr"
PASSWORD = "Solid_2023"

# Hedef Cihaz
DEVICE_SERIAL = "865456056700519"

# Tarih
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

def fetch_raw_api_data(token):
    print(f"📡 API İsteği Yapılıyor: {API_ENDPOINT}")
    
    headers = {'Authorization': f'Bearer {token}'}
    
    params = {
        "SerialNumber": DEVICE_SERIAL,
        "AfterDate": START_DATE,
        "BeforeDate": END_DATE,
        "Count": 10000,
        "SortDescending": "false",
        "ActivityFilter": "All",
        "SeparateByDay": "false"
    }
    
    try:
        response = requests.get(API_ENDPOINT, headers=headers, params=params)
        
        if response.status_code != 200:
            print("❌ API Hata Döndürdü:")
            print(response.text)
            return

        json_data = response.json()
        print("✅ Veri çekildi.")
        
        # --- VERİYİ AYIKLAMA (REVİZE EDİLDİ) ---
        data_list = []
        
        # 1. Ana bilgileri alalım (Üst Bilgiler)
        parent_info = {
            "CihazSeriNo": json_data.get("SerialNumber"),
            "GrupID": json_data.get("GroupId"),
            "ProfilID": json_data.get("ProfileId")
        }
        
        # 2. Aktiviteleri alalım
        if "Activities" in json_data:
            data_list = json_data["Activities"]
        elif "List" in json_data:
            data_list = json_data["List"]
        elif "Items" in json_data:
            data_list = json_data["Items"]
        else:
            # Eğer sadece tekil bir obje geldiyse onu listeye koy
            data_list = [json_data]

        print(f"📊 Aktivite Sayısı: {len(data_list)}")

        if not data_list:
            print("⚠️ Liste boş geldi.")
            return

        # 3. Tabloyu Oluştur
        df = pd.json_normalize(data_list)
        
        # 4. EKSİK OLAN ÜST BİLGİLERİ TABLOYA EKLE
        # Her satıra bu bilgileri kopyala
        for key, value in parent_info.items():
            df.insert(0, key, value) # En başa ekle

        filename = "Trusted_GetUnit_Full_Response.xlsx"
        df.to_excel(filename, index=False)
        
        print(f"🎉 Tüm veriler (Seri No dahil) '{filename}' dosyasına kaydedildi.")
        print("-" * 40)
        print("Sütunlar:", df.columns.tolist())

    except Exception as e:
        print(f"💥 Kod Hatası: {e}")

if __name__ == "__main__":
    token_str = get_token()
    if token_str:
        fetch_raw_api_data(token_str)