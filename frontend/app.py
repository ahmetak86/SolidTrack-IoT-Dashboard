# frontend/app.py (MODÜLER YAPI - ROUTER)
import streamlit as st
import sys
import os

# --- PATH AYARI ---
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from backend.database import login_user

# --- SAYFA AYARLARI ---
st.set_page_config(page_title="SolidTrack IoT", page_icon="🚜", layout="wide")

# --- CSS (GENEL) ---
st.markdown("""
    <style>
    .main {background-color: #F8F9FA;}
    div[data-testid="stExpander"] {background-color: #FFFFFF; border-radius: 10px; border: 1px solid #E0E0E0;}
    /* Sarı-Siyah Şerit */
    .hazard-bar {
        width: 100%; height: 15px;
        background: repeating-linear-gradient(45deg, #f1c40f, #f1c40f 20px, #2c3e50 20px, #2c3e50 40px);
        margin-bottom: 20px; border-radius: 5px; opacity: 0.8;
    }
    </style>
    """, unsafe_allow_html=True)

# --- VIEWS IMPORT ---
from frontend.views import dashboard, map, inventory, analysis, alarms, geofence, settings

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