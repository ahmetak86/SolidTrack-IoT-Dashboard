# backend/models.py (FİNAL - CSV UYUMLU & ADRES EKLENDİ)
from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import declarative_base, relationship
from datetime import datetime

Base = declarative_base()

# ---------------------------------------------------------
# 1. KULLANICILAR (CSV'deki gibi String ID)
# ---------------------------------------------------------
class User(Base):
    __tablename__ = 'users'
    id = Column(String, primary_key=True) # Örn: "CUST_001"
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
    geosites = relationship("GeoSite", back_populates="owner")

# ---------------------------------------------------------
# 2. CİHAZLAR (Adres Sütunu Eklendi!)
# ---------------------------------------------------------
class Device(Base):
    __tablename__ = 'devices'
    device_id = Column(String, primary_key=True)
    owner_id = Column(String, ForeignKey('users.id'))
    unit_name = Column(String)
    asset_model = Column(String)
    is_active = Column(Boolean, default=True)
    # --- YENİ EKLENEN KRİTİK SÜTUN ---
    address = Column(String, default="Konum Yok") 
    icon_type = Column(String, default="truck") # Varsayılan ikon 'truck' olsun
    # ---------------------------------

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
    utilization_logs = relationship("UtilizationLog", back_populates="device")
    alarms = relationship("AlarmEvent", back_populates="device") # Alarm ilişkisi

# ---------------------------------------------------------
# 3. LOGLAR
# ---------------------------------------------------------
class TelemetryLog(Base):
    __tablename__ = 'telemetry_logs'
    log_id = Column(String, primary_key=True) # Örn: "LOG_123"
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
    is_active = Column(Boolean, default=True) # Eksikti, ekledim
    
    user = relationship("User")

# ---------------------------------------------------------
# 4. GEOSITE (BÖLGE YÖNETİMİ)
# ---------------------------------------------------------
class GeoSite(Base):
    __tablename__ = 'geosites'
    site_id = Column(Integer, primary_key=True, autoincrement=True)
    owner_id = Column(String, ForeignKey('users.id'))
    name = Column(String, nullable=False)
    address = Column(String)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    radius_meters = Column(Integer, default=500)
    
    visible_to_subgroups = Column(Boolean, default=False)
    apply_to_all_devices = Column(Boolean, default=True)
    auto_enable_new_devices = Column(Boolean, default=True)
    auto_enable_alarms = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    owner = relationship("User", back_populates="geosites")

# ---------------------------------------------------------
# 5. ALARM OLAYLARI
# ---------------------------------------------------------
class AlarmEvent(Base):
    __tablename__ = 'alarm_events'
    id = Column(Integer, primary_key=True, autoincrement=True)
    device_id = Column(String, ForeignKey('devices.device_id'))
    alarm_type = Column(String)
    severity = Column(String)
    value = Column(String)
    description = Column(String)
    is_active = Column(Boolean, default=True)
    acknowledged_by = Column(String)
    acknowledged_at = Column(DateTime)
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    device = relationship("Device", back_populates="alarms")

# ---------------------------------------------------------
# 6. PUBLIC LINK (PAYLAŞIM SİSTEMİ)
# ---------------------------------------------------------
class ShareLink(Base):
    __tablename__ = 'share_links'
    
    token = Column(String, primary_key=True)
    device_id = Column(String, ForeignKey('devices.device_id'))
    created_by = Column(String, ForeignKey('users.id'))
    expires_at = Column(DateTime)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # --- YENİ EKLENEN SÜTUN ---
    note = Column(String, nullable=True) # Örn: "Mehmet Bey - Batı Şantiyesi"
    
    # İlişkiler
    device = relationship("Device")