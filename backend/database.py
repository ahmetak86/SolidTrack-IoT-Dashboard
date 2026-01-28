# backend/database.py (TÜM PARÇALAR BİRLEŞTİRİLDİ)
import os
import uuid # <-- YENİ EKLENDİ (Şifre üretmek için)
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, joinedload
from backend.trusted_api import api_create_geosite, api_delete_geosite, api_update_registrations, api_get_geosites
from passlib.context import CryptContext
from sqlalchemy import or_
from sqlalchemy import func
from backend.models import Base, User, Device, TelemetryLog, UtilizationLog, ReportSubscription, GeoSite, AlarmEvent, ShareLink, UtilizationEvent

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
# backend/database.py (GÜNCELLENMİŞ VERSİYON)

def create_geosite(user_id, name, lat, lon, radius, address, adv_settings):
    db = SessionLocal()
    try:
        # 1. ÖNCE TRUSTED API'YE ŞANTİYEYİ GÖNDER
        print(f"🌍 Sunucuya şantiye gönderiliyor: {name}")
        api_res = api_create_geosite(name, lat, lon, radius)
        
        trusted_id = None
        if api_res['success']:
            trusted_id = api_res['trusted_id']
            print(f"✅ Uzak sunucuda Şantiye Oluşturuldu. ID: {trusted_id}")
        else:
            print(f"⚠️ Uzak sunucuda Oluşturma Hatası: {api_res.get('error')}")
        
        # 2. YEREL VERİTABANINA KAYDET
        new_site = GeoSite(
            owner_id=user_id,
            name=name,
            latitude=lat,
            longitude=lon,
            radius_meters=radius,
            address=address,
            trusted_site_id=trusted_id,
            visible_to_subgroups=adv_settings.get('visible_to_subgroups', False),
            apply_to_all_devices=adv_settings.get('apply_to_all_devices', True),
            auto_enable_new_devices=adv_settings.get('auto_enable_new_devices', True),
            auto_enable_alarms=adv_settings.get('auto_enable_alarms', True)
        )
        db.add(new_site)
        db.commit()
        db.refresh(new_site)

        # 3. CİHAZLARI TRUSTED'A GÖNDER (Eğer "Tüm Cihazlar" seçildiyse)
        if new_site.apply_to_all_devices and trusted_id:
            # Kullanıcının tüm cihazlarını bul
            all_devices = db.query(Device).filter(Device.owner_id == user_id).all()
            if all_devices:
                device_ids = [d.device_id for d in all_devices]
                
                # Yerel ilişkiyi kur
                new_site.devices = all_devices
                db.commit()
                
                # API'ye gönder
                print(f"📡 {len(device_ids)} cihaz sunucudaki şantiyeye ekleniyor...")
                api_update_registrations(
                    trusted_id, 
                    device_ids, 
                    register=True, 
                    alarm=new_site.auto_enable_alarms
                )

        return new_site
    except Exception as e:
        print(f"DB Create Hatası: {e}")
        db.rollback()
        return None
    finally:
        db.close()

# backend/database.py içindeki update_geosite fonksiyonunu bununla değiştir:

