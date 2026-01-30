# scripts/test_groups.py (DEDEKTİF SCRIPT)
import requests
import json

API_BASE_URL = "https://api.trusted.dk/api"
API_USERNAME = "s.ozsarac@hkm.com.tr"
API_PASSWORD = "Solid_2023"

def test_discovery():
    print("🕵️‍♂️ GRUP KEŞİF TESTİ BAŞLIYOR...")
    
    # 1. LOGIN OL
    payload = {"grant_type": "password", "username": API_USERNAME, "password": API_PASSWORD}
    try:
        resp = requests.post("https://api.trusted.dk/token", data=payload)
        if resp.status_code != 200:
            print(f"❌ Giriş Yapılamadı! Kod: {resp.status_code}")
            return
        token = resp.json().get("access_token")
        headers = {"Authorization": f"Bearer {token}"}
        print("✅ Giriş Başarılı.")
    except Exception as e:
        print(f"❌ Bağlantı Hatası: {e}")
        return

    # 2. HIERARCHY (AĞAÇ) SORGUSU YAP
    url = f"{API_BASE_URL}/Groups/Hierarchy"
    print(f"📡 API Sorgulanıyor: {url}")
    
    resp = requests.get(url, headers=headers)
    
    if resp.status_code == 200:
        data = resp.json()
        print("✅ API Yanıt Verdi.")
        
        all_ids = []
        
        # Recursive fonksiyon ile ağacı gez
        def find_ids(node):
            if isinstance(node, dict):
                gid = node.get("Id")
                name = node.get("Name")
                print(f"   📍 BULUNDU -> Grup Adı: {name} | ID: {gid}")
                all_ids.append(gid)
                
                children = node.get("Children", [])
                for child in children:
                    find_ids(child)
            elif isinstance(node, list):
                for item in node:
                    find_ids(item)

        find_ids(data)
        
        print("\n--------------------------------")
        if 9840 in all_ids:
            print("🎉 BAŞARILI: 9840 Grubu (Fel-Tech) Listede VAR!")
            print("Sorun kodda değil, veritabanına yazmada olabilir.")
        else:
            print("⚠️ KRİTİK SORUN: API 9840 Grubunu DÖNDÜRMÜYOR!")
            print("Listede sadece bunlar var:", all_ids)
            print("Bu durumda 'Hierarchy' yerine manuel liste kullanmak zorundayız.")
        print("--------------------------------")
            
    else:
        print(f"❌ API Hatası: {resp.status_code}")
        print(resp.text)

if __name__ == "__main__":
    test_discovery()