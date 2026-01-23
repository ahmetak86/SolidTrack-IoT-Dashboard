import sys
import os
import requests
import json
from datetime import datetime, timedelta, timezone
import time

# Proje dizinini bul
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from backend.models import Device, UtilizationEvent
from backend.database import SessionLocal

# --- AYARLAR ---
API_BASE_URL = "https://api.trusted.dk/api"
API_USERNAME = "s.ozsarac@hkm.com.tr"
API_PASSWORD = "Solid_2023"

# TARİHÇE BAŞLANGICI
START_DATE_HISTORY = datetime(2023, 1, 1)

# --- SINIFLANDIRMA FONKSİYONU ---
def classify_event(duration, activity_val):
    is_active = str(activity_val).lower() in ['true', '1']
    
    if not is_active:
        return {"cat": "Boşta Bekleme (Idle)", "color": "#E0E0E0", "is_burst": False, "raw": 0}

    if duration > 180:
        return {"cat": "Nakliye / Uzun Hareket", "color": "#000000", "is_burst": True, "raw": 1}
    elif duration <= 20:
        return {"cat": "İdeal Çalışma (0-20s)", "color": "#00C853", "is_burst": True, "raw": 1}
    elif duration <= 40:
        return {"cat": "Riskli Çalışma (21-40s)", "color": "#FFAB00", "is_burst": True, "raw": 1}
    elif duration <= 80:
        return {"cat": "Uç Şişirme Riski (41-80s)", "color": "#D50000", "is_burst": True, "raw": 1}
    else:
        return {"cat": "Operatör Hatası (81-180s)", "color": "#AA00FF", "is_burst": True, "raw": 1}

class HistoricalSyncV2:
    def __init__(self):
        self.db = SessionLocal()
        self.session = requests.Session()
        self.token = None

    def login(self):
        print("🔑 Token alınıyor...")
        try:
            payload = {'grant_type': 'password', 'username': API_USERNAME, 'password': API_PASSWORD}
            resp = self.session.post("https://api.trusted.dk/token", data=payload)
            if resp.status_code == 200:
                self.token = resp.json()['access_token']
                self.session.headers.update({'Authorization': f'Bearer {self.token}'})
                print("✅ Token alındı.")
                return True
            else:
                print(f"❌ Giriş Başarısız: {resp.text}")
                return False
        except Exception as e:
            print(f"💥 Bağlantı Hatası: {e}")
            return False

    def fetch_data(self, device, start_dt, end_dt):
        """Belirli aralık için API isteği atar"""
        s_date = start_dt.strftime("%Y-%m-%dT%H:%M:%S")
        e_date = end_dt.strftime("%Y-%m-%dT%H:%M:%S")
        
        url = f"{API_BASE_URL}/Utilization/GetUnit"
        params = {
            "SerialNumber": device.device_id,
            "AfterDate": s_date,
            "BeforeDate": e_date,
            "Count": 10000, 
            "SeparateByDay": "false",
            "ActivityFilter": "All"
        }
        
        try:
            resp = self.session.get(url, params=params)
            if resp.status_code == 200:
                raw_data = resp.json()
                if isinstance(raw_data, dict):
                    if "Activities" in raw_data: return raw_data["Activities"]
                    elif "List" in raw_data: return raw_data["List"]
                elif isinstance(raw_data, list):
                    return raw_data
            return []
        except:
            return []

    def sync_device_history(self, device):
        print(f"\n🚜 {device.unit_name} ({device.device_id}) için GEÇMİŞ Veri Taranıyor...")
        
        current_cursor = START_DATE_HISTORY
        # Deprecation uyarısını düzeltmek için timezone duyarlı yapıyoruz
        now = datetime.now(timezone.utc).replace(tzinfo=None) # Basit kıyaslama için tz siliyoruz
        
        total_added_device = 0
        
        while current_cursor < now:
            # Varsayılan: 7 Günlük periyot
            next_cursor = current_cursor + timedelta(days=7)
            if next_cursor > now: next_cursor = now
            
            # Veriyi Çek
            data_list = self.fetch_data(device, current_cursor, next_cursor)
            count = len(data_list)
            
            # BİLGİLENDİRME YAZISI (Senin istediğin detay)
            status_msg = f"   ⏳ {current_cursor.strftime('%Y-%m-%d')} -> {next_cursor.strftime('%Y-%m-%d')} | Veri: {count}/10000"
            
            # KONTROL MEKANİZMASI: Limit Doldu mu?
            if count >= 10000:
                print(f"{status_msg} ⚠️ LİMİT DOLDU! GÜNLÜK TARAMAYA GEÇİLİYOR...")
                # Bu 7 günü gün gün tara (Detaylı tarama)
                sub_added = self.drill_down_daily(device, current_cursor, next_cursor)
                total_added_device += sub_added
            else:
                # Limit dolmadıysa normal işle
                print(status_msg)
                added = self.process_batch(device, data_list)
                total_added_device += added

            current_cursor = next_cursor

        print(f"\n   ✅ {device.unit_name} tamamlandı. Toplam {total_added_device} kayıt eklendi.")

    def drill_down_daily(self, device, start_dt, end_dt):
        """Limit aşılırsa o haftayı gün gün tarar"""
        temp_cursor = start_dt
        total_sub = 0
        while temp_cursor < end_dt:
            next_temp = temp_cursor + timedelta(days=1)
            data_list = self.fetch_data(device, temp_cursor, next_temp)
            print(f"      ↳ Günlük Detay ({temp_cursor.strftime('%Y-%m-%d')}): {len(data_list)} veri")
            total_sub += self.process_batch(device, data_list)
            temp_cursor = next_temp
        return total_sub

    def process_batch(self, device, data_list):
        if not data_list: return 0
        count = 0
        
        # Toplu insert için listede biriktir (Hızlandırma)
        new_logs = []
        
        for item in data_list:
            start_str = item.get("ActivityStart")
            duration = item.get("Duration", 0)
            activity_val = item.get("Activity", 0)

            if not start_str: continue
            
            try:
                # ISO format düzeltme
                clean_str = str(start_str).split('.')[0]
                start_ts = datetime.fromisoformat(clean_str)
            except:
                continue

            # DB Sorgusu (Var mı yok mu?)
            exists = self.db.query(UtilizationEvent.id).filter(
                UtilizationEvent.device_id == device.device_id,
                UtilizationEvent.start_time == start_ts
            ).first()

            if not exists:
                info = classify_event(duration, activity_val)
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
                count += 1
        
        if count > 0:
            try:
                self.db.commit()
            except:
                self.db.rollback()
        
        return count

    def run(self):
        devices = self.db.query(Device).filter(Device.is_active == True).all()
        print(f"Toplam {len(devices)} cihaz için GEÇMİŞ TARAMASI (V2 - GÜVENLİ MOD) başlıyor...")
        for dev in devices:
            self.sync_device_history(dev)
        print("\n🎉 TÜM İŞLEMLER BİTTİ!")
        self.db.close()

if __name__ == "__main__":
    syncer = HistoricalSyncV2()
    if syncer.login():
        syncer.run()