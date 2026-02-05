# backend/models.py (V7 - FİNAL MASTER SÜRÜM)
# TÜM ÖZELLİKLER DAHİL: CİHAZLAR, KULLANICILAR, ALARMLAR, SERVİS GEÇMİŞİ, VARDİYA, OPERATÖR

from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, ForeignKey, Text, Table
from sqlalchemy.orm import declarative_base, relationship, backref
from datetime import datetime

Base = declarative_base()

# ---------------------------------------------------------
# ARA TABLO: Cihazlar ve Şantiyeler (Çoka-Çok İlişki)
# ---------------------------------------------------------
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
# 2. KULLANICILAR (ŞİRKETLER / YÖNETİCİLER)
# ---------------------------------------------------------
class User(Base):
    __tablename__ = 'users'
    
    id = Column(String, primary_key=True)
    username = Column(String, unique=True, nullable=False)
    email = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(String, default='Client')
    trusted_group_id = Column(String, nullable=True) 
    is_active = Column(Boolean, default=True) 
    allowed_pages = Column(String, nullable=True)      
    allowed_device_ids = Column(String, nullable=True) 
    admin_note = Column(String, nullable=True)        
    subscription_end_date = Column(DateTime, nullable=True) 
    device_limit = Column(Integer, default=100)       
    last_login_at = Column(DateTime, nullable=True)   
    
    # Profil Bilgileri
    company_name = Column(String)
    full_name = Column(String)
    first_name = Column(String, nullable=True)  # Ad
    last_name = Column(String, nullable=True)   # Soyad
    country = Column(String, default="Türkiye") # Ülke
    phone = Column(String)
    logo_url = Column(String)
    company_address = Column(String) 
    
    # --- Hiyerarşi ve Kurumsal Detaylar ---
    parent_id = Column(String, ForeignKey('users.id'), nullable=True) # Üst Kullanıcı ID'si
    
    # Fatura Detayları
    tax_no = Column(String, nullable=True)      # Vergi Numarası
    tax_office = Column(String, nullable=True)  # Vergi Dairesi
    billing_address = Column(String, nullable=True) # Fatura Adresi
    
    # Hiyerarşik İlişki (Self-Referential)
    children = relationship("User", backref=backref('parent', remote_side=[id]))
    
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
    notify_weekly_report = Column(Boolean, default=False) 
    notify_monthly_report = Column(Boolean, default=False)
    
    reset_token = Column(String, nullable=True)
    
    # İlişkiler
    devices = relationship("Device", back_populates="owner")
    geosites = relationship("GeoSite", back_populates="owner")
    report_subscriptions = relationship("ReportSubscription", back_populates="user")
    
    # [YENİ] Kullanıcının tanımladığı Operatörler
    operators = relationship("Operator", back_populates="owner")

# ---------------------------------------------------------
# 3. OPERATÖR VE VARDİYA SİSTEMİ (YENİ EKLENDİ 🔥)
# ---------------------------------------------------------
class Operator(Base):
    __tablename__ = 'operators'

    id = Column(Integer, primary_key=True, autoincrement=True)
    owner_id = Column(String, ForeignKey('users.id')) # Hangi şirkete bağlı?
    
    full_name = Column(String, nullable=False)
    phone = Column(String, nullable=True)
    tckn = Column(String, nullable=True)      # Opsiyonel: TC Kimlik
    card_id = Column(String, nullable=True)   # Opsiyonel: RFID Kart ID
    
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # İlişkiler
    owner = relationship("User", back_populates="operators")
    shifts = relationship("DeviceShift", back_populates="operator")
    alarms = relationship("Alarm", back_populates="operator_rel") # Operatörün sebep olduğu alarmlar

