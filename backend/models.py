# backend/models.py (GÜNCELLENMİŞ HALİ)
from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import declarative_base, relationship
from datetime import datetime

Base = declarative_base()

# 1. KULLANICILAR
class User(Base):
    __tablename__ = 'users'
    id = Column(String, primary_key=True)
    username = Column(String, unique=True, nullable=False)
    email = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(String, default='Client')
    
    # Profil
    company_name = Column(String)
    full_name = Column(String)
    phone = Column(String)
    logo_url = Column(String)
    company_address = Column(String) 
    tax_office = Column(String)
    tax_number = Column(String)
    
    # Ayarlar
    language = Column(String, default='Turkish')
    timezone = Column(String, default='Europe/Istanbul')
    date_format = Column(String, default='DD.MM.YYYY')
    unit_length = Column(String, default='Metre/Km')
    unit_temp = Column(String, default='Celsius (°C)')
    unit_pressure = Column(String, default='Bar')
    unit_volume = Column(String, default='Litre')
    
    # Bildirimler
    notification_email_enabled = Column(Boolean, default=True)
    notify_low_battery = Column(Boolean, default=True)
    notify_shock = Column(Boolean, default=True)
    notify_geofence = Column(Boolean, default=True)
    notify_maintenance = Column(Boolean, default=True)
    notify_daily_report = Column(Boolean, default=True)
    
    # İlişkiler
    devices = relationship("Device", back_populates="owner")
    geosites = relationship("GeoSite", back_populates="owner") # YENİ EKLENDİ

# 2. CİHAZLAR
class Device(Base):
    __tablename__ = 'devices'
    device_id = Column(String, primary_key=True)
    owner_id = Column(String, ForeignKey('users.id'))
    unit_name = Column(String)
    asset_model = Column(String)
    initial_hours_offset = Column(Float, default=0.0) 
    min_battery_threshold = Column(Integer, default=20) 
    notification_email = Column(String) 
    is_active = Column(Boolean, default=True) 
    limit_shock_g = Column(Float, default=8.0)
    limit_tilt_deg = Column(Integer, default=45)
    limit_temp_c = Column(Integer, default=80)
    maintenance_interval_hours = Column(Integer, default=200)
    last_service_date = Column(DateTime)
    next_service_hours = Column(Integer)

    owner = relationship("User", back_populates="devices")
    telemetry_logs = relationship("TelemetryLog", back_populates="device")
    utilization_logs = relationship("UtilizationLog", back_populates="device") # Eksik ilişki tamamlandı

# 3. LOGLAR
class TelemetryLog(Base):
    __tablename__ = 'telemetry_logs'
    log_id = Column(String, primary_key=True)
    device_id = Column(String, ForeignKey('devices.device_id'))
    timestamp = Column(DateTime, default=datetime.utcnow)
    latitude = Column(Float)
    longitude = Column(Float)
    speed_kmh = Column(Float)
    battery_pct = Column(Float)
    temp_c = Column(Float)
    max_shock_g = Column(Float)
    tilt_deg = Column(Float)
    humidity_pct = Column(Float)
    device = relationship("Device", back_populates="telemetry_logs")

class UtilizationLog(Base):
    __tablename__ = 'utilization_logs'
    id = Column(Integer, primary_key=True, autoincrement=True)
    device_id = Column(String, ForeignKey('devices.device_id'))
    report_date = Column(DateTime)
    total_work_min = Column(Integer)
    motion_work_min = Column(Integer)
    daily_efficiency = Column(Float)
    device = relationship("Device", back_populates="utilization_logs")

class ReportSubscription(Base):
    __tablename__ = 'report_subscriptions'
    sub_id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey('users.id'))
    report_type = Column(String)
    frequency = Column(String) 
    email_recipients = Column(String)
    user = relationship("User")

# --- YENİ EKLENEN SINIF: GEOSITE (BÖLGE YÖNETİMİ) ---
class GeoSite(Base):
    __tablename__ = 'geosites'
    
    site_id = Column(Integer, primary_key=True, autoincrement=True)
    owner_id = Column(String, ForeignKey('users.id'))
    
    # Temel Bilgiler
    name = Column(String, nullable=False) # Örn: "Kadıköy Ev"
    address = Column(String) # Açık adres
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    radius_meters = Column(Integer, default=500) # Çap (Yarıçap)
    
    # Gelişmiş Ayarlar (Advanced Settings)
    visible_to_subgroups = Column(Boolean, default=False) # Sadece Admin görür
    apply_to_all_devices = Column(Boolean, default=True)
    auto_enable_new_devices = Column(Boolean, default=True)
    auto_enable_alarms = Column(Boolean, default=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    owner = relationship("User", back_populates="geosites")

    # backend/models.py dosyasının EN ALTINA ekle:

# ---------------------------------------------------------
# 6. ALARM OLAYLARI (YENİ TABLO)
# ---------------------------------------------------------
class AlarmEvent(Base):
    __tablename__ = 'alarm_events'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    device_id = Column(String, ForeignKey('devices.device_id'))
    
    # Alarm Detayları
    alarm_type = Column(String)  # 'LowBattery', 'Shock', 'Geofence', 'Speed', 'Offline'
    severity = Column(String)    # 'Critical', 'Warning', 'Info'
    value = Column(String)       # Örn: "9.2 G", "%12", "120 km/h"
    description = Column(String) # Örn: "Batı Şantiyesi dışına çıkıldı"
    
    # Durum
    is_active = Column(Boolean, default=True) # True: Bekliyor, False: Okundu/Arşiv
    acknowledged_by = Column(String)          # Kim okudu?
    acknowledged_at = Column(DateTime)        # Ne zaman okudu?
    
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    # İlişki
    device = relationship("Device")