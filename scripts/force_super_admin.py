import sys
import os

# Proje ana dizinini yola ekle
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.database import SessionLocal, User, Device, get_password_hash

def force_fix():
    db = SessionLocal()
    print("👑 SÜPER ADMIN VE CİHAZ KURTARMA OPERASYONU...")

    # 1. HEDEF EMAIL İLE KİM VARSA ONU BUL (HKM Trusted Sync olabilir)
    target_email = "s.ozsarac@hkm.com.tr"
    user = db.query(User).filter(User.email == target_email).first()

    if not user:
        print("❌ Hata: Bu mail adresiyle kayıtlı kimse yok! Lütfen önce sync yapın.")
        return

    print(f"🕵️  Bulunan Kullanıcı: {user.username} (ID: {user.id})")
    print("🔄  Bu hesap 'Süper Admin'e dönüştürülüyor...")

    # 2. KİMLİK BİLGİLERİNİ GÜNCELLE
    user.username = "s.ozsarac"         # Kritik: İsim bu olmazsa cihazları göremez
    user.full_name = "Serkan Özsaraç"   # Ekranda güzel görünsün
    user.role = "Admin"
    user.trusted_group_id = 7153        # HKM Grubu
    user.company_name = "HKM Hidrolik"
    user.password_hash = get_password_hash("1") # Şifreyi de 1 yapalım garanti olsun
    
    # 3. TÜM CİHAZLARI BU ADAMA ZİMMETLE
    # (Böylece Demo veya Gerçek fark etmeksizin hepsi senin listene düşer)
    all_devices = db.query(Device).all()
    print(f"🚜  Toplam {len(all_devices)} cihaz bu hesaba aktarılıyor...")
    
    for dev in all_devices:
        dev.owner_id = user.id
    
    db.commit()
    db.close()
    
    print("\n✅ İŞLEM BAŞARILI!")
    print("------------------------------------------------")
    print("Artık şu bilgilerle giriş yapabilirsiniz:")
    print("👤 Kullanıcı Adı: s.ozsarac")
    print("📧 E-Posta:       s.ozsarac@hkm.com.tr")
    print("🔑 Şifre:         1")
    print("------------------------------------------------")
    print("Not: Giriş yaptıktan sonra SOL ÜSTTE 'Serkan Özsaraç' yazdığını görmelisin.")

if __name__ == "__main__":
    force_fix()