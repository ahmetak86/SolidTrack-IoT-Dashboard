import logging
from datetime import datetime
import sys
import os
from geopy.distance import geodesic
from timezonefinder import TimezoneFinder
import pytz
import json

# SQLAlchemy optimizasyonu için
from sqlalchemy.orm import joinedload

tf = TimezoneFinder()

# --- AKILLI IMPORT BLOĞU (Hata almamak için) ---
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

try:
    # 1. Yöntem: Backend modülü olarak çağırma
    from backend.database import SessionLocal
    from backend.models import AlarmEvent, Device, TelemetryLog, GeoSite, Setting
except ImportError:
    try:
        # 2. Yöntem: Aynı klasörden direkt çağırma
        from database import SessionLocal
        from models import AlarmEvent, Device, TelemetryLog, GeoSite, Setting
    except ImportError:
        # 3. Yöntem: Manuel yol ekleme
        sys.path.append(current_dir)
        from database import SessionLocal
        from models import AlarmEvent, Device, TelemetryLog, GeoSite, Setting
# --------------------------------------------------

# Loglama ayarları
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_device_local_time(db, device_id, utc_time):
    """
    Cihazın son konumuna bakarak UTC zamanını cihazın YEREL zamanına çevirir.
    """
    # 1. Cihazın son konumunu bul
    last_pos = db.query(TelemetryLog).filter(
        TelemetryLog.device_id == device_id
    ).order_by(TelemetryLog.timestamp.desc()).first()

    if last_pos and last_pos.latitude and last_pos.longitude:
        try:
            # 2. Koordinattan Saat Dilimi Adını Bul (Örn: 'Asia/Almaty')
            timezone_str = tf.timezone_at(lng=last_pos.longitude, lat=last_pos.latitude)
            
            if timezone_str:
                # 3. UTC zamanını bu dilime çevir
                local_tz = pytz.timezone(timezone_str)
                # UTC zamanını işaretle ve çevir
                utc_aware = pytz.utc.localize(utc_time)
                local_time = utc_aware.astimezone(local_tz)
                return local_time, timezone_str
        except Exception as e:
            print(f"⚠️ Zaman dilimi hesaplama hatası: {e}")
    
    # Konum bulunamazsa UTC dön
    return pytz.utc.localize(utc_time), "UTC"

def check_geofence_violations():
    """
    Geofence İhlalleri (Global - Dinamik Saat Gösterimli)
    [GÜNCELLENDİ]: Kullanıcı 'notify_geofence' kapattıysa alarm üretilmez.
    """
    db = SessionLocal()
    new_alarms_count = 0
    now_utc = datetime.utcnow()
    
    try:
        print("\n🔎 [ALARM MOTORU] İhlal taraması başlatılıyor...")
        active_sites = db.query(GeoSite).filter(GeoSite.auto_enable_alarms == True).all()
        
        if not active_sites:
            print("   ℹ️ Takip edilecek aktif alarm kuralı (şantiye) bulunamadı.")
            return

        for site in active_sites:
            site_center = (site.latitude, site.longitude)
            radius_m = site.radius_meters
            
            if not site.devices: continue
                
            for device in site.devices:
                # --- [BEKÇİ] Kullanıcı İzni Kontrolü ---
                # Cihaz sahibine bak, eğer 'Bölge İhlali' bildirimini kapattıysa geç.
                if not device.owner or not device.owner.notify_geofence:
                    continue
                # ---------------------------------------

                last_log = db.query(TelemetryLog).filter(
                    TelemetryLog.device_id == device.device_id
                ).order_by(TelemetryLog.timestamp.desc()).first()
                
                if not last_log or not last_log.latitude: continue
                
                try:
                    distance_m = geodesic(site_center, (last_log.latitude, last_log.longitude)).meters
                except: continue 
                
                # Cihazın Yerel Saatini Bul
                local_time, tz_name = get_device_local_time(db, device.device_id, now_utc)
                local_time_str = local_time.strftime("%H:%M")

                if distance_m > radius_m:
                    existing_alarm = db.query(AlarmEvent).filter(
                        AlarmEvent.device_id == device.device_id,
                        AlarmEvent.geosite_id == site.site_id,
                        AlarmEvent.is_active == True
                    ).first()
                    
                    if not existing_alarm:
                        alarm = AlarmEvent(
                            device_id=device.device_id,
                            geosite_id=site.site_id,
                            alarm_type='Geofence_Exit',
                            severity='Critical',
                            is_active=True,
                            description=f"Sınır İhlali! Mesafe: {int(distance_m)}m (Yerel Saat: {local_time_str})",
                            timestamp=now_utc 
                        )
                        db.add(alarm)
                        new_alarms_count += 1
                        print(f"   🚨 ALARM: {device.unit_name} @ {site.name} (Saat: {local_time_str} {tz_name})")
                
                else:
                    # Bölgeye geri döndü
                    existing_alarm = db.query(AlarmEvent).filter(
                        AlarmEvent.device_id == device.device_id,
                        AlarmEvent.geosite_id == site.site_id,
                        AlarmEvent.is_active == True
                    ).first()
                    
                    if existing_alarm:
                        existing_alarm.is_active = False
                        existing_alarm.resolution_note = f"Otomatik: Cihaz bölgeye döndü. ({local_time_str})"
                        existing_alarm.acknowledged_at = now_utc
                        print(f"   ✅ DÖNDÜ: {device.unit_name} (Saat: {local_time_str})")

        db.commit()
        if new_alarms_count > 0:
            print(f"   🔥 Toplam {new_alarms_count} yeni alarm.")

    except Exception as e:
        print(f"   ❌ Alarm Motoru Hatası: {e}")
        db.rollback()
    finally:
        db.close()

