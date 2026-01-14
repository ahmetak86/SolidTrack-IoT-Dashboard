# frontend/app.py (PUBLIC LINK DESTEKLİ FİNAL SÜRÜM)
import streamlit as st
import sys
import os
import folium
from streamlit_folium import st_folium

# --- PATH AYARI ---
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# --- IMPORTLAR ---
from views import dashboard, map, inventory, analysis, alarms, geofence, settings, reports
from backend.database import login_user, get_active_share_link, get_device_telemetry

# --- SAYFA AYARI (Dinamik Başlık İçin Önce Burası) ---
st.set_page_config(page_title="SolidTrack IoT", page_icon="🚜", layout="wide")

# --- CSS (GENEL) ---
st.markdown("""
    <style>
    .main {background-color: #F8F9FA;}
    div[data-testid="stExpander"] {background-color: #FFFFFF; border-radius: 10px; border: 1px solid #E0E0E0;}
    .hazard-bar {
        width: 100%; height: 15px;
        background: repeating-linear-gradient(45deg, #f1c40f, #f1c40f 20px, #2c3e50 20px, #2c3e50 40px);
        margin-bottom: 20px; border-radius: 5px; opacity: 0.8;
    }
    </style>
    """, unsafe_allow_html=True)

# =========================================================
# 🎩 SİHİRLİ KAPI: PUBLIC LINK KONTROLÜ
# =========================================================
# URL'de "?token=..." var mı diye bakıyoruz
query_params = st.query_params
if "token" in query_params:
    token = query_params["token"]
    # Yeni fonksiyonu da import etmeyi unutma: get_last_operation_stats
    from backend.database import get_active_share_link, get_device_telemetry, get_last_operation_stats
    
    shared_device = get_active_share_link(token)
    
    if shared_device:
        stats = get_last_operation_stats(shared_device.device_id)
        
        # --- MİSAFİR GÖRÜNÜMÜ ---
        st.markdown('<div class="hazard-bar"></div>', unsafe_allow_html=True)
        
        # Header (Basit ve Net)
        h1, h2 = st.columns([3, 1])
        h1.title(f"{shared_device.unit_name}")
        h1.caption(f"Model: {shared_device.asset_model} | Seri No: {shared_device.device_id}")
        h2.markdown(f"### {'🟢 Aktif' if shared_device.is_active else '🔴 Pasif'}")

        col_map, col_info = st.columns([2.5, 1])
        
        with col_map:
            # Harita
            telemetry = get_device_telemetry(shared_device.device_id, limit=1)
            if telemetry:
                last_loc = [telemetry[0].latitude, telemetry[0].longitude]
                m = folium.Map(location=last_loc, zoom_start=15)
                folium.Marker(
                    last_loc, 
                    popup=shared_device.unit_name,
                    icon=folium.Icon(color="green", icon="truck", prefix="fa")
                ).add_to(m)
                st_folium(m, height=450, use_container_width=True)
            else:
                st.warning("Konum verisi bekleniyor...")

        with col_info:
            st.subheader("📋 Son Durum")
            
            st.markdown("**📍 Güncel Adres**")
            st.info(stats["address"])
            
            st.markdown("**⏱️ Son Çalışma**")
            st.write(f"Zaman: **{stats['last_seen']}**")
            st.write(f"Süre: **{stats['duration']}**")
            
            st.markdown("---")
            
            # WHATSAPP PAYLAŞ BUTONU
            current_url = f"http://localhost:8501/?token={token}"
            whatsapp_url = f"https://wa.me/?text=Makineyi%20buradan%20izleyebilirsin:%20{current_url}"
            
            st.link_button("📲 WhatsApp ile Gönder", whatsapp_url, type="primary", use_container_width=True)
            
            st.markdown("---")
            st.caption("Powered by SolidTrack IoT")
        
        st.stop()
    else:
        st.error("❌ Bu link geçersiz veya süresi dolmuş.")

# =========================================================
# NORMAL UYGULAMA AKIŞI (LOGIN)
# =========================================================

# --- OTURUM ---
if 'user' not in st.session_state: st.session_state.user = None

if not st.session_state.user:
    # GİRİŞ EKRANI
    c1, c2, c3 = st.columns([1,0.8,1])
    with c2:
        st.title("🚜 SolidTrack")
        st.markdown("---")
        with st.form("login_form"):
            u = st.text_input("Kullanıcı Adı")
            p = st.text_input("Şifre", type="password")
            if st.form_submit_button("Giriş Yap", use_container_width=True):
                user = login_user(u, p)
                if user:
                    st.session_state.user = user
                    st.rerun()
                else:
                    st.error("Hatalı Giriş")
        st.markdown("---")
        if st.button("🚀 Demo Modu ile Hemen Dene", use_container_width=True, type="primary"):
            user = login_user("solidus_admin", "123456") 
            if user:
                st.session_state.user = user
                st.rerun()
else:
    # --- SIDEBAR & NAVIGASYON ---
    user = st.session_state.user
    with st.sidebar:
        logo = user.logo_url if user.logo_url else "https://via.placeholder.com/150x50?text=SolidTrack"
        st.image(logo, use_container_width=True)
        st.markdown(f"**{user.full_name}**")
        st.caption(user.company_name)
        
        menu_options = {
            "📊 Genel Bakış": dashboard,
            "🌍 Canlı İzleme": map,
            "📈 Raporlar": reports,
            "🚜 Cihaz Listesi": inventory,
            "🔍 Teknik Analiz": analysis,
            "🔔 Alarm Merkezi": alarms,
            "🚧 Şantiye Yönetimi": geofence,
            "⚙️ Ayarlar": settings
        }
        
        selected_menu = st.radio("Menü", list(menu_options.keys()))
        
        st.markdown("---")
        if st.button("Çıkış Yap"): 
            st.session_state.user = None
            st.rerun()

    # SEÇİLEN SAYFAYI YÜKLE
    if selected_menu in menu_options:
        menu_options[selected_menu].load_view(user)