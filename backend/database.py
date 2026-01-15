# backend/database.py (TÜM PARÇALAR BİRLEŞTİRİLDİ)
import os
import uuid # <-- YENİ EKLENDİ (Şifre üretmek için)
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, joinedload

# BURASI ÇOK ÖNEMLİ: ShareLink'i buraya ekledik
from backend.models import Base, User, Device, TelemetryLog, UtilizationLog, ReportSubscription, GeoSite, AlarmEvent, ShareLink

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
# ALARM FONKSİYONLARI
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

# ---------------------------------------------------------
# RAPOR FONKSİYONLARI (YENİ)
# ---------------------------------------------------------
def get_daily_utilization(device_id, days=7):
    db = SessionLocal()
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)
    
    logs = db.query(TelemetryLog).filter(
        TelemetryLog.device_id == device_id,
        TelemetryLog.timestamp >= start_date
    ).order_by(TelemetryLog.timestamp.asc()).all()
    
    db.close()
    
    daily_stats = {}
    for i in range(days):
        d_str = (end_date - timedelta(days=i)).strftime("%Y-%m-%d")
        daily_stats[d_str] = {"hours": 0, "distance": 0, "max_speed": 0}

    for log in logs:
        day_str = log.timestamp.strftime("%Y-%m-%d")
        if day_str in daily_stats:
            if log.speed_kmh > 1:
                daily_stats[day_str]["hours"] += 0.25 
            if log.speed_kmh > 0:
                daily_stats[day_str]["distance"] += (log.speed_kmh * 0.25)
            if log.speed_kmh > daily_stats[day_str]["max_speed"]:
                daily_stats[day_str]["max_speed"] = log.speed_kmh

    result = []
    for date, stat in daily_stats.items():
        result.append({
            "Tarih": date,
            "Çalışma Saati": round(stat["hours"], 1),
            "Mesafe (km)": round(stat["distance"], 1),
            "Max Hız": stat["max_speed"]
        })
    result.sort(key=lambda x: x["Tarih"])
    return result

def get_fleet_summary_report():
    db = SessionLocal()
    devices = db.query(Device).all()
    summary = []
    for d in devices:
        last_24h = datetime.utcnow() - timedelta(days=1)
        logs_count = db.query(TelemetryLog).filter(
            TelemetryLog.device_id == d.device_id,
            TelemetryLog.timestamp >= last_24h,
            TelemetryLog.speed_kmh > 0
        ).count()
        work_hours = logs_count * 0.25
        summary.append({
            "Makine": d.unit_name,
            "Model": d.asset_model,
            "Bugün Çalışma": f"{work_hours} Saat",
            "Durum": "Aktif" if d.is_active else "Pasif"
        })
    db.close()
    return summary

# ---------------------------------------------------------
# 7. PUBLIC LINK (PAYLAŞIM) FONKSİYONLARI (V2 - GÜNCEL)
# ---------------------------------------------------------

def create_share_link(user_id, device_id, expires_at_dt, note=""):
    """
    Belirli bir tarihe kadar geçerli link üretir.
    expires_at_dt: datetime objesi olmalı.
    """
    db = SessionLocal()
    token = str(uuid.uuid4()) # Uzun güvenli token
    
    link = ShareLink(
        token=token,
        device_id=device_id,
        created_by=user_id,
        expires_at=expires_at_dt,
        note=note,
        is_active=True
    )
    db.add(link)
    db.commit()
    db.close()
    return token

def get_device_share_links(device_id):
    """Bir cihaza ait AKTİF paylaşım linklerini getirir (YENİ)"""
    db = SessionLocal()
    links = db.query(ShareLink).filter(
        ShareLink.device_id == device_id,
        ShareLink.is_active == True,
        ShareLink.expires_at > datetime.utcnow()
    ).order_by(ShareLink.created_at.desc()).all()
    db.close()
    return links

def get_active_share_link(token):
    """Misafir girişi için token kontrolü"""
    db = SessionLocal()
    link = db.query(ShareLink).filter(ShareLink.token == token).first()
    
    result = None
    if link and link.is_active:
        if link.expires_at > datetime.utcnow():
            device = db.query(Device).filter(Device.device_id == link.device_id).first()
            result = device
        else:
            link.is_active = False # Süresi dolmuşsa pasife çek
            db.commit()
            
    db.close()
    return result

def revoke_share_link(token):
    """Linki iptal eder (Kırmızı Buton)"""
    db = SessionLocal()
    link = db.query(ShareLink).filter(ShareLink.token == token).first()
    if link:
        link.is_active = False
        db.commit()
    db.close()


# ---------------------------------------------------------
# 8. CİHAZ İSTATİSTİK FONKSİYONU (Bunu koruyoruz!)
# ---------------------------------------------------------

def get_last_operation_stats(device_id):
    """
    Cihazın son çalışma periyodunu hesaplar.
    Mantık: Geriye doğru tarar, hız > 0 olan son anı bulur.
    """
    db = SessionLocal()
    # Son hareket ettiği zamanı bul
    last_move = db.query(TelemetryLog).filter(
        TelemetryLog.device_id == device_id, 
        TelemetryLog.speed_kmh > 0
    ).order_by(TelemetryLog.timestamp.desc()).first()
    
    result = {
        "last_seen": "Uzun süredir sinyal yok",
        "duration": "0 dk",
        "address": "Konum verisi bekleniyor"
    }
    
    if last_move:
        # Son görülme zamanı
        diff = datetime.utcnow() - last_move.timestamp
        days = diff.days
        hours = int(diff.seconds / 3600)
        mins = int((diff.seconds % 3600) / 60)
        
        time_str = ""
        if days > 0: time_str += f"{days} gün "
        if hours > 0: time_str += f"{hours} sa "
        time_str += f"{mins} dk önce"
        
        result["last_seen"] = time_str
        
        # Basit Simülasyon: Son çalışma süresi
        import random
        simulated_duration = random.choice([45, 120, 210, 30]) 
        h = int(simulated_duration / 60)
        m = simulated_duration % 60
        result["duration"] = f"{h} saat {m} dakika"
        
        # Adres Simülasyonu
        result["address"] = "Ostim OSB, 1234. Cadde, Yenimahalle/ANKARA"

    db.close()
    return result