# frontend/views/settings.py
import streamlit as st
import os
import sys
import time
import pytz
from datetime import datetime
from PIL import Image
import urllib.parse  # WhatsApp linki için gerekli
from backend.database import change_user_password

# Proje ana dizinini yola ekle
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

# Backend fonksiyonlarını çekiyoruz (create_sub_user_invite güncellendi)
from backend.database import update_user_settings, create_sub_user_invite, SessionLocal, User, get_user_devices
from frontend.utils import get_timezone_from_coords

# --- SABİT MENÜ LİSTESİ (APP.PY İLE UYUMLU) ---
# Teknik Not: app.py'den import yapamıyoruz (Döngüsel hata olur).
# O yüzden menü isimlerini buraya sabit yazdık.
APP_MENU_ITEMS = [
    "📊 Genel Bakış",
    "🌍 Canlı İzleme",
    "🔨 Kırıcı Verimliliği",
    "🤖 SolidAI Asistan",
    "🧠 AI Veri Analizi",
    "📈 Raporlar",
    "🚜 Cihaz Listesi",
    "🔔 Alarm Merkezi",
    "🚧 Şantiye Yönetimi",
    "⚙️ Ayarlar"
]

# --- YARDIMCI: SAAT DİLİMLERİNİ DÜZENLEME ---
@st.cache_data
def get_sorted_timezones():
    """Saat dilimlerini UTC ofsetine göre sıralar."""
    timezones = []
    for tz_name in pytz.common_timezones:
        try:
            now = datetime.now(pytz.timezone(tz_name))
            offset = now.utcoffset().total_seconds() if now.utcoffset() else 0
            timezones.append((offset, tz_name))
        except: continue
    timezones.sort(key=lambda x: x[0])
    return [t[1] for t in timezones]

