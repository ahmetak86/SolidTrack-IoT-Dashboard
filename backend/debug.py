# backend/debug.py
from sqlalchemy import create_engine, text

# Veritabanına bağlan
engine = create_engine("sqlite:///solidtrack.db")

print("\n--- VERİTABANI RAPORU ---")
try:
    with engine.connect() as con:
        # Kullanıcıları çek
        rs = con.execute(text("SELECT username, password_hash FROM users"))
        rows = rs.fetchall()
        
        if not rows:
            print("❌ Veritabanı BOŞ! Hiç kullanıcı yok.")
        
        for row in rows:
            kullanici = row[0]
            sifre = row[1]
            # Tırnak işaretleri içinde yazdırıyorum ki boşluk varsa görelim
            print(f"Kullanıcı: '{kullanici}' | Şifre: '{sifre}'")
            
            if sifre == "123456":
                print("   ✅ Bu şifre DOĞRU, giriş yapabilmen lazım.")
            elif sifre == "123456.0":
                print("   ❌ HATA: Şifre ondalıklı sayı (float) olarak kalmış.")
            elif " " in sifre:
                print("   ❌ HATA: Şifrede boşluk var.")
            else:
                print(f"   ⚠️ Şifre '{sifre}' olarak kayıtlı.")

except Exception as e:
    print(f"HATA OLUŞTU: {e}")
    print("Veritabanı dosyası (solidtrack.db) bulunamadı veya okunamadı.")

print("-------------------------\n")