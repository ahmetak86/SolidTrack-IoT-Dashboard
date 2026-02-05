import sys
import os
import logging
import requests
import json
from datetime import datetime, timedelta
import time

# --- YOL AYARLARI ---
# Proje ana dizinini path'e ekle
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.database import SessionLocal
from backend.models import Device, TelemetryLog, UtilizationEvent, User
import backend.trusted_api as api

# --- ALARM MOTORUNU İÇERİ ALIYORUZ (INTEGRATION) ---
# Senin 522 satırlık 'alarm_engine.py' dosyanı buradan çalıştırıyoruz.
from backend.alarm_engine import (
    check_telemetry_alarms, 
    check_geofence_violations, 
    check_utilization_alarm, 
    check_work_hours_alarm,
    check_maintenance_alarms,
    check_inactivity_alarms
)

# --- LOGLAMA ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("solid_sync.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("SyncEngine")

class SyncEngine:
    def __init__(self):
        self.db = SessionLocal()
        self.token = None

    def close(self):
        self.db.close()

    def refresh_token(self):
        """Token alır ve sınıf içinde saklar."""
        self.token = api.get_api_token()
        if not self.token:
            logger.error("❌ Token alınamadı!")
            return False
        return True

    # =========================================================
    # YARDIMCI MANTIKLAR (Sizin scriptlerden alındı)
    # =========================================================
    
    def determine_correct_owner(self, unit_name, trusted_group_id):
        """
        [AKILLI SAHİPLİK - SMART OWNERSHIP]
        1. Bu Grup ID (trusted_group_id) hangi müşteriye tanımlıysa ona verir.
        2. Eğer Grup ID kimseye tanımlı değilse, cihaz 'Admin'e (s.ozsarac) düşer.
        """
        # 1. Bu Grup ID'ye sahip bir kullanıcı var mı?
        owner_user = self.db.query(User).filter(User.trusted_group_id == trusted_group_id).first()
        
        if owner_user:
            return owner_user.id  # Örn: "musteri_1"
        
        # 2. Eğer özel bir grup değilse (root ise), veya sahibi yoksa Admin'e ver.
        # Varsayılan Admin Kullanıcısı (Settings tablosundan da çekilebilir ama şimdilik hardcode)
        DEFAULT_ADMIN = "s.ozsarac" 
        
        return DEFAULT_ADMIN

    def determine_profile_and_icon(self, unit_name):
        """
        [MANTIK KAYNAĞI: scripts/sync_trusted.py]
        İsme göre ikon ve profil belirler.
        """
        name_lower = str(unit_name).lower().replace('İ', 'i').replace('ı', 'i')
        
        breaker_models = ["kırıcı", "kirici", "breaker", "r50", "r250", "r300", "g40", "g100"]
        
        if any(m in name_lower for m in breaker_models):
            return "breaker", "PROF_BREAKER"
        elif "eks" in name_lower or "exc" in name_lower:
            return "excavator", "PROF_EXCAVATOR"
        elif "kamyon" in name_lower or "truck" in name_lower:
            return "truck", "PROF_TRANSPORT"
        else:
            return "truck", "PROF_TRANSPORT" # Varsayılan

    def fetch_all_group_ids_recursive(self):
        """
        [MANTIK KAYNAĞI: scripts/sync_trusted.py]
        API'deki ağaç yapısını tarar ve tüm alt grup ID'lerini bulur.
        Bu sayede yeni açılan bir müşteri grubunu otomatik keşfederiz.
        """
        if not self.token: return [7153]
        
        url = "https://api.trusted.dk/api/Groups/Hierarchy"
        headers = {"Authorization": f"Bearer {self.token}", "Accept": "application/json"}
        
        all_ids = []
        try:
            resp = requests.get(url, headers=headers, timeout=20)
            if resp.status_code == 200:
                data = resp.json()
                
                def extract(node):
                    if not node: return
                    if "Id" in node: all_ids.append(node["Id"])
                    for child in node.get("Children", []): extract(child)
                
                if isinstance(data, list):
                    for item in data: extract(item)
                else:
                    extract(data)
                
                unique_ids = list(set(all_ids))
                logger.info(f"🌳 Otomatik Grup Taraması: {len(unique_ids)} grup bulundu.")
                return unique_ids
        except Exception as e:
            logger.error(f"Grup Tarama Hatası: {e}")
        
        return [7153, 9840] # Hata olursa bildiğimiz ana grupları dön

    # =========================================================
    # 1. CANLI FİLO SENKRONİZASYONU (MASTER SYNC)
    # =========================================================
    def sync_live_fleet(self):
        """
        [GÖREV: Fetch Live + Auto Discovery + Alarm Check]
        Bu fonksiyon her 5 dakikada bir çalışır.
        """
        if not self.refresh_token(): return

        logger.info("🚀 [SYNC] Canlı Filo Taraması Başlıyor...")
        
        # 1. Tüm Grupları Bul (Auto-Discovery)
        target_groups = self.fetch_all_group_ids_recursive()

        headers = {"Authorization": f"Bearer {self.token}", "Accept": "application/json"}
        
        count_new = 0
        count_updated = 0

        for group_id in target_groups:
            try:
                # GroupCurrentPosition en verimli endpointtir (Konum + Temel Bilgi)
                # units14.pdf dokümanındaki önerilen yöntem.
                url = f"https://api.trusted.dk/api/Units/GroupCurrentPosition?groupid={group_id}"
                resp = requests.get(url, headers=headers, timeout=30)
                
                if resp.status_code != 200: continue
                device_list = resp.json()
                if not device_list: continue

                for item in device_list:
                    unit = item.get("Unit", {})
                    pos = item.get("CurrentPosition", {})
                    
                    serial_no = str(unit.get("SerialNumber"))
                    if not serial_no or serial_no == "None": continue

                    unit_name = unit.get("UnitName", f"Cihaz-{serial_no}")
                    
                    # Konum Verileri
                    lat = pos.get("Latitude")
                    lon = pos.get("Longitude")
                    speed = pos.get("Speed", 0)
                    heading = pos.get("Heading", 0)
                    
                    # Zaman
                    ts_str = pos.get("Timestamp")
                    last_seen = datetime.utcnow()
                    if ts_str:
                        try: last_seen = datetime.fromisoformat(ts_str.split(".")[0].replace("Z", ""))
                        except: pass

                    # --- SENSÖR VERİSİ ÇEKME (ENRICHMENT) ---
                    # GroupCurrentPosition pil bilgisini vermez, onu ayrıca çekiyoruz.
                    # Bu sync_trusted.py içindeki mantığın aynısıdır.
                    batt_pct = 0
                    temp_c = 0
                    shock_g = 0
                    
                    try:
                        sensor_url = f"https://api.trusted.dk/api/SensorData/GetLatest?serialNumber={serial_no}&count=1"
                        s_resp = requests.get(sensor_url, headers=headers, timeout=5)
                        if s_resp.status_code == 200:
                            s_data = s_resp.json()
                            if s_data and len(s_data) > 0:
                                latest = s_data[0]
                                batt_pct = latest.get("BatteryPercent", 0) or latest.get("BatteryVoltage", 0)
                                temp_c = latest.get("Temperature", 0)
                                shock_g = latest.get("MaxAcceleration", 0)
                    except:
                        pass # Sensör hatası akışı bozmasın

                    # --- DB İŞLEMLERİ ---
                    device = self.db.query(Device).filter(Device.device_id == serial_no).first()
                    
                    icon, profile_id = self.determine_profile_and_icon(unit_name)
                    correct_owner = self.determine_correct_owner(unit_name, group_id)
                    
                    if not device:
                        # YENİ CİHAZ (AUTO DISCOVERY)
                        logger.info(f"✨ Yeni Cihaz Keşfedildi: {unit_name} -> {correct_owner}")
                        device = Device(
                            device_id=serial_no,
                            owner_id=correct_owner,
                            unit_name=unit_name,
                            asset_model=unit.get("ProductTypeName", "T7"),
                            icon_type=icon,
                            profile_id=profile_id,
                            is_active=True,
                            created_at=datetime.utcnow()
                        )
                        self.db.add(device)
                        count_new += 1
                    else:
                        # MEVCUT CİHAZ GÜNCELLEME
                        # SAHİPLİK KORUMASI: Eğer sahibi "s.ozsarac" (varsayılan) ise ve kural "akkaya" diyorsa güncelle.
                        # Ama zaten "akkaya" ise dokunma (fix_ownership_final.py mantığı).
                        if device.owner_id == "s.ozsarac" and correct_owner != "s.ozsarac":
                            device.owner_id = correct_owner
                        
                        device.unit_name = unit_name
                        device.is_active = True
                        if lat and lon:
                            device.last_latitude = lat
                            device.last_longitude = lon
                            device.last_seen_at = last_seen
                            device.address = f"{lat:.5f}, {lon:.5f}"
                        count_updated += 1

                    # --- TELEMETRİ LOGU ---
                    if lat and lon:
                        log_id = f"LOG_{serial_no}_{int(last_seen.timestamp())}"
                        if not self.db.query(TelemetryLog).filter(TelemetryLog.log_id == log_id).first():
                            new_log = TelemetryLog(
                                log_id=log_id,
                                device_id=serial_no,
                                timestamp=last_seen,
                                latitude=lat, longitude=lon,
                                speed_kmh=speed,
                                battery_pct=batt_pct,
                                temp_c=temp_c,
                                max_shock_g=shock_g
                            )
                            self.db.add(new_log)
                            
                            # --- ALARM MOTORU ENTEGRASYONU ---
                            # Telemetri verisini senin alarm_engine.py dosyana yolluyoruz
                            check_telemetry_alarms(serial_no, batt_pct, speed, shock_g, last_seen)
                            
                            # Bakım Saati Kontrolü
                            run_hours = unit.get("TotalPowerOnTimerGPS", 0)
                            if run_hours:
                                check_maintenance_alarms(serial_no, float(run_hours))

                self.db.commit()

            except Exception as e:
                logger.error(f"Grup {group_id} işlenirken hata: {e}")
                self.db.rollback()

        # --- GLOBAL ALARM KONTROLLERİ ---
        # Canlı takip bitince tüm filoyu tarayan alarmları çalıştır (Geofence vb.)
        logger.info("🛡️ Alarm Motorları Çalıştırılıyor (Geofence, Inactivity)...")
        check_geofence_violations() # alarm_engine.py'den gelir
        check_inactivity_alarms()   # alarm_engine.py'den gelir

        logger.info(f"✅ Canlı Sync Bitti: {count_new} yeni, {count_updated} güncel.")

    # =========================================================
    # 2. VERİMLİLİK ANALİZİ (UTILIZATION HISTORY)
    # =========================================================
    def sync_utilization_history(self):
        """
        [MANTIK KAYNAĞI: scripts/sync_utilization_smart.py]
        Her 30-60 dakikada bir çalışır. Geçmiş çalışma verilerini çeker.
        Renklendirme ve Alarm (Uç şişirme, Mesai Dışı) yapar.
        """
        if not self.refresh_token(): return
        logger.info("📊 [ANALİZ] Verimlilik Verileri Çekiliyor...")

        devices = self.db.query(Device).filter(Device.is_active == True).all()
        
        # Son 48 saati tara (Eksik kalmasın)
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(hours=48)
        
        headers = {"Authorization": f"Bearer {self.token}", "Accept": "application/json"}
        
        count_events = 0

        for dev in devices:
            try:
                url = "https://api.trusted.dk/api/Utilization/GetUnit"
                params = {
                    "SerialNumber": dev.device_id,
                    "AfterDate": start_date.strftime("%Y-%m-%dT%H:%M:%S"),
                    "BeforeDate": end_date.strftime("%Y-%m-%dT%H:%M:%S"),
                    "ActivityFilter": "All"
                }
                
                resp = requests.get(url, params=params, headers=headers, timeout=20)
                if resp.status_code != 200: continue
                
                raw_data = resp.json()
                activities = []
                
                # API bazen dict, bazen list döner (API davranışı)
                if isinstance(raw_data, dict): activities = raw_data.get("Activities", [])
                elif isinstance(raw_data, list): activities = raw_data
                
                for item in activities:
                    start_str = item.get("ActivityStart")
                    duration = item.get("Duration", 0)
                    act_val = item.get("Activity", 0)
                    
                    if not start_str: continue
                    try: 
                        start_ts = datetime.fromisoformat(start_str.split(".")[0])
                    except: continue

                    # DB Kontrolü (Aynı veri tekrar kaydedilmesin)
                    exists = self.db.query(UtilizationEvent).filter(
                        UtilizationEvent.device_id == dev.device_id,
                        UtilizationEvent.start_time == start_ts
                    ).first()
                    
                    if not exists:
                        # --- AKILLI SINIFLANDIRMA (SMART LOGIC) ---
                        # Bu mantık sync_utilization_smart.py'dan alındı
                        is_active = str(act_val).lower() in ['true', '1']
                        cat, color, is_burst, raw = "Boşta", "#E0E0E0", False, 0
                        
                        if is_active:
                            raw = 1
                            is_burst = True
                            if duration > 180: cat, color = "Nakliye", "#000000"
                            elif duration <= 20: cat, color = "İdeal", "#00C853"
                            elif duration <= 80: cat, color = "Riskli", "#FFAB00"
                            else: cat, color = "Hatalı", "#D50000"
                        
                        # Kaydet
                        new_event = UtilizationEvent(
                            device_id=dev.device_id,
                            start_time=start_ts,
                            end_time=start_ts + timedelta(seconds=duration),
                            duration_sec=duration,
                            category=cat,
                            color_code=color,
                            is_burst=is_burst,
                            raw_activity=raw
                        )
                        self.db.add(new_event)
                        count_events += 1

                        # --- ALARM MOTORU ENTEGRASYONU ---
                        if raw == 1:
                            # 1. Uç Şişirme / Operatör Hatası (alarm_engine.py'yi çağırır)
                            check_utilization_alarm(dev.device_id, duration, start_ts)
                            # 2. Mesai Dışı Çalışma (alarm_engine.py'yi çağırır)
                            check_work_hours_alarm(dev.device_id, start_ts)

                self.db.commit()

            except Exception as e:
                logger.error(f"Cihaz {dev.unit_name} analiz hatası: {e}")
                self.db.rollback()
        
        logger.info(f"✅ Analiz Bitti: {count_events} yeni olay işlendi.")

if __name__ == "__main__":
    # TEST MODU: Dosya doğrudan çalıştırılırsa bir tur atar
    engine = SyncEngine()
    print("Test: Canlı Sync...")
    engine.sync_live_fleet()
    print("Test: Analiz Sync...")
    engine.sync_utilization_history()
    engine.close()