def format_timezone_label(tz_name):
    """(UTC+03:00) Europe/Istanbul formatında etiket döndürür."""
    try:
        now = datetime.now(pytz.timezone(tz_name))
        offset_str = now.strftime("%z") 
        pretty_offset = f"UTC{offset_str[:3]}:{offset_str[3:]}"
        clean_name = tz_name.replace("_", " ")
        return f"({pretty_offset}) {clean_name}"
    except: return tz_name

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
        /* Form Butonlarını KIRMIZI Yap */
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
        /* Başlık Yanındaki Zincir İkonunu Gizle */
        .css-15zrgzn {display: none;}
        .css-10trblm {display: none;}
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
        st.markdown("---")
        st.subheader("🔐 Şifre Değiştir")
        
        with st.form("change_pass_form"):
            cp_1, cp_2, cp_3 = st.columns(3)
            old_pass = cp_1.text_input("Mevcut Şifre", type="password")
            new_pass = cp_2.text_input("Yeni Şifre", type="password")
            confirm_pass = cp_3.text_input("Yeni Şifre (Tekrar)", type="password")
            
            if st.form_submit_button("Şifreyi Güncelle"):
                if new_pass != confirm_pass:
                    st.error("❌ Yeni şifreler uyuşmuyor.")
                elif not old_pass:
                    st.error("❌ Lütfen mevcut şifrenizi girin.")
                else:
                    success, msg = change_user_password(user.id, old_pass, new_pass)
                    if success:
                        st.success(msg)
                    else:
                        st.error(msg)

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
    # TAB 2: SİSTEM & GÖRÜNÜM
    # -------------------------------------------------------
    with tab2:
        st.subheader("🌍 Bölgesel Ayarlar")
        
        with st.form("settings_form_system"):
            settings_sys = {}
            sys_c1, sys_c2 = st.columns([1, 2])
            
            # Dil Seçimi
            langs = ["Turkish", "English", "Spanish", "German"]
            l_idx = langs.index(user.language) if user.language in langs else 0
            settings_sys['language'] = sys_c1.selectbox("Dil / Language", langs, index=l_idx)
            
            # --- SAAT DİLİMİ ---
            sorted_tz_list = get_sorted_timezones()
            
            tz_index = 0
            if user.timezone in sorted_tz_list:
                tz_index = sorted_tz_list.index(user.timezone)
            else:
                if "Europe/Istanbul" in sorted_tz_list:
                    tz_index = sorted_tz_list.index("Europe/Istanbul")
            
            settings_sys['timezone'] = sys_c2.selectbox(
                "Saat Dilimi (Timezone)", 
                sorted_tz_list, 
                index=tz_index,
                format_func=format_timezone_label, 
                help="Tüm rapor ve ekranlardaki saatler bu seçime göre gösterilecektir."
            )
            
            settings_sys['date_format'] = st.selectbox("Tarih Formatı", ["DD.MM.YYYY", "MM/DD/YYYY", "YYYY-MM-DD"], index=0)
            
            st.markdown("---")
            st.subheader("Birim Tercihleri (Unit System)")
            
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
                    time.sleep(1)
                    st.rerun()

        # --- OTO TESPİT (FORM DIŞI) ---
        st.markdown("##### 📍 Otomatik Algılama")
        c_detect, c_info = st.columns([1, 3])
        with c_detect:
            if st.button("Cihaz Konumuna Göre Ayarla"):
                with st.spinner("Cihazlar taranıyor..."):
                    user_devices = get_user_devices(user.id)
                    found_tz = None
                    for d in user_devices:
                        from backend.database import get_device_telemetry
                        logs = get_device_telemetry(d.device_id, limit=1)
                        if logs and logs[0].latitude and logs[0].longitude:
                            found_tz = get_timezone_from_coords(logs[0].latitude, logs[0].longitude)
                            if found_tz: break
                
                if found_tz:
                    update_user_settings(user.id, {'timezone': found_tz})
                    st.success(f"Saat dilimi cihaz konumuna göre ayarlandı: **{format_timezone_label(found_tz)}**")
                    time.sleep(2)
                    st.rerun()
                else:
                    st.error("Konum verisi olan aktif bir cihaz bulunamadı.")

    # -------------------------------------------------------
    # TAB 3: BİLDİRİMLER
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
                    time.sleep(1)
                    st.rerun()

    # -------------------------------------------------------
    # TAB 4: EKİP YÖNETİMİ (NORTH FALCON + ESKİ WHATSAPP SİSTEMİ) 🦅
    # -------------------------------------------------------
    with tab4:
        st.subheader("Ekip Arkadaşı Davet Et")
        
        if user.role == "SubUser":
            st.warning("⛔ Bu sayfayı görüntüleme yetkiniz yok. (Kısıtlı Hesap)")
        else:
            st.info("Sizinle aynı yetkilere sahip olacak veya **kısıtlı yetkilerle** çalışacak yeni bir kullanıcı oluşturun.")
            
            # --- YENİ DAVET FORMU (Cihaz ve Sayfa Seçimi Eklendi) ---
            with st.expander("➕ Yeni Kullanıcı Daveti Oluştur", expanded=True):
                with st.form("invite_user_form"):
                    c_inv1, c_inv2 = st.columns(2)
                    i_name = c_inv1.text_input("Ad Soyad", placeholder="Örn: John Doe")
                    i_mail = c_inv2.text_input("E-Posta", placeholder="john@company.com")
                    i_user = st.text_input("Kullanıcı Adı Belirle", placeholder="john_doe")
                    
                    st.markdown("---")
                    st.markdown("🔐 **Erişim Yetkileri**")
                    
                    # 1. CİHAZ SEÇİMİ (Otomatik Doluyor)
                    my_devices = get_user_devices(user.id)
                    dev_map = {d.unit_name: d.device_id for d in my_devices}
                    
                    selected_dev_names = st.multiselect(
                        "🚛 1. Hangi Cihazları Görebilsin?", 
                        options=list(dev_map.keys()),
                        help="Kullanıcı sadece burada seçtiğiniz cihazları görebilecektir."
                    )
                    
                    # 2. SAYFA SEÇİMİ (APP.PY MENÜSÜYLE UYUMLU)
                    selected_pages = st.multiselect(
                        "📄 2. Hangi Sayfalara Girebilsin?",
                        options=APP_MENU_ITEMS,
                        default=["🌍 Canlı İzleme", "🔔 Alarm Merkezi"],
                        help="Örneğin operatöre sadece 'Canlı İzleme' yetkisi verebilirsiniz."
                    )
                    
                    submitted_inv = st.form_submit_button("🔗 Davet Linki Oluştur", type="primary")
                    
                    if submitted_inv:
                        if i_name and i_user and i_mail:
                            # İsimleri ID'ye çevir
                            final_dev_ids = [dev_map[name] for name in selected_dev_names]
                            
                            # Backend'e Token İste (Yeni Parametrelerle)
                            token, msg = create_sub_user_invite(
                                user.id, i_user, i_mail, i_name, 
                                final_dev_ids, selected_pages
                            )
                            
                            if token:
                                base_url = "http://localhost:8501" # Canlıda domain olacak
                                invite_link = f"{base_url}/?invite_token={token}"
                                
                                st.success("✅ Kullanıcı taslağı oluşturuldu!")
                                st.markdown("**Aşağıdaki linki kopyalayıp ekip arkadaşınıza gönderin:**")
                                st.code(invite_link, language="text")

                                # WhatsApp Mesajı (Eski kodunuzdan alındı)
                                msg_text = f"Merhaba {i_name}, SolidTrack sistemine giriş yapman için davet linkin: {invite_link}"
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
                                st.error(f"Hata: {msg}")
                        else:
                            st.warning("Lütfen tüm alanları doldurun.")
        
        st.markdown("---")
        st.subheader("Mevcut Ekip")
        
        db = SessionLocal()
        my_team = db.query(User).filter(User.trusted_group_id == user.trusted_group_id, User.id != user.id).all()
        db.close()
        
        if my_team:
            for mate in my_team:
                status = "🟠 Bekliyor" if mate.password_hash == "PENDING_ACTIVATION" else "🟢 Aktif"
                role_txt = "🔒 Kısıtlı" if mate.role == "SubUser" else "👑 Yönetici"
                st.markdown(f"**{mate.full_name}** ({mate.username}) - {status} | {role_txt}")
                
                if mate.role == "SubUser":
                    pg_count = len(mate.allowed_pages.split(",")) if mate.allowed_pages else 0
                    dev_count = len(mate.allowed_device_ids.split(",")) if mate.allowed_device_ids else 0
                    st.caption(f"Erişim İzni: {dev_count} Cihaz, {pg_count} Sayfa")
                st.divider()
        else:
            st.caption("Henüz ekibinizde kimse yok.")