# frontend/utils.py
from datetime import datetime
import pytz
from timezonefinder import TimezoneFinder

# Koordinattan saat dilimi bulan motor
tf = TimezoneFinder()

def get_timezone_from_coords(lat, lon):
    """
    Verilen koordinatın saat dilimini (örn: 'America/New_York') bulur.
    """
    try:
        if lat is None or lon is None: return None
        # timezonefinder kütüphanesi ile konumdan bölgeyi bul
        timezone_str = tf.timezone_at(lng=lon, lat=lat)
        return timezone_str
    except:
        return None

def convert_to_user_time(dt_utc, user_timezone_str="Europe/Istanbul"):
    """
    UTC verisini, kullanıcının seçtiği saat dilimine çevirir.
    """
    if not dt_utc: return None
    
    # Gelen veri naive (tz bilgisi yok) ise önce UTC olduğunu belirtelim
    if dt_utc.tzinfo is None:
        dt_utc = pytz.utc.localize(dt_utc)
    
    try:
        # Kullanıcının tercihi (örn: 'Asia/Tokyo')
        target_tz = pytz.timezone(user_timezone_str)
        # Çevir
        local_dt = dt_utc.astimezone(target_tz)
        return local_dt
    except:
        # Hata olursa (örn: geçersiz timezone stringi) UTC dön
        return dt_utc

def format_date_for_ui(dt_utc, user_timezone_str="Europe/Istanbul", include_offset=True):
    """
    Ekrana basılacak son formatı üretir.
    Çıktı Örneği: "29.01.2026 14:30 (UTC+03:00)"
    """
    if not dt_utc: return "-"
    
    local_dt = convert_to_user_time(dt_utc, user_timezone_str)
    
    # Tarih Formatı (İsteğe göre değiştirilebilir)
    date_str = local_dt.strftime("%d.%m.%Y %H:%M")
    
    if include_offset:
        # UTC Ofsetini hesapla (Örn: +0300 -> +03:00 formatına çevir)
        offset = local_dt.strftime("%z") # +0300
        formatted_offset = f"UTC{offset[:3]}:{offset[3:]}" # UTC+03:00
        return f"{date_str} ({formatted_offset})"
    
    return date_str