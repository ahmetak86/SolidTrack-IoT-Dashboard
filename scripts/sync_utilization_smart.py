import sys
import os
import requests
import json
from datetime import datetime, timedelta
import time
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# --- KRİTİK DÜZELTME: PATH AYARI EN ÜSTTE OLMALI ---
# Önce ana dizini Python'a tanıtıyoruz, sonra import yapıyoruz.
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Şimdi backend modüllerini çağırabiliriz (Hata vermez)
from backend.database import SessionLocal
from backend.models import Device, UtilizationEvent
from backend.alarm_engine import check_utilization_alarm, check_work_hours_alarm
# ---------------------------------------------------

# --- AYARLAR ---
API_BASE_URL = "https://api.trusted.dk/api"
API_USERNAME = "s.ozsarac@hkm.com.tr"
API_PASSWORD = "Solid_2023"

# --- SINIFLANDIRMA FONKSİYONU ---
def classify_event(duration, activity_val):
    """
    API'den gelen Activity (0/1) ve Süre (sn) bilgisine göre
    kategori, renk ve veritabanı statüsünü belirler.
    """
    # DURUM 1: Activity = 0 (Boşta / Idle)
    is_active = str(activity_val).lower() in ['true', '1']
    
    if not is_active:
        return {
            "cat": "Boşta Bekleme (Idle)",
            "color": "#E0E0E0", # Çok açık gri
            "is_burst": False,
            "raw": 0
        }

    # DURUM 2: Activity = 1 (Vuruş / Çalışma)
    if duration > 180:
        return {
            "cat": "Nakliye / Uzun Hareket",
            "color": "#000000", # SİYAH
            "is_burst": True,
            "raw": 1
        }
    elif duration <= 20:
        return {"cat": "İdeal Çalışma (0-20s)", "color": "#00C853", "is_burst": True, "raw": 1}
    elif duration <= 40:
        return {"cat": "Riskli Çalışma (21-40s)", "color": "#FFAB00", "is_burst": True, "raw": 1}
    elif duration <= 80:
        return {"cat": "Uç Şişirme Riski (41-80s)", "color": "#D50000", "is_burst": True, "raw": 1}
    else: # 81 - 180 arası
        return {"cat": "Operatör Hatası (81-180s)", "color": "#AA00FF", "is_burst": True, "raw": 1}

class UtilizationSyncSmart:
    def __init__(self):
        self.db = SessionLocal()
        self.session = requests.Session()
        self.token = None

    def login(self):
        print("🔑 Token alınıyor...")
        payload = {'grant_type': 'password', 'username': API_USERNAME, 'password': API_PASSWORD}
        try:
            resp = self.session.post("https://api.trusted.dk/token", data=payload)
            if resp.status_code == 200:
                self.token = resp.json()['access_token']
                self.session.headers.update({'Authorization': f'Bearer {self.token}'})
                print("✅ Token alındı.")
                return True
            else:
                print(f"❌ Giriş Hatası: {resp.text}")
                return False
        except Exception as e:
            print(f"💥 Bağlantı Hatası: {e}")
            return False

    def sync_device_daily(self, device):
        print(f"\n🔨 {device.unit_name} ({device.device_id}) senkronize ediliyor...")
        
        # Son 15 günü çekelim
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=15)
        
        url = f"{API_BASE_URL}/Utilization/GetUnit"
        params = {
            "SerialNumber": device.device_id,
            "AfterDate": start_date.strftime("%Y-%m-%dT%H:%M:%S"),
            "BeforeDate": end_date.strftime("%Y-%m-%dT%H:%M:%S"),
            "Count": 10000,
            "SortDescending": "false",
            "SeparateByDay": "false",
            "ActivityFilter": "All"
        }
        
        try:
            resp = self.session.get(url, params=params)
            if resp.status_code != 200:
                print(f"   ⚠️ API Hatası: {resp.status_code}")
                return

            raw_data = resp.json()
            data_list = []
            
            if isinstance(raw_data, dict):
                if "Activities" in raw_data: data_list = raw_data["Activities"]
                elif "List" in raw_data: data_list = raw_data["List"]
            elif isinstance(raw_data, list):
                data_list = raw_data
                
            if not data_list:
                print("   -> Veri yok.")
                return

            self.process_data_list(device, data_list)

        except Exception as e:
            print(f"   ❌ Kritik Hata: {e}")

    def process_data_list(self, device, data_list):
        count_new = 0
        
        for item in data_list:
            start_str = item.get("ActivityStart")
            duration = item.get("Duration", 0)
            activity_val = item.get("Activity", 0) 

            if not start_str: continue
            
            try:
                start_ts = datetime.fromisoformat(str(start_str).split('.')[0])
            except:
                continue

            # Sınıflandırma
            info = classify_event(duration, activity_val)
            
            # DB Kontrolü
            exists = self.db.query(UtilizationEvent).filter(
                UtilizationEvent.device_id == device.device_id,
                UtilizationEvent.start_time == start_ts
            ).first()

            if not exists:
                end_ts = start_ts + timedelta(seconds=duration)
                
                log = UtilizationEvent(
                    device_id=device.device_id,
                    start_time=start_ts,
                    end_time=end_ts,
                    duration_sec=duration,
                    category=info["cat"],
                    color_code=info["color"],
                    is_burst=info["is_burst"],
                    raw_activity=info["raw"]
                )
                self.db.add(log)
                count_new += 1
        
                # --- ALARM KONTROL NOKTASI ---
                if info["raw"] == 1:
                    # 1. Kullanım Hatası (Uç Şişirme vb.)
                    check_utilization_alarm(device.device_id, duration, end_ts)

                    # 2. Mesai Dışı Çalışma Kontrolü
                    check_work_hours_alarm(device.device_id, start_ts)
                # -----------------------------
                
        try:
            self.db.commit()
            if count_new > 0:
                print(f"   ✅ {count_new} yeni kayıt eklendi.")
        except Exception as e:
            self.db.rollback()
            print(f"   ⚠️ DB Kayıt Hatası: {e}")

    def run(self):
        devices = self.db.query(Device).filter(Device.is_active == True).all()
        print(f"Toplam {len(devices)} aktif cihaz için tarama başlıyor...")
        for dev in devices:
            self.sync_device_daily(dev)
        self.db.close()

if __name__ == "__main__":
    syncer = UtilizationSyncSmart()
    if syncer.login():
        syncer.run()