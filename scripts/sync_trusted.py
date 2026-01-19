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
API_PASSWORD = "Solid_2023" # <--- ŞİFRENİ BURAYA YAZMAYI UNUTMA
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
        """
        İsme göre İKON (Dosya adı) ve PROFİL belirler.
        Excel Listesi ve PDF'teki dosya isimleri baz alınmıştır.
        """
        name_lower = str(unit_name).lower().replace('İ', 'i').replace('ı', 'i')
        
        # --- HKM Kırıcı Modelleri (Tam Liste) ---
        breaker_models = [
            "kırıcı", "kirici", "breaker",
            "r50", "r100", "r150", "r200", "r250", "r260", "r300", "r350", "r550", "r750",
            "r250m", "r260m", "r300m", "r350m", "r550m", "r750m",
            "rs50", "rs100", "rs150", "rs200", "rs250", "rs260", "rs300", "rs350", "rs550", "rs750",
            "rs250m", "rs260m", "rs300m", "rs350m", "rs550m", "rs750m",
            "g10", "g12", "g15", "g20", "g30", "g40", "g60", "g90", 
            "g120", "g130", "g160", "g170", "g190", "g210", "g230", "g270", "g280"
        ]
        
        # --- İKON EŞLEŞTİRME (Dosya adlarıyla aynı olmalı) ---
        
        # 1. KIRICI GRUBU
        if any(model in name_lower for model in breaker_models):
            # Dosya adı: breaker.png
            return "breaker", "PROF_BREAKER"
        
        # 2. EKSKAVATÖR GRUBU
        elif "eks" in name_lower or "exc" in name_lower:
            # Dosya adı: excavator.png
            return "excavator", "PROF_EXCAVATOR"
            
        # 3. KAMYON / NAKLİYE GRUBU
        elif "kamyon" in name_lower or "truck" in name_lower:
            # Dosya adı: truck.png
            return "truck", "PROF_TRANSPORT"
            
        # 4. MİKSER GRUBU
        elif "mikser" in name_lower or "mix" in name_lower:
            # PDF'te görünen dosya adı: mixer.png (concrete_mixer değil)
            return "mixer", "PROF_TRANSPORT"
        
        # 5. DİĞERLERİ (Varsayılan)
        else:
            return "truck", "PROF_TRANSPORT"

    def sync_fleet_and_sensors(self):
        print("\n🚜 Filo Senkronizasyonu (V3 - İkon Düzeltme)...")
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
            
            # Profil ve İkon Seçimi
            icon, profile_id = self.determine_profile_and_icon(unit_name)
            
            # Adres
            address = "Konum Yok"
            if pos_info and pos_info.get("Latitude"):
                address = f"{pos_info.get('Latitude')}, {pos_info.get('Longitude')}"

            device = self.db.query(Device).filter(Device.device_id == serial_no).first()
            
            if not device:
                print(f"   -> Yeni Cihaz: {unit_name} | İkon: {icon}.png")
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
                # İkon veya Profil değişmişse güncelle
                if device.icon_type != icon or device.profile_id != profile_id:
                     print(f"   -> GÜNCELLENDİ: {unit_name} | İkon: {device.icon_type}->{icon} | Profil: {device.profile_id}->{profile_id}")
                     updated_devices += 1
                
                device.unit_name = unit_name
                device.address = address
                device.icon_type = icon
                device.profile_id = profile_id 
                device.is_active = True

            # Basit Log
            if pos_info and pos_info.get("Latitude"):
                ts_str = pos_info.get("Timestamp")
                try: ts = datetime.fromisoformat(ts_str) if ts_str else datetime.utcnow()
                except: ts = datetime.utcnow()

                log_id = f"LOG_{serial_no}_{int(ts.timestamp())}"
                if not self.db.query(TelemetryLog).filter(TelemetryLog.log_id == log_id).first():
                    self.db.add(TelemetryLog(
                        log_id=log_id, device_id=serial_no, timestamp=ts,
                        latitude=pos_info.get("Latitude"), longitude=pos_info.get("Longitude"),
                        speed_kmh=pos_info.get("Speed", 0), battery_pct=0, temp_c=0
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