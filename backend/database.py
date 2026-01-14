# backend/database.py (HATA DÜZELTİLDİ: JOINEDLOAD EKLENDİ)
import os
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, joinedload # <-- joinedload EKLENDİ!
from backend.models import Base, User, Device, TelemetryLog, UtilizationLog, ReportSubscription, GeoSite, AlarmEvent

# --- AKILLI ADRES AYARI ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "solidtrack.db")
SQL_DB_URL = f"sqlite:///{DB_PATH}"

# Veritabanı Bağlantısı
engine = create_engine(SQL_DB_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ---------------------------------------------------------
# KULLANICI & CİHAZ FONKSİYONLARI
# ---------------------------------------------------------
def login_user(username, password):
    db = SessionLocal()
    user = db.query(User).filter(User.username == username, User.password_hash == str(password)).first()
    db.close()
    return user

def get_user_devices(user_id):
    db = SessionLocal()
    devices = db.query(Device).filter(Device.owner_id == user_id).all()
    db.close()
    return devices

def get_device_telemetry(device_id, limit=100):
    db = SessionLocal()
    logs = db.query(TelemetryLog).filter(TelemetryLog.device_id == device_id)\
             .order_by(TelemetryLog.timestamp.desc()).limit(limit).all()
    db.close()
    return logs

def get_all_devices_for_admin():
    db = SessionLocal()
    devices = db.query(Device).all()
    db.close()
    return devices

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
        print(f"HATA: Ayarlar güncellenemedi - {e}")
        db.rollback()
    finally:
        db.close()
    return None

# ---------------------------------------------------------
# GEOSITE (ŞANTİYE) FONKSİYONLARI
# ---------------------------------------------------------
def create_geosite(user_id, name, lat, lon, radius, address, adv_settings):
    db = SessionLocal()
    try:
        new_site = GeoSite(
            owner_id=user_id,
            name=name,
            latitude=lat,
            longitude=lon,
            radius_meters=radius,
            address=address,
            visible_to_subgroups=adv_settings.get('visible_to_subgroups', False),
            apply_to_all_devices=adv_settings.get('apply_to_all_devices', True),
            auto_enable_new_devices=adv_settings.get('auto_enable_new_devices', True),
            auto_enable_alarms=adv_settings.get('auto_enable_alarms', True)
        )
        db.add(new_site)
        db.commit()
        db.refresh(new_site)
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
    except Exception as e:
        print(f"Update Hatası: {e}")
        db.rollback()
    finally:
        db.close()
    return False

def get_user_geosites(user_id):
    db = SessionLocal()
    sites = db.query(GeoSite).filter(GeoSite.owner_id == user_id).all()
    db.close()
    return sites

def delete_geosite(site_id):
    db = SessionLocal()
    try:
        site = db.query(GeoSite).filter(GeoSite.site_id == site_id).first()
        if site:
            db.delete(site)
            db.commit()
            return True
    except:
        db.rollback()
    finally:
        db.close()
    return False

# ---------------------------------------------------------
# ALARM FONKSİYONLARI (BURASI DÜZELDİ)
# ---------------------------------------------------------
def create_alarm(device_id, type, severity, value, desc):
    db = SessionLocal()
    try:
        alarm = AlarmEvent(
            device_id=device_id,
            alarm_type=type,
            severity=severity,
            value=value,
            description=desc,
            is_active=True
        )
        db.add(alarm)
        db.commit()
    except Exception as e:
        db.rollback()
    finally:
        db.close()

def get_alarms(active_only=True):
    db = SessionLocal()
    # DÜZELTME: options(joinedload(...)) ile veriyi peşin çekiyoruz.
    # Artık kapı kapansa bile alarmın içinde cihaz bilgisi hazır oluyor.
    query = db.query(AlarmEvent).options(joinedload(AlarmEvent.device)).order_by(AlarmEvent.timestamp.desc())
    
    if active_only:
        query = query.filter(AlarmEvent.is_active == True)
    
    alarms = query.all()
    db.close()
    return alarms

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
    except:
        db.rollback()
    finally:
        db.close()
    return False