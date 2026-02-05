# scripts/create_fake_alarms.py
import sys
import os
from datetime import datetime, timedelta
import random

# Yolu ayarla
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

from backend.database import SessionLocal, engine
from backend.models import Alarm, Device, User

def create_fakes():
    db = SessionLocal()
    try:
        # 1. Önce alarm atayacak bir cihaz bulalım
        device = db.query(Device).first()
        if not device:
            print("❌ Hiç cihaz bulunamadı! Önce sisteme bir cihaz eklemelisin.")
            # Geçici cihaz oluşturabiliriz ama senin sisteminde zaten vardır.
            return

        print(f"🎯 Hedef Cihaz: {device.unit_name} ({device.device_id})")

        # 2. Alarm Tipleri (Excelindeki kategorilere göre)
        scenarios = [
            {"type": "LowBattery", "sev": "Warning", "desc": "Pil seviyesi %18. Düşük şarj uyarısı.", "status": "Active"},
            {"type": "Overspeed", "sev": "Critical", "desc": "Hız limiti aşıldı: 110 km/s (Limit: 90)", "status": "Active"},
            {"type": "GeofenceExit", "sev": "Critical", "desc": "Şantiye sahası dışına çıkıldı (Bölge: Merkez)", "status": "Active"},
            {"type": "Maintenance", "sev": "Warning", "desc": "Periyodik Bakım: 250 saat bakımı geldi.", "status": "Active"},
            {"type": "Shock", "sev": "Critical", "desc": "Kritik Darbe Algılandı: 12G", "status": "Resolved"}, # Çözülmüş örnek
            {"type": "Inactivity", "sev": "Info", "desc": "Cihaz 3 gündür hareket etmedi.", "status": "Active"},
            {"type": "AfterHours", "sev": "Critical", "desc": "Mesai dışı çalışma algılandı (Saat: 03:45).", "status": "Active"},
            {"type": "NoCommunication", "sev": "Critical", "desc": "Cihazdan 48 saattir sinyal alınamıyor.", "status": "Active"},
            {"type": "Misuse", "sev": "Critical", "desc": "Operatör Hatası: Uç Şişirme Riski", "status": "Active"},
            # Operatörlü örnek
            {"type": "Overspeed", "sev": "Warning", "desc": "Hız ihlali (Limit sınırında)", "status": "Active", "op": "Ahmet Yılmaz"}
        ]

        # 3. Alarmleri Ekle
        count = 0
        for sc in scenarios:
            # Rastgele bir zaman (Son 24 saat içinde)
            rand_min = random.randint(1, 1400)
            start_t = datetime.now() - timedelta(minutes=rand_min)
            
            alarm = Alarm(
                device_id=device.device_id,
                alarm_type=sc["type"],
                severity=sc["sev"],
                start_time=start_t,
                status=sc["status"],
                description=sc["desc"],
                operator=sc.get("op", None) # Varsa operatör ekle
            )
            db.add(alarm)
            count += 1

        db.commit()
        print(f"✅ Başarılı! {count} adet fake alarm '{device.unit_name}' cihazına eklendi.")
        print("🚀 Şimdi Admin Paneli > Alarm Merkezi sayfasına gidip F5 yapabilirsin.")

    except Exception as e:
        print(f"Hata: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    create_fakes()