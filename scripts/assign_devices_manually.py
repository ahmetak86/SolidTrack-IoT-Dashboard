# scripts/assign_devices_manually.py (ADMİN PANELİ SİMÜLASYONU)
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.database import SessionLocal
from backend.models import Device

def assign_devices():
    db = SessionLocal()
    print("📋 Cihaz Atama İşlemi Başlıyor...")

    # 1. TRÇAN CİHAZINI 'akkaya' KULLANICISINA VER
    target_device = db.query(Device).filter(Device.unit_name == "TRÇAN BIG R250 #1").first()
    if target_device:
        target_device.owner_id = "akkaya"
        print(f"✅ {target_device.unit_name} -> 'akkaya' kullanıcısına atandı.")
    else:
        print("⚠️ TRÇAN cihazı bulunamadı.")

    # 2. 9840 GRUBUNDAKİLERİ 'chris' KULLANICISINA VER
    # Not: Burada Trusted'dan gelen grup bilgisini bilmediğimiz için 
    # (Robot DB'ye Grup ID yazmıyor) manuel isimle veya şimdilik böyle bırakıyoruz.
    # Eğer cihaz listesinde Chris'in cihazlarının adını biliyorsan buraya ekleyebilirsin.
    
    # 3. GERİ KALAN HER ŞEY 's.ozsarac' ÜZERİNDE KALSIN
    
    db.commit()
    db.close()
    print("🏁 Atama Tamamlandı. Robot artık bu sahipliklere saygı duyacak.")

if __name__ == "__main__":
    assign_devices()