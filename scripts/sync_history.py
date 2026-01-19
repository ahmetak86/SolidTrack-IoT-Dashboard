import sys
import os
import requests
import json
from datetime import datetime, timedelta
import time

# Proje ana dizinini path'e ekle
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.database import SessionLocal
from backend.models import User, Device, TelemetryLog

# --- AYARLAR ---
API_BASE_URL = "https://api.trusted.dk/api"
API_USERNAME = "s.ozsarac@hkm.com.tr"
API_PASSWORD = "Solid_2023" 
START_YEAR = 2020 # <-- DEĞİŞİKLİK: Sonsuz geçmiş için başlangıç yılı

class HistoryFetcher:
    def __init__(self):
        self.token = None
        self.session = requests.Session()
        self.db = SessionLocal()

    def login(self):
        print(f"🔑 Trusted API'ye giriş yapılıyor...")
        payload = {"grant_type": "password", "username": API_USERNAME, "password": API_PASSWORD}
        try:
            response = self.session.post("https://api.trusted.dk/token", data=payload)
            if response.status_code == 200:
                data = response.json()
                self.token = data.get("access_token")
                self.session.headers.update({"Authorization": f"Bearer {self.token}"})
                print("✅ Token alındı.")
                return True
            else:
                print(f"❌ Giriş Hatası: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Bağlantı Hatası: {e}")
            return False

    def fetch_logs_for_device(self, device_serial, start_date, end_date):
        print(f"⏳ Veri Çekiliyor: {device_serial} | {start_date.date()} -> {end_date.date()}")

        url = f"{API_BASE_URL}/Positions/Get"
        
        # Count'u yüksek tutuyoruz (Sonsuz geçmiş için)
        params = {
            "SerialNumber": device_serial,
            "AfterDate": start_date.strftime("%Y-%m-%dT%H:%M:%S"),
            "BeforeDate": end_date.strftime("%Y-%m-%dT%H:%M:%S"),
            "Count": 100000, 
            "SortDescending": "false" 
        }
        
        try:
            resp = self.session.get(url, params=params)
            
            if resp.status_code != 200:
                print(f"❌ API Hatası ({resp.status_code}): {resp.text}")
                return

            logs = resp.json()
            if not logs:
                print("   -> Bu tarih aralığında hareket yok.")
                return

            print(f"   -> {len(logs)} adet konum verisi yakalandı. Veritabanına işleniyor...")

            added_count = 0
            for log in logs:
                ts_str = log.get("Timestamp")
                if not ts_str: continue

                try:
                    ts = datetime.fromisoformat(ts_str)
                except:
                    continue

                lat = log.get("Latitude")
                lon = log.get("Longitude")
                
                # Koordinat kontrolü (0.0 veya None ise alma)
                if not lat or not lon: continue

                log_id = f"LOG_{device_serial}_{int(ts.timestamp())}"
                
                if not self.db.query(TelemetryLog).filter(TelemetryLog.log_id == log_id).first():
                    new_log = TelemetryLog(
                        log_id=log_id,
                        device_id=str(device_serial),
                        timestamp=ts,
                        latitude=lat,
                        longitude=lon,
                        speed_kmh=log.get("Speed", 0),
                        battery_pct=0, 
                        temp_c=0
                    )
                    self.db.add(new_log)
                    added_count += 1
            
            self.db.commit()
            print(f"   ✅ {added_count} yeni nokta başarıyla kaydedildi.")

        except Exception as e:
            print(f"   ❌ Kritik Hata: {e}")

    def sync_all_history(self):
        devices = self.db.query(Device).filter(Device.is_active == True).all()
        
        end_date = datetime.now()
        # Başlangıç tarihini 2020 yapıyoruz
        start_date = datetime(START_YEAR, 1, 1)
        
        print(f"\n🚜 FİLO GEÇMİŞİ SENKRONİZASYONU ({START_YEAR}'den Bugüne)")
        
        for dev in devices:
            self.fetch_logs_for_device(dev.device_id, start_date, end_date)

    def close(self):
        self.db.close()

if __name__ == "__main__":
    fetcher = HistoryFetcher()
    if fetcher.login():
        fetcher.sync_all_history()
    fetcher.close()