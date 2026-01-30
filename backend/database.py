# backend/database.py (FİNAL TEMİZLENMİŞ & HATA KORUMALI SÜRÜM)
import os
import uuid
from datetime import datetime, timedelta
from sqlalchemy import create_engine, or_, func
from sqlalchemy.orm import sessionmaker, joinedload
from passlib.context import CryptContext

# --- IMPORT MODELLER & API ---
from backend.models import Base, User, Device, TelemetryLog, UtilizationLog, ReportSubscription, GeoSite, AlarmEvent, ShareLink, UtilizationEvent, Setting
from backend.trusted_api import api_create_geosite, api_delete_geosite, api_update_registrations, api_get_geosites

# --- VERİTABANI BAĞLANTISI ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "solidtrack.db")
SQL_DB_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(SQL_DB_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- ŞİFRELEME MOTORU (GİRİŞ HATASINI ÇÖZEN KISIM) ---
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")

def get_password_hash(password):
    """Şifreyi kriptolar."""
    return pwd_context.hash(password)

def verify_password(plain_password, hashed_password):
    if not hashed_password:
        return False
    
    # 1. Önce güvenli Hash kontrolü yap (Standart Yöntem)
    try:
        if pwd_context.verify(plain_password, hashed_password):
            return True
    except Exception:
        pass # Hata verirse (örneğin eski veri varsa) devam et
        
    # 2. Eğer hash tutmadıysa, çok zorda kalırsak düz metin kontrolü yap
    # (Bu satırı güvenlik için istersen silebilirsin ama geçiş sürecinde kalsın)
    if str(plain_password) == str(hashed_password):
        return True
        
    return False

# ---------------------------------------------------------
# KULLANICI İŞLEMLERİ
# ---------------------------------------------------------
def login_user(identifier, password):
    """Kullanıcı Adı VEYA E-Posta ile giriş yapılmasını sağlar."""
    db = SessionLocal()
    try:
        # Hem username hem email sütununda arama yapıyoruz
        user = db.query(User).filter(
            or_(User.username == identifier, User.email == identifier)
        ).first()
        
        if not user:
            return None
        
        if not verify_password(password, user.password_hash):
            return None
            
        return user
    finally:
        db.close()

def create_sub_user_invite(parent_user_id, new_username, new_email, new_name, allowed_device_ids_list, allowed_pages_list):
    """
    North Falcon Modeli + Davet Sistemi: 
    Alt kullanıcıyı 'PENDING' modunda oluşturur, yetkilerini kaydeder 
    ve şifre belirlemesi için bir DAVET TOKEN'ı döndürür.
    """
    db = SessionLocal()
    try:
        parent = db.query(User).filter(User.id == parent_user_id).first()
        if not parent: return None, "Ana kullanıcı bulunamadı."
        
        # 1. Çakışma Kontrolü
        if db.query(User).filter(User.username == new_username).first():
            return None, "❌ Bu Kullanıcı Adı zaten alınmış."
        if db.query(User).filter(User.email == new_email).first():
            return None, "❌ Bu E-Posta adresi zaten kayıtlı."

        # 2. Yetkileri String'e Çevir (North Falcon)
        dev_str = ",".join(allowed_device_ids_list) if allowed_device_ids_list else ""
        page_str = ",".join(allowed_pages_list) if allowed_pages_list else ""

        # 3. Token Oluştur (Eski Sistem)
        invite_token = str(uuid.uuid4())

        # 4. Kullanıcıyı "Beklemede" Olarak Oluştur
        new_user = User(
            id=new_username,
            username=new_username,
            email=new_email,
            full_name=new_name,
            password_hash="PENDING_ACTIVATION", # Şifre henüz yok
            reset_token=invite_token,           # Davet linki için anahtar
            
            role="SubUser", 
            trusted_group_id=parent.trusted_group_id,
            company_name=parent.company_name,
            
            # --- YENİ YETKİLER KAYDEDİLİYOR ---
            allowed_device_ids=dev_str,
            allowed_pages=page_str
        )
        
        db.add(new_user)
        db.commit()
        
        # Başarılı ise Token'ı döndür
        return invite_token, "Kullanıcı taslağı oluşturuldu."
        
    except Exception as e:
        db.rollback()
        return None, str(e)
    finally:
        db.close()

def complete_user_registration(token, new_password):
    """Davet tokenı ile şifre belirler."""
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.reset_token == token).first()
        if not user: return False, "Geçersiz link."
        
        user.password_hash = get_password_hash(new_password)
        user.reset_token = None
        db.commit()
        return True, user.username
    except Exception as e:
        return False, str(e)
    finally:
        db.close()