def check_utilization_alarm(device_id, duration_seconds, timestamp):
    """
    [YENİ] Kullanım (Utilization) sürelerini kontrol eder.
    """
    db = SessionLocal()
    try:
        # --- [BEKÇİ] İzin Kontrolü ---
        # Bu alarm türü için özel bir kutucuk yapmadık ama genelde 'Kritik Darbe/Şok'
        # veya genel sistem uyarısı sayılabilir. Şimdilik açık bırakıyoruz.
        # İstersen buraya 'notify_shock' bağlayabiliriz.
        # -----------------------------

        if not timestamp: timestamp = datetime.utcnow()
        local_time, tz_str = get_device_local_time(db, device_id, timestamp)
        local_time_str = local_time.strftime("%H:%M")

        alarm_data = None
        
        # Excel Kuralı 18: Uç Şişirme Riski (41-80 sn)
        if 41 <= duration_seconds <= 80:
            alarm_data = {
                "type": "Hatalı Kullanım",
                "severity": "Warning",
                "desc": f"Operatör makineyi verimsiz kullanıyor ({local_time_str}).", 
                "rule": "source_18"
            }

        # Excel Kuralı 19: Operatör Hatası (81-180 sn)
        elif 81 <= duration_seconds <= 180:
            alarm_data = {
                "type": "Hatalı Kullanım",
                "severity": "Critical",
                "desc": f"Operatör makineyi hatalı kullanıyor ({local_time_str}).", 
                "rule": "source_19"
            }
        
        if alarm_data:
            last_alarm = db.query(AlarmEvent).filter(
                AlarmEvent.device_id == device_id,
                AlarmEvent.alarm_type == alarm_data["type"],
                AlarmEvent.rule_id == alarm_data["rule"]
            ).order_by(AlarmEvent.timestamp.desc()).first()

            if last_alarm and (timestamp - last_alarm.timestamp).total_seconds() < 60:
                return 

            new_alarm = AlarmEvent(
                device_id=device_id,
                alarm_type=alarm_data["type"],
                severity=alarm_data["severity"],
                description=alarm_data["desc"],
                value=f"{duration_seconds} sn",
                rule_id=alarm_data["rule"],
                timestamp=timestamp,
                is_active=True
            )
            db.add(new_alarm)
            db.commit()
            print(f"🚨 [UTILIZATION ALARM] {device_id}: {alarm_data['desc']} ({duration_seconds}s)")

    except Exception as e:
        print(f"❌ Utilization Alarm Hatası: {e}")
        db.rollback()
    finally:
        db.close()

