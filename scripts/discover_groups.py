import requests
import pandas as pd

# API Bilgileri
BASE_URL = "https://api.trusted.dk"
USERNAME = "s.ozsarac@hkm.com.tr"
PASSWORD = "Solid_2023"

def get_token():
    payload = {"grant_type": "password", "username": USERNAME, "password": PASSWORD}
    try:
        response = requests.post(f"{BASE_URL}/token", data=payload)
        response.raise_for_status()
        return response.json().get("access_token")
    except Exception as e:
        print(f"❌ Token Hatası: {e}")
        return None

def audit_groups():
    token = get_token()
    if not token: return

    headers = {"Authorization": f"Bearer {token}"}
    
    print("🔍 Tüm Cihazlar Taranıyor (Grup ID Tespiti)...")
    
    # units12.pdf'e göre GetAllSerialnumbers tüm alt grupları da getirir
    url = f"{BASE_URL}/api/Units/GetAllSerialnumbers" 
    
    try:
        res = requests.get(url, headers=headers)
        if res.status_code == 200:
            units = res.json()
            print(f"📦 Toplam Cihaz Sayısı: {len(units)}")
            
            # Gruplara Göre Analiz
            df = pd.DataFrame(units)
            if not df.empty and 'UserGroupId' in df.columns:
                group_counts = df.groupby('UserGroupId').size().reset_index(name='Cihaz Sayısı')
                print("\n📊 TESPİT EDİLEN GRUPLAR:")
                print(group_counts.to_string(index=False))
                
                # Fel-Tech Muhtemelen bu ID'lerden biri
                print("\n👉 Eğer Fel-Tech cihazlarını görüyorsan, yukarıdaki ID'lerden hangisi onlara ait?")
            else:
                print("⚠️ Cihaz listesi geldi ama 'UserGroupId' alanı yok veya boş.")
                print(units[:2]) # Örnek veri görelim
        else:
            print(f"❌ Hata: {res.status_code} - {res.text}")
            
    except Exception as e:
        print(f"❌ Bağlantı Hatası: {e}")

if __name__ == "__main__":
    audit_groups()