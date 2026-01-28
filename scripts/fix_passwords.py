import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from backend.database import SessionLocal, User, get_password_hash

db = SessionLocal()
users = db.query(User).all()
print("🔐 Şifreler Onarılıyor...")

for u in users:
    # Hepsini '1' yapıyoruz (pbkdf2 formatında)
    u.password_hash = get_password_hash("1")
    print(f" -> {u.username} şifresi güncellendi.")

db.commit()
db.close()
print("✅ Tamamlandı. Artık '1' şifresiyle giriş yapabilirsin.")