def check_maintenance_alarms(device_id, current_hours):
    """
    [YENİ] Makine saati üzerinden bakım zamanı kontrolü yapar.
    [GÜNCELLENDİ]: Kullanıcı 'notify_maintenance' kapattıysa alarm üretilmez.
    """
    db = SessionLocal()
    now_utc = datetime.utcnow()

    # Cihazı ve Sahibini Çek (joinedload ile hızlandırılmış)
    device = db.query(Device).options(joinedload(Device.owner)).filter(Device.device_id == device_id).first()
    if not device: 
        db.close()
        return

    # --- [BEKÇİ] İzin Kontrolü ---
    if not device.owner or not device.owner.notify_maintenance:
        db.close()
        return # Bakım bildirimi kapalı, çık.
    # -----------------------------

    local_time, _ = get_device_local_time(db, device_id, now_utc)
    local_date_str = local_time.strftime("%d.%m.%Y")

    try:
        last_maint = device.last_maintenance_hour or 0.0
        diff = current_hours - last_maint
        
        # Bakım Kuralları
        rules = [
            {"interval": 50, "tol": 5, "severity": "Warning", "desc": "Günlük Yağlama ve Tork Kontrolü", "rule": "source_10"},
            {"interval": 100, "tol": 10, "severity": "Critical", "desc": "Keçe (Sızdırmazlık) Kontrolü", "rule": "source_11"},
            {"interval": 200, "tol": 10, "severity": "Warning", "desc": "Genel Bakım (Hortum/Rekor)", "rule": "source_12"},
            {"interval": 300, "tol": 15, "severity": "Warning", "desc": "Uç ve Burç Aşınma Kontrolü", "rule": "source_13"},
            {"interval": 500, "tol": 20, "severity": "Critical", "desc": "Gaz Ayarı (Azot) Kontrolü", "rule": "source_14"},
            {"interval": 1000, "tol": 30, "severity": "Critical", "desc": "Tamir Takımı ve Diyafram Değişimi", "rule": "source_15"},
            {"interval": 1500, "tol": 50, "severity": "Critical", "desc": "Ana Revizyon (Atölye Bakımı)", "rule": "source_15_b"}
        ]

        for r in rules:
            if diff >= r["interval"]:
                existing = db.query(AlarmEvent).filter(
                    AlarmEvent.device_id == device_id,
                    AlarmEvent.rule_id == r["rule"],
                    AlarmEvent.is_active == True
                ).first()
                
                if not existing:
                    new_alarm = AlarmEvent(
                        device_id=device_id,
                        alarm_type="Bakım Zamanı",
                        severity=r["severity"],
                        description=f"{r['desc']} ({int(diff)} saat geçti) - Tarih: {local_date_str}",
                        value=f"{current_hours} saat",
                        rule_id=r["rule"],
                        timestamp=now_utc,
                        is_active=True
                    )
                    db.add(new_alarm)
                    db.commit()
                    print(f"🔧 [BAKIM ALARMI] {device_id}: {r['desc']}")

    except Exception as e:
        print(f"❌ Bakım Alarm Hatası: {e}")
        db.rollback()
    finally:
        db.close()

