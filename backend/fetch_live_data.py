import sys
import os
import requests
import time
import uuid  # <-- EKLENDİ: Benzersiz ID üretmek için
from datetime import datetime

# Yolları ayarla
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from backend.database import SessionLocal, Device, TelemetryLog, get_trusted_api_token, API_BASE_URL

def fetch_and_update_live_data():
    """Trusted API'den canlı veriyi çeker. SANAL CİHAZLARI ATLAR."""
    print("🔄 [Live Data] Başlatıldı...")
    
    db = SessionLocal()
    try:
        # Sadece AKTİF ve GERÇEK (Sanal Olmayan) cihazları çek
        devices = db.query(Device).filter(
            Device.is_active == True,
            Device.is_virtual == False
        ).all()
        
        if not devices:
            print("⚠️ Sorgulanacak aktif ve gerçek cihaz bulunamadı.")
            return

        token = get_trusted_api_token()
        if not token:
            print("❌ Token alınamadı.")
            return

        headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
        
        updated_count = 0
        
        for dev in devices:
            try:
                # Canlı Konum Endpoint'i
                url = f"https://api.trusted.dk/api/Positions/GetLatest"
                params = {"SerialNumber": dev.device_id, "Count": 1}
                
                resp = requests.get(url, headers=headers, params=params, timeout=10)
                
                if resp.status_code == 200:
                    data = resp.json()
                    if isinstance(data, list) and len(data) > 0:
                        pos = data[0]
                        
                        lat = pos.get("Latitude")
                        lon = pos.get("Longitude")
                        ts_str = pos.get("Timestamp")
                        
                        if lat is not None and lon is not None:
                            # DB GÜNCELLEME
                            dev.last_latitude = lat
                            dev.last_longitude = lon
                            
                            # Tarih Parse Et
                            try:
                                ts_clean = ts_str.replace("Z", "")
                                if "." in ts_clean:
                                    last_seen = datetime.strptime(ts_clean, "%Y-%m-%dT%H:%M:%S.%f")
                                else:
                                    last_seen = datetime.strptime(ts_clean, "%Y-%m-%dT%H:%M:%S")
                                dev.last_seen_at = last_seen
                            except:
                                last_seen = datetime.utcnow()

                            # Geçmişe de log at (TelemetryLog)
                            # Mükerrer kontrolü
                            exists = db.query(TelemetryLog).filter(
                                TelemetryLog.device_id == dev.device_id,
                                TelemetryLog.timestamp == last_seen
                            ).first()
                            
                            if not exists:
                                # DÜZELTME: log_id'yi elle üretiyoruz
                                log = TelemetryLog(
                                    log_id=str(uuid.uuid4()), # <-- KRİTİK EKLEME
                                    device_id=dev.device_id,
                                    timestamp=last_seen,
                                    latitude=lat,
                                    longitude=lon,
                                    speed_kmh=pos.get("Speed", 0), # speed_kmh kullanıldı
                                    battery_pct=0, # Default değer
                                    temp_c=0,      # Default değer
                                    max_shock_g=0  # Default değer
                                )
                                db.add(log)
                            
                            updated_count += 1
                            print(f"   ✅ {dev.unit_name}: Konum güncellendi.")
                elif resp.status_code == 404:
                    print(f"   ⚠️ {dev.unit_name}: API'de bulunamadı (404).")
                else:
                    print(f"   ❌ {dev.unit_name}: API Hatası {resp.status_code}")
                    
            except Exception as e:
                print(f"   ❌ {dev.unit_name} Hata: {e}")
                continue

        db.commit()
        print(f"✅ Toplam {updated_count} cihaz güncellendi.")

    except Exception as e:
        db.rollback()
        print(f"❌ Genel Hata: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    fetch_and_update_live_data()