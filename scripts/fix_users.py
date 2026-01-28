import sys
import os

# Proje ana dizinini yola ekle
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.database import SessionLocal, User, get_password_hash

def final_user_fix():
    db = SessionLocal()
    print("🕵️  HESAP YAPILANDIRMASI BAŞLATILIYOR...")
    
    target_username = "s.ozsarac"
    target_email = "s.ozsarac@hkm.com.tr"
    target_pass = "1"
    
    # ---------------------------------------------------------
    # ADIM 1: GEREKSİZLERİ SİL (Çakışan Hesap Temizliği)
    # ---------------------------------------------------------
    # Kural: Email'i bizimkiyle aynı olan ama kullanıcı adı 's.ozsarac' OLMAYAN herkesi sil.
    duplicates = db.query(User).filter(
        User.email == target_email,
        User.username != target_username
    ).all()
    
    if duplicates:
        print(f"⚠️  {len(duplicates)} adet çakışan (hatalı) hesap bulundu ve siliniyor:")
        for d in duplicates:
            print(f"    🗑️  SILINDI: {d.username} (ID: {d.id})")
            db.delete(d)
        db.commit()
    else:
        print("✅  Çakışan hesap bulunamadı. Temiz.")

    # ---------------------------------------------------------
    # ADIM 2: ANA HESABI SABİTLE (s.ozsarac)
    # ---------------------------------------------------------
    admin_user = db.query(User).filter(User.username == target_username).first()
    
    if not admin_user:
        print(f"➕  '{target_username}' hesabı bulunamadı, sıfırdan oluşturuluyor...")
        admin_user = User(
            id="admin_hkm_master",
            username=target_username,
            role="Admin",
            trusted_group_id=7153,
            company_name="HKM Hidrolik",
            full_name="Serkan Özsaraç"
        )
        db.add(admin_user)
    else:
        print(f"🔄  '{target_username}' hesabı bulundu, ayarları güncelleniyor...")

    # Özellikleri kesin olarak ayarla (Şifre, Email, Yetki)
    admin_user.email = target_email
    admin_user.password_hash = get_password_hash(target_pass)
    admin_user.role = "Admin" # Yetkiyi de garantiye alalım
    
    db.commit()
    print("-" * 50)
    print(f"✅  İŞLEM TAMAMLANDI!")
    print(f"👤  Kullanıcı: {target_username}")
    print(f"📧  Email:     {target_email}")
    print(f"🔑  Şifre:     {target_pass}")
    print("-" * 50)
    
    db.close()

if __name__ == "__main__":
    final_user_fix()