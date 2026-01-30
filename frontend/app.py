import streamlit as st
import sys
import os
import folium
import urllib.parse
from datetime import datetime, timedelta
from streamlit_folium import st_folium

# --- PATH AYARI ---
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# --- VİEW IMPORTLARI ---
from views import (
    dashboard, map, inventory, alarms, geofence, 
    settings, reports, ai_analysis, solid_ai, utilization_view,
    admin_users, admin_documents
)

# --- BACKEND IMPORTLARI ---
# Yeni fonksiyonları (reset_token vb.) buraya ekledik
from backend.database import (
    login_user, get_active_share_link, get_device_telemetry, get_last_operation_stats,
    create_password_reset_token, reset_password_by_token, 
    complete_user_registration, get_invite_details,
    SessionLocal, User
)

# 1. DAVET / ŞİFRE BELİRLEME EKRANI KONTROLÜ
if "invite_token" in st.query_params:
    token = st.query_params["invite_token"]
    # Yeni eklediğimiz get_invite_details fonksiyonunu da import ediyoruz
    from backend.database import complete_user_registration, get_invite_details
    
    # --- ÖNCE TOKEN KONTROLÜ VE BİLGİ ALMA ---
    invitee_user = get_invite_details(token)
    
    # CSS: Sayfayı Temizle ve Ortala
    st.markdown("""
        <style>
        .block-container {padding-top: 3rem !important;}
        header {visibility: hidden;}
        .stApp {background-color: #f8f9fa;}
        .brand-title {
            font-family: 'Helvetica Neue', sans-serif;
            font-size: 42px;
            font-weight: 800;
            color: #225d97;
            margin-bottom: 0px;
            letter-spacing: -1px;
        }
        .brand-subtitle {
            font-size: 16px;
            color: #666;
            margin-bottom: 20px;
        }
        .welcome-text {
            font-size: 18px;
            color: #333;
            line-height: 1.6;
            margin-bottom: 20px;
            text-align: center;
        }
        .company-highlight {
            color: #225d97;
            font-weight: bold;
        }
        </style>
    """, unsafe_allow_html=True)

    c_left, c_mid, c_right = st.columns([1, 2, 1])
    
    with c_mid:
        # LOGO
        if os.path.exists("static/logo.png"):
            st.image("static/logo.png", width=120)
        else:
            st.markdown("<div style='text-align:center; font-size: 50px;'>🚜</div>", unsafe_allow_html=True)

        st.markdown('<div class="brand-title">SolidTrack</div>', unsafe_allow_html=True)
        st.markdown('<div class="brand-subtitle">IoT Filo Yönetim Sistemi</div>', unsafe_allow_html=True)
        st.divider()

        if not invitee_user:
            st.error("⚠️ Bu davet linki geçersiz veya süresi dolmuş.")
        else:
            # --- DİNAMİK KARŞILAMA MESAJI ---
            # Firma adını invitee_user objesinden alıyoruz
            firma_adi = invitee_user.company_name if invitee_user.company_name else "SolidTrack"
            
            st.markdown(f"""
            <div class="welcome-text">
                <span class="company-highlight">{firma_adi}</span> yönetimi tarafından 
                <b>SolidTrack IoT ve Operasyonel Analitik Platformu</b>'na davet edildiniz.<br><br>
                Platforma giriş yapmak ve hesabınızı aktifleştirmek için lütfen şifrenizi belirleyiniz.
            </div>
            """, unsafe_allow_html=True)
            
            st.info(f"👤 Kullanıcı Adınız: **{invitee_user.username}**")
            
            with st.form("set_pass_form", clear_on_submit=True):
                p1 = st.text_input("Yeni Şifre", type="password", placeholder="******")
                p2 = st.text_input("Şifre Tekrar", type="password", placeholder="******")
                
                st.write("")
                submit = st.form_submit_button("🚀 Kaydı Tamamla & Giriş Yap", type="primary", use_container_width=True)
                
                if submit:
                    if p1 != p2:
                        st.error("⚠️ Şifreler eşleşmiyor!")
                    elif len(p1) < 4:
                        st.error("⚠️ Şifre en az 4 karakter olmalı.")
                    else:
                        success, msg = complete_user_registration(token, p1)
                        if success:
                            st.success(f"Harika! Hesabınız oluşturuldu. Giriş ekranına yönlendiriliyorsunuz...")
                            # st.balloons()  <-- BU SATIRI SİLDİK (Artık yok)
                            
                            st.query_params.clear()
                            import time
                            time.sleep(2)
                            st.rerun()
                        else:
                            st.error(f"Hata: {msg}")
    
    st.stop()