def get_invite_details(token):
    db = SessionLocal()
    try:
        return db.query(User).filter(User.reset_token == token).first()
    finally:
        db.close()

def update_user_settings(user_id, settings_dict):
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if user:
            for key, value in settings_dict.items():
                if hasattr(user, key):
                    setattr(user, key, value)
            db.commit()
            db.refresh(user)
            return user
    except Exception as e:
        db.rollback()
    finally:
        db.close()
    return None

# ---------------------------------------------------------
# CİHAZ (DEVICE) İŞLEMLERİ
# ---------------------------------------------------------
def get_user_devices(user_id: str):
    """Yetkiye ve Gruba göre cihazları getirir."""
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user: return []

        # Süper Adminler
        super_admins = ["s.ozsarac", "a.akkaya"]
        if user.username in super_admins:
            return db.query(Device).order_by(Device.is_active.desc()).all()

        # Diğerleri (Grup Bazlı)
        return db.query(Device).join(User, Device.owner_id == User.id)\
                 .filter(User.trusted_group_id == user.trusted_group_id)\
                 .order_by(Device.is_active.desc()).all()
    finally:
        db.close()

def get_all_devices_for_admin():
    db = SessionLocal()
    devices = db.query(Device).all()
    db.close()
    return devices

def get_device_telemetry(device_id, limit=100):
    db = SessionLocal()
    logs = db.query(TelemetryLog).filter(TelemetryLog.device_id == device_id)\
             .order_by(TelemetryLog.timestamp.desc()).limit(limit).all()
    db.close()
    return logs

def get_device_total_hours(device_id):
    db = SessionLocal()
    try:
        total_sec = db.query(func.sum(UtilizationEvent.duration_sec)).filter(
            UtilizationEvent.device_id == device_id,
            UtilizationEvent.raw_activity > 0
        ).scalar()
        if total_sec: return round(total_sec / 3600, 1)
        return 0.0
    finally:
        db.close()

def get_last_operation_stats(device_id):
    """Cihazın son çalışma durumu ve adresi."""
    db = SessionLocal()
    result = {"last_seen": "Veri yok", "duration": "0 dk", "address": "Konum Yok"}
    try:
        device = db.query(Device).filter(Device.device_id == device_id).first()
        if device and device.address: result["address"] = device.address
            
        last_log = db.query(TelemetryLog).filter(TelemetryLog.device_id == device_id)\
                        .order_by(TelemetryLog.timestamp.desc()).first()
        
        if last_log:
            diff = datetime.utcnow() - last_log.timestamp
            if diff.days > 0: result["last_seen"] = f"{diff.days} gün önce"
            elif diff.seconds > 3600: result["last_seen"] = f"{diff.seconds // 3600} sa önce"
            else: result["last_seen"] = f"{diff.seconds // 60} dk önce"

        last_work = db.query(UtilizationEvent).filter(
            UtilizationEvent.device_id == device_id, UtilizationEvent.raw_activity > 0
        ).order_by(UtilizationEvent.start_time.desc()).first()

        if last_work:
            m = last_work.duration_sec // 60
            h = m // 60
            result["duration"] = f"{h} sa {m%60} dk" if h > 0 else f"{m} dk"

    except Exception: pass
    finally: db.close()
    return result

