# backend/fetch_live_data.py (FİNAL VERSİYON - GEOFENCE MOTORU DAHİL)
import time
import sys
import os
import requests
import math
from datetime import datetime, timedelta
from dateutil import parser

# Proje yolunu ekle
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.database import SessionLocal, Device, TelemetryLog, UtilizationEvent, create_alarm, GeoSite
from backend.trusted_api import get_api_token, API_BASE_URL

# KONTROL SIKLIĞI (Dakika)
POLL_INTERVAL_MINUTES = 15 

# --- YARDIMCI: MESAFE HESAPLA (Haversine Formülü) ---
def calculate_distance(lat1, lon1, lat2, lon2):
    R = 6371000 # Dünya yarıçapı (metre)
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c # Metre cinsinden mesafe

def check_geofence(db, device, lat, lon):
    """
    Cihazın atandığı şantiyeleri kontrol eder.
    Eğer şantiye dışındaysa ALARM oluşturur.
    """
    # Cihazın bağlı olduğu şantiyeleri bul (GeoSite <-> Device ilişkisi)
    # Bu ilişki database.py'deki backref='devices' sayesinde çalışır
    assigned_sites = device.geosites 
    
    if not assigned_sites:
        return # Şantiye atanmamış

    for site in assigned_sites:
        if not site.auto_enable_alarms:
            continue # Bu şantiyenin alarmı kapalı

        # Mesafe Ölç
        dist = calculate_distance(lat, lon, site.latitude, site.longitude)
        
        # Tolerans (GPS sapması için 50m ekleyelim)
        limit = site.radius_meters + 50 
        
        if dist > limit:
            # --- ALARM TETİKLE ---
            msg = f"{device.unit_name}, '{site.name}' şantiyesinin dışına çıktı! (Fark: {int(dist - site.radius_meters)}m)"
            print(f"   🚨 GEOFENCE İHLALİ: {msg}")
            
            # Son 1 saatte aynı alarm atıldı mı? (Spam engelleme)
            # Buraya basit bir kontrol eklenebilir. Şimdilik direkt atıyoruz.
            create_alarm(
                device_id=device.device_id,
                type="Geofence",
                severity="Critical",
                value=f"{int(dist)}m",
                desc=msg
            )

def sync_device_data():
    print(f"\n🔄 [{datetime.now().strftime('%H:%M:%S')}] Trusted Veri ve Alarm Kontrolü...")
    
    token = get_api_token()
    if not token:
        print("❌ Token alınamadı!")
        return

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    db = SessionLocal()
    devices = db.query(Device).filter(Device.is_active == True).all()
    
    for dev in devices:
        try:
            # API'den Son Veriyi Çek
            url_latest = f"{API_BASE_URL}/SensorData/GetLatest"
            resp = requests.get(url_latest, headers=headers, params={"SerialNumber": dev.device_id}, timeout=10)
            
            if resp.status_code == 200:
                data_list = resp.json()
                if data_list:
                    raw = data_list[0]
                    
                    # 1. ZAMAN KONTROLÜ
                    api_time_str = raw.get("Timestamp")
                    api_time = parser.isoparse(api_time_str).replace(tzinfo=None)
                    
                    last_log = db.query(TelemetryLog).filter(TelemetryLog.device_id == dev.device_id)\
                                 .order_by(TelemetryLog.timestamp.desc()).first()
                    
                    # Yeni veri yoksa bile GEOFENCE kontrolü yapalım mı?
                    # Hayır, konum değişmediyse tekrar alarm atmaya gerek yok.
                    if last_log and last_log.timestamp >= api_time:
                        print(f"   ⏭️  {dev.unit_name}: Güncel. (Son: {api_time.strftime('%H:%M')})")
                        continue
                    
                    print(f"   📥 {dev.unit_name}: Yeni Veri! -> İşleniyor...")

                    # 2. VERİLERİ AL
                    temp = raw.get("Temperature") 
                    bat = raw.get("BatteryPercent")
                    lat = raw.get("Latitude")
                    lon = raw.get("Longitude")
                    
                    acc_x = raw.get("PeakAccelerationX", 0) or 0
                    acc_y = raw.get("PeakAccelerationY", 0) or 0
                    acc_z = raw.get("PeakAccelerationZ", 0) or 0
                    vibration_score = (acc_x**2 + acc_y**2 + acc_z**2) ** 0.5
                    
                    # 3. DB'YE YAZ
                    new_log = TelemetryLog(
                        device_id=dev.device_id,
                        timestamp=api_time,
                        latitude=lat if lat else dev.latitude,
                        longitude=lon if lon else dev.longitude,
                        speed_kmh=0, # Hız verisi API'de yoksa 0
                        heading=0,
                        pressure_bar=0,
                        oil_temp_c=temp if temp else 0,
                        battery_pct=bat if bat else 0,
                        g_force=vibration_score,
                        usage_score=0 
                    )
                    db.add(new_log)
                    
                    # 4. KONUM GÜNCELLE & GEOFENCE KONTROLÜ (🔥 YENİ 🔥)
                    if lat and lon:
                        dev.latitude = lat
                        dev.longitude = lon
                        dev.last_seen = api_time
                        
                        # ---> BURADA KONTROL EDİYORUZ <---
                        check_geofence(db, dev, lat, lon)

            else:
                print(f"   ⚠️ {dev.unit_name}: API Hatası ({resp.status_code})")

        except Exception as e:
            print(f"   ❌ Hata ({dev.unit_name}): {e}")

    db.commit()
    db.close()
    print("✅ Tur Tamamlandı.")

if __name__ == "__main__":
    print(f"🚀 SolidTrack Motoru Başlatıldı (Periyot: {POLL_INTERVAL_MINUTES} dk)")
    sync_device_data() # <-- İLK ÇALIŞTIRMA (Doğru İsim)
    
    while True:
        for i in range(POLL_INTERVAL_MINUTES * 60, 0, -1):
             if i % 60 == 0:
                 sys.stdout.write(f"\r⏳ Sonraki kontrol: {i//60} dk... ")
                 sys.stdout.flush()
             time.sleep(1)
        
        sync_device_data() # <-- DÖNGÜ İÇİNDEKİ ÇAĞRI (Doğru İsim)