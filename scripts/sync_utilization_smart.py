import sys
import os
import requests
import json
from datetime import datetime, timedelta
import time
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from backend.models import Device, UtilizationEvent
from backend.database import SessionLocal

# --- AYARLAR ---
API_BASE_URL = "https://api.trusted.dk/api"
API_USERNAME = "s.ozsarac@hkm.com.tr"
API_PASSWORD = "Solid_2023"

# Başlangıç Tarihi (Verilerin başladığı yıl)
START_YEAR = 2024
START_MONTH = 1

# RENK HARİTASI
COLOR_MAP = {
    "breaker tool good": "#00ff00",       # YEŞİL
    "breaker tool in danger": "#ffae00",  # TURUNCU
    "mushrooming (41-60)": "#ff0000",     # KIRMIZI
    "mushrooming, training": "#9900ff",   # MOR
    "Transport": "#000000"                # SİYAH
}

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
        except Exception as e:
            print(f"❌ Giriş Hatası: {e}")
            return False

    def sync_device_daily(self, device):
        print(f"\n🔨 {device.unit_name} ({device.device_id}) için Hassas Tarama (Günlük)...")
        
        # Başlangıç: 1 Ocak 2024
        current_date = datetime(START_YEAR, START_MONTH, 1)
        # Bitiş: Bugün (Şimdi)
        end_date_limit = datetime.utcnow()
        
        total_added_device = 0
        
        # GÜNLÜK DÖNGÜ (Limit sorununu çözer)
        while current_date < end_date_limit:
            next_date = current_date + timedelta(days=1) # Sadece 1 gün ileri git
            
            s_str = current_date.strftime("%Y-%m-%dT%H:%M:%S")
            e_str = next_date.strftime("%Y-%m-%dT%H:%M:%S")
            
            # API İsteği (1 Günlük Veri)
            url = f"{API_BASE_URL}/Utilization/GetUnit"
            params = {
                "SerialNumber": device.device_id,
                "AfterDate": s_str,
                "BeforeDate": e_str,
                "Count": 10000 # Bir günde 10.000 kayıt olması imkansıza yakın
            }
            
            try:
                resp = self.session.get(url, params=params)
                if resp.status_code == 200:
                    raw_data = resp.json()
                    data_list = []
                    
                    if isinstance(raw_data, dict):
                        if "Activities" in raw_data: data_list = raw_data["Activities"]
                        else:
                            for key in ["Items", "List", "Data", "Result"]:
                                if key in raw_data: data_list = raw_data[key]; break
                    elif isinstance(raw_data, list):
                        data_list = raw_data
                    
                    if data_list:
                        added_count = self.process_data_list(device, data_list)
                        total_added_device += added_count
                        # Sadece veri varsa ekrana bas, kalabalık yapmasın
                        if added_count > 0:
                            print(f"   📅 {current_date.date()}: {len(data_list)} olay bulundu -> {added_count} yeni eklendi.")
                
                # API Limit aşımını önlemek için çok kısa bekleme
                # time.sleep(0.05) 

            except Exception as e:
                print(f" ❌ Hata ({current_date.date()}): {e}")

            # Bir sonraki güne geç
            current_date = next_date

        print(f"   🏁 {device.unit_name} için toplam {total_added_device} yeni kayıt eklendi.")

    def process_data_list(self, device, data_list):
        count = 0
        # Toplu Ekleme (Bulk Insert) için liste
        logs_to_add = []
        
        for item in data_list:
            start_str = item.get("ActivityStart") or item.get("UsageStartUTC") or item.get("Start")
            duration = item.get("Duration") or item.get("UsageDurationSeconds") or item.get("DurationSeconds") or 0
            cat_name = item.get("Category") or item.get("ActivityType") or item.get("Name") or "Unknown"
            is_burst = item.get("IsBurst", True)

            if not start_str: continue
            
            # Tarih formatı temizliği
            start_str = str(start_str).split('.')[0]
            try:
                start_ts = datetime.fromisoformat(start_str)
            except:
                continue

            # Basit kontrol: Eğer duration 0 ise ve kategori "Transport" değilse kaydetme (Gürültü verisi olabilir)
            # if duration == 0 and "Transport" not in cat_name: continue

            # Hız için DB sorgusunu atlıyoruz, try-except ile unique constraint'e güveneceğiz 
            # ya da burada basitçe ekliyoruz. (Unique constraint varsa patlar, yoksa çift ekler)
            # En temiz yöntem: Önce ekle, sonra commit ederken hata vereni atla (fakat yavaş olur).
            # Şimdilik DB'de 'exists' kontrolünü yapalım ama hızlı olsun.
            
            # Renk
            color = "#808080"
            for key, val in COLOR_MAP.items():
                if key.lower() in str(cat_name).lower(): color = val; break

            # Python tarafında kontrol (Performans için DB'ye her satırda gitmek yerine)
            # Not: En sağlamı DB'ye sormaktır, şimdilik böyle devam edelim.
            exists = self.db.query(UtilizationEvent.id).filter(
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
                    category=str(cat_name),
                    color_code=color,
                    is_burst=is_burst
                )
                self.db.add(log)
                count += 1
        
        if count > 0:
            try:
                self.db.commit()
            except Exception as e:
                self.db.rollback()
                print(f"   ⚠️ Kayıt hatası (Muhtemelen çift kayıt): {e}")
        
        return count

    def run(self):
        devices = self.db.query(Device).filter(Device.is_active == True).all()
        for dev in devices:
            self.sync_device_daily(dev)
        self.db.close()

if __name__ == "__main__":
    syncer = UtilizationSyncSmart()
    if syncer.login():
        syncer.run()