def check_telemetry_alarms(device_id, battery_pct, speed_kmh, shock_g, timestamp):
    """
    [YENİ] Pil, Hız ve Darbe alarmları.
    [GÜNCELLENDİ]: Kullanıcı tercihlerine göre filtreler.
    """
    db = SessionLocal()
    if not timestamp: timestamp = datetime.utcnow()

    # Cihaz ve Sahibi Çek
    device = db.query(Device).options(joinedload(Device.owner)).filter(Device.device_id == device_id).first()
    if not device or not device.owner:
        db.close()
        return

    # Yerel Saat
    local_time, tz_str = get_device_local_time(db, device_id, timestamp)
    local_time_str = local_time.strftime("%H:%M")

    alarms_to_create = []

    try:
        # 1. PİL KONTROLLERİ (İzin varsa)
        if device.owner.notify_low_battery and battery_pct is not None:
            if battery_pct < 10:
                alarms_to_create.append({
                    "type": "Düşük Pil", "sev": "Critical", 
                    "desc": f"Kritik Pil Seviyesi! ({local_time_str})", 
                    "val": f"%{battery_pct}", "rule": "source_2"
                })
            elif battery_pct < 20:
                alarms_to_create.append({
                    "type": "Düşük Pil", "sev": "Warning", 
                    "desc": f"Pil azalıyor. ({local_time_str})", 
                    "val": f"%{battery_pct}", "rule": "source_1"
                })

        # 2. DARBE (SHOCK) KONTROLÜ (İzin varsa)
        if device.owner.notify_shock and shock_g is not None and shock_g > 7.0:
            alarms_to_create.append({
                "type": "Darbe/Kaza", "sev": "Critical", 
                "desc": f"Yüksek G-Kuvveti Algılandı ({local_time_str})", 
                "val": f"{shock_g} G", "rule": "source_21"
            })

        # 3. HIZ KONTROLLERİ (Güvenlik kapsamında her zaman açık kalabilir veya Shock ile bağlanabilir)
        # Şimdilik açık bırakıyoruz, kullanıcı güvenliği için.
        if speed_kmh is not None:
            if speed_kmh > 120:
                alarms_to_create.append({
                    "type": "Aşırı Hız", "sev": "Critical", 
                    "desc": f"Hız Limiti Aşıldı (120 km/s)! ({local_time_str})", 
                    "val": f"{speed_kmh} km/s", "rule": "source_4"
                })
            elif speed_kmh > 90:
                alarms_to_create.append({
                    "type": "Aşırı Hız", "sev": "Critical", 
                    "desc": f"Hız Limiti Aşıldı (90 km/s)! ({local_time_str})", 
                    "val": f"{speed_kmh} km/s", "rule": "source_3"
                })

        # ALARMLARI OLUŞTUR
        for item in alarms_to_create:
            # Spam Kontrolü (30 dk)
            last_alarm = db.query(AlarmEvent).filter(
                AlarmEvent.device_id == device_id,
                AlarmEvent.rule_id == item["rule"]
            ).order_by(AlarmEvent.timestamp.desc()).first()

            # Darbe hariç diğerlerinde süre kontrolü
            if item["type"] != "Darbe/Kaza":
                if last_alarm and (timestamp - last_alarm.timestamp).total_seconds() < 1800:
                    continue

            new_alarm = AlarmEvent(
                device_id=device_id,
                alarm_type=item["type"],
                severity=item["sev"],
                description=item["desc"],
                value=item["val"],
                rule_id=item["rule"],
                timestamp=timestamp,
                is_active=True
            )
            db.add(new_alarm)
            print(f"⚠️ [TELEMETRİ ALARMI] {device_id}: {item['desc']}")
        
        db.commit()

    except Exception as e:
        print(f"❌ Telemetri Alarm Hatası: {e}")
        db.rollback()
    finally:
        db.close()

