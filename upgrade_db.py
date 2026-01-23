import sqlite3
import os

# Veritabanı dosyasının yolu
# Eğer backend klasöründeyse 'backend/solidtrack.db' olarak değiştirin
DB_FILE = "solidtrack.db" 

if not os.path.exists(DB_FILE):
    # Belki backend klasöründedir, orayı kontrol et
    if os.path.exists(os.path.join("backend", "solidtrack.db")):
        DB_FILE = os.path.join("backend", "solidtrack.db")
    else:
        print(f"❌ HATA: {DB_FILE} dosyası bulunamadı! Lütfen dosya yolunu kontrol edin.")
        exit()

print(f"🔧 Veritabanı Güncelleniyor: {DB_FILE}")

try:
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Yeni kolon ekleme komutu
    # raw_activity kolonu ekleniyor, varsayılan değeri 1 yapıyoruz.
    cursor.execute("ALTER TABLE utilization_events ADD COLUMN raw_activity INTEGER DEFAULT 1")
    
    conn.commit()
    print("✅ BAŞARILI: 'raw_activity' kolonu eklendi. Verileriniz güvende.")
    
except sqlite3.OperationalError as e:
    if "duplicate column" in str(e):
        print("ℹ️ BİLGİ: Bu kolon zaten ekli, tekrar işlem yapmaya gerek yok.")
    else:
        print(f"❌ Bir hata oluştu: {e}")
finally:
    conn.close()