# backend/fix_data.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Device
import random
import os

# --- AKILLI YOL ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "solidtrack.db")
print(f"Hedef Veritabanı: {DB_PATH}")

engine = create_engine(f"sqlite:///{DB_PATH}")
Session = sessionmaker(bind=engine)
session = Session()

# EXCEL LİSTESİNDEN OLUŞTURULAN ANAHTAR KELİMELER
# Sol taraf: Aranan Kelime (Hem Türkçe hem İngilizce varyasyonları)
# Sağ taraf: atanacak icon_type (dosya adı uzantısız)
KEYWORD_TO_ICON = {
    # İş Makineleri
    "kırıcı": "hydraulic_breaker", "breaker": "hydraulic_breaker",
    "burgu": "hydraulic_auger", "auger": "hydraulic_auger",
    "makas": "hydraulic_shear", "shear": "hydraulic_shear",
    "beton kesici": "concrete_cutter", "beton kesme": "concrete_cutter", "concrete cutter": "concrete_cutter",
    "tambur": "drum_cutter", "drum": "drum_cutter",
    "pulveriz": "pulverizer",
    "kütük": "log_grapple", "log grapple": "log_grapple",
    "ekskavatör kıskacı": "excavator_grapple", "excavator grapple": "excavator_grapple",
    "delici": "hydraulic_drifter", "drifter": "hydraulic_drifter",
    "kova": "crusher_bucket", "bucket": "crusher_bucket",
    "riper": "ripper", "ripper": "ripper",
    
    # Ana Makineler
    "ekskavatör": "excavator", "excavator": "excavator", "cat": "excavator",
    "kamyon": "truck", "truck": "truck", "ford": "truck", "mercedes": "truck",
    "mikser": "concrete_mixer", "mixer": "concrete_mixer", "beton mikseri": "concrete_mixer",
    "forklift": "forklift",
    "jeneratör": "generator", "generator": "generator",
    "buldozer": "bulldozer", "bulldozer": "bulldozer", "dozer": "bulldozer",
    "damper": "dump_truck", "dump": "dump_truck",
    "traktör": "tractor", "tractor": "tractor",
    "mobil vinç": "mobile_crane", "mobile crane": "mobile_crane",
    "kule vinç": "tower_crane", "tower crane": "tower_crane",
    "silindir": "roller", "kompaktör": "roller", "roller": "roller",
    "kazıcı": "backhoe", "bekoloder": "backhoe", "backhoe": "backhoe", "jcb": "backhoe",
    "makaslı": "scissor_lift", "lift": "scissor_lift", "platform": "scissor_lift",
    "pikap": "pickup", "pickup": "pickup",
    "ışık": "light_tower", "light": "light_tower"
}

def fix_and_seed_db():
    print("🔧 Veritabanı İkon Eşleştirmesi Başlıyor (Excel Listesine Göre)...")
    
    devices = session.query(Device).all()
    count_updated = 0
    count_null_fix = 0

    for d in devices:
        # 1. NULL Saat Düzeltmesi
        if d.initial_hours_offset is None:
            d.initial_hours_offset = random.randint(100, 5000)
            count_null_fix += 1

        # 2. İsimden Tip Tahmini
        unit_name_lower = d.unit_name.lower()
        found_icon = None
        
        # En uzun anahtar kelimeyi önce bulmak için sıralıyoruz (örn: "beton kesici" > "kesici")
        sorted_keys = sorted(KEYWORD_TO_ICON.keys(), key=len, reverse=True)
        
        for key in sorted_keys:
            if key in unit_name_lower:
                found_icon = KEYWORD_TO_ICON[key]
                break
        
        if found_icon:
            d.icon_type = found_icon
            count_updated += 1
        elif not d.icon_type:
            d.icon_type = "truck" # Varsayılan

    session.commit()
    print(f"✅ BİTTİ!")
    print(f"   - {count_null_fix} cihazın saati (NoneType) onarıldı.")
    print(f"   - {count_updated} cihazın ikonu ismine göre (Excel listesi) güncellendi.")

if __name__ == "__main__":
    fix_and_seed_db()