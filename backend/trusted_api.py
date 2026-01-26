# backend/trusted_api.py
import requests
import json

# --- KULLANICI BİLGİLERİ (sync_trusted.py'dan alındı) ---
API_USERNAME = "s.ozsarac@hkm.com.tr"
API_PASSWORD = "Solid_2023"
DEFAULT_GROUP_ID = 7153  # <--- KRİTİK GÜNCELLEME: Senin Grup ID'n

# --- ADRES VE TOKEN ---
TOKEN_URL = "https://api.trusted.dk/Token"
API_BASE_URL = "https://api.trusted.dk/api"

_CURRENT_TOKEN = None

def get_api_token():
    global _CURRENT_TOKEN
    if _CURRENT_TOKEN: return _CURRENT_TOKEN

    payload = {"grant_type": "password", "username": API_USERNAME, "password": API_PASSWORD}
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    
    print("🔑 Token İsteniyor...")
    try:
        response = requests.post(TOKEN_URL, data=payload, headers=headers, timeout=15)
        if response.status_code == 200:
            token = response.json().get("access_token")
            if token:
                _CURRENT_TOKEN = token
                return token
        else:
            print(f"❌ Token Hatası: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"❌ Token Bağlantı Hatası: {e}")
    return None

def get_headers():
    token = get_api_token()
    if not token: return None
    return {"Content-Type": "application/json", "Authorization": f"Bearer {token}"}

# ---------------------------------------------------------
# 1. ŞANTİYE OLUŞTURMA (CREATE)
# ---------------------------------------------------------
def api_create_geosite(name, lat, lon, radius, user_group_id=None):
    headers = get_headers()
    if not headers: return {"success": False, "error": "Token yok"}

    # PDF'teki doğru endpoint'e geri dönüyoruz
    endpoint = f"{API_BASE_URL}/GeoSites/CreateFromLatLong"
    print(f"🚀 CREATE İsteği: {endpoint}")

    # Grup ID'yi parametre gelmezse 7153 yapıyoruz
    group_id = user_group_id if user_group_id else DEFAULT_GROUP_ID

    payload = {
        "Name": name,
        "Latitude": lat,
        "Longitude": lon,
        "Radius": int(radius),
        "UserGroupId": group_id,  # <--- 7153 Gidiyor!
        "VisibleChildren": True,
        "RegisterUnitsOnMove": True,
        "RegisterUnitsForAlarmsOnMove": True,
        "RegisterUnits": False,
        "RegisterForAlarms": False
    }
    
    try:
        response = requests.post(endpoint, json=payload, headers=headers, timeout=10)
        
        if response.status_code in [200, 201]:
            data = response.json()
            # API bazen ID'yi, bazen tüm objeyi döner.
            trusted_id = data.get("Id")
            print(f"✅ Şantiye Başarıyla Oluşturuldu! Trusted ID: {trusted_id}")
            return {"success": True, "trusted_id": trusted_id, "data": data}
        else:
            # Hata detayını tam görelim
            print(f"❌ API Create Hata ({response.status_code}): {response.text}")
            return {"success": False, "error": f"{response.status_code} - {response.text}"}
    except Exception as e:
        return {"success": False, "error": str(e)}

# ---------------------------------------------------------
# 2. ŞANTİYE SİLME
# ---------------------------------------------------------
def api_delete_geosite(trusted_id):
    if not trusted_id: return {"success": True}
    headers = get_headers()
    endpoint = f"{API_BASE_URL}/GeoSites/{trusted_id}"
    print(f"🚀 DELETE İsteği: {endpoint}")
    
    try:
        response = requests.delete(endpoint, headers=headers, timeout=10)
        if response.status_code in [200, 204]: return {"success": True}
        else: return {"success": False, "error": response.text}
    except Exception as e: return {"success": False, "error": str(e)}

# ---------------------------------------------------------
# 3. CİHAZ ATAMA
# ---------------------------------------------------------
def api_update_registrations(trusted_id, device_serials, register=True, alarm=True):
    if not trusted_id: return {"success": False}
    headers = get_headers()
    endpoint = f"{API_BASE_URL}/GeoSites/{trusted_id}/UpdateUnitRegistrations"
    
    # Güvenlik önlemi: Hepsini string yapalım
    safe_serials = [str(s) for s in device_serials]

    payload = {
        "SerialNumbers": safe_serials, 
        "RegisterUnits": register,
        "RegisterForAlarms": alarm
    }
    
    try:
        response = requests.put(endpoint, json=payload, headers=headers, timeout=10)
        if response.status_code == 200:
            return {"success": True}
        else:
            # Hata kodunu görelim
            err = f"{response.status_code} - {response.text}"
            print(f"❌ Update Reg Hata: {err}")
            return {"success": False, "error": err}
    except Exception as e:
        return {"success": False, "error": str(e)}

def api_get_geosites(user_group_id=None):
    """
    Sunucu üzerindeki tüm şantiyeleri ve içindeki cihazları çeker.
    """
    headers = get_headers()
    if not headers: return {"success": False, "error": "Token yok"}
    
    # --- DEĞİŞİKLİK BURADA: IncludeUnitInfo=true eklendi ---
    endpoint = f"{API_BASE_URL}/GeoSites?IncludeUnitInfo=true"
    
    print(f"📡 API GET İsteği: {endpoint}")
    
    try:
        response = requests.get(endpoint, headers=headers, timeout=15)
        if response.status_code == 200:
            return {"success": True, "data": response.json()}
        else:
            return {"success": False, "error": f"{response.status_code} - {response.text}"}
    except Exception as e:
        return {"success": False, "error": str(e)}