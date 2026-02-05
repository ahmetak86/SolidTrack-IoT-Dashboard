import sys
import os

# 1. Proje ana dizinini yola ekleyelim ki 'backend' modülünü bulabilsin
current_dir = os.path.dirname(os.path.abspath(__file__))
# Eğer scripts klasörü içindeysek bir üst dizine, ana dizindeysek olduğu yere bakmalı
parent_dir = os.path.dirname(current_dir) if "scripts" in current_dir else current_dir
sys.path.append(parent_dir)

print(f"📂 Çalışma Dizini: {parent_dir}")

try:
    from backend.database import engine
    from backend.models import Base
    
    # Yeni eklediğimiz modellerin de import edildiğinden emin olalım
    from backend.models import Alarm, AlarmRule, Device, DeviceDocument

    print("🔄 Veritabanı şeması taranıyor...")

    # BU SİHİRLİ KOMUT:
    # Veritabanına bakar, models.py'da olup da veritabanında OLMAYAN tabloları oluşturur.
    # Mevcut tablolara (Users, Devices vb.) ve içindeki verilere ASLA zarar vermez.
    Base.metadata.create_all(bind=engine)

    print("✅ BAŞARILI: Yeni tablolar (Alarm, AlarmRule) oluşturuldu/güncellendi.")
    print("🚀 Artık uygulamayı çalıştırabilirsiniz.")

except Exception as e:
    print(f"❌ HATA OLUŞTU: {e}")
    input("Kapatmak için Enter'a basın...")