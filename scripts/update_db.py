# update_db.py
from backend.database import SessionLocal, Device

def update_address():
    db = SessionLocal()
    # "Kirici #1" cihazının ID'si (CSV'den bildiğimiz ID)
    target_id = "865456056700519" 
    
    device = db.query(Device).filter(Device.device_id == target_id).first()
    
    if device:
        print(f"Eski Adres: {device.address}")
        # Senin verdiğin gerçek adres
        device.address = "Caferağa, Dr. Şakirpaşa Sk., 34710 Kadıköy/İstanbul"
        db.commit()
        print(f"✅ Yeni Adres İşlendi: {device.address}")
    else:
        print("❌ Cihaz bulunamadı!")
    
    db.close()

if __name__ == "__main__":
    update_address()