# ---------------------------------------------------------
# ŞANTİYE (GEOSITE) İŞLEMLERİ
# ---------------------------------------------------------
def create_geosite(user_id, name, lat, lon, radius, address, adv_settings):
    db = SessionLocal()
    try:
        # 1. Trusted API'ye gönder
        api_res = api_create_geosite(name, lat, lon, radius)
        trusted_id = api_res.get('trusted_id') if api_res['success'] else None
        
        # 2. Yerel DB Kayıt
        new_site = GeoSite(
            owner_id=user_id, name=name, latitude=lat, longitude=lon,
            radius_meters=radius, address=address, trusted_site_id=trusted_id,
            visible_to_subgroups=adv_settings.get('visible_to_subgroups', False),
            apply_to_all_devices=adv_settings.get('apply_to_all_devices', True),
            auto_enable_new_devices=adv_settings.get('auto_enable_new_devices', True),
            auto_enable_alarms=adv_settings.get('auto_enable_alarms', True)
        )
        db.add(new_site)
        db.commit()
        db.refresh(new_site)

        # 3. Cihazları Eşle
        if new_site.apply_to_all_devices and trusted_id:
            all_devices = db.query(Device).filter(Device.owner_id == user_id).all()
            if all_devices:
                new_site.devices = all_devices
                db.commit()
                api_update_registrations(
                    trusted_id, [d.device_id for d in all_devices], 
                    register=True, alarm=new_site.auto_enable_alarms
                )
        return new_site
    except Exception as e:
        print(f"Hata: {e}")
        db.rollback()
        return None
    finally:
        db.close()

def update_geosite(site_id, name, lat, lon, radius, address, adv_settings):
    db = SessionLocal()
    try:
        site = db.query(GeoSite).filter(GeoSite.site_id == site_id).first()
        if site:
            # Trusted API'de güncelleme (Sil ve Yeniden Oluştur mantığı)
            if site.trusted_site_id: api_delete_geosite(site.trusted_site_id)
            
            api_res = api_create_geosite(name, lat, lon, radius)
            site.trusted_site_id = api_res.get('trusted_id') if api_res['success'] else None

            # Yerel Güncelleme
            site.name = name
            site.latitude = lat
            site.longitude = lon
            site.radius_meters = radius
            site.address = address
            site.visible_to_subgroups = adv_settings.get('visible_to_subgroups', False)
            site.apply_to_all_devices = adv_settings.get('apply_to_all_devices', True)
            site.auto_enable_new_devices = adv_settings.get('auto_enable_new_devices', True)
            site.auto_enable_alarms = adv_settings.get('auto_enable_alarms', True)
            
            db.commit()
            return True
    except Exception:
        db.rollback()
    finally:
        db.close()
    return False

def delete_geosite(site_id):
    db = SessionLocal()
    try:
        site = db.query(GeoSite).filter(GeoSite.site_id == site_id).first()
        if site:
            if site.trusted_site_id: api_delete_geosite(site.trusted_site_id)
            db.delete(site)
            db.commit()
            return True
    except Exception:
        db.rollback()
    finally:
        db.close()
    return False

def get_user_geosites(user_id):
    """
    Kullanıcının görebileceği şantiyeleri getirir.
    1. Kendi oluşturdukları.
    2. Görmeye yetkili olduğu cihazlara atanmış olanlar (Read-Only).
    """
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user: return []

        # A. Admin ise hepsini görsün
        if user.role == "Admin":
            return db.query(GeoSite).options(joinedload(GeoSite.devices)).all()

        # B. Normal Kullanıcı (Müşteri)
        # 1. Kendi oluşturdukları (Owner ID eşleşenler)
        own_sites = db.query(GeoSite).filter(GeoSite.owner_id == user_id).all()

        # 2. Cihazlarına atanmış başkasının (Adminin) şantiyeleri
        # Önce kullanıcının cihazlarını bul
        user_devices = get_user_devices(user_id)
        device_ids = [d.device_id for d in user_devices]
        
        # Bu cihazlara bağlı olan şantiyeleri bul
        inherited_sites = []
        if device_ids:
            inherited_sites = db.query(GeoSite).join(GeoSite.devices)\
                                .filter(Device.device_id.in_(device_ids))\
                                .filter(GeoSite.owner_id != user_id).all() # Zaten kendisininkileri aldık

        # Listeleri birleştir (Tekrarları önlemek için set kullan)
        all_sites = list(set(own_sites + inherited_sites))
        
        return all_sites
    finally:
        db.close()