# 2. ŞİFRE SIFIRLAMA EKRANI (Linkle Gelenler İçin)
if "reset_token" in st.query_params:
    token = st.query_params["reset_token"]
    
    st.markdown("""
        <style>
        .block-container {padding-top: 3rem !important;}
        header {visibility: hidden;}
        .stApp {background-color: #f8f9fa;}
        </style>
    """, unsafe_allow_html=True)

    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        st.info("🔐 **Şifre Sıfırlama**")
        st.write("Lütfen hesabınız için yeni şifrenizi belirleyin.")
        
        with st.form("reset_pass_final"):
            new_p1 = st.text_input("Yeni Şifre", type="password")
            new_p2 = st.text_input("Yeni Şifre (Tekrar)", type="password")
            
            if st.form_submit_button("Şifreyi Değiştir", type="primary"):
                if new_p1 == new_p2 and new_p1:
                    success, msg = reset_password_by_token(token, new_p1)
                    if success:
                        st.success(msg)
                        st.query_params.clear()
                        import time
                        time.sleep(2)
                        st.rerun()
                    else:
                        st.error(msg)
                else:
                    st.error("Şifreler uyuşmuyor.")
    st.stop()

# --- SAYFA AYARI ---
st.set_page_config(page_title="SolidTrack IoT", page_icon="🚜", layout="wide")

# --- CSS (TEPE BOŞLUĞU VE SİDEBAR KESİN ÇÖZÜM) ---
st.markdown("""
    <style>
    /* 1. Tüm sayfa konteynerini hedef al ve üst boşluğu (padding) sıfırla */
    .block-container {
        padding-top: 1rem !important;
        padding-bottom: 0rem !important;
    }

    /* 2. Streamlit'in en üstteki görünmez Header (başlık) alanını tamamen yok et */
    header {
        visibility: hidden;
        height: 0px !important;
    }

    /* 3. Ana zemin rengi (Aydınlık Mod) */
    .main { background-color: #F8F9FA; }

    /* 4. Sidebar Genişliği ve Tasarımı */
    [data-testid="stSidebar"] {
        min-width: 270px;
        max-width: 270px;
        background-color: #FFFFFF;
        border-right: 1px solid #E0E0E0;
    }

    /* 5. Menü (Radio Button) Tasarımı */
    div[role="radiogroup"] > label > div:first-child { display: none !important; }
    div[role="radiogroup"] label {
        padding: 10px 15px !important;
        margin-bottom: 4px !important;
        border-radius: 8px !important;
        cursor: pointer;
        display: block !important;
    }
    div[role="radiogroup"] label:hover { background-color: #f0f2f6 !important; }
    div[role="radiogroup"] label[data-checked="true"] {
        background-color: #E8F0FE !important;
        color: #1976D2 !important;
        font-weight: bold !important;
        border-left: 5px solid #1976D2 !important;
    }

    /* 6. Logo Hizalama (Boşlukları temizlenmiş) */
    [data-testid="stSidebar"] img {
        display: block;
        margin: 0 auto 15px auto;
        object-fit: contain;
    }
    
    /* Sidebar altındaki şirket ismini ortala */
    [data-testid="stSidebar"] .stMarkdown {
        text-align: center;
    }
    </style>
    """, unsafe_allow_html=True)

