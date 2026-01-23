import sys
import os
from sqlalchemy import text

# Backend klasörünü bulması için yol ayarı
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from backend.database import SessionLocal

def clean_events():
    print("🧹 Temizlik başlıyor...")
    db = SessionLocal()
    try:
        # UtilizationEvent tablosundaki TÜM verileri siler (Cihazlar ve Kullanıcılar kalır)
        # SQLite'da tabloyu tamamen boşaltmak için DELETE kullanılır
        rows_deleted = db.execute(text("DELETE FROM utilization_events"))
        
        db.commit()
        print(f"✅ BİTTİ: utilization_events tablosu tamamen temizlendi.")
        print("   -> Artık sync dosyasını çalıştırıp temiz veri çekebilirsin.")
        
    except Exception as e:
        db.rollback()
        print(f"❌ Hata oluştu: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    clean_events()