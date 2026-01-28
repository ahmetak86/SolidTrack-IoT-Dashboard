import sys
import os

# Proje ana dizinini yola ekle
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.database import SessionLocal, User, get_password_hash

def clean_database_users():
    db = SessionLocal()
    print("\n🧹 TEMİZLİK OPERASYONU BAŞLADI...")

    # 1. ADIM: Hatalı (Duplicate) Kullanıcıyı Bul ve Sil
    # Mantık: E-postası s.ozsarac@hkm.com.tr olan AMA kullanıcı adı 's.ozsarac' OLMAYAN kişiyi sil.
    bad_users = db.query(User).filter(
        User.email == "s.ozsarac@hkm.com.tr", 
        User.username != "s.ozsarac"
    ).all()
    
    if bad_users:
        for u in bad_users:
            print(f"❌ SİLİNİYOR: Kullanıcı Adı: {u.username} | ID: {u.id}")
            db.delete(u)
        db.commit()
    else:
        print("✅ Silinecek hatalı kullanıcı bulunamadı (Zaten temiz).")

    # 2. ADIM: Gerçek Hesabı (s.ozsarac) Garantiye Al
    real_user = db.query(User).filter(User.username == "s.ozsarac").first()
    
    if real_user:
        print(f"🔄 GÜNCELLENİYOR: {real_user.username}")
        real_user.email = "s.ozsarac@hkm.com.tr"
        real_user.password_hash = get_password_hash("1")
        real_user.role = "Admin"
        real_user.company_name = "HKM Hidrolik"
        real_user.full_name = "Serkan Özsaraç"
        real_user.trusted_group_id = 7153
        
        db.commit()
        print("✅ Ana hesap ayarları (Email, Şifre, Yetki) doğrulandı.")
    else:
        print("⚠️ UYARI: 's.ozsarac' kullanıcısı bulunamadı! (Önce force_super_admin.py çalıştırılmalıydı)")

    db.close()
    print("\n🚀 İŞLEM TAMAMLANDI.")
    print("------------------------------------------------")
    print("Artık şu bilgilerle giriş yapabilirsin:")
    print("👤 Kullanıcı: s.ozsarac")
    print("📧 VEYA Email: s.ozsarac@hkm.com.tr")
    print("🔑 Şifre:      1")
    print("------------------------------------------------")

if __name__ == "__main__":
    clean_database_users()