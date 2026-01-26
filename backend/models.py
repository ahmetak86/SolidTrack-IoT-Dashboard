# backend/models.py (V5 - FINAL + YENİ ÖZELLİKLER)
from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, ForeignKey, Text, Table
from sqlalchemy.orm import declarative_base, relationship
from datetime import datetime

Base = declarative_base()

# Cihazlar ve Şantiyeler Arasındaki Çoka-Çok İlişki
device_geosite_association = Table(
    'device_geosite_link', Base.metadata,
    Column('device_id', String, ForeignKey('devices.device_id'), primary_key=True),
    Column('site_id', Integer, ForeignKey('geosites.site_id'), primary_key=True)
)

# ---------------------------------------------------------
# 1. KULLANIM PROFİLLERİ
# ---------------------------------------------------------
class UtilizationProfile(Base):
    __tablename__ = 'utilization_profiles'
    
    profile_id = Column(String, primary_key=True)
    profile_name = Column(String, nullable=False)
    description = Column(String)
    color_code = Column(String, default="#FFC107")
    
    # --- Zeka Ayarları ---
    motion_threshold_g = Column(Float, default=0.5)
    min_active_time_sec = Column(Integer, default=10)
    burst_mode_enabled = Column(Boolean, default=False)
    
    # Mod Adı (Burst, Motion Extended, Standard)
    mode_name = Column(String, default="Standard")
    
    # İlişkiler
    devices = relationship("Device", back_populates="profile")

# ---------------------------------------------------------
# 2. KULLANICILAR
# ---------------------------------------------------------
class User(Base):
    __tablename__ = 'users'
    id = Column(String, primary_key=True)
    username = Column(String, unique=True, nullable=False)
    email = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(String, default='Client')
    
    # Profil Bilgileri
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
    
    # Birimler
    unit_length = Column(String, default='Metre / Km')
    unit_temp = Column(String, default='Celsius (°C)')
    unit_pressure = Column(String, default='Bar')
    unit_volume = Column(String, default='Litre')

    # Bildirim Ayarları
    notification_email_enabled = Column(Boolean, default=True)
    notify_low_battery = Column(Boolean, default=True)
    notify_shock = Column(Boolean, default=True)
    notify_geofence = Column(Boolean, default=True)
    notify_maintenance = Column(Boolean, default=True)
    notify_daily_report = Column(Boolean, default=True)
    
    # İlişkiler
    devices = relationship("Device", back_populates="owner")
    geosites = relationship("GeoSite", back_populates="owner")
    report_subscriptions = relationship("ReportSubscription", back_populates="user")

# ---------------------------------------------------------
# 3. CİHAZLAR
# ---------------------------------------------------------
class Device(Base):
    __tablename__ = 'devices'
    device_id = Column(String, primary_key=True)
    owner_id = Column(String, ForeignKey('users.id'))
    profile_id = Column(String, ForeignKey('utilization_profiles.profile_id'))
    
    unit_name = Column(String)
    asset_model = Column(String)
    address = Column(String, default="Konum Yok") 
    icon_type = Column(String, default="truck")
    is_active = Column(Boolean, default=True)

    # İnce Ayarlar
    initial_hours_offset = Column(Float, default=0.0)
    min_battery_threshold = Column(Integer, default=20)
    notification_email = Column(String)
    
    # Limitler
    limit_shock_g = Column(Float, default=8.0)
    limit_temp_c = Column(Integer, default=80)
    
    # Servis
    maintenance_interval_hours = Column(Integer, default=200)
    last_service_date = Column(DateTime)
    next_service_hours = Column(Integer)
    
    # İlişkiler
    owner = relationship("User", back_populates="devices")
    profile = relationship("UtilizationProfile", back_populates="devices")
    
    telemetry_logs = relationship("TelemetryLog", back_populates="device")
    utilization_logs = relationship("UtilizationLog", back_populates="device") # Günlük Özet
    utilization_events = relationship("UtilizationEvent", back_populates="device") # Detaylı Eventler (Düzeltildi)
    
    alarms = relationship("AlarmEvent", back_populates="device")
    # Şantiyelerle İlişki (Many-to-Many)
    geosites = relationship("GeoSite", secondary=device_geosite_association, back_populates="devices")