class DeviceShift(Base):
    """
    Her cihaza özel tanımlanan vardiya saatleri.
    Örn: Cihaz X için -> 08:00-16:00 (Ahmet), 16:00-00:00 (Mehmet)
    """
    __tablename__ = 'device_shifts'

    id = Column(Integer, primary_key=True, autoincrement=True)
    device_id = Column(String, ForeignKey('devices.device_id'))
    
    shift_name = Column(String) # Örn: "Gündüz Vardiyası", "Vardiya 1"
    start_time = Column(String) # "08:00" formatında
    end_time = Column(String)   # "18:00" formatında
    
    # Bu vardiyada varsayılan kim çalışıyor?
    operator_id = Column(Integer, ForeignKey('operators.id'), nullable=True)
    
    is_active = Column(Boolean, default=True)
    
    # İlişkiler
    device = relationship("Device", back_populates="shifts")
    operator = relationship("Operator", back_populates="shifts")

# ---------------------------------------------------------
# 4. CİHAZLAR (DEVICES)
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
    is_virtual = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow) # Sıralama için gerekli

    # İnce Ayarlar
    initial_hours_offset = Column(Float, default=0.0)
    min_battery_threshold = Column(Integer, default=20)
    notification_email = Column(String)
    
    # Limitler
    limit_shock_g = Column(Float, default=8.0)
    limit_temp_c = Column(Integer, default=80)
    
    # Servis & Bakım Ayarları
    maintenance_interval_hours = Column(Integer, default=250) # Varsayılan: 250 saat
    last_service_date = Column(DateTime)
    next_service_hours = Column(Integer)
    last_maintenance_hour = Column(Float, default=0.0) # Son bakım yapıldığında motor saati kaçtı?
    
    # İlişkiler
    owner = relationship("User", back_populates="devices")
    profile = relationship("UtilizationProfile", back_populates="devices")
    
    # CASCADE RULES: Cihaz silinirse bağlı tüm veriler silinmeli
    telemetry_logs = relationship("TelemetryLog", back_populates="device", cascade="all, delete-orphan")
    utilization_logs = relationship("UtilizationLog", back_populates="device", cascade="all, delete-orphan") 
    utilization_events = relationship("UtilizationEvent", back_populates="device", cascade="all, delete-orphan") 
    
    # Alarmlar (Eski ve Yeni)
    alarms_legacy = relationship("AlarmEvent", back_populates="device", cascade="all, delete-orphan") # Eskisi
    alarms = relationship("Alarm", back_populates="device", cascade="all, delete-orphan") # Yenisi
    
    # Diğer Bağlantılar
    geosites = relationship("GeoSite", secondary=device_geosite_association, back_populates="devices")
    documents = relationship("DeviceDocument", back_populates="device", cascade="all, delete-orphan")
    
    # [YENİ] Vardiya ve Servis Geçmişi İlişkileri
    shifts = relationship("DeviceShift", back_populates="device", cascade="all, delete-orphan")
    service_history = relationship("ServiceRecord", back_populates="device", cascade="all, delete-orphan")

# ---------------------------------------------------------
# 5. LOGLAR (TELEMETRY & UTILIZATION)
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
    
    # API'den gelen ham aktivite (0=Idle, 1=Active)
    raw_activity = Column(Integer, default=1) 
    
    device = relationship("Device", back_populates="utilization_events")

# ---------------------------------------------------------
# 6. ALARMLAR (ESKİ & YENİ SİSTEMLER BİR ARADA)
# ---------------------------------------------------------

# A. ESKİ ALARM TABLOSU (Backward Compatibility için silinmedi)
class AlarmEvent(Base):
    __tablename__ = 'alarm_events'

    id = Column(Integer, primary_key=True, autoincrement=True)
    device_id = Column(String, ForeignKey('devices.device_id'))
    geosite_id = Column(Integer, ForeignKey("geosites.site_id"), nullable=True)

    alarm_type = Column(String)   # Örn: 'Geofence_Exit'
    severity = Column(String)     # Örn: 'Critical', 'Warning'
    description = Column(String)  # Örn: 'Sınır İhlali: 50m dışarıda'
    value = Column(String, nullable=True) 
    rule_id = Column(String, nullable=True) 

    is_active = Column(Boolean, default=True) 
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    acknowledged_by = Column(String, nullable=True)
    acknowledged_at = Column(DateTime, nullable=True)
    resolution_note = Column(String, nullable=True)

    # İlişkiler
    device = relationship("Device", back_populates="alarms_legacy")
    geosite = relationship("GeoSite")

