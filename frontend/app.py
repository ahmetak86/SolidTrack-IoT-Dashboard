# frontend/app.py (V3 - FINAL MİSAFİR EKRANI)
import streamlit as st
import sys
import os
import folium
from datetime import datetime, timedelta
from streamlit_folium import st_folium

# --- PATH AYARI ---
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# --- IMPORTLAR ---
from views import dashboard, map, inventory, analysis, alarms, geofence, settings, reports
from backend.database import login_user, get_active_share_link, get_device_telemetry, get_last_operation_stats

# --- SAYFA AYARI ---
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
query_params = st.query_params
if "token" in query_params:
    token = query_params["token"]
    
    shared_device = get_active_share_link(token)
    
    if shared_device:
        stats = get_last_operation_stats(shared_device.device_id)
        
        # --- MİSAFİR GÖRÜNÜMÜ ---
        st.markdown('<div class="hazard-bar"></div>', unsafe_allow_html=True)
        
        # Header Düzeni: İsim | Son Durum
        h1, h2 = st.columns([3, 1])
        with h1:
            st.title(f"{shared_device.unit_name}")
            st.caption(f"Model: {shared_device.asset_model} | Seri No: {shared_device.device_id}")
        with h2:
            # Durum göstergesi (Başlığın yanında)
            status_color = "🟢" if shared_device.is_active else "🔴"
            status_text = "Aktif" if shared_device.is_active else "Pasif"
            st.markdown(f"### Son Durum: {status_color} {status_text}")

        col_map, col_info = st.columns([2.5, 1])
        
        with col_map:
            # Harita (Kırmızı Marker)
            telemetry = get_device_telemetry(shared_device.device_id, limit=1)
            if telemetry:
                last_loc = [telemetry[0].latitude, telemetry[0].longitude]
                m = folium.Map(location=last_loc, zoom_start=15)
                # İKONU KIRMIZI YAPTIK
                folium.Marker(
                    last_loc, 
                    popup=shared_device.unit_name,
                    icon=folium.Icon(color="red", icon="truck", prefix="fa")
                ).add_to(m)
                st_folium(m, height=450, use_container_width=True)
            else:
                st.warning("Konum verisi bekleniyor...")

        with col_info:
            # --- SAĞ PANEL BİLGİLERİ ---
            st.subheader("📋 Son Çalışma Bilgileri")
            
            # Adres
            st.markdown("**📍 Güncel Adres**")
            st.info(stats["address"])
            
            # Zaman Hesaplama (Demo için simülasyon)
            # Backend'den gelen 'duration' (Örn: "2 saat 10 dakika") stringini parse ediyoruz
            # veya şu anın tarihinden geriye giderek mantıklı bir aralık oluşturuyoruz.
            now = datetime.now()
            
            # Rastgele bir bitiş saati (Gerçekçi dursun diye)
            end_time = now - timedelta(minutes=45) 
            # Süreyi backend'den gelen stringden çıkarabiliriz ama demo için sabit mantık kuralım:
            start_time = end_time - timedelta(hours=1, minutes=22)
            
            st.write(f"**Başlangıç:** {start_time.strftime('%d.%m.%Y - %H:%M')}")
            st.write(f"**Bitiş:** {end_time.strftime('%d.%m.%Y - %H:%M')}")
            st.write(f"**Süre:** 1 saat 22 dakika")
            
            st.markdown("---")
            
            # WHATSAPP PAYLAŞ BUTONU (YEŞİL)
            current_url = f"http://localhost:8501/?token={token}"
            whatsapp_url = f"https://wa.me/?text=Makineyi%20buradan%20izleyebilirsin:%20{current_url}"
            
            # type="secondary" normal gri butondur, custom style ile yeşil yapalım ya da emoji kullanalım.
            # Streamlit native buton renkleri kısıtlıdır, emoji ile destekliyoruz.
            st.markdown(f"""
                <a href="{whatsapp_url}" target="_blank" style="text-decoration: none;">
                    <div style="background-color: #25D366; color: white; padding: 10px; border-radius: 5px; text-align: center; font-weight: bold;">
                        📲 WhatsApp ile Gönder
                    </div>
                </a>
            """, unsafe_allow_html=True)
            
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

    if selected_menu in menu_options:
        menu_options[selected_menu].load_view(user)