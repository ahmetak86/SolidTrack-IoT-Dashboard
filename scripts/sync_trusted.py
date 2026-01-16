import sys
import os
import requests
import json
from datetime import datetime
import time

# Proje ana dizinini path'e ekle
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.database import SessionLocal
from backend.models import User, Device, TelemetryLog

# --- AYARLAR ---
API_BASE_URL = "https://api.trusted.dk/api"
API_USERNAME = "s.ozsarac@hkm.com.tr"  
API_PASSWORD = "Solid_2023" # <--- ŞİFRENİ YAZMAYI UNUTMA!
GROUP_ID = 7153 
DEFAULT_LOCAL_PASSWORD = "123456" 

class TrustedClient:
    def __init__(self):
        self.token = None
        self.session = requests.Session()
        self.db = SessionLocal()

    def login(self):
        print(f"🔑 Trusted API'ye giriş yapılıyor: {API_USERNAME}")
        payload = {
            "grant_type": "password",
            "username": API_USERNAME,
            "password": API_PASSWORD
        }
        try:
            response = self.session.post("https://api.trusted.dk/token", data=payload)
            if response.status_code == 200:
                data = response.json()
                self.token = data.get("access_token")
                self.session.headers.update({"Authorization": f"Bearer {self.token}"})
                print("✅ Token başarıyla alındı.")
                return True
            else:
                print(f"❌ Giriş Başarısız! Kod: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Bağlantı Hatası: {e}")
            return False

    def sync_users(self):
        print("\n👤 Kullanıcı Senkronizasyonu...")
        url = f"{API_BASE_URL}/User?userGroupid={GROUP_ID}"
        resp = self.session.get(url)
        if resp.status_code != 200: return

        users_data = resp.json()
        if isinstance(users_data, dict): users_data = [users_data]

        count = 0
        for u_data in users_data:
            t_login = u_data.get("Login") or u_data.get("UserName")
            t_email = u_data.get("Email")
            t_name = u_data.get("Name")
            
            if not t_login: continue

            existing_user = self.db.query(User).filter(User.username == t_login).first()
            if not existing_user:
                print(f"   -> Yeni Kullanıcı: {t_login}")
                new_user = User(
                    id=t_login,
                    username=t_login,
                    email=t_email if t_email else f"{t_login}@hkm.local",
                    full_name=t_name,
                    password_hash=DEFAULT_LOCAL_PASSWORD,
                    role="Admin",
                    company_name="HKM Trusted Sync"
                )
                self.db.add(new_user)
                count += 1
        self.db.commit()
        print(f"✅ {count} kullanıcı işlendi.")

    def determine_icon(self, unit_name):
        name_lower = str(unit_name).lower()
        if "kırıcı" in name_lower or "kirici" in name_lower or "breaker" in name_lower: return "hydraulic_breaker"
        if "eks" in name_lower or "exc" in name_lower: return "excavator"
        if "kamyon" in name_lower or "truck" in name_lower: return "truck"
        if "mikser" in name_lower or "mix" in name_lower: return "concrete_mixer"
        return "truck"

    def sync_fleet_and_sensors(self):
        print("\n🚜 Cihaz ve Sensör Verisi Çekiliyor...")
        
        url = f"{API_BASE_URL}/Units/GroupCurrentPosition?groupid={GROUP_ID}"
        resp = self.session.get(url)
        
        if resp.status_code != 200:
            print(f"❌ API Hatası: {resp.status_code}")
            return

        raw_list = resp.json() # Gelen liste
        if not raw_list:
            print("⚠️ Cihaz listesi boş döndü.")
            return

        print(f"   -> API'den {len(raw_list)} adet ham veri paketi geldi.")

        added_devices = 0
        added_logs = 0

        for item in raw_list:
            # --- DÜZELTME BURADA ---
            # Veriler "Unit" ve "CurrentPosition" objelerinin içinde saklı
            unit_info = item.get("Unit", {})
            pos_info = item.get("CurrentPosition", {})

            # 1. Serial Number'ı "Unit" içinden alıyoruz
            serial_no = unit_info.get("SerialNumber")
            
            # Eğer hala yoksa atla
            if not serial_no:
                # Debug için gerekirse açarsın: print("   ⚠️ Seri No bulunamadı, atlanıyor.")
                continue
            
            serial_no = str(serial_no)
            unit_name = unit_info.get("UnitName", f"Cihaz-{serial_no}")
            
            # Veritabanı sorgusu
            device = self.db.query(Device).filter(Device.device_id == serial_no).first()
            icon = self.determine_icon(unit_name)
            
            # Adres Oluşturma
            address = "Konum Verisi Yok"
            if pos_info and pos_info.get("Latitude"):
                lat = pos_info.get("Latitude")
                lon = pos_info.get("Longitude")
                address = f"{lat}, {lon}"

            # 2. Cihazı DB'ye İşle
            if not device:
                print(f"   -> Yeni Cihaz: {unit_name} ({serial_no})")
                device = Device(
                    device_id=serial_no,
                    owner_id=API_USERNAME, 
                    unit_name=unit_name,
                    asset_model=unit_info.get("UnitTypeName", "T7"),
                    icon_type=icon,
                    address=address,
                    is_active=True
                )
                self.db.add(device)
                added_devices += 1
            else:
                # Güncelle
                device.unit_name = unit_name
                device.address = address
                device.icon_type = icon
                device.is_active = True

            # 3. Log Kaydı
            # DİKKAT: Gönderdiğin JSON'da Battery ve Temp "CurrentPosition" içinde yoktu.
            # O yüzden şimdilik sadece GPS ve Hız alıyoruz.
            if pos_info and pos_info.get("Latitude"):
                ts_str = pos_info.get("Timestamp")
                try:
                    ts = datetime.fromisoformat(ts_str) if ts_str else datetime.utcnow()
                except:
                    ts = datetime.utcnow()

                log_id = f"LOG_{serial_no}_{int(ts.timestamp())}"
                existing_log = self.db.query(TelemetryLog).filter(TelemetryLog.log_id == log_id).first()

                if not existing_log:
                    new_log = TelemetryLog(
                        log_id=log_id,
                        device_id=serial_no,
                        timestamp=ts,
                        latitude=pos_info.get("Latitude"),
                        longitude=pos_info.get("Longitude"),
                        speed_kmh=pos_info.get("Speed", 0),
                        # Bu endpointte pil verisi görünmüyor, varsayılan 0 geçiyoruz
                        battery_pct=0, 
                        temp_c=0
                    )
                    self.db.add(new_log)
                    added_logs += 1
        
        self.db.commit()
        print(f"✅ Tamamlandı: {added_devices} yeni cihaz, {added_logs} yeni log eklendi.")

    def close(self):
        self.db.close()

if __name__ == "__main__":
    print("🚀 SolidTrack <-> Trusted Sync v3 (Fix Nested)")
    client = TrustedClient()
    if client.login():
        client.sync_users()
        client.sync_fleet_and_sensors()
    client.close()