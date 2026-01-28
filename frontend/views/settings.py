# frontend/views/settings.py
import streamlit as st
import os
from PIL import Image
from backend.database import update_user_settings

# Resim kaydetme fonksiyonu
def save_uploaded_file(uploadedfile, user_id):
    if not os.path.exists("static/logos"):
        os.makedirs("static/logos")
    
    file_ext = os.path.splitext(uploadedfile.name)[1]
    new_filename = f"logo_{user_id}{file_ext}"
    file_path = os.path.join("static/logos", new_filename)
    
    with open(file_path, "wb") as f:
        f.write(uploadedfile.getbuffer())
        
    return file_path

def load_view(user):
    # --- CSS AYARLARI ---
    st.markdown("""
        <style>
        /* 1. Form Butonlarını KIRMIZI Yap */
        div[data-testid="stForm"] button[kind="secondaryFormSubmit"] {
            background-color: #d63031 !important;
            color: white !important;
            border: none !important;
            font-weight: bold !important;
        }
        div[data-testid="stForm"] button[kind="secondaryFormSubmit"]:hover {
            background-color: #b71c1c !important;
            box-shadow: 0 4px 6px rgba(0,0,0,0.2);
        }
        /* 2. Başlık Yanındaki Zincir İkonunu Gizle (İsteğe Bağlı) */
        .css-15zrgzn {display: none;}
        .css-10trblm {display: none;}
        /* Streamlit'in yeni versiyonları için: */
        [data-testid="stHeaderAction"] {display: none !important;}
        </style>
    """, unsafe_allow_html=True)

    st.header("⚙️ Yapılandırma ve Ayarlar")
    tab1, tab2, tab3, tab4 = st.tabs(["👤 Profil & Firma", "🌍 Sistem & Görünüm", "🔔 Bildirimler", "👥 Ekip Yönetimi"])
    
    # -------------------------------------------------------
    # TAB 1: PROFİL & FİRMA & LOGO
    # -------------------------------------------------------
    with tab1:
        st.subheader("1. Firma Bilgileri & İletişim")
        
        with st.form("settings_form_company"):
            settings_company = {}
            r1_c1, r1_c2 = st.columns(2)
            settings_company['company_name'] = r1_c1.text_input("Firma Ünvanı", value=user.company_name)
            settings_company['full_name'] = r1_c2.text_input("Yetkili Ad Soyad", value=user.full_name)
            
            r2_c1, r2_c2 = st.columns(2)
            settings_company['tax_office'] = r2_c1.text_input("Vergi Dairesi", value=user.tax_office)
            settings_company['tax_number'] = r2_c2.text_input("Vergi Numarası", value=user.tax_number)
            
            settings_company['company_address'] = st.text_area("Fatura Adresi", value=user.company_address)
            
            st.markdown("---")
            r3_c1, r3_c2 = st.columns(2)
            settings_company['email'] = r3_c1.text_input("E-Posta", value=user.email)
            settings_company['phone'] = r3_c2.text_input("Telefon", value=user.phone)
            
            st.write("")
            if st.form_submit_button("💾 Bilgileri Güncelle"):
                updated_user = update_user_settings(user.id, settings_company)
                if updated_user:
                    st.session_state.user = updated_user
                    st.success("Bilgiler başarıyla güncellendi!")
                    st.rerun()

        st.markdown("---")
        
        # --- LOGO ALANI ---
        st.subheader("3. Firma Logosu")
        st.caption("Firma logonuzu yükleyerek raporlarda ve menüde görünmesini sağlayabilirsiniz.")

        if "edit_logo_mode" not in st.session_state:
            st.session_state.edit_logo_mode = False

        has_logo = user.logo_url and os.path.exists(user.logo_url)
        
        if has_logo and not st.session_state.edit_logo_mode:
            col_show_1, col_show_2 = st.columns([1, 3], vertical_alignment="center")
            with col_show_1:
                st.image(user.logo_url, width=150)
            with col_show_2:
                st.success("✅ Mevcut logo sistemde yüklü.")
                if st.button("🔄 Logoyu Değiştir"):
                    st.session_state.edit_logo_mode = True
                    st.rerun()
        else:
            col_up_1, col_up_2 = st.columns([3, 1], vertical_alignment="bottom")
            with col_up_1:
                uploaded_logo = st.file_uploader("Logo Seçin (Sürükle Bırak)", type=['png', 'jpg', 'jpeg'], help="Maksimum 5MB")
            with col_up_2:
                if has_logo and st.button("❌ Vazgeç"):
                    st.session_state.edit_logo_mode = False
                    st.rerun()

            if uploaded_logo is not None:
                if uploaded_logo.size > 5 * 1024 * 1024:
                    st.error("❌ Dosya boyutu 5MB'dan büyük olamaz!")
                else:
                    if st.button("Logoyu Sisteme Yükle", type="primary", use_container_width=True):
                        saved_path = save_uploaded_file(uploaded_logo, user.id)
                        updated_user = update_user_settings(user.id, {'logo_url': saved_path})
                        if updated_user: st.session_state.user = updated_user
                        st.session_state.edit_logo_mode = False
                        st.success("✅ Logo yüklendi!")
                        st.rerun()

    # -------------------------------------------------------
    # TAB 2: SİSTEM & GÖRÜNÜM (Kodlar Geri Geldi)
    # -------------------------------------------------------
    with tab2:
        st.subheader("Bölgesel Ayarlar")
        with st.form("settings_form_system"):
            settings_sys = {}
            sys_c1, sys_c2, sys_c3 = st.columns(3)
            
            langs = ["Turkish", "English", "Spanish", "German"]
            l_idx = langs.index(user.language) if user.language in langs else 0
            
            settings_sys['language'] = sys_c1.selectbox("Dil / Language", langs, index=l_idx)
            settings_sys['timezone'] = sys_c2.selectbox("Saat Dilimi", ["Europe/Istanbul", "UTC", "Europe/London"], index=0)
            settings_sys['date_format'] = sys_c3.selectbox("Tarih Formatı", ["DD.MM.YYYY", "MM/DD/YYYY", "YYYY-MM-DD"], index=0)
            
            st.markdown("---")
            st.subheader("Birim Tercihleri (Unit System)")
            
            # Seçili değerlerin indexini bulma (Basitlik için varsayılan 0 alındı, geliştirilebilir)
            u_len = ["Metre / Km", "Feet / Mile"]
            u_tmp = ["Celsius (°C)", "Fahrenheit (°F)"]
            u_prs = ["Bar", "PSI"]
            u_vol = ["Litre", "Galon"]
            
            u_row1_c1, u_row1_c2 = st.columns(2)
            settings_sys['unit_length'] = u_row1_c1.selectbox("Uzunluk", u_len, index=0)
            settings_sys['unit_temp'] = u_row1_c2.selectbox("Sıcaklık", u_tmp, index=0)
            
            u_row2_c1, u_row2_c2 = st.columns(2)
            settings_sys['unit_pressure'] = u_row2_c1.selectbox("Basınç", u_prs, index=0)
            settings_sys['unit_volume'] = u_row2_c2.selectbox("Hacim", u_vol, index=0)
            
            st.write("")
            if st.form_submit_button("💾 Sistem Ayarlarını Kaydet"):
                updated_user = update_user_settings(user.id, settings_sys)
                if updated_user:
                    st.session_state.user = updated_user
                    st.success("Sistem ayarları güncellendi!")
                    st.rerun()

    # -------------------------------------------------------
    # TAB 3: BİLDİRİMLER (Kodlar Geri Geldi)
    # -------------------------------------------------------
    with tab3:
        st.subheader("Bildirim Tercihleri")
        with st.form("settings_form_notify"):
            settings_notif = {}
            
            settings_notif['notification_email_enabled'] = st.toggle("📧 E-Posta Bildirimleri (Genel)", value=user.notification_email_enabled)
            
            st.markdown("---")
            st.write("**Hangi durumlarda bildirim almak istersiniz?**")
            
            b_c1, b_c2 = st.columns(2)
            with b_c1:
                settings_notif['notify_low_battery'] = st.checkbox("Düşük Pil Uyarısı", value=user.notify_low_battery)
                settings_notif['notify_shock'] = st.checkbox("Kritik Darbe / Şok", value=user.notify_shock)
                settings_notif['notify_geofence'] = st.checkbox("Bölge İhlali", value=user.notify_geofence)
            with b_c2:
                settings_notif['notify_maintenance'] = st.checkbox("Bakım Zamanı", value=user.notify_maintenance)
                settings_notif['notify_daily_report'] = st.checkbox("Günlük Rapor", value=user.notify_daily_report)
                
            st.write("")
            if st.form_submit_button("💾 Bildirim Ayarlarını Kaydet"):
                updated_user = update_user_settings(user.id, settings_notif)
                if updated_user:
                    st.session_state.user = updated_user
                    st.success("Bildirim tercihleri kaydedildi!")
                    st.rerun()

    # -------------------------------------------------------
    # TAB 4: EKİP YÖNETİMİ (YENİ)
    # -------------------------------------------------------
    from backend.database import create_sub_user_invite, SessionLocal, User # Importu en üste taşıyabilirsin
    
    with tab4: # Tab tanımlarken: tab1, tab2, tab3, tab4 = st.tabs(["...", "...", "...", "👥 Ekip Yönetimi"])
        st.subheader("Ekip Arkadaşı Davet Et")
        st.info("Sizinle aynı yetkilere sahip olacak ve **sadece sizin makinelerinizi** görebilecek yeni bir kullanıcı oluşturun.")
        
        with st.form("invite_user_form"):
            c_inv1, c_inv2 = st.columns(2)
            i_name = c_inv1.text_input("Ad Soyad", placeholder="Örn: Mehmet Şef")
            i_mail = c_inv2.text_input("E-Posta", placeholder="mehmet@firma.com")
            
            i_user = st.text_input("Kullanıcı Adı Belirle", placeholder="mehmet_sef")
            
            submitted_inv = st.form_submit_button("🔗 Davet Linki Oluştur", type="primary")
            
            if submitted_inv:
                if i_name and i_user:
                    token, err = create_sub_user_invite(user.id, i_user, i_mail, i_name)
                    if token:
                        base_url = "http://localhost:8501" # Canlıda burası domain olacak
                        invite_link = f"{base_url}/?invite_token={token}"
                        
                        st.success("✅ Kullanıcı taslağı oluşturuldu!")
                        st.markdown(f"""
                        **Aşağıdaki linki kopyalayıp ekip arkadaşınıza gönderin:**
                        
                        Ekip arkadaşınız bu linke tıkladığında kendi şifresini belirleyerek sisteme giriş yapabilecektir.
                        """)
                        st.code(invite_link, language="text")

                        # WHATSAPP BUTONU
                        import urllib.parse
                        msg_text = f"Merhaba, SolidTrack sistemine giriş yapman için davet linkin: {invite_link}"
                        encoded_msg = urllib.parse.quote(msg_text)
                        wa_url = f"https://wa.me/?text={encoded_msg}"
                        
                        st.markdown(f"""
                        <a href="{wa_url}" target="_blank" style="text-decoration: none;">
                            <div style="
                                display: inline-block;
                                background-color: #25D366;
                                color: white;
                                padding: 10px 20px;
                                border-radius: 8px;
                                font-weight: bold;
                                text-align: center;
                                margin-top: 10px;
                                box-shadow: 0 2px 5px rgba(0,0,0,0.2);">
                                📲 WhatsApp ile Gönder
                            </div>
                        </a>
                        """, unsafe_allow_html=True)
                    else:
                        st.error(f"Hata: {err}")
                else:
                    st.warning("Lütfen Ad Soyad ve Kullanıcı Adı alanlarını doldurun.")
        
        st.markdown("---")
        st.subheader("Mevcut Ekip")
        # Basit liste
        db = SessionLocal()
        # Sadece benim grubumdaki kullanıcıları getir (ve ben hariç)
        my_team = db.query(User).filter(User.trusted_group_id == user.trusted_group_id, User.id != user.id).all()
        db.close()
        
        if my_team:
            for mate in my_team:
                status = "🟠 Bekliyor" if mate.password_hash == "PENDING_ACTIVATION" else "🟢 Aktif"
                st.markdown(f"**{mate.full_name}** ({mate.username}) - {status}")
        else:
            st.caption("Henüz ekibinizde kimse yok.")