# B. YENİ GELİŞMİŞ ALARM SİSTEMİ (V2)
class Alarm(Base):
    __tablename__ = "alarms"

    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(String, ForeignKey("devices.device_id"))
    
    alarm_type = Column(String)  # Örn: Overspeed, LowBattery
    severity = Column(String)    # Critical, Warning, Info
    start_time = Column(DateTime)
    end_time = Column(DateTime, nullable=True)
    status = Column(String)      # Active, Resolved
    description = Column(String)
    
    # Operatör Bağlantısı (İsteğe bağlı veya vardiyadan otomatik)
    operator = Column(String, nullable=True) # UI'da göstermek için (İsim)
    operator_id = Column(Integer, ForeignKey('operators.id'), nullable=True) # İlişkisel (ID)
    
    # İlişkiler
    device = relationship("Device", back_populates="alarms")
    operator_rel = relationship("Operator", back_populates="alarms")

class AlarmRule(Base):
    __tablename__ = "alarm_rules"

    id = Column(Integer, primary_key=True, index=True)
    rule_name = Column(String, unique=True) # Örn: Hız Limiti
    parameter = Column(String) # Örn: speed
    operator = Column(String)  # Örn: >
    threshold = Column(Float)  # Örn: 100
    severity = Column(String)  # Critical
    description = Column(String)

# ---------------------------------------------------------
# 7. SERVİS VE BAKIM GEÇMİŞİ (YENİ EKLENDİ 🔥)
# ---------------------------------------------------------
class ServiceRecord(Base):
    __tablename__ = 'service_records'

    id = Column(Integer, primary_key=True, autoincrement=True)
    device_id = Column(String, ForeignKey('devices.device_id'))
    
    # Servis Detayları
    service_date = Column(DateTime, default=datetime.utcnow) # Servis Tarihi
    technician_name = Column(String, nullable=False)         # Servis Personeli
    description = Column(String)                             # Tanım (Periyodik bakım vb.)
    
    # Parça Detayları
    changed_part = Column(String, nullable=True)             # Değişen Parça
    part_number = Column(String, nullable=True)              # Parça No (Tedarikçi Kodu)
    
    # Saat Bilgileri
    usage_hours_at_service = Column(Float)   # Kullanım Süresi (Bu bakım aralığında kaç saat çalıştı?)
    total_machine_hours = Column(Float)      # Toplam Çalışma Süresi (Kümülatif, T=0 anından beri)
    
    notes = Column(Text, nullable=True)      # Notlar
    
    # İlişki
    device = relationship("Device", back_populates="service_history")

# ---------------------------------------------------------
# 8. DİĞER (DOKÜMANLAR, AYARLAR, GEOFENCE, SUBSCRIPTIONS)
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
    trusted_site_id = Column(Integer, nullable=True) 
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Gelişmiş Ayarlar
    visible_to_subgroups = Column(Boolean, default=False)
    apply_to_all_devices = Column(Boolean, default=True)
    auto_enable_new_devices = Column(Boolean, default=True)
    auto_enable_alarms = Column(Boolean, default=True)
    auto_enable_entry_alarms = Column(Boolean, default=False)

    owner = relationship("User", back_populates="geosites")
    devices = relationship("Device", secondary=device_geosite_association, back_populates="geosites")

class DeviceDocument(Base):
    __tablename__ = 'device_documents'

    id = Column(Integer, primary_key=True, autoincrement=True)
    device_id = Column(String, ForeignKey('devices.device_id'))
    
    file_name = Column(String, nullable=False) 
    file_path = Column(String, nullable=False) 
    file_type = Column(String) 
    
    upload_date = Column(DateTime, default=datetime.utcnow)
    uploaded_by = Column(String, nullable=True) 
    
    device = relationship("Device", back_populates="documents")

class Setting(Base):
    __tablename__ = 'settings'
    
    key = Column(String, primary_key=True)   # Örn: 'work_hours'
    value = Column(String, nullable=False)   # JSON string
    description = Column(String)             

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