def update_geosite_devices(site_id, device_ids_list):
    db = SessionLocal()
    try:
        site = db.query(GeoSite).filter(GeoSite.site_id == site_id).first()
        if not site: return False

        # API Güncelleme
        if site.trusted_site_id:
            old_ids = [d.device_id for d in site.devices]
            to_add = list(set(device_ids_list) - set(old_ids))
            to_remove = list(set(old_ids) - set(device_ids_list))
            
            if to_remove: api_update_registrations(site.trusted_site_id, to_remove, register=False, alarm=False)
            if to_add: api_update_registrations(site.trusted_site_id, to_add, register=True, alarm=site.auto_enable_alarms)

        # Yerel DB Güncelleme
        site.devices = [] 
        db.commit()
        if device_ids_list:
            site.devices = db.query(Device).filter(Device.device_id.in_(device_ids_list)).all()
        db.commit()
        return True
    except Exception:
        db.rollback()
        return False
    finally:
        db.close()

def sync_geosites_from_trusted(user_id):
    """Sunucudan şantiyeleri çeker ve yerel DB'yi günceller."""
    db = SessionLocal()
    try:
        api_res = api_get_geosites()
        if not api_res['success']: return False, "API Hatası"

        trusted_sites = api_res['data']
        local_sites = db.query(GeoSite).options(joinedload(GeoSite.devices)).filter(GeoSite.owner_id == user_id).all()
        all_devices = db.query(Device).filter(Device.owner_id == user_id).all()
        device_map = {d.device_id: d for d in all_devices}
        
        updated_count = 0
        for l_site in local_sites:
            if not l_site.trusted_site_id: continue
            
            remote = next((item for item in trusted_sites if item["Id"] == l_site.trusted_site_id), None)
            if remote:
                # Özellik Güncelle
                if remote.get("Radius") != l_site.radius_meters: l_site.radius_meters = remote["Radius"]
                if abs(l_site.latitude - remote.get("Latitude", 0)) > 0.00001: l_site.latitude = remote["Latitude"]
                if abs(l_site.longitude - remote.get("Longitude", 0)) > 0.00001: l_site.longitude = remote["Longitude"]
                
                # Cihaz Listesi Güncelle
                remote_ids = [str(u["SerialNumber"]) for u in remote.get("RegisteredUnits", []) if "SerialNumber" in u]
                current_ids = [d.device_id for d in l_site.devices]
                
                if set(remote_ids) != set(current_ids):
                    l_site.devices = [device_map[did] for did in remote_ids if did in device_map]
                    updated_count += 1
        
        db.commit()
        return True, f"{updated_count} şantiye güncellendi."
    finally:
        db.close()

def toggle_geosite_alarm_status(site_id, is_active):
    db = SessionLocal()
    try:
        site = db.query(GeoSite).filter(GeoSite.site_id == site_id).first()
        if site:
            site.auto_enable_alarms = is_active
            db.commit()
            if site.trusted_site_id and site.devices:
                api_update_registrations(
                    site.trusted_site_id, [d.device_id for d in site.devices], 
                    register=True, alarm=is_active
                )
            return True
    except Exception:
        db.rollback()
    finally:
        db.close()
    return False

# ---------------------------------------------------------
# ALARM & RAPORLAMA
# ---------------------------------------------------------
def create_alarm(device_id, type, severity, value, desc):
    db = SessionLocal()
    try:
        db.add(AlarmEvent(device_id=device_id, alarm_type=type, severity=severity, value=value, description=desc, is_active=True))
        db.commit()
    except: db.rollback()
    finally: db.close()

def get_alarms(active_only=True, user_id=None):
    db = SessionLocal()
    try:
        query = db.query(AlarmEvent).join(Device, AlarmEvent.device_id == Device.device_id)\
                  .options(joinedload(AlarmEvent.device)).order_by(AlarmEvent.timestamp.desc())

        if user_id:
            user = db.query(User).filter(User.id == user_id).first()
            if user and user.role != "Admin":
                query = query.filter(Device.owner_id == user.id)

        if active_only: query = query.filter(AlarmEvent.is_active == True)
        return query.all()
    finally:
        db.close()

