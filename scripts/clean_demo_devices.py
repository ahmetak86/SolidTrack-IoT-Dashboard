# scripts/clean_demo_devices.py (PATH DÜZELTİLMİŞ VERSİYON)
import sys
import os

# 1. Mevcut klasörü bul (scripts)
current_dir = os.path.dirname(os.path.abspath(__file__))
# 2. Bir üst klasöre çık (SolidTrack ana dizini)
parent_dir = os.path.dirname(current_dir)
# 3. Yola ekle ki 'backend' modülünü bulabilsin
sys.path.append(parent_dir)

from backend.database import SessionLocal
from backend.models import Device

def clean_demos():
    print("🧹 Temizlik Başlıyor...")
    db = SessionLocal()
    
    # Silinecek demo cihaz isimleri
    demo_names = ["Demo Device", "Kova Atasmani", "Kova Ataşmanı"]
    
    demos = db.query(Device).filter(Device.unit_name.in_(demo_names)).all()
    
    if not demos:
        print("✅ Zaten silinmiş veya demo cihaz bulunamadı.")
    else:
        for d in demos:
            db.delete(d)
            print(f"🗑️ SİLİNDİ: {d.unit_name}")
        db.commit()
    
    db.close()
    print("🏁 İşlem Tamam.")

if __name__ == "__main__":
    clean_demos()