def update_geosite(site_id, name, lat, lon, radius, address, adv_settings):
    db = SessionLocal()
    try:
        site = db.query(GeoSite).filter(GeoSite.site_id == site_id).first()
        if site:
            # --- API SENKRONİZASYONU ---
            # Koordinat veya İsim değiştiyse Trusted tarafında güncelleme yapmamız lazım.
            # Trusted API'de Lat/Lon update olmadığı için: ESKİYİ SİL -> YENİYİ EKLE
            
            if site.trusted_site_id:
                print(f"🔄 Sunucu Güncelleme: Eski ID {site.trusted_site_id} siliniyor...")
                api_delete_geosite(site.trusted_site_id)
            
            # Yeni ayarlarla tekrar oluştur
            print(f"🌍 Uzak Sunucu Yeniden Oluşturuluyor: {name}")
            api_res = api_create_geosite(name, lat, lon, radius)
            
            if api_res['success']:
                site.trusted_site_id = api_res['trusted_id']
                print(f"✅ Güncelleme Başarılı. Yeni Sunucu ID: {site.trusted_site_id}")
            else:
                print(f"⚠️ Güncelleme sırasında API hatası: {api_res.get('error')}")
                site.trusted_site_id = None # Bağlantı koptu

            # --- YEREL DB GÜNCELLEME ---
            site.name = name
            site.latitude = lat
            site.longitude = lon
            site.radius_meters = radius
            site.address = address
            
            # Ayarlar
            site.visible_to_subgroups = adv_settings.get('visible_to_subgroups', False)
            site.apply_to_all_devices = adv_settings.get('apply_to_all_devices', True)
            site.auto_enable_new_devices = adv_settings.get('auto_enable_new_devices', True)
            
            # Alarm ayarı değişirse (API'ye yansıtmak gerekir ama şimdilik yerelde tutuyoruz)
            site.auto_enable_alarms = adv_settings.get('auto_enable_alarms', True)
            site.auto_enable_entry_alarms = adv_settings.get('auto_enable_entry_alarms', False)
            
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
    # joinedload(GeoSite.devices) sayesinde cihaz listesi her zaman taze gelir!
    sites = db.query(GeoSite).options(joinedload(GeoSite.devices)).filter(GeoSite.owner_id == user_id).all()
    db.close()
    return sites

def delete_geosite(site_id):
    db = SessionLocal()
    try:
        site = db.query(GeoSite).filter(GeoSite.site_id == site_id).first()
        if site:
            # 1. TRUSTED API'DEN SİL
            if site.trusted_site_id:
                print(f"🗑️ Sunucu ID {site.trusted_site_id} siliniyor...")
                api_delete_geosite(site.trusted_site_id)
            
            # 2. YEREL DB'DEN SİL
            db.delete(site)
            db.commit()
            return True
    except Exception as e:
        print(f"Delete Hatası: {e}")
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

def get_alarms(active_only=True, user_id=None):
    """
    Kullanıcının yetkisine göre alarmları getirir.
    """
    db = SessionLocal()
    try:
        query = db.query(AlarmEvent).join(Device, AlarmEvent.device_id == Device.device_id)\
                  .options(joinedload(AlarmEvent.device))\
                  .order_by(AlarmEvent.timestamp.desc())

        # FİLTRELEME (User ID varsa)
        if user_id:
            user = db.query(User).filter(User.id == user_id).first()
            if user and user.role != "Admin": # Admin değilse (veya Süper Admin değilse)
                # Sadece kendi grubunun cihazlarına ait alarmlar
                query = query.filter(Device.owner_id == user.id)
            elif user and user.username != "s.ozsarac": # Ahmet Akkaya (Grup Admin) ise
                 # Sadece kendi grubunun cihazlarına ait alarmlar (Join User ile yapılabilir ama owner_id yeterli şu an)
                 # Burada User tablosuna join atıp trusted_group_id kontrolü yapmak en doğrusu
                 query = query.join(User, Device.owner_id == User.id)\
                              .filter(User.trusted_group_id == user.trusted_group_id)

        if active_only:
            query = query.filter(AlarmEvent.is_active == True)
            
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
    
    # --- daily_stats SÖZLÜĞÜNÜ BURADA TANIMLIYORUZ ---
    daily_stats = {}
    for i in range(days):
        d_str = (end_date - timedelta(days=i)).strftime("%Y-%m-%d")
        daily_stats[d_str] = {"hours": 0, "distance": 0, "max_speed": 0}

    # --- VERİLERİ İŞLEME ---
    for log in logs:
        day_str = log.timestamp.strftime("%Y-%m-%d")
        
        if day_str in daily_stats:
            # Hız verisi None ise 0 kabul et
            speed = log.speed_kmh if log.speed_kmh is not None else 0.0
            
            if speed > 1:
                daily_stats[day_str]["hours"] += 0.25 
            if speed > 0:
                daily_stats[day_str]["distance"] += (speed * 0.25)
            if speed > daily_stats[day_str]["max_speed"]:
                daily_stats[day_str]["max_speed"] = speed

    # --- SONUÇ FORMATLAMA ---
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