# ---------------------------------------------------------
# 4. LOGLAR
# ---------------------------------------------------------
class TelemetryLog(Base):
    __tablename__ = 'telemetry_logs'
    log_id = Column(String, primary_key=True)
    device_id = Column(String, ForeignKey('devices.device_id'))
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    latitude = Column(Float)
    longitude = Column(Float)
    speed_kmh = Column(Float)
    
    battery_pct = Column(Float, default=0)
    temp_c = Column(Float, default=0)
    max_shock_g = Column(Float, default=0)
    
    device = relationship("Device", back_populates="telemetry_logs")

# GÜNLÜK ÖZET (Daily Stats)
class UtilizationLog(Base):
    __tablename__ = 'utilization_logs'
    id = Column(Integer, primary_key=True, autoincrement=True)
    device_id = Column(String, ForeignKey('devices.device_id'))
    report_date = Column(DateTime)
    
    total_work_min = Column(Integer, default=0)
    motion_work_min = Column(Integer, default=0)
    daily_efficiency = Column(Float, default=0.0)
    
    device = relationship("Device", back_populates="utilization_logs")

# DETAYLI EVENT TABLOSU (Timeline Verisi)
class UtilizationEvent(Base):
    __tablename__ = 'utilization_events'
    id = Column(Integer, primary_key=True, autoincrement=True)
    device_id = Column(String, ForeignKey('devices.device_id'))
    
    start_time = Column(DateTime)
    end_time = Column(DateTime)
    duration_sec = Column(Float)
    
    category = Column(String)
    color_code = Column(String)
    is_burst = Column(Boolean) # Grafik çizimi için (True/False)
    
    # [YENİ] API'den gelen ham aktivite (0=Idle, 1=Active)
    raw_activity = Column(Integer, default=1) 
    
    # İlişki düzeltildi: back_populates="utilization_events"
    device = relationship("Device", back_populates="utilization_events")

# ---------------------------------------------------------
# 5. DİĞERLERİ
# ---------------------------------------------------------
class ReportSubscription(Base):
    __tablename__ = 'report_subscriptions'
    sub_id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey('users.id'))
    report_type = Column(String)
    frequency = Column(String) 
    email_recipients = Column(String)
    is_active = Column(Boolean, default=True)
    
    user = relationship("User", back_populates="report_subscriptions")

class GeoSite(Base):
    __tablename__ = 'geosites'
    site_id = Column(Integer, primary_key=True, autoincrement=True)
    owner_id = Column(String, ForeignKey('users.id'))
    name = Column(String, nullable=False)
    address = Column(String)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    radius_meters = Column(Integer, default=500)
    trusted_site_id = Column(Integer, nullable=True) # Trusted API'den gelen ID
    
    # --- YENİ EKLENEN ALANLAR (Gelişmiş Ayarlar) ---
    visible_to_subgroups = Column(Boolean, default=False)
    apply_to_all_devices = Column(Boolean, default=True)
    auto_enable_new_devices = Column(Boolean, default=True)
    auto_enable_alarms = Column(Boolean, default=True)
    auto_enable_entry_alarms = Column(Boolean, default=False)

    owner = relationship("User", back_populates="geosites")

    devices = relationship("Device", secondary=device_geosite_association, back_populates="geosites")

class AlarmEvent(Base):
    __tablename__ = 'alarm_events'
    id = Column(Integer, primary_key=True, autoincrement=True)
    device_id = Column(String, ForeignKey('devices.device_id'))
    alarm_type = Column(String)
    severity = Column(String)
    description = Column(String)
    is_active = Column(Boolean, default=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    device = relationship("Device", back_populates="alarms")

class ShareLink(Base):
    __tablename__ = 'share_links'
    token = Column(String, primary_key=True)
    device_id = Column(String, ForeignKey('devices.device_id'))
    created_by = Column(String, ForeignKey('users.id'))
    expires_at = Column(DateTime)
    note = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    device = relationship("Device") # Tek yönlü ilişki yeterli