def acknowledge_alarm(alarm_id, user_name):
    db = SessionLocal()
    try:
        alarm = db.query(AlarmEvent).filter(AlarmEvent.id == alarm_id).first()
        if alarm:
            alarm.is_active = False
            alarm.acknowledged_by = user_name
            alarm.acknowledged_at = datetime.utcnow()
            db.commit()
            return True
    finally:
        db.close()
    return False

def get_daily_utilization(device_id, days=7):
    db = SessionLocal()
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)
    
    logs = db.query(TelemetryLog).filter(
        TelemetryLog.device_id == device_id, TelemetryLog.timestamp >= start_date
    ).order_by(TelemetryLog.timestamp.asc()).all()
    db.close()
    
    daily_stats = { (end_date - timedelta(days=i)).strftime("%Y-%m-%d"): {"hours": 0, "distance": 0, "max_speed": 0} for i in range(days) }

    for log in logs:
        day_str = log.timestamp.strftime("%Y-%m-%d")
        if day_str in daily_stats:
            speed = log.speed_kmh or 0.0
            if speed > 1: daily_stats[day_str]["hours"] += 0.25 
            if speed > 0: daily_stats[day_str]["distance"] += (speed * 0.25)
            if speed > daily_stats[day_str]["max_speed"]: daily_stats[day_str]["max_speed"] = speed

    result = []
    for date, stat in daily_stats.items():
        result.append({"Tarih": date, "Çalışma Saati": round(stat["hours"], 1), "Mesafe (km)": round(stat["distance"], 1), "Max Hız": stat["max_speed"]})
    result.sort(key=lambda x: x["Tarih"])
    return result

def get_fleet_summary_report(user_id=None):
    db = SessionLocal()
    try:
        devices = []
        if user_id:
            user = db.query(User).filter(User.id == user_id).first()
            if user:
                if user.username == "s.ozsarac": devices = db.query(Device).all()
                else: devices = db.query(Device).join(User, Device.owner_id == User.id).filter(User.trusted_group_id == user.trusted_group_id).all()
        
        summary = []
        last_24h = datetime.utcnow() - timedelta(days=1)
        for d in devices:
            logs_count = db.query(TelemetryLog).filter(
                TelemetryLog.device_id == d.device_id, TelemetryLog.timestamp >= last_24h, TelemetryLog.speed_kmh > 0
            ).count()
            summary.append({
                "Makine": d.unit_name, "Model": d.asset_model,
                "Bugün Çalışma": f"{round(logs_count * (10/3600), 2)} Saat",
                "Durum": "Aktif" if d.is_active else "Pasif"
            })
        return summary
    finally:
        db.close()

def get_fleet_efficiency_metrics(user_id):
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user: return 0, 0
        
        if user.username == "s.ozsarac": devices = db.query(Device).all()
        else: devices = db.query(Device).join(User, Device.owner_id == User.id).filter(User.trusted_group_id == user.trusted_group_id).all()
        device_ids = [d.device_id for d in devices]
        if not device_ids: return 0, 0

        def calculate_ratio(start, end):
            events = db.query(UtilizationEvent).filter(
                UtilizationEvent.device_id.in_(device_ids),
                UtilizationEvent.start_time >= start, UtilizationEvent.start_time < end,
                UtilizationEvent.raw_activity > 0
            ).all()
            total = sum(e.duration_sec for e in events)
            efficient = sum(e.duration_sec for e in events if e.duration_sec <= 40)
            return (efficient / total * 100) if total > 0 else 0

        now = datetime.utcnow()
        curr_score = calculate_ratio(now - timedelta(days=7), now)
        prev_score = calculate_ratio(now - timedelta(days=14), now - timedelta(days=7))
        return round(curr_score, 1), round(curr_score - prev_score, 1)
    finally:
        db.close()

# ---------------------------------------------------------
# PAYLAŞIM (PUBLIC LINK)
# ---------------------------------------------------------
def create_share_link(user_id, device_id, expires_at_dt, note=""):
    db = SessionLocal()
    try:
        existing = db.query(ShareLink).filter(ShareLink.device_id == device_id, ShareLink.note == note, ShareLink.is_active == True).first()
        if existing:
            existing.expires_at = expires_at_dt
            token = existing.token
        else:
            token = str(uuid.uuid4())
            db.add(ShareLink(token=token, device_id=device_id, created_by=user_id, expires_at=expires_at_dt, note=note, is_active=True))
        db.commit()
        return token
    finally:
        db.close()

