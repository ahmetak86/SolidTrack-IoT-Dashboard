import sys
import os
import requests
import json
from datetime import datetime, timedelta

# Proje ana dizinini yola ekle
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# DÜZELTME BURADA: get_token -> get_api_token, BASE_URL -> API_BASE_URL
from backend.trusted_api import get_api_token, API_BASE_URL 
from backend.database import SessionLocal, Device

def print_header(title):
    print(f"\n{'='*60}")
    print(f"🕵️  {title}")
    print(f"{'='*60}")

def check_endpoint(endpoint_name, url, headers, params=None):
    """API ucunu test eder ve sonucu raporlar."""
    try:
        response = requests.get(url, headers=headers, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            # Liste boş mu dolu mu?
            if isinstance(data, list) and not data:
                print(f"   ⚠️  {endpoint_name}: [200 OK] Ancak VERİ BOŞ.")
                return None
            elif not data: # None veya boş dict
                print(f"   ⚠️  {endpoint_name}: [200 OK] Ancak VERİ YOK.")
                return None
            else:
                print(f"   ✅ {endpoint_name}: [200 OK] VERİ AKIYOR! (Tip: {type(data)})")
                return data
        elif response.status_code == 403:
            print(f"   🚫 {endpoint_name}: [403 FORBIDDEN] - Yetki Yok / Özellik Kapalı.")
        elif response.status_code == 401:
            print(f"   ❌ {endpoint_name}: [401 UNAUTHORIZED] - Token Hatası.")
        else:
            print(f"   ❌ {endpoint_name}: [{response.status_code}] - {response.text[:100]}")
            
    except Exception as e:
        print(f"   💥 {endpoint_name}: Bağlantı Hatası ({e})")
    return None

def diagnose():
    print_header("SOLIDTRACK SENSÖR KEŞİF AJANI BAŞLATILIYOR...")
    
    # 1. TOKEN AL (Fonksiyon ismi düzeltildi)
    token = get_api_token()
    if not token:
        print("❌ Token alınamadı. İşlem iptal.")
        return

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    print("✅ Token alındı. Sunucuya bağlanılıyor...")

    # 2. CİHAZLARI ÇEK
    db = SessionLocal()
    devices = db.query(Device).all()
    db.close()

    if not devices:
        print("⚠️ Veritabanında kayıtlı cihaz yok. Önce sync yapın.")
        return

    print(f"🔍 Toplam {len(devices)} cihaz incelenecek.\n")

    # 3. HER CİHAZ İÇİN TEST YAP
    for dev in devices:
        print(f"🚜 CİHAZ: {dev.unit_name} (SN: {dev.device_id})")
        print("-" * 40)

        # --- TEST A: Sensor 6 (GetLatest) - GENEL SAĞLIK ---
        # URL değişkeni düzeltildi: API_BASE_URL
        url_latest = f"{API_BASE_URL}/SensorData/GetLatest"
        latest_data = check_endpoint("GetLatest (Genel)", url_latest, headers, {"SerialNumber": dev.device_id})
        
        if latest_data:
            # İçeriğe bakalım
            record = latest_data[0] if isinstance(latest_data, list) else latest_data
            
            temp = record.get("Temperature")
            press = record.get("Pressure")
            acc_peak = record.get("PeakAccelerationX") 
            
            print(f"      -> 🌡️  Sıcaklık: {temp if temp else 'YOK'}")
            print(f"      -> 💨  Basınç:   {press if press else 'YOK'}")
            print(f"      -> 💥  Max Darbe: {acc_peak if acc_peak else 'YOK'}")

        # --- TEST B: Sensor 11 (ToolDamageData) - HASAR ANALİZİ ---
        url_damage = f"{API_BASE_URL}/SensorData/AccelerometerToolDamageData"
        params_dmg = {
            "serialNumber": dev.device_id,
            "count": 5
        }
        damage_data = check_endpoint("ToolDamage (Hasar)", url_damage, headers, params_dmg)
        
        if damage_data:
            print("      💎 HAZİNE BULUNDU: Bu cihaz Hasar/Yıpranma verisi üretiyor!")
            try:
                print(f"      -> Örnek Veri: {json.dumps(damage_data[0], indent=2)}")
            except:
                print(f"      -> Veri: {damage_data}")

        # --- TEST C: Sensor 10 (Histogram) - TİTREŞİM PROFİLİ ---
        url_hist = f"{API_BASE_URL}/SensorData/AccelerometerHistogramData"
        hist_data = check_endpoint("Histogram (Titreşim)", url_hist, headers, {"serialNumber": dev.device_id})
        
        if hist_data:
             print("      📊 HİSTOGRAM AKTİF: Operatör kullanım detayları çekilebilir.")

        # --- TEST D: Sensor 8 (TagData) - HARİCİ SENSÖRLER ---
        url_tag = f"{API_BASE_URL}/SensorData/GetSensorTagData"
        tag_data = check_endpoint("SensorTags (Harici)", url_tag, headers, {"SerialNumber": dev.device_id})
        
        if tag_data:
            print(f"      🏷️  Harici Sensör Bulundu! ({len(tag_data)} kayıt)")
            try:
                tag_rec = tag_data[0]
                print(f"      -> Tag Adı: {tag_rec.get('TagName')} | Tip: {tag_rec.get('TagType')}")
            except:
                pass

        print("\n")

    print_header("TANI RAPORU TAMAMLANDI")

if __name__ == "__main__":
    diagnose()