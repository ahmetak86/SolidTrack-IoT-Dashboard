import sys
import os
import requests
import json
from datetime import datetime, timedelta
import time

# Proje ana dizinini path'e ekle
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.database import SessionLocal
from backend.models import Device, TelemetryLog

# --- AYARLAR ---
API_BASE_URL = "https://api.trusted.dk/api"
API_USERNAME = "s.ozsarac@hkm.com.tr"
API_PASSWORD = "Solid_2023"
START_YEAR = 2023 # Hangi yıldan itibaren pil verisini düzeltelim?

class BatteryBackfiller:
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

    def backfill_device(self, device_serial):
        print(f"\n🔋 {device_serial} için Pil Geçmişi İndiriliyor...")
        
        # API'den Sensör Verilerini Çek (Tek seferde çok veri almak için tarih aralığı geniş tutulabilir)
        # Not: Trusted API çok fazla veriyi tek seferde vermeyebilir, yıl yıl bölebiliriz ama şimdilik tek atış deneyelim.
        url = f"{API_BASE_URL}/SensorData/Get"
        
        # Son 3 yılı kapsayacak şekilde
        params = {
            "SerialNumber": device_serial,
            "AfterDate": f"{START_YEAR}-01-01T00:00:00",
            "BeforeDate": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
            "Count": 10000, # Maksimum kayıt sayısı
            "SortDescending": "true"
        }
        
        try:
            resp = self.session.get(url, params=params)
            if resp.status_code != 200:
                print(f"   ❌ API Hatası: {resp.status_code}")
                return

            sensors = resp.json()
            if not sensors:
                print("   ⚠️ Bu cihaz için sensör geçmişi yok.")
                return
            
            print(f"   📥 {len(sensors)} adet sensör verisi indirildi. Veritabanı eşleştiriliyor...")
            
            updated_count = 0
            
            # Gelen her sensör verisi için DB'deki en yakın kaydı bul ve güncelle
            for s_data in sensors:
                ts_str = s_data.get("Timestamp")
                bat_val = s_data.get("BatteryPercent")
                
                if not ts_str or bat_val is None: continue
                
                ts = datetime.fromisoformat(ts_str)
                
                # DB'de bu zamana yakın (+- 30 dakika) ve pili 0 olan kaydı bul
                # Tam saniyesi saniyesine tutmayabilir, o yüzden aralık veriyoruz.
                time_margin = timedelta(minutes=30)
                
                log_to_update = self.db.query(TelemetryLog).filter(
                    TelemetryLog.device_id == str(device_serial),
                    TelemetryLog.timestamp >= ts - time_margin,
                    TelemetryLog.timestamp <= ts + time_margin,
                    TelemetryLog.battery_pct == 0 # Sadece boş olanları doldur
                ).first()
                
                if log_to_update:
                    log_to_update.battery_pct = bat_val
                    # Varsa sıcaklığı da güncelleyelim
                    if s_data.get("Temperature"):
                        log_to_update.temp_c = s_data.get("Temperature")
                    
                    updated_count += 1
            
            self.db.commit()
            print(f"   ✅ {updated_count} adet kayıt güncellendi (Pil verisi işlendi).")

        except Exception as e:
            print(f"   ❌ Hata: {e}")

    def run(self):
        devices = self.db.query(Device).filter(Device.is_active == True).all()
        for dev in devices:
            self.backfill_device(dev.device_id)
        
        self.db.close()

if __name__ == "__main__":
    backfiller = BatteryBackfiller()
    if backfiller.login():
        backfiller.run()