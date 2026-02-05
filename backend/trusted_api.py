# backend/trusted_api.py (FİNAL - FULL VERSİYON)
import requests
import json
import time
from datetime import datetime

# --- KULLANICI BİLGİLERİ ---
API_USERNAME = "s.ozsarac@hkm.com.tr"
API_PASSWORD = "Solid_2023"
DEFAULT_GROUP_ID = 7153  # Şantiye oluştururken kullanılacak Grup ID

# --- ADRES VE AYARLAR ---
TOKEN_URL = "https://api.trusted.dk/Token"
API_BASE_URL = "https://api.trusted.dk/api"

# Token Önbellekleme (Sürekli sormamak için)
_CURRENT_TOKEN = None
_TOKEN_EXPIRE_TIME = 0

# =========================================================
# 🔐 BÖLÜM 1: KİMLİK DOĞRULAMA (AUTH)
# =========================================================

def get_api_token():
    """
    Trusted API'den token alır.
    Eğer son alınan token hala geçerliyse (50 dk) yenisini istemez.
    """
    global _CURRENT_TOKEN, _TOKEN_EXPIRE_TIME
    
    # Token var ve süresi dolmadıysa direkt onu ver
    if _CURRENT_TOKEN and time.time() < _TOKEN_EXPIRE_TIME:
        return _CURRENT_TOKEN

    payload = {"grant_type": "password", "username": API_USERNAME, "password": API_PASSWORD}
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    
    print("🔑 Trusted API: Yeni Token isteniyor...")
    try:
        response = requests.post(TOKEN_URL, data=payload, headers=headers, timeout=15)
        if response.status_code == 200:
            data = response.json()
            token = data.get("access_token")
            if token:
                _CURRENT_TOKEN = token
                # Token'ı 50 dakika (3000 saniye) boyunca geçerli say
                _TOKEN_EXPIRE_TIME = time.time() + 3000
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


# =========================================================
# 📡 BÖLÜM 2: VERİ ÇEKME (TELEMETRİ)
# =========================================================
# Bu kısım fetch_live_data ve recover_super_data mantığını içerir.

def api_get_latest_position(serial_number):
    """Cihazın en son konumunu çeker (Canlı Takip İçin)."""
    headers = get_headers()
    if not headers: return None
    
    endpoint = f"{API_BASE_URL}/Positions/GetLatest"
    params = {"SerialNumber": serial_number, "Count": 1}
    
    try:
        r = requests.get(endpoint, headers=headers, params=params, timeout=10)
        return r.json() if r.status_code == 200 else []
    except Exception as e:
        print(f"❌ GetLatest Hatası ({serial_number}): {e}")
        return []

def api_get_positions(serial_number, start_date, end_date):
    """Belirli tarih aralığındaki tüm konumları çeker."""
    headers = get_headers()
    if not headers: return []

    endpoint = f"{API_BASE_URL}/Positions/Get"
    params = {
        "SerialNumber": serial_number,
        "AfterDate": start_date.strftime("%Y-%m-%dT%H:%M:%S"),
        "BeforeDate": end_date.strftime("%Y-%m-%dT%H:%M:%S"),
        "Count": 100000,
        "SortDescending": "false"
    }
    try:
        r = requests.get(endpoint, headers=headers, params=params, timeout=60)
        return r.json() if r.status_code == 200 else []
    except Exception as e:
        print(f"❌ GetPositions Hatası ({serial_number}): {e}")
        return []

def api_get_sensors(serial_number, start_date, end_date):
    """Sıcaklık ve Pil verilerini çeker."""
    headers = get_headers()
    if not headers: return []

    endpoint = f"{API_BASE_URL}/SensorData/Get"
    params = {
        "SerialNumber": serial_number,
        "AfterDate": start_date.strftime("%Y-%m-%dT%H:%M:%S"),
        "BeforeDate": end_date.strftime("%Y-%m-%dT%H:%M:%S"),
        "Count": 100000
    }
    try:
        r = requests.get(endpoint, headers=headers, params=params, timeout=60)
        return r.json() if r.status_code == 200 else []
    except Exception as e:
        print(f"❌ GetSensors Hatası ({serial_number}): {e}")
        return []

