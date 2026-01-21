import sys
import os
import requests
import json
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from backend.models import Device, UtilizationEvent
from backend.database import SessionLocal

# --- AYARLAR ---
API_BASE_URL = "https://api.trusted.dk/api"
API_USERNAME = "s.ozsarac@hkm.com.tr"
API_PASSWORD = "Solid_2023"

# RENK HARİTASI (Trusted PDF ile Birebir)
COLOR_MAP = {
    "breaker tool good": "#00ff00",       # YEŞİL
    "breaker tool in danger": "#ffae00",  # TURUNCU
    "mushrooming (41-60)": "#ff0000",     # KIRMIZI
    "mushrooming, training": "#9900ff",   # MOR
    "Transport": "#000000"                # SİYAH
}

class UtilizationSync:
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
        except Exception as e:
            print(f"❌ Giriş Hatası: {e}")
            return False

    def sync_device(self, device):
        print(f"\n🔨 {device.unit_name} ({device.device_id}) verileri çekiliyor...")
        
        # --- DÜZELTME BURADA: 90 gün yerine 3 YIL (1095 Gün) geriye bakıyoruz ---
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=1095) 
        
        url = f"{API_BASE_URL}/Utilization/GetUnit"
        params = {
            "SerialNumber": device.device_id,
            "AfterDate": start_date.strftime("%Y-%m-%dT%H:%M:%S"),
            "BeforeDate": end_date.strftime("%Y-%m-%dT%H:%M:%S"),
            "Count": 10000 # Maksimum limiti artırdık
        }
        
        try:
            resp = self.session.get(url, params=params)
            if resp.status_code != 200: 
                print(f"   ❌ API Hatası: {resp.status_code}")
                return

            raw_data = resp.json()
            data_list = []
            
            # API Dönüş Formatını Yakala
            if isinstance(raw_data, list): data_list = raw_data
            elif isinstance(raw_data, dict):
                for key in ["Items", "List", "Data", "Result"]:
                    if key in raw_data: data_list = raw_data[key]; break
            
            if not data_list:
                print(f"   ⚠️ Veri yok. (Taranan aralık: {start_date.date()} - {end_date.date()})")
                return

            print(f"   📥 {len(data_list)} adet kayıt işleniyor...")
            new_count = 0
            
            for item in data_list:
                cat_name = item.get("Category", "Unknown")
                start_str = item.get("UsageStartUTC")
                duration = item.get("UsageDurationSeconds", 0)
                is_burst = item.get("IsBurst", True) 
                
                if not start_str: continue
                
                # Tarih formatı bazen milisaniyeli gelebilir, düzeltelim
                start_str = start_str.split('.')[0] 
                try:
                    start_ts = datetime.fromisoformat(start_str)
                except:
                    continue # Tarih bozuksa geç

                end_ts = start_ts + timedelta(seconds=duration)
                
                # Renk Bul
                color = "#808080"
                for key, val in COLOR_MAP.items():
                    if key in cat_name: color = val; break
                
                # Çift Kayıt Kontrolü
                exists = self.db.query(UtilizationEvent).filter(
                    UtilizationEvent.device_id == device.device_id,
                    UtilizationEvent.start_time == start_ts
                ).first()
                
                if not exists:
                    log = UtilizationEvent(
                        device_id=device.device_id,
                        start_time=start_ts,
                        end_time=end_ts,
                        duration_sec=duration,
                        category=cat_name,
                        color_code=color,
                        is_burst=is_burst
                    )
                    self.db.add(log)
                    new_count += 1
            
            self.db.commit()
            print(f"   ✅ {new_count} yeni olay eklendi.")

        except Exception as e:
            print(f"   ❌ Hata: {e}")

    def run(self):
        devices = self.db.query(Device).filter(Device.is_active == True).all()
        for dev in devices:
            self.sync_device(dev)
        self.db.close()

if __name__ == "__main__":
    syncer = UtilizationSync()
    if syncer.login():
        syncer.run()