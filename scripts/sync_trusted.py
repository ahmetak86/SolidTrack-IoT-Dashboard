# scripts/sync_trusted.py (FULL VERSİYON: AUTO GROUP DISCOVERY + USER SYNC + ICON + GEOFENCE + OWNER PROTECTION)
import sys
import os
import requests
import json
import math
from datetime import datetime
import time

# Proje ana dizinini path'e ekle
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.database import SessionLocal, create_alarm, get_password_hash, get_active_geofence_alarm, resolve_geofence_alarm
from backend.models import User, Device, TelemetryLog, GeoSite
from backend.alarm_engine import check_telemetry_alarms, check_maintenance_alarms

# --- AYARLAR ---
API_BASE_URL = "https://api.trusted.dk/api"
API_USERNAME = "s.ozsarac@hkm.com.tr"  
API_PASSWORD = "Solid_2023"
DEFAULT_LOCAL_PASSWORD = "123456" 
DEFAULT_ADMIN_USER = "s.ozsarac" # Yeni keşfedilen cihazlar ilk buna düşer

# --- YARDIMCI: HARİTA MESAFE HESABI (Haversine) ---
def calculate_distance(lat1, lon1, lat2, lon2):
    R = 6371000 # Dünya yarıçapı (metre)
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c # Metre cinsinden mesafe

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

    def fetch_all_group_ids(self):
        """
        [YENİ] API'deki 'Hierarchy' metodunu kullanarak ana hesap altındaki
        TÜM alt grupları (Children) otomatik bulur ve listeler.
        """
        print("🌳 Grup Ağacı Taranıyor (Hierarchy API)...")
        url = f"{API_BASE_URL}/Groups/Hierarchy"
        
        all_ids = []
        try:
            resp = self.session.get(url)
            if resp.status_code == 200:
                data = resp.json()
                
                # Recursive fonksiyon: Ağacın dallarında gezer
                def extract_ids(node):
                    if not node: return
                    # Mevcut düğümün ID'sini al
                    if "Id" in node:
                        all_ids.append(node["Id"])
                    
                    # Varsa çocuklarını da gez (Children)
                    children = node.get("Children", [])
                    if children:
                        for child in children:
                            extract_ids(child)

                # API tek bir root obje mi yoksa liste mi dönüyor kontrol et
                if isinstance(data, list):
                    for item in data: extract_ids(item)
                else:
                    extract_ids(data)
                
                # ID'leri tekrarsız (unique) yap ve sırala
                unique_ids = sorted(list(set(all_ids)))
                print(f"✅ Toplam {len(unique_ids)} adet grup keşfedildi: {unique_ids}")
                return unique_ids
            else:
                print(f"⚠️ Grup Hiyerarşisi çekilemedi: {resp.status_code}")
                # Hata olursa varsayılan olarak ana grubu dön (Fallback)
                return [7153] 
        except Exception as e:
            print(f"❌ Grup Tarama Hatası: {e}")
            return [7153]

    def sync_users(self):
        """
        Kullanıcıları Senkronize Et.
        """
        # Not: Bu fonksiyon şu an main bloğunda aktif değil ama 
        # manuel tetikleme ihtimaline karşı kodda tutuluyor.
        # Kullanıcılar artık veritabanında yönetildiği için burası sadece referans.
        print("\n👤 Kullanıcı Senkronizasyonu (Trusted -> DB)...")
        
        # Ana grup (7153) üzerindeki kullanıcıları çeker
        url = f"{API_BASE_URL}/User?userGroupid=7153"
        resp = self.session.get(url)
        if resp.status_code != 200: return

        users_data = resp.json()
        if isinstance(users_data, dict): users_data = [users_data]

        for u_data in users_data:
            t_login = u_data.get("Login") or u_data.get("UserName")
            if not t_login: continue

            existing = self.db.query(User).filter(User.username == t_login).first()
            if not existing:
                print(f"   -> Yeni Kullanıcı Bulundu: {t_login}")
                # Otomatik ekleme yaparken şifreyi hash'leyerek ekliyoruz
                self.db.add(User(
                    id=t_login, 
                    username=t_login, 
                    email=f"{t_login}@hkm.local",
                    full_name=u_data.get("Name"), 
                    password_hash=get_password_hash(DEFAULT_LOCAL_PASSWORD),
                    role="User",
                    company_name="HKM Trusted Sync",
                    trusted_group_id=7153 
                ))
        self.db.commit()

    def determine_profile_and_icon(self, unit_name):
        """İkon Belirleme Mantığı"""
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

    def check_geofence_for_device(self, device, lat, lon):
        """
        AKILLI GEOFENCE KONTROLÜ (SPAM ENGELLEYİCİ)
        """
        if not device.geosites:
            return

        for site in device.geosites:
            # Alarmı kapalı şantiyeleri geç
            if not site.auto_enable_alarms:
                continue

            # Mesafe Ölç
            dist = calculate_distance(lat, lon, site.latitude, site.longitude)
            
            # Tolerans (GPS sapması için 50m ekleyelim)
            limit = site.radius_meters + 50 
            
            # DURUM 1: CİHAZ DIŞARIDA! (İHLAL VAR)
            if dist > limit:
                # Önce kontrol et: Zaten bu ihlal için alarm çalıyor mu?
                existing_alarm = get_active_geofence_alarm(device.device_id, site.name)
                
                fark = int(dist - site.radius_meters)
                msg = f"{device.unit_name}, '{site.name}' dışına çıktı! (Fark: {fark}m)"

                if existing_alarm:
                    # ZATEN ALARM VAR -> Sadece veritabanında güncelle (Yeni satır ekleme!)
                    # (İstersen burada alarmın değerini güncelleyebilirsin ama DB session gerektirir.
                    # Şimdilik "Zaten var" diyip pas geçiyoruz, böylece spam olmuyor.)
                    print(f"      ℹ️ Aktif Alarm Mevcut: {site.name} (Spam Engellendi)")
                else:
                    # ALARM YOK -> Yeni Alarm Oluştur
                    print(f"      🚨 YENİ GEOFENCE İHLALİ: {msg}")
                    create_alarm(
                        device_id=device.device_id,
                        type="Geofence",
                        severity="Critical",
                        value=f"{int(dist)}m Dışarıda",
                        desc=msg
                    )

            # DURUM 2: CİHAZ İÇERİDE (GÜVENLİ)
            else:
                # Eğer önceden kalma açık bir alarm varsa, onu "ÇÖZÜLDÜ" olarak kapat.
                resolved = resolve_geofence_alarm(device.device_id, site.name)
                if resolved:
                    print(f"      ✅ Alarm Otomatik Kapatıldı: {device.unit_name} -> {site.name} içine girdi.")

    def sync_fleet_and_sensors(self):
        # 1. ÖNCE OTOMATİK OLARAK TÜM GRUPLARI BUL
        target_groups = self.fetch_all_group_ids()
        
        print(f"\n🚜 FİLO VE SENSÖR SENKRONİZASYONU ({len(target_groups)} Grup Taranacak)...")
        
        added_devices = 0
        updated_devices = 0

        # 2. BULUNAN HER GRUBU DÖNGÜ İLE TARA
        for group_id in target_groups:
            # print(f"   📡 Grup Taranıyor: {group_id} ...")
            url = f"{API_BASE_URL}/Units/GroupCurrentPosition?groupid={group_id}"
            
            try:
                resp = self.session.get(url)
                if resp.status_code != 200: 
                    # print(f"      ⚠️ Grup {group_id} erişilemedi.")
                    continue
                
                raw_list = resp.json()
                if not raw_list:
                    # print("      ℹ️ Cihaz yok.")
                    continue

                for item in raw_list:
                    unit_info = item.get("Unit", {})
                    pos_info = item.get("CurrentPosition", {})
                    serial_no = unit_info.get("SerialNumber")
                    
                    if not serial_no: continue
                    serial_no = str(serial_no)
                    unit_name = unit_info.get("UnitName", f"Cihaz-{serial_no}")
                    
                    # 3. Sensör Verisini Çek
                    sensor_data = self.get_latest_sensor_data(serial_no)
                    
                    # Verileri Hazırla
                    battery_val = sensor_data.get("BatteryPercent", 0)
                    temp_val = sensor_data.get("Temperature", 0)
                    shock_val = sensor_data.get("MaxAcceleration", 0)
                    speed_val = pos_info.get("Speed", 0)
                    
                    lat = pos_info.get("Latitude")
                    lon = pos_info.get("Longitude")
                    
                    # --- CİHAZ KAYDI / GÜNCELLEME ---
                    icon, profile_id = self.determine_profile_and_icon(unit_name)
                    address = "Konum Yok"
                    
                    if lat and lon:
                        address = f"{lat:.5f}, {lon:.5f}" 

                    device = self.db.query(Device).filter(Device.device_id == serial_no).first()
                    
                    if not device:
                        # --- YENİ CİHAZ ---
                        # Sahibini varsayılan admin yapıyoruz (Sonra panelden atanacak)
                        print(f"      -> Yeni Keşif: {unit_name} (Grup: {group_id})")
                        device = Device(
                            device_id=serial_no,
                            owner_id=DEFAULT_ADMIN_USER, 
                            unit_name=unit_name,
                            asset_model=unit_info.get("UnitTypeName", "T7"),
                            icon_type=icon,
                            profile_id=profile_id,
                            address=address,
                            is_active=True
                        )
                        if lat and lon:
                            device.latitude = lat
                            device.longitude = lon
                        
                        self.db.add(device)
                        added_devices += 1
                    else:
                        # --- MEVCUT CİHAZ ---
                        # DİKKAT: owner_id'yi ELLEMEMELİYİZ! 
                        device.unit_name = unit_name
                        if lat and lon:
                            device.latitude = lat
                            device.longitude = lon
                            device.address = address
                        device.icon_type = icon
                        device.profile_id = profile_id 
                        device.is_active = True
                        updated_devices += 1

                    # --- GEOFENCE KONTROLÜ ---
                    if lat and lon:
                        self.check_geofence_for_device(device, lat, lon)

                    # --- LOG KAYDI (Telemetri) ---
                    if lat:
                        ts_str = pos_info.get("Timestamp")
                        try: ts = datetime.fromisoformat(ts_str) if ts_str else datetime.utcnow()
                        except: ts = datetime.utcnow()

                        log_id = f"LOG_{serial_no}_{int(ts.timestamp())}"
                        
                        if not self.db.query(TelemetryLog).filter(TelemetryLog.log_id == log_id).first():
                            self.db.add(TelemetryLog(
                                log_id=log_id, 
                                device_id=serial_no, 
                                timestamp=ts,
                                latitude=lat, 
                                longitude=lon,
                                speed_kmh=speed_val, 
                                battery_pct=battery_val, 
                                temp_c=temp_val,
                                max_shock_g=shock_val
                            ))

                            # --- ALARMLAR ---
                            check_telemetry_alarms(
                                device_id=serial_no,
                                battery_pct=battery_val,
                                speed_kmh=speed_val,
                                shock_g=shock_val, 
                                timestamp=ts
                            )

                            current_hours = unit_info.get("TotalPowerOnTimerGPS", 0.0) 
                            if current_hours:
                                 check_maintenance_alarms(serial_no, float(current_hours))
            except Exception as e:
                print(f"      ❌ Grup tarama hatası ({group_id}): {e}")
        
        self.db.commit()
        print(f"✅ Tamamlandı: {added_devices} yeni, {updated_devices} güncellendi.")

    def close(self):
        self.db.close()

if __name__ == "__main__":
    c = TrustedClient()
    if c.login():
        # DİKKAT: sync_users'ı kapattık ki manuel atamaları ezmesin.
        # client.sync_users() 
        c.sync_fleet_and_sensors()
    c.close()