# =========================================================
# 🎩 SİHİRLİ KAPI: PUBLIC LINK KONTROLÜ
# =========================================================
query_params = st.query_params
if "token" in query_params:
    token = query_params["token"]
    
    # Gerekli Importlar
    from backend.database import get_active_share_link, get_last_operation_stats, get_device_telemetry
    from frontend.utils import format_date_for_ui
    # Geopy kütüphanesi (Adres Çözümleme için)
    try:
        from geopy.geocoders import Nominatim
    except ImportError:
        st.error("Sistem Hatası: 'geopy' kütüphanesi yüklü değil. Terminale 'pip install geopy' yazınız.")
        st.stop()
    
    shared_device = get_active_share_link(token)
    
    if shared_device:
        telemetry = get_device_telemetry(shared_device.device_id, limit=1)
        
        # --- BAŞLIK ---
        st.title(f"{shared_device.unit_name}")
        st.caption(f"Seri No: {shared_device.device_id}")

        # --- İKİ KOLONLU DÜZEN ---
        col_map, col_info = st.columns([2.5, 1])
        
        # 1. SOL TARAF (HARİTA)
        with col_map:
            if telemetry:
                last_loc = [telemetry[0].latitude, telemetry[0].longitude]
                
                m = folium.Map(location=last_loc, zoom_start=15, tiles=None)
                
                # Katmanlar
                folium.TileLayer('https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}&hl=tr', attr='Google', name='Uydu', overlay=False, control=True, show=True).add_to(m)
                folium.TileLayer('https://mt1.google.com/vt/lyrs=m&x={x}&y={y}&z={z}&hl=tr', attr='Google', name='Sokak', overlay=False, control=True, show=False).add_to(m)
                
                # İkon
                folium.Marker(last_loc, popup=shared_device.unit_name, icon=folium.Icon(color="red", icon="truck fa-2x", prefix="fa")).add_to(m)
                
                folium.LayerControl(position='topright', collapsed=False).add_to(m)
                st_folium(m, height=500, use_container_width=True)
            else:
                st.warning("Konum verisi yok.")

        # 2. SAĞ TARAF (BİLGİ KARTI)
        with col_info:
            
            # A) ADRES ÇÖZÜMLEME (DAHA GÜÇLÜ KOD)
            st.markdown("### 📍 Konum Bilgisi")
            
            address_display = "Adres bulunamadı."
            gmaps_link = "#"
            
            if telemetry:
                lat = telemetry[0].latitude
                lon = telemetry[0].longitude
                gmaps_link = f"https://www.google.com/maps?q={lat},{lon}"
                
                # Önce veritabanına bak
                if shared_device.address and len(shared_device.address) > 10:
                    address_display = shared_device.address
                else:
                    # Yoksa Canlı Çevir
                    try:
                        # user_agent'ı değiştirdik ki engellenmeyelim
                        geolocator = Nominatim(user_agent="solidtrack_v2_geo_finder")
                        # timeout'u 10 saniye yaptık
                        location = geolocator.reverse(f"{lat}, {lon}", language='tr', timeout=10)
                        
                        if location and location.address:
                            address_display = location.address
                        else:
                            address_display = f"{lat:.5f}, {lon:.5f}"
                    except Exception as e:
                        # Hata olursa koordinat göster ama hatayı terminale bas
                        print(f"Geocoding Hatası: {e}") 
                        address_display = f"{lat:.5f}, {lon:.5f}"

            # Adresi Mavi Kutu İçinde Göster
            st.info(f"{address_display}")
            
            # Google Maps Linki
            st.markdown(f"[🗺️ Google Haritalar'da Aç]({gmaps_link})")
            
            st.markdown("---")
            
            # B) SON SİNYAL
            if telemetry:
                ts_str = format_date_for_ui(telemetry[0].timestamp, "Europe/Istanbul", include_offset=True)
                
                st.markdown(f"""
                <div style="background-color: #f1f3f4; padding: 15px; border-radius: 8px; border-left: 5px solid #225d97;">
                    <div style="display: flex; align-items: center;">
                        <div style="width: 12px; height: 12px; background-color: #28a745; border-radius: 50%; margin-right: 10px; box-shadow: 0 0 5px #28a745;"></div>
                        <span style="font-size: 14px; font-weight: bold; color: #333;">Son Sinyal</span>
                    </div>
                    <div style="margin-top: 8px; font-size: 16px; font-weight: bold; color: #555; margin-left: 22px;">
                        {ts_str}
                    </div>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.warning("Sinyal yok.")
            
            st.markdown("---")
            st.caption("Powered by SolidTrack IoT")
        
        st.stop()
    else:
        st.error("❌ Bu link geçersiz.")

        # 3 saniye bekle, URL'i temizle ve ana ekrana dön
        import time
        time.sleep(2)
        st.query_params.clear() # URL'deki ?token=... kısmını siler
        st.rerun() # Sayfayı yeniler

# =========================================================
# NORMAL UYGULAMA AKIŞI (LOGIN)
# =========================================================

if 'user' not in st.session_state: st.session_state.user = None

if not st.session_state.user:
    c1, c2, c3 = st.columns([1,0.8,1])
    with c2:
        st.title("🚜 SolidTrack")
        st.markdown("---")
        with st.form("login_form"):
            u = st.text_input("Kullanıcı Adı veya E-Posta") 
            p = st.text_input("Şifre", type="password")
            if st.form_submit_button("Giriş Yap", use_container_width=True):
                user = login_user(u, p)
                if user:
                    st.session_state.user = user
                    st.rerun()
                else:
                    st.error("Hatalı Giriş")

            # --- ŞİFREMİ UNUTTUM MODU (YENİ) ---
        if "forgot_mode" not in st.session_state: st.session_state.forgot_mode = False

        if st.session_state.forgot_mode:
            st.warning("🔒 Şifre Sıfırlama Linki Gönder")
            email_input = st.text_input("E-Posta Adresiniz", key="forgot_email")
            
            c_f1, c_f2 = st.columns(2)
            if c_f1.button("Linki Gönder", type="primary"):
                token, msg = create_password_reset_token(email_input)
                if token:
                    # Linki oluştur (Canlıda domain olacak)
                    base_url = "http://localhost:8501"
                    link = f"{base_url}/?reset_token={token}"
                    
                    st.success("✅ Link oluşturuldu!")
                    st.code(link, language="text") # E-posta servisi olmadığı için ekrana basıyoruz
                    
                    # WhatsApp ile alma kolaylığı
                    import urllib.parse
                    wa_text = f"SolidTrack Şifre Sıfırlama Linkim: {link}"
                    wa_link = f"https://wa.me/?text={urllib.parse.quote(wa_text)}"
                    st.markdown(f"[📲 WhatsApp'a Gönder]({wa_link})")
                else:
                    st.error(msg)
            
            if c_f2.button("İptal"):
                st.session_state.forgot_mode = False
                st.rerun()
        else:
            # Şifremi unuttum linki (Buton görünümlü)
            if st.button("Şifremi Unuttum?", type="secondary", use_container_width=True):
                st.session_state.forgot_mode = True
                st.rerun()
        st.markdown("---")
        if st.button("🚀 Demo Modu ile Hemen Dene", use_container_width=True, type="primary"):
            user = login_user("solidus_admin", "123456") 
            if user:
                st.session_state.user = user
                st.rerun()
else:
    user = st.session_state.user
    with st.sidebar:
        # --- LOGO & KULLANICI BİLGİSİ ---
        # Logo varsa göster, yoksa standart ikon
        if user.logo_url and os.path.exists(user.logo_url):
            st.image(user.logo_url, width=140)
        else:
            st.markdown("<h1 style='text-align: center;'>🚜</h1>", unsafe_allow_html=True)

        st.markdown(f"<div style='text-align: center; margin-bottom: 20px;'><b>{user.company_name}</b><br><span style='font-size:0.8em; color:gray;'>{user.full_name}</span></div>", unsafe_allow_html=True)
        
        # --- MENÜ TANIMLARI ---
        menu_options = {
            "📊 Genel Bakış": dashboard,
            "🌍 Canlı İzleme": map,
            "🔨 Kırıcı Verimliliği": utilization_view,
            "🤖 SolidAI Asistan": solid_ai,   
            "🧠 AI Veri Analizi": ai_analysis, 
            "📈 Raporlar": reports,
            "🚜 Cihaz Listesi": inventory,
            "🔔 Alarm Merkezi": alarms,
            "🚧 Şantiye Yönetimi": geofence,
            "⚙️ Ayarlar": settings
        }
        
        if user.role == "Admin":
            menu_options["👥 Müşteri Yönetimi"] = admin_users
            menu_options["📂 Doküman Yönetimi"] = admin_documents

        # --- NORTH FALCON FİLTRESİ ---
        # Eğer SubUser ise ve kısıtlıysa, menüyü daralt
        if user.role == "SubUser" and user.allowed_pages:
            allowed_list = user.allowed_pages.split(",") # Örn: "Harita,Raporlar"
            filtered_menu = {}
            
            # Ayarlar her zaman açık olsun (Şifre değişimi için)
            if "⚙️ Ayarlar" in menu_options:
                filtered_menu["⚙️ Ayarlar"] = settings

            for name, module in menu_options.items():
                is_allowed = False
                for allowed_item in allowed_list:
                    # "Harita" kelimesi "🌍 Canlı İzleme" içinde geçiyor mu?
                    if allowed_item in name: 
                        is_allowed = True
                        break
                
                if is_allowed:
                    filtered_menu[name] = module
            
            # Menüyü güncelle
            menu_options = filtered_menu

        default_index = 0
        if "menu_selection" in st.session_state:
            try:
                target_menu = st.session_state["menu_selection"]
                if target_menu in menu_options:
                    default_index = list(menu_options.keys()).index(target_menu)
                else:
                    default_index = 0
            except ValueError:
                default_index = 0
        
        # Radio buton (CSS ile buton gibi gözükmesi sağlandı)
        selected_menu = st.radio("Menü", list(menu_options.keys()), index=default_index, label_visibility="collapsed")
        
        if selected_menu != st.session_state.get("menu_selection"):
             st.session_state["menu_selection"] = selected_menu
             st.rerun()

        if "original_admin" in st.session_state and st.session_state["original_admin"]:
            st.sidebar.warning("🕵️‍♂️ Şu an Gözcü Modundasınız")
            if st.sidebar.button("🔙 Admin Hesabıma Dön", use_container_width=True):
                st.session_state["user"] = st.session_state["original_admin"]
                del st.session_state["original_admin"]
                st.rerun()
                
        st.markdown("---")
        if st.button("Çıkış Yap", use_container_width=True): 
            st.session_state.user = None
            st.rerun()

    # SEÇİLEN SAYFAYI YÜKLE
    if selected_menu in menu_options:
        menu_options[selected_menu].load_view(user)