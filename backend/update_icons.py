# backend/update_icons.py
from sqlalchemy import create_engine, text
import random

# DB Bağlantısı
engine = create_engine("sqlite:///solidtrack.db")

# 1. Sütun Ekleme (Eğer yoksa)
try:
    with engine.connect() as con:
        con.execute(text("ALTER TABLE devices ADD COLUMN icon_type VARCHAR DEFAULT 'truck'"))
        print("✅ 'icon_type' sütunu başarıyla eklendi.")
except Exception as e:
    print("ℹ️ Sütun zaten var veya bir hata oluştu (Önemli değil):", e)

# 2. Rastgele İkon Atama (Test için)
icon_list = [
    "excavator", "truck", "mixer", "dozer", 
    "hydraulic_breaker", "generator", "forklift"
]

try:
    with engine.connect() as con:
        # Cihaz ID'lerini çek
        result = con.execute(text("SELECT device_id FROM devices"))
        devices = result.fetchall()
        
        for d in devices:
            # Rastgele bir ikon seç
            rnd_icon = random.choice(icon_list)
            # Update sorgusu
            sql = text("UPDATE devices SET icon_type = :icn WHERE device_id = :did")
            con.execute(sql, {"icn": rnd_icon, "did": d[0]})
            print(f"🚜 Cihaz {d[0]} -> {rnd_icon} olarak güncellendi.")
        
        con.commit()
    print("🎉 Tüm cihazlara ikon atandı!")
except Exception as e:
    print("Hata:", e)