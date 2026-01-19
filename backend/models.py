# backend/models.py (V2 - UTILIZATION PROFILES & SMART LOGIC)
from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import declarative_base, relationship
from datetime import datetime

Base = declarative_base()

# ---------------------------------------------------------
# 1. KULLANIM PROFİLLERİ (YENİ BEYİN 🧠)
# ---------------------------------------------------------
class UtilizationProfile(Base):
    __tablename__ = 'utilization_profiles'
    
    profile_id = Column(String, primary_key=True) # Örn: "PROF_BREAKER", "PROF_EXCAVATOR"
    profile_name = Column(String, nullable=False) # Örn: "Hidrolik Kırıcı (Standart)"
    description = Column(String)
    color_code = Column(String, default="#FFC107") # Haritada/Grafikte görünecek renk
    
    # --- Zeka Ayarları (Sensitivity & Burst) ---
    motion_threshold_g = Column(Float, default=0.5) # Kaç G yerse "Çalıştı" sayalım? (Sensitivity)
    min_active_time_sec = Column(Integer, default=10) # En az kaç saniye titreşim lazım?
    burst_mode_enabled = Column(Boolean, default=False) # Sık veri gönderim modu açık mı?
    
    # İlişki
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
    
    company_name = Column(String)
    full_name = Column(String)
    phone = Column(String)
    logo_url = Column(String)
    company_address = Column(String) 
    tax_office = Column(String)
    tax_number = Column(String)
    
    # Kullanıcı Ayarları
    language = Column(String, default='Turkish')
    timezone = Column(String, default='Europe/Istanbul')
    
    # İlişkiler
    devices = relationship("Device", back_populates="owner")
    geosites = relationship("GeoSite", back_populates="owner")

# ---------------------------------------------------------
# 3. CİHAZLAR (GÜNCELLENDİ)
# ---------------------------------------------------------
class Device(Base):
    __tablename__ = 'devices'
    device_id = Column(String, primary_key=True)
    owner_id = Column(String, ForeignKey('users.id'))
    
    # --- YENİ BAĞLANTI ---
    profile_id = Column(String, ForeignKey('utilization_profiles.profile_id')) # Ayarları buradan alacak
    
    unit_name = Column(String)
    asset_model = Column(String)
    address = Column(String, default="Konum Yok") 
    icon_type = Column(String, default="truck")
    is_active = Column(Boolean, default=True)

    # Cihaza özel ince ayarlar (Profilin üzerine yazar)
    initial_hours_offset = Column(Float, default=0.0) 
    maintenance_interval_hours = Column(Integer, default=200)
    last_service_date = Column(DateTime)
    next_service_hours = Column(Integer)
    
    # İlişkiler
    owner = relationship("User", back_populates="devices")
    profile = relationship("UtilizationProfile", back_populates="devices") # Profile erişim
    telemetry_logs = relationship("TelemetryLog", back_populates="device")
    utilization_logs = relationship("UtilizationLog", back_populates="device")
    alarms = relationship("AlarmEvent", back_populates="device")

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
    
    # Sensör Verileri
    battery_pct = Column(Float, default=0)
    temp_c = Column(Float, default=0)
    max_shock_g = Column(Float, default=0) # Bunu DataLog'dan alacağız
    
    device = relationship("Device", back_populates="telemetry_logs")

class UtilizationLog(Base):
    __tablename__ = 'utilization_logs'
    id = Column(Integer, primary_key=True, autoincrement=True)
    device_id = Column(String, ForeignKey('devices.device_id'))
    report_date = Column(DateTime)
    
    total_work_min = Column(Integer, default=0)
    motion_work_min = Column(Integer, default=0) # Titreşim/Hareket ile çalışma
    daily_efficiency = Column(Float, default=0.0)
    
    device = relationship("Device", back_populates="utilization_logs")

class ReportSubscription(Base):
    __tablename__ = 'report_subscriptions'
    sub_id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey('users.id'))
    report_type = Column(String)
    frequency = Column(String) 
    email_recipients = Column(String)
    is_active = Column(Boolean, default=True)
    
    user = relationship("User")

# ---------------------------------------------------------
# 5. DİĞER (GEOSITE, ALARM, SHARE)
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
    owner = relationship("User", back_populates="geosites")

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
    device = relationship("Device")