def get_fleet_summary_report(user_id=None):
    """
    Kullanıcının yetkisine göre özet rapor hazırlar.
    """
    db = SessionLocal()
    try:
        # Eğer user_id verilmişse, o kullanıcının cihazlarını bulalım
        if user_id:
            # get_user_devices mantığının aynısını buraya uyguluyoruz (DB session içinde olduğumuz için)
            user = db.query(User).filter(User.id == user_id).first()
            if user:
                if user.username == "s.ozsarac": # Patron
                    devices = db.query(Device).all()
                else: # Grup Admini veya Müşteri
                    # Kullanıcının grubuyla eşleşen cihazları bul
                    devices = db.query(Device).join(User, Device.owner_id == User.id)\
                                .filter(User.trusted_group_id == user.trusted_group_id).all()
            else:
                devices = []
        else:
            # User ID yoksa boş dön (Güvenlik)
            devices = []

        summary = []
        for d in devices:
            # Son 24 saatteki hareketleri say
            last_24h = datetime.utcnow() - timedelta(days=1)
            logs_count = db.query(TelemetryLog).filter(
                TelemetryLog.device_id == d.device_id,
                TelemetryLog.timestamp >= last_24h,
                TelemetryLog.speed_kmh > 0
            ).count()
            
            # Basit hesap: Her log 15 saniye olsa (örnek) veya direk log sayısı
            # Burayı kendi mantığına göre düzeltebilirsin, şimdilik basit tuttum
            work_hours = round(logs_count * (10/3600), 2) # Örn: her log 10 saniye ise saate çevir
            
            summary.append({
                "Makine": d.unit_name,
                "Model": d.asset_model,
                "Bugün Çalışma": f"{work_hours} Saat",
                "Durum": "Aktif" if d.is_active else "Pasif"
            })
        return summary
    finally:
        db.close()

# ---------------------------------------------------------
# 7. PUBLIC LINK (PAYLAŞIM) FONKSİYONLARI (V2 - GÜNCEL)
# ---------------------------------------------------------

# backend/database.py -> create_share_link fonksiyonunu GÜNCELLE

