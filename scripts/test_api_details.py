import requests
import json
from datetime import datetime, timedelta

# Ayarlar
API_USERNAME = "s.ozsarac@hkm.com.tr"
API_PASSWORD = "Solid_2023"
# Senin verisi var dediğin cihazın ID'si (TRÇAN BIG R250 #1)
TARGET_SERIAL = "865456056700519" 

def check_hidden_data():
    # 1. Token Al
    payload = {'grant_type': 'password', 'username': API_USERNAME, 'password': API_PASSWORD}
    try:
        resp = requests.post("https://api.trusted.dk/Token", data=payload, timeout=10)
        if resp.status_code != 200:
            print(f"Token Hatası: {resp.text}")
            return
        token = resp.json().get('access_token')
    except Exception as e:
        print(f"Bağlantı Hatası: {e}")
        return
    
    # 2. Utilization Verisini Çek (Son 30 GÜN - Kesin veri olsun diye)
    headers = {'Authorization': f'Bearer {token}'}
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=30)
    
    url = "https://api.trusted.dk/api/Utilization/GetUnit"
    params = {
        "SerialNumber": TARGET_SERIAL,
        "AfterDate": start_date.strftime("%Y-%m-%dT%H:%M:%S"),
        "BeforeDate": end_date.strftime("%Y-%m-%dT%H:%M:%S"),
        "Count": 5 # Sadece 5 örnek getir
    }
    
    print(f"🔍 {TARGET_SERIAL} için API Röntgeni Çekiliyor...")
    try:
        r = requests.get(url, headers=headers, params=params, timeout=15)
        
        if r.status_code == 200:
            data = r.json()
            # Liste mi Dictionary mi kontrolü
            if isinstance(data, list):
                if len(data) > 0:
                    print("✅ VERİ GELDİ! İşte içindeki tüm detaylar:")
                    print("-" * 40)
                    # İlk kaydın tamamını yazdır
                    print(json.dumps(data[0], indent=4)) 
                    print("-" * 40)
                    
                    # KONTROL ANI
                    first_record = data[0]
                    if "Latitude" in first_record or "StartLatitude" in first_record:
                        print("🎉 MÜJDE! Konum verisi gizliymiş, haritayı kurtarabiliriz!")
                    else:
                        print("😔 MAALESEF... Veri var ama içinde Konum (Latitude/Longitude) yok.")
                else:
                    print("⚠️ Liste boş döndü. Bu cihaz son 30 gündür hiç kontak açmamış olabilir.")
            else:
                print("⚠️ API Garip bir format döndürdü:")
                print(data)
        else:
            print(f"❌ API Hatası: {r.status_code} - {r.text}")
            
    except Exception as e:
        print(f"Hata oluştu: {e}")

if __name__ == "__main__":
    check_hidden_data()