def check_inactivity_alarms():
    """
    [GLOBAL-DINAMIK] Haberleşme kopukluğu.
    """
    db = SessionLocal()
    now_utc = datetime.utcnow()
    
    try:
        devices = db.query(Device).all()
        print("\n💤 [ALARM MOTORU] Hareketsizlik kontrolü yapılıyor...")

        for dev in devices:
            # Burası sistemin genel sağlığı ile ilgili, kapatılmasını önermiyoruz.
            # Ancak yine de maintenance bildirimi kapalıysa es geçilebilir.
            # Şimdilik açık bırakıyoruz (Kritik).

            last_log = db.query(TelemetryLog).filter(
                TelemetryLog.device_id == dev.device_id
            ).order_by(TelemetryLog.timestamp.desc()).first()

            if not last_log: continue

            local_time, tz_name = get_device_local_time(db, dev.device_id, last_log.timestamp)
            last_seen_str = local_time.strftime("%d.%m.%Y %H:%M")

            diff_hours = (now_utc - last_log.timestamp).total_seconds() / 3600
            diff_days = diff_hours / 24
            
            alarm_data = None
            
            if diff_hours > 168: # 7 Gün
                alarm_data = {"type": "Haberleşme Yok", "sev": "Critical", "desc": f"7 gündür sinyal alınamıyor. (Son: {last_seen_str})", "rule": "source_20"}
            elif diff_hours > 72: # 3 Gün
                alarm_data = {"type": "Haberleşme Yok", "sev": "Critical", "desc": f"3 gündür sinyal alınamıyor. (Son: {last_seen_str})", "rule": "source_19"}
            
            if alarm_data:
                existing = db.query(AlarmEvent).filter(
                    AlarmEvent.device_id == dev.device_id,
                    AlarmEvent.rule_id == alarm_data["rule"],
                    AlarmEvent.is_active == True
                ).first()

                if not existing:
                    new_alarm = AlarmEvent(
                        device_id=dev.device_id,
                        alarm_type=alarm_data["type"],
                        severity=alarm_data["sev"],
                        description=alarm_data["desc"],
                        value=f"{int(diff_days)} gün",
                        rule_id=alarm_data["rule"],
                        timestamp=now_utc,
                        is_active=True
                    )
                    db.add(new_alarm)
                    db.commit()
                    print(f"📡 [BAĞLANTI ALARMI] {dev.unit_name}: {alarm_data['desc']}")

    except Exception as e:
        print(f"❌ Hareketsizlik Kontrol Hatası: {e}")
    finally:
        db.close()

def check_work_hours_alarm(device_id, timestamp):
    """
    [GLOBAL-DINAMIK] Mesai Saati Kontrolü
    [GÜNCELLENDİ]: Kullanıcı 'notify_geofence' (Güvenlik İhlali) kapattıysa çalışmaz.
    """
    db = SessionLocal()
    
    try:
        if not timestamp: timestamp = datetime.utcnow()
        
        # Cihaz Sahibi Kontrolü (Bekçi)
        device = db.query(Device).options(joinedload(Device.owner)).filter(Device.device_id == device_id).first()
        
        # Eğer kullanıcı Bölge/Güvenlik ihlallerini kapattıysa mesai kontrolü de yapma
        if not device or not device.owner or not device.owner.notify_geofence:
            return 

        device_local_time, tz_name = get_device_local_time(db, device_id, timestamp)
        
        current_hour = device_local_time.hour
        weekday = device_local_time.weekday()

        setting = db.query(Setting).filter(Setting.key == "work_hours").first()
        start_hour, end_hour = 8, 18
        weekend_allowed = False

        if setting:
            try:
                import json
                config = json.loads(setting.value)
                start_hour = int(config.get("start", "08:00").split(":")[0])
                end_hour = int(config.get("end", "18:00").split(":")[0])
                weekend_allowed = config.get("weekend_work", False)
            except: pass 

        is_violation = False
        reason = ""

        if not weekend_allowed and weekday >= 5:
            is_violation = True
            reason = f"Hafta Sonu İzinsiz Çalışma ({tz_name})"
        elif not (start_hour <= current_hour < end_hour):
            is_violation = True
            reason = f"Mesai Dışı Çalışma (Yerel: {current_hour}:00, Bölge: {tz_name})"

        if is_violation:
            last_alarm = db.query(AlarmEvent).filter(
                AlarmEvent.device_id == device_id,
                AlarmEvent.rule_id == "source_8"
            ).order_by(AlarmEvent.timestamp.desc()).first()

            if last_alarm and (timestamp - last_alarm.timestamp).total_seconds() < 14400:
                return

            new_alarm = AlarmEvent(
                device_id=device_id,
                alarm_type="Mesai Dışı Kullanım",
                severity="Critical", 
                description=f"{reason}. Hırsızlık şüphesi.",
                value=f"Saat: {device_local_time.strftime('%H:%M')}",
                rule_id="source_8",
                timestamp=timestamp,
                is_active=True
            )
            db.add(new_alarm)
            db.commit()
            print(f"🚨 [GÜVENLİK ALARMI] {device_id}: {reason}")

    except Exception as e:
        print(f"❌ Mesai Kontrol Hatası: {e}")
    finally:
        db.close()