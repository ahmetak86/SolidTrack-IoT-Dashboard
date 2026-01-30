# scripts/export_users_excel.py
import sys
import os
import pandas as pd

# Ana dizini tanıt
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.database import SessionLocal
from backend.models import User

def export_users():
    db = SessionLocal()
    users = db.query(User).all()
    
    data = []
    for u in users:
        # Yetki Açıklaması
        permission_desc = "Bilinmiyor"
        if u.role == "Admin":
            permission_desc = "TÜM FİLO (Full Yetki)"
        elif u.role == "User":
            permission_desc = f"Sadece Grup ID: {u.trusted_group_id}"
            
        data.append({
            "Rol": u.role,
            "Ad Soyad": u.full_name,
            "Kullanıcı Adı": u.username,
            "E-Posta": u.email,
            "Şifre (Hashlenmiş)": "**** (Varsayılan: 1)",
            "Grup ID": u.trusted_group_id,
            "Şirket": u.company_name,
            "Erişim Yetkisi": permission_desc
        })
    
    df = pd.DataFrame(data)
    
    # Dosyayı kaydet
    filename = "SolidTrack_Kullanici_Listesi.xlsx"
    df.to_excel(filename, index=False)
    
    print(f"✅ Excel dosyası oluşturuldu: {filename}")
    db.close()

if __name__ == "__main__":
    export_users()