def create_share_link(user_id, device_id, expires_at_dt, note=""):
    """
    V2: Aynı 'note' (isim) ile aktif bir link varsa yenisini oluşturmaz,
    mevcut olanın süresini günceller ve aynı token'ı döner.
    """
    db = SessionLocal()
    
    # 1. Aynı cihaza, aynı isimle (note), iptal edilmemiş (active) bir link var mı?
    existing_link = db.query(ShareLink).filter(
        ShareLink.device_id == device_id,
        ShareLink.note == note,
        ShareLink.is_active == True
    ).first()

    if existing_link:
        # --- VARSA GÜNCELLE ---
        # Sadece tarihini güncelle, token aynı kalsın.
        existing_link.expires_at = expires_at_dt
        # Eğer süresi dolmuşsa ve tekrar canlandırılıyorsa created_at güncellenebilir
        existing_link.created_at = datetime.utcnow() 
        token = existing_link.token
        db.commit()
    else:
        # --- YOKSA OLUŞTUR ---
        token = str(uuid.uuid4()) # Yeni Token
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
    Cihazın son çalışma periyodunu ve adresini GERÇEK veriden çeker.
    """
    db = SessionLocal()
    result = {
        "last_seen": "Veri yok",
        "duration": "0 dk",
        "address": "Konum verisi bekleniyor"
    }
    
    try:
        # 1. ADRES ve SON SİNYAL (Device tablosundan)
        device = db.query(Device).filter(Device.device_id == device_id).first()
        if device:
            if device.address: result["address"] = device.address
            
            # Son sinyal zamanı için TelemetryLog'a bakıyoruz
            last_log = db.query(TelemetryLog).filter(TelemetryLog.device_id == device_id)\
                         .order_by(TelemetryLog.timestamp.desc()).first()
            
            if last_log:
                diff = datetime.utcnow() - last_log.timestamp
                if diff.days > 0:
                    result["last_seen"] = f"{diff.days} gün önce"
                elif diff.seconds > 3600:
                    result["last_seen"] = f"{diff.seconds // 3600} sa önce"
                else:
                    result["last_seen"] = f"{diff.seconds // 60} dk önce"

        # 2. SON ÇALIŞMA SÜRESİ (UtilizationEvent tablosundan)
        # En son biten 'Çalışma' olayını bul
        last_work = db.query(UtilizationEvent).filter(
            UtilizationEvent.device_id == device_id,
            UtilizationEvent.raw_activity > 0
        ).order_by(UtilizationEvent.start_time.desc()).first()

        if last_work:
            m = last_work.duration_sec // 60
            h = m // 60
            m = m % 60
            if h > 0:
                result["duration"] = f"{h} sa {m} dk"
            else:
                result["duration"] = f"{m} dk"

    except Exception as e:
        print(f"Stats Hatası: {e}")
    finally:
        db.close()
    
    return result

# backend/database.py

def update_geosite_devices(site_id, device_ids_list):
    """
    Şantiyeye atanan cihazları günceller ve API ile senkronize eder.
    Yerel veritabanı güncellemesi GARANTİ altına alındı.
    """
    db = SessionLocal()
    try:
        site = db.query(GeoSite).filter(GeoSite.site_id == site_id).first()
        if not site: return False

        # Yerel DB'deki eski cihaz listesini al (API farkı hesaplamak için)
        old_device_ids = [d.device_id for d in site.devices]
        
        set_old = set(old_device_ids)
        set_new = set(device_ids_list)
        
        to_add = list(set_new - set_old)
        to_remove = list(set_old - set_new)
        
        print(f"📊 Cihaz Güncelleme: +{len(to_add)} Eklenecek, -{len(to_remove)} Çıkarılacak")

        # --- API İŞLEMLERİ (Hata olsa bile yerel devam etsin) ---
        if site.trusted_site_id:
            # 1. SİLME (RegisterUnits=False)
            if to_remove:
                api_update_registrations(site.trusted_site_id, to_remove, register=False, alarm=False)

            # 2. EKLEME (RegisterUnits=True)
            if to_add:
                api_update_registrations(site.trusted_site_id, to_add, register=True, alarm=site.auto_enable_alarms)

        # --- YEREL DB GÜNCELLEME (Fix: Önce Temizle Sonra Ekle) ---
        site.devices = [] 
        db.commit() # Ara kayıt (İlişkiyi kopar)
        
        if device_ids_list:
            selected_devices = db.query(Device).filter(Device.device_id.in_(device_ids_list)).all()
            site.devices = selected_devices
        
        db.commit() # Son kayıt
        return True

    except Exception as e:
        print(f"Cihaz Güncelleme Exception: {e}")
        db.rollback()
        return False
    finally:
        db.close()

def sync_geosites_from_trusted(user_id):
    """
    Sunucu API'den verileri çeker (Radius, Lat, Lon VE CİHAZLAR) ve yerel DB'yi günceller.
    """
    db = SessionLocal()
    try:
        print("🔄 Sunucudan veri çekiliyor...")
        # IncludeUnitInfo=true ile çağırıyoruz (trusted_api.py içinde düzelttik)
        api_res = api_get_geosites()
        
        if not api_res['success']:
            print("❌ Sync Hatası:", api_res.get('error'))
            return False, "API Hatası"

        trusted_sites = api_res['data'] 
        updated_count = 0
        
        all_user_devices = db.query(Device).filter(Device.owner_id == user_id).all()
        device_map = {d.device_id: d for d in all_user_devices}

        # joinedload ile yerel cihazları da çek
        local_sites = db.query(GeoSite).options(joinedload(GeoSite.devices)).filter(GeoSite.owner_id == user_id).all()
        
        for l_site in local_sites:
            if not l_site.trusted_site_id: continue
            
            # API listesinde bu ID'yi bul
            remote_site = next((item for item in trusted_sites if item["Id"] == l_site.trusted_site_id), None)
            
            if remote_site:
                changes = False
                
                # 1. TEMEL BİLGİLER
                if remote_site.get("Radius") and l_site.radius_meters != remote_site["Radius"]:
                    l_site.radius_meters = remote_site["Radius"]
                    changes = True
                
                if remote_site.get("Latitude") and abs(l_site.latitude - remote_site["Latitude"]) > 0.00001:
                    l_site.latitude = remote_site["Latitude"]
                    changes = True
                    
                if remote_site.get("Longitude") and abs(l_site.longitude - remote_site["Longitude"]) > 0.00001:
                    l_site.longitude = remote_site["Longitude"]
                    changes = True
                
                # 2. CİHAZ LİSTESİNİ GÜNCELLE
                remote_units = remote_site.get("RegisteredUnits", [])
                remote_device_ids = []
                
                if remote_units:
                    for u in remote_units:
                        # API yapısına göre SerialNumber'ı al [cite: 107]
                        sn = u.get("SerialNumber")
                        if sn: remote_device_ids.append(str(sn))
                
                current_local_ids = [d.device_id for d in l_site.devices]
                
                # Listeler farklıysa güncelle
                if set(remote_device_ids) != set(current_local_ids):
                    print(f"   -> Cihaz Senkronizasyonu: {l_site.name}")
                    new_device_list = []
                    for did in remote_device_ids:
                        if did in device_map:
                            new_device_list.append(device_map[did])
                    
                    l_site.devices = new_device_list
                    changes = True

                if changes:
                    updated_count += 1
                    
        db.commit()
        return True, f"{updated_count} şantiye güncellendi."
        
    except Exception as e:
        print(f"Sync Exception: {e}")
        return False, str(e)
    finally:
        db.close()

        # backend/database.py dosyasının EN ALTINA ekle:

def toggle_geosite_alarm_status(site_id, is_active):
    """
    Şantiyenin alarm durumunu değiştirir ve Sunucuya bildirir.
    """
    db = SessionLocal()
    try:
        site = db.query(GeoSite).filter(GeoSite.site_id == site_id).first()
        if not site: return False

        # 1. Yerel DB Güncelle
        site.auto_enable_alarms = is_active
        db.commit()
        
        print(f"🔔 Alarm Durumu Değişti: {site.name} -> {'Aktif' if is_active else 'Pasif'}")

        # 2. Sunucuya Bildir (Kritik Kısım)
        if site.trusted_site_id and site.devices:
            device_ids = [d.device_id for d in site.devices]
            if device_ids:
                print(f"📡 Sunucudaki {len(device_ids)} cihazın alarm ayarı güncelleniyor...")
                # Cihazları "RegisterUnits=True" ama "Alarm" durumu yeni gelen değer (is_active) olacak şekilde güncelle
                api_update_registrations(
                    site.trusted_site_id,
                    device_ids,
                    register=True,
                    alarm=is_active
                )
        return True
    except Exception as e:
        print(f"Alarm Toggle Hatası: {e}")
        db.rollback()
        return False
    finally:
        db.close()

        # --- ŞİFRELEME MOTORU ---
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")

def get_password_hash(password):
    """Şifreyi kriptolar."""
    return pwd_context.hash(password)

def verify_password(plain_password, hashed_password):
    """Girilen şifre ile kayıtlı olanı kıyaslar."""
    return pwd_context.verify(plain_password, hashed_password)

# --- BU KISMI DOSYANIN EN ALTINA EKLE ---

def login_user(identifier, password):
    """
    Kullanıcı Adı VEYA E-Posta ile giriş yapılmasını sağlar.
    """
    db = SessionLocal()
    try:
        # Hem username hem email sütununda arama yapıyoruz (OR mantığı)
        user = db.query(User).filter(
            or_(User.username == identifier, User.email == identifier)
        ).first()
        
        if not user:
            return None
        
        # Şifre kontrolü
        if not verify_password(password, user.password_hash):
            return None
            
        return user
    finally:
        db.close()

def get_user_devices(user_id: str):
    """
    Kullanıcının yetkisine ve GRUBUNA göre cihazları getirir.
    """
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user: return []

        # 1. SÜPER ADMINLER (Tanrı Modu)
        # Bu listedeki herkes tüm cihazları görür.
        super_admins = ["s.ozsarac", "a.akkaya"]
        
        if user.username in super_admins:
            return db.query(Device).order_by(Device.is_active.desc()).all()

        # 2. GRUP VE MÜŞTERİLER
        # Mantık: "Cihazın Sahibinin Grubu" == "Benim Grubum" ise göster.
        # Ahmet (7153) -> Serkan Bey'in (7153) cihazlarını görür.
        # Chris (9840) -> Kendi (9840) cihazlarını görür.
        devices = db.query(Device).join(User, Device.owner_id == User.id)\
                    .filter(User.trusted_group_id == user.trusted_group_id)\
                    .order_by(Device.is_active.desc())\
                    .all()
        
        return devices
    finally:
        db.close()

def create_sub_user_invite(parent_user_id, new_username, new_email, new_name):
    """
    Mevcut kullanıcının (parent) grubuyla AYNI grupta yeni bir kullanıcı oluşturur.
    AYNI EMAIL veya AYNI KULLANICI ADI varsa işlemi reddeder.
    """
    db = SessionLocal()
    try:
        # 1. Ana kullanıcıyı bul
        parent = db.query(User).filter(User.id == parent_user_id).first()
        if not parent: return None, "Ana kullanıcı bulunamadı."
        
        # --- GÜVENLİK KONTROLÜ 1: KULLANICI ADI ---
        if db.query(User).filter(User.username == new_username).first():
            return None, "❌ Bu Kullanıcı Adı zaten alınmış. Lütfen başka bir ad seçin."

        # --- GÜVENLİK KONTROLÜ 2: E-POSTA (YENİ EKLENDİ) ---
        if db.query(User).filter(User.email == new_email).first():
            return None, "❌ Bu E-Posta adresi ile kayıtlı bir kullanıcı zaten var."

        # 3. Yeni Token ve ID
        import uuid
        invite_token = str(uuid.uuid4())
        new_id = f"u_{uuid.uuid4().hex[:8]}"
        
        # 4. Kullanıcıyı oluştur
        new_user = User(
            id=new_id,
            username=new_username,
            email=new_email,
            password_hash="PENDING_ACTIVATION", # Geçici
            role=parent.role,
            trusted_group_id=parent.trusted_group_id, # Aynı gruba ekle
            company_name=parent.company_name,
            full_name=new_name,
            reset_token=invite_token
        )
        db.add(new_user)
        db.commit()
        
        return invite_token, None
    except Exception as e:
        db.rollback()
        return None, str(e)
    finally:
        db.close()

def complete_user_registration(token, new_password):
    """
    Token ile gelen kullanıcının şifresini belirler ve hesabı aktif eder.
    """
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.reset_token == token).first()
        if not user:
            return False, "Geçersiz veya süresi dolmuş davet linki."
            
        # Şifreyi güncelle
        user.password_hash = get_password_hash(new_password)
        user.reset_token = None # Token'ı sil (tek kullanımlık)
        db.commit()
        return True, user.username
    except Exception as e:
        return False, str(e)
    finally:
        db.close()

# backend/database.py - EN ALTA EKLE

def get_invite_details(token):
    """
    Token geçerli mi diye bakar ve davet edilen kullanıcının bilgilerini döner.
    Böylece ekranda 'HKM Hidrolik sizi davet etti' yazabiliriz.
    """
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.reset_token == token).first()
        return user # Kullanıcı objesini döner (Bulamazsa None)
    finally:
        db.close()

def get_device_total_hours(device_id):
    """
    Cihazın UtilizationEvent tablosundaki TÜM çalışma sürelerini toplar.
    """
    db = SessionLocal()
    try:
        # raw_activity > 0 olan (yani çalışan) tüm kayıtların süresini topla
        total_sec = db.query(func.sum(UtilizationEvent.duration_sec)).filter(
            UtilizationEvent.device_id == device_id,
            UtilizationEvent.raw_activity > 0
        ).scalar()
        
        if total_sec:
            return round(total_sec / 3600, 1) # Saate çevir
        return 0.0
    except Exception as e:
        return 0.0
    finally:
        db.close()

def get_fleet_efficiency_metrics(user_id):
    """
    Kullanıcının filosunun GENEL verimlilik puanını ve geçen haftaya göre değişimini (trend) hesaplar.
    Verimlilik = (İdeal + Riskli Çalışma Süresi) / Toplam Çalışma Süresi
    """
    db = SessionLocal()
    try:
        # 1. Kullanıcının Cihazlarını Bul (get_user_devices mantığıyla aynı filtre)
        user = db.query(User).filter(User.id == user_id).first()
        if not user: return 0, 0
        
        if user.username == "s.ozsarac": # Patron hepsini görür
            devices = db.query(Device).all()
        else: # Grup filtresi
            devices = db.query(Device).join(User, Device.owner_id == User.id)\
                        .filter(User.trusted_group_id == user.trusted_group_id).all()
            
        device_ids = [d.device_id for d in devices]
        if not device_ids: return 0, 0

        # --- YARDIMCI HESAPLAMA FONKSİYONU ---
        def calculate_ratio(start_date, end_date):
            # Verilen tarih aralığındaki tüm cihazların çalışma olaylarını çek
            events = db.query(UtilizationEvent).filter(
                UtilizationEvent.device_id.in_(device_ids),
                UtilizationEvent.start_time >= start_date,
                UtilizationEvent.start_time < end_date,
                UtilizationEvent.raw_activity > 0 # Sadece çalışma
            ).all()
            
            total_sec = 0
            efficient_sec = 0
            
            for e in events:
                dur = e.duration_sec
                total_sec += dur
                # Verimlilik Kriteri: 0-40 saniye arası (İdeal + Riskli) verimli kabul edilir
                # (utilization_view.py'deki mantığın aynısı)
                if dur <= 40:
                    efficient_sec += dur
            
            if total_sec == 0: return 0
            return (efficient_sec / total_sec) * 100

        # 2. BU HAFTA (Son 7 Gün)
        now = datetime.utcnow()
        week_start = now - timedelta(days=7)
        current_score = calculate_ratio(week_start, now)
        
        # 3. GEÇEN HAFTA (7-14 Gün Önce)
        prev_week_start = now - timedelta(days=14)
        prev_score = calculate_ratio(prev_week_start, week_start)
        
        # 4. TREND HESAPLA (Fark)
        trend = current_score - prev_score
        
        return round(current_score, 1), round(trend, 1)

    except Exception as e:
        print(f"Efficiency Error: {e}")
        return 0, 0
    finally:
        db.close()