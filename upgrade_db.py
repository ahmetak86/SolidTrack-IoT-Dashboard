import sys
import os
import logging
from sqlalchemy import text, inspect

# Backend klasörünü yola ekle
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from database import engine, Base
# Modelleri import ediyoruz
from models import Device, AlarmEvent, Setting

# Loglama ayarı
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def upgrade_database():
    """
    Mevcut veritabanı şemasını verileri silmeden günceller.
    SQLite sürüm uyumsuzluğunu aşmak için önce kontrol eder, sonra ekler.
    """
    logger.info("Veritabanı güncellemesi başlatılıyor...")

    # Veritabanı yapısını incelemek için Inspector kullanıyoruz
    inspector = inspect(engine)

    with engine.connect() as connection:
        trans = connection.begin()
        try:
            # ---------------------------------------------------------
            # 1. DEVICES TABLOSU KONTROLÜ
            # ---------------------------------------------------------
            if inspector.has_table("devices"):
                # Mevcut sütunları al
                columns = [col['name'] for col in inspector.get_columns("devices")]
                
                if "last_maintenance_hour" not in columns:
                    logger.info("'devices' tablosuna 'last_maintenance_hour' ekleniyor...")
                    # 'IF NOT EXISTS' kullanmadan direkt ekliyoruz çünkü yukarıda olmadığını teyit ettik
                    connection.execute(text("ALTER TABLE devices ADD COLUMN last_maintenance_hour FLOAT DEFAULT 0.0"))
                else:
                    logger.info("'devices' tablosunda 'last_maintenance_hour' zaten var. Atlanıyor.")
            
            # ---------------------------------------------------------
            # 2. ALARM_EVENTS TABLOSU KONTROLÜ
            # ---------------------------------------------------------
            if inspector.has_table("alarm_events"):
                # Mevcut sütunları al
                alarm_columns = [col['name'] for col in inspector.get_columns("alarm_events")]
                
                if "rule_id" not in alarm_columns:
                    logger.info("'alarm_events' tablosuna 'rule_id' ekleniyor...")
                    connection.execute(text("ALTER TABLE alarm_events ADD COLUMN rule_id VARCHAR"))
                else:
                    logger.info("'alarm_events' tablosunda 'rule_id' zaten var. Atlanıyor.")

            trans.commit()
            logger.info("Sütun ekleme işlemleri başarılı.")
            
        except Exception as e:
            trans.rollback()
            logger.error(f"Sütun eklerken hata oluştu: {e}")
            return

    # ---------------------------------------------------------
    # 3. YENİ TABLOLARI OLUŞTURMA (Settings vb.)
    # ---------------------------------------------------------
    logger.info("Eksik tablolar kontrol ediliyor ve oluşturuluyor...")
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Tablo oluşturma işlemleri tamamlandı.")
    except Exception as e:
        logger.error(f"Tablo oluştururken hata: {e}")

    logger.info("🚀 Veritabanı güncellemesi başarıyla tamamlandı!")

if __name__ == "__main__":
    upgrade_database()