def get_device_share_links(device_id):
    db = SessionLocal()
    links = db.query(ShareLink).filter(ShareLink.device_id == device_id, ShareLink.is_active == True).all()
    db.close()
    return links

def get_active_share_link(token):
    db = SessionLocal()
    link = db.query(ShareLink).filter(ShareLink.token == token).first()
    res = None
    if link and link.is_active:
        if link.expires_at > datetime.utcnow():
            res = db.query(Device).filter(Device.device_id == link.device_id).first()
        else:
            link.is_active = False
            db.commit()
    db.close()
    return res

def revoke_share_link(token):
    db = SessionLocal()
    try:
        link = db.query(ShareLink).filter(ShareLink.token == token).first()
        if link:
            link.is_active = False
            db.commit()
    finally:
        db.close()

def get_active_geofence_alarm(device_id, site_name):
    """
    Belirtilen cihaz ve şantiye için HALA AKTİF (Kapatılmamış) bir alarm var mı?
    Varsa o alarmı döndürür, yoksa None döner.
    """
    db = SessionLocal()
    try:
        # Description içinde şantiye adı geçiyor mu diye bakıyoruz
        alarm = db.query(AlarmEvent).filter(
            AlarmEvent.device_id == device_id,
            AlarmEvent.alarm_type == "Geofence",
            AlarmEvent.is_active == True,
            AlarmEvent.description.contains(site_name)
        ).first()
        return alarm
    finally:
        db.close()

def resolve_geofence_alarm(device_id, site_name):
    """
    Cihaz şantiyeye geri döndüyse, açık olan alarmı OTOMATİK KAPAT.
    """
    db = SessionLocal()
    try:
        alarm = db.query(AlarmEvent).filter(
            AlarmEvent.device_id == device_id,
            AlarmEvent.alarm_type == "Geofence",
            AlarmEvent.is_active == True,
            AlarmEvent.description.contains(site_name)
        ).first()
        
        if alarm:
            alarm.is_active = False
            alarm.acknowledged_by = "Sistem (Otomatik)"
            alarm.acknowledged_at = datetime.utcnow()
            alarm.resolution_note = "Cihaz güvenli bölgeye geri döndü."
            db.commit()
            return True
    except:
        db.rollback()
    finally:
        db.close()
    return False

def change_user_password(user_id, old_password, new_password):
    """
    Ayarlar sayfasından şifre değiştirmek için kullanılır.
    Eski şifreyi doğrular, yenisini kaydeder.
    """
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return False, "Kullanıcı bulunamadı."
        
        # Eski şifre doğru mu?
        if not verify_password(old_password, user.password_hash):
            return False, "❌ Mevcut şifreniz hatalı."
            
        # Yeni şifreyi hash'le ve kaydet
        user.password_hash = get_password_hash(new_password)
        db.commit()
        return True, "✅ Şifreniz başarıyla değiştirildi."
    except Exception as e:
        return False, str(e)
    finally:
        db.close()

def create_password_reset_token(email):
    """
    Şifremi unuttum diyen kullanıcı için token üretir.
    """
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email).first()
        if not user:
            return None, "Bu e-posta adresiyle kayıtlı kullanıcı bulunamadı."
            
        token = str(uuid.uuid4())
        user.reset_token = token
        db.commit()
        return token, "Token oluşturuldu."
    finally:
        db.close()

def reset_password_by_token(token, new_password):
    """
    Link ile gelen kullanıcının şifresini günceller.
    """
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.reset_token == token).first()
        if not user:
            return False, "Geçersiz veya süresi dolmuş bağlantı."
            
        user.password_hash = get_password_hash(new_password)
        user.reset_token = None # Token'ı temizle (tek kullanımlık)
        db.commit()
        return True, "✅ Şifreniz başarıyla sıfırlandı. Giriş yapabilirsiniz."
    except Exception as e:
        return False, str(e)
    finally:
        db.close()