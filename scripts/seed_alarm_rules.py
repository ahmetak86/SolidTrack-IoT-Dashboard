# scripts/seed_alarm_rules.py (FULL VERSİYON - 24 SATIR)
import sys
import os

# Yolu ayarla
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

from backend.database import SessionLocal, engine
from backend.models import AlarmRule, Base

# EXCEL'DEKİ TAM LİSTE
FULL_RULES = [
    # --- 1. GÜVENLİK (PİL & HABERLEŞME) ---
    {"rule_name": "Düşük Pil (Uyarı)", "parameter": "battery_level", "operator": "<", "threshold": 20.0, "severity": "Warning", "description": "Pil seviyesi %20 altına düştü."},
    {"rule_name": "Düşük Pil (Kritik)", "parameter": "battery_level", "operator": "<", "threshold": 10.0, "severity": "Critical", "description": "Pil seviyesi %10 kritik seviyede!"},
    {"rule_name": "Haberleşme Yok (3 Gün)", "parameter": "last_signal_hours", "operator": ">", "threshold": 72.0, "severity": "Warning", "description": "Cihazdan 3 gündür sinyal alınamıyor."},
    {"rule_name": "Haberleşme Yok (7 Gün)", "parameter": "last_signal_hours", "operator": ">", "threshold": 168.0, "severity": "Critical", "description": "Cihazdan 7 gündür sinyal yok! Kayıp riski."},
    
    # --- 2. HAREKET & GEOFENCE ---
    {"rule_name": "Hareketsizlik (3 Gün)", "parameter": "last_movement_days", "operator": ">", "threshold": 3.0, "severity": "Warning", "description": "Makine 3 gündür yatmada."},
    {"rule_name": "Hareketsizlik (10 Gün)", "parameter": "last_movement_days", "operator": ">", "threshold": 10.0, "severity": "Critical", "description": "Makine 10 gündür çalıştırılmadı."},
    {"rule_name": "Geofence İhlali (Çıkış)", "parameter": "geofence_status", "operator": "==", "threshold": 0, "severity": "Critical", "description": "Cihaz şantiye sahası dışına çıktı!"},
    {"rule_name": "Geofence Giriş", "parameter": "geofence_status", "operator": "==", "threshold": 1, "severity": "Info", "description": "Cihaz şantiye sahasına giriş yaptı."},
    
    # --- 3. ARAÇ (KAMYON) KURALLARI ---
    {"rule_name": "Aşırı Hız (Limit)", "parameter": "speed_kmh", "operator": ">", "threshold": 90.0, "severity": "Warning", "description": "Hız limiti (90 km/s) aşıldı."},
    {"rule_name": "Aşırı Hız (Tehlike)", "parameter": "speed_kmh", "operator": ">", "threshold": 120.0, "severity": "Critical", "description": "Aşırı hız! (120 km/s üzeri)."},
    
    # --- 4. KIRICI (BREAKER) KULLANIM HATALARI ---
    # Excel notuna göre: İsimler saniyelerle dinamik.
    {"rule_name": "Riskli Çalışma (Isınma)", "parameter": "continuous_work_sec", "operator": ">", "threshold": 20.0, "severity": "Info", "description": "20 sn üzeri kesintisiz çalışma."},
    {"rule_name": "Uç Şişirme Riski", "parameter": "continuous_work_sec", "operator": ">", "threshold": 40.0, "severity": "Warning", "description": "40 sn üzeri çalışma! Uç şişirme riski."},
    {"rule_name": "Operatör Hatası (Kırılma)", "parameter": "continuous_work_sec", "operator": ">", "threshold": 80.0, "severity": "Critical", "description": "80 sn üzeri çalışma! Piston/Uç kırma riski."},
    
    # --- 5. DARBE (SHOCK) ---
    {"rule_name": "Darbe Algılandı (Hafif)", "parameter": "shock_g", "operator": ">", "threshold": 4.0, "severity": "Warning", "description": "Cihazda 4G üzeri darbe algılandı."},
    {"rule_name": "Darbe Algılandı (Kaza)", "parameter": "shock_g", "operator": ">", "threshold": 8.0, "severity": "Critical", "description": "8G üzeri şiddetli darbe! Kaza veya düşme riski."},
    
    # --- 6. BAKIM (MAINTENANCE) - Varsayılanlar ---
    # Not: Cihaz eklendiğinde bu değerler cihaza kopyalanacak.
    {"rule_name": "Periyodik Bakım (Yaklaşan)", "parameter": "maintenance_hours_left", "operator": "<", "threshold": 20.0, "severity": "Warning", "description": "Bakıma 20 saatten az kaldı."},
    {"rule_name": "Periyodik Bakım (Geçmiş)", "parameter": "maintenance_hours_left", "operator": "<", "threshold": 0.0, "severity": "Critical", "description": "Bakım saati geçti! Acil servis gerekli."},
    
    # --- 7. MESAİ DIŞI ---
    {"rule_name": "Mesai Dışı Çalışma", "parameter": "is_working_hours", "operator": "==", "threshold": 0, "severity": "Critical", "description": "İzin verilen saatler dışında çalışma algılandı."}
]

def seed_rules():
    db = SessionLocal()
    try:
        print("🌱 Alarm Kuralları (Excel Verisi) işleniyor...")
        added = 0
        updated = 0

        for rule in FULL_RULES:
            existing = db.query(AlarmRule).filter(AlarmRule.rule_name == rule["rule_name"]).first()
            if existing:
                existing.parameter = rule["parameter"]
                existing.operator = rule["operator"]
                existing.threshold = rule["threshold"]
                existing.severity = rule["severity"]
                existing.description = rule["description"]
                updated += 1
            else:
                new_rule = AlarmRule(**rule)
                db.add(new_rule)
                added += 1
        
        db.commit()
        print(f"✅ İŞLEM TAMAM: {added} Yeni Kural, {updated} Güncelleme.")
        
    except Exception as e:
        print(f"❌ HATA: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed_rules()