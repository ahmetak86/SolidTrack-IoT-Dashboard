# frontend/views/admin_users.py (PURE INTERNAL VERSION)
import streamlit as st
import pandas as pd
import sys
import os
import uuid

# Backend yolları
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from backend.database import SessionLocal, User, get_password_hash

def load_view(user):
    st.title("👥 Müşteri ve Bayi Yönetimi (Dahili)")
    st.markdown("Buradan sisteme yeni bayiler veya kullanıcılar ekleyebilirsiniz. Bu kullanıcılar **sadece SolidTrack** üzerinde oluşturulur.")

    if user.role != "Admin":
        st.error("Bu sayfaya erişim yetkiniz yok.")
        return

    # --- SEKME YAPISI ---
    tab_create, tab_list = st.tabs(["➕ Yeni Kullanıcı Ekle", "📋 Kullanıcı Listesi"])

    # --- 1. YENİ KULLANICI OLUŞTURMA ---
    with tab_create:
        with st.form("create_internal_user"):
            st.subheader("Yeni Hesap Bilgileri")
            
            c1, c2 = st.columns(2)
            new_name = c1.text_input("Ad Soyad / Firma Adı", placeholder="Örn: Kuzey İnşaat Ltd.")
            new_username = c2.text_input("Kullanıcı Adı", placeholder="kuzey_insaat")
            
            c3, c4 = st.columns(2)
            new_email = c3.text_input("E-Posta Adresi")
            new_pass = c4.text_input("Şifre", type="password")
            
            st.markdown("---")
            st.subheader("Yetkilendirme")
            
            r1, r2 = st.columns(2)
            
            # Grup ID'si çok önemli. Buraya doğru ID girilmeli.
            # İleride burayı otomatik listeden seçmeli yapabiliriz.
            new_group_id = r1.number_input(
                "Bağlı Olduğu Trusted Grup ID", 
                min_value=0, 
                value=7153, 
                help="Bu kullanıcının hangi cihazları göreceğini belirler. (HKM: 7153, Fel-Tech: 9840)"
            )
            
            role_select = r2.selectbox(
                "Sistem Rolü", 
                ["Client", "Admin"], 
                index=0, 
                help="Client: Sadece kendi grup cihazlarını görür. Admin: Tüm sistemi görür."
            )
            
            st.markdown("---")
            submitted = st.form_submit_button("💾 Kullanıcıyı Kaydet", type="primary", use_container_width=True)

            if submitted:
                if not (new_name and new_username and new_pass):
                    st.error("Lütfen zorunlu alanları (Ad, Kullanıcı Adı, Şifre) doldurun.")
                else:
                    db = SessionLocal()
                    try:
                        # Kullanıcı adı çakışması kontrolü
                        existing = db.query(User).filter(User.username == new_username).first()
                        if existing:
                            st.error("Bu kullanıcı adı zaten kullanılıyor!")
                        else:
                            # Yeni ID oluştur
                            unique_id = f"u_{uuid.uuid4().hex[:8]}"
                            
                            new_user = User(
                                id=unique_id,
                                username=new_username,
                                email=new_email,
                                password_hash=get_password_hash(new_pass),
                                role=role_select,
                                trusted_group_id=int(new_group_id),
                                company_name=new_name,
                                full_name=new_name
                            )
                            db.add(new_user)
                            db.commit()
                            st.success(f"✅ BAŞARILI! '{new_name}' kullanıcısı oluşturuldu ve {new_group_id} grubuna bağlandı.")
                            st.balloons()
                            
                    except Exception as e:
                        st.error(f"Veritabanı Hatası: {e}")
                    finally:
                        db.close()

    # --- 2. KULLANICI LİSTESİ ---
    with tab_list:
        db = SessionLocal()
        users = db.query(User).all()
        db.close()
        
        data = []
        for u in users:
            data.append({
                "Kullanıcı Adı": u.username,
                "Ad / Firma": u.company_name,
                "Rol": u.role,
                "Grup ID": u.trusted_group_id,
                "E-Posta": u.email,
                "ID": u.id
            })
        
        df = pd.DataFrame(data)
        st.dataframe(df, use_container_width=True)
        
        st.info("💡 Not: Kullanıcı silme işlemi şimdilik sadece veritabanından yapılabilir.")