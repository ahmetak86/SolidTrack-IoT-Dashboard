# backend/check_users.py
from database import SessionLocal
from models import User

db = SessionLocal()
users = db.query(User).all()

print("\n--- VERİTABANINDAKİ KULLANICILAR ---")
for u in users:
    print(f"Kullanıcı: '{u.username}' | Şifre: '{u.password_hash}'")
print("------------------------------------\n")
db.close()