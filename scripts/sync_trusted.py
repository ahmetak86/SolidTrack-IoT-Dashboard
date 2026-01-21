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
API_PASSWORD = "Solid_2023"
GROUP_ID = 7153 
DEFAULT_LOCAL_PASSWORD = "123456" 

class TrustedClient:
    def __init__(self):
        self.token = None
        self.session = requests.Session()
        self.db = SessionLocal()

    def login(self):
        print(f"🔑 Trusted API'ye giriş yapılıyor: {API_USERNAME}")
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

    def get_latest_sensor_data(self, serial_no):
        """
        Cihazın son sensör verilerini (Pil, Isı) çeker.
        """
        try:
            url = f"{API_BASE_URL}/SensorData/GetLatest?serialNumber={serial_no}&count=1"
            resp = self.session.get(url)
            if resp.status_code == 200:
                data = resp.json()
                if data and isinstance(data, list) and len(data) > 0:
                    return data[0] # En son paketi dön
        except Exception as e:
            print(f"   ⚠️ Sensör hatası ({serial_no}): {e}")
        return {}

    def sync_users(self):
        print("\n👤 Kullanıcı Senkronizasyonu...")
        url = f"{API_BASE_URL}/User?userGroupid={GROUP_ID}"
        resp = self.session.get(url)
        if resp.status_code != 200: return

        users_data = resp.json()
        if isinstance(users_data, dict): users_data = [users_data]

        for u_data in users_data:
            t_login = u_data.get("Login") or u_data.get("UserName")
            if not t_login: continue

            existing = self.db.query(User).filter(User.username == t_login).first()
            if not existing:
                print(f"   -> Yeni Admin: {t_login}")
                self.db.add(User(
                    id=t_login, username=t_login, email=f"{t_login}@hkm.local",
                    full_name=u_data.get("Name"), password_hash=DEFAULT_LOCAL_PASSWORD,
                    role="Admin", company_name="HKM Trusted Sync"
                ))
        self.db.commit()

    def determine_profile_and_icon(self, unit_name):
        name_lower = str(unit_name).lower().replace('İ', 'i').replace('ı', 'i')
        
        breaker_models = [
            "kırıcı", "kirici", "breaker",
            "r50", "r100", "r150", "r200", "r250", "r260", "r300", "r350", "r550", "r750",
            "r250m", "r260m", "r300m", "r350m", "r550m", "r750m",
            "rs50", "rs100", "rs150", "rs200", "rs250", "rs260", "rs300", "rs350", "rs550", "rs750",
            "rs250m", "rs260m", "rs300m", "rs350m", "rs550m", "rs750m",
            "g10", "g12", "g15", "g20", "g30", "g40", "g60", "g90", 
            "g120", "g130", "g160", "g170", "g190", "g210", "g230", "g270", "g280"
        ]
        
        if any(model in name_lower for model in breaker_models):
            return "breaker", "PROF_BREAKER"
        elif "eks" in name_lower or "exc" in name_lower:
            return "excavator", "PROF_EXCAVATOR"
        elif "kamyon" in name_lower or "truck" in name_lower:
            return "truck", "PROF_TRANSPORT"
        elif "mikser" in name_lower or "mix" in name_lower:
            return "mixer", "PROF_TRANSPORT"
        else:
            return "truck", "PROF_TRANSPORT"

    def sync_fleet_and_sensors(self):
        print("\n🚜 Filo ve Sensör (Pil) Senkronizasyonu...")
        
        # 1. Konumları Çek
        url = f"{API_BASE_URL}/Units/GroupCurrentPosition?groupid={GROUP_ID}"
        resp = self.session.get(url)
        if resp.status_code != 200: return

        raw_list = resp.json()
        if not raw_list: return

        added_devices = 0
        updated_devices = 0

        for item in raw_list:
            unit_info = item.get("Unit", {})
            pos_info = item.get("CurrentPosition", {})
            serial_no = unit_info.get("SerialNumber")
            
            if not serial_no: continue
            serial_no = str(serial_no)
            unit_name = unit_info.get("UnitName", f"Cihaz-{serial_no}")
            
            # 2. Sensör Verisini Çek (PİL BURADA!)
            # Her cihaz için API'ye soruyoruz: "Pili kaç?"
            sensor_data = self.get_latest_sensor_data(serial_no)
            
            # Pil ve Isı verisini al (Yoksa 0)
            battery_val = sensor_data.get("BatteryPercent", 0)
            temp_val = sensor_data.get("Temperature", 0)
            
            # --- CİHAZ KAYDI ---
            icon, profile_id = self.determine_profile_and_icon(unit_name)
            address = "Konum Yok"
            if pos_info and pos_info.get("Latitude"):
                address = f"{pos_info.get('Latitude')}, {pos_info.get('Longitude')}"

            device = self.db.query(Device).filter(Device.device_id == serial_no).first()
            
            if not device:
                print(f"   -> Yeni: {unit_name} (Pil: %{battery_val})")
                device = Device(
                    device_id=serial_no,
                    owner_id=API_USERNAME, 
                    unit_name=unit_name,
                    asset_model=unit_info.get("UnitTypeName", "T7"),
                    icon_type=icon,
                    profile_id=profile_id,
                    address=address,
                    is_active=True
                )
                self.db.add(device)
                added_devices += 1
            else:
                device.unit_name = unit_name
                device.address = address
                device.icon_type = icon
                device.profile_id = profile_id 
                device.is_active = True
                updated_devices += 1

            # --- LOG KAYDI (Telemetri) ---
            if pos_info and pos_info.get("Latitude"):
                ts_str = pos_info.get("Timestamp")
                try: ts = datetime.fromisoformat(ts_str) if ts_str else datetime.utcnow()
                except: ts = datetime.utcnow()

                log_id = f"LOG_{serial_no}_{int(ts.timestamp())}"
                
                # Eğer bu log daha önce kaydedilmemişse kaydet
                if not self.db.query(TelemetryLog).filter(TelemetryLog.log_id == log_id).first():
                    self.db.add(TelemetryLog(
                        log_id=log_id, 
                        device_id=serial_no, 
                        timestamp=ts,
                        latitude=pos_info.get("Latitude"), 
                        longitude=pos_info.get("Longitude"),
                        speed_kmh=pos_info.get("Speed", 0), 
                        
                        # İŞTE BURASI: Gerçek Pil Verisini Yazıyoruz!
                        battery_pct=battery_val, 
                        temp_c=temp_val
                    ))
        
        self.db.commit()
        print(f"✅ Tamamlandı: {added_devices} yeni, {updated_devices} güncellendi.")

    def close(self):
        self.db.close()

if __name__ == "__main__":
    client = TrustedClient()
    if client.login():
        client.sync_users()
        client.sync_fleet_and_sensors()
    client.close()