def api_get_accelerometer(serial_number, start_date, end_date):
    """Darbe (Kaza) verilerini çeker."""
    headers = get_headers()
    if not headers: return []

    endpoint = f"{API_BASE_URL}/SensorData/AccelerometerHistogramData"
    params = {
        "serialNumber": serial_number,
        "afterDate": start_date.strftime("%Y-%m-%dT%H:%M:%S"),
        "beforeDate": end_date.strftime("%Y-%m-%dT%H:%M:%S")
    }
    try:
        r = requests.get(endpoint, headers=headers, params=params, timeout=45)
        return r.json() if r.status_code == 200 else []
    except Exception as e:
        print(f"❌ GetAccelerometer Hatası ({serial_number}): {e}")
        return []


# =========================================================
# 🏗️ BÖLÜM 3: ŞANTİYE YÖNETİMİ (GEOFENCE)
# =========================================================
# Senin yazdığın ve çalışan kodlar.

def api_create_geosite(name, lat, lon, radius, user_group_id=None):
    headers = get_headers()
    if not headers: return {"success": False, "error": "Token yok"}

    endpoint = f"{API_BASE_URL}/GeoSites/CreateFromLatLong"
    print(f"🚀 CREATE İsteği: {endpoint}")

    group_id = user_group_id if user_group_id else DEFAULT_GROUP_ID

    payload = {
        "Name": name,
        "Latitude": lat,
        "Longitude": lon,
        "Radius": int(radius),
        "UserGroupId": group_id,
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
            trusted_id = data.get("Id")
            print(f"✅ Şantiye Başarıyla Oluşturuldu! Trusted ID: {trusted_id}")
            return {"success": True, "trusted_id": trusted_id, "data": data}
        else:
            print(f"❌ API Create Hata ({response.status_code}): {response.text}")
            return {"success": False, "error": f"{response.status_code} - {response.text}"}
    except Exception as e:
        return {"success": False, "error": str(e)}

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

def api_update_registrations(trusted_id, device_serials, register=True, alarm=True):
    if not trusted_id: return {"success": False}
    headers = get_headers()
    endpoint = f"{API_BASE_URL}/GeoSites/{trusted_id}/UpdateUnitRegistrations"
    
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
            err = f"{response.status_code} - {response.text}"
            print(f"❌ Update Reg Hata: {err}")
            return {"success": False, "error": err}
    except Exception as e:
        return {"success": False, "error": str(e)}

def api_get_geosites(user_group_id=None):
    headers = get_headers()
    if not headers: return {"success": False, "error": "Token yok"}
    
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
    
# backend/trusted_api.py EN ALTINA YAPIŞTIR:

def api_get_all_subgroups():
    """
    Admin hesabına bağlı TÜM alt grupları çeker.
    Hem Liste [] hem de Sözlük {} yanıtlarını destekler.
    """
    token = get_api_token()
    if not token: return []

    endpoint = f"{API_BASE_URL}/Groups?includeUnitSerials=false&maxDepth=10"
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
    
    try:
        response = requests.get(endpoint, headers=headers, timeout=15)
        if response.status_code == 200:
            data = response.json()
            
            flat_list = []
            
            # İç içe grupları gezen yardımcı fonksiyon
            def recurse_groups(group):
                if not isinstance(group, dict): return # Garanti kontrol
                
                g_id = str(group.get("Id"))
                g_name = group.get("Name")
                flat_list.append({"id": g_id, "name": g_name})
                
                # Alt grupları gez
                subgroups = group.get("SubGroups")
                if subgroups and isinstance(subgroups, list):
                    for sub in subgroups:
                        recurse_groups(sub)
            
            # --- ANA DÜZELTME BURADA ---
            # API liste dönerse döngüye al, sözlük dönerse direkt işle
            if isinstance(data, list):
                for item in data:
                    recurse_groups(item)
            elif isinstance(data, dict):
                recurse_groups(data)
                
            return flat_list
        else:
            print(f"❌ Grup Listesi Hatası: {response.status_code}")
            return []
    except Exception as e:
        print(f"❌ API Bağlantı Hatası: {e}")
        return []