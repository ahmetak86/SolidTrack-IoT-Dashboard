import streamlit as st
import sys
import os
import folium
from datetime import datetime, timedelta
from streamlit_folium import st_folium

# --- PATH AYARI ---
# Backend modüllerini bulabilmesi için bir üst dizini yola ekliyoruz
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# --- IMPORTLAR ---
from views import dashboard, map, inventory, analysis, alarms, geofence, settings, reports
from backend.database import login_user, get_active_share_link, get_device_telemetry, get_last_operation_stats

# --- SAYFA AYARI ---
st.set_page_config(page_title="SolidTrack IoT", page_icon="🚜", layout="wide")

# --- CSS (MENÜ VE GENEL GÖRÜNÜM) ---
st.markdown("""
    <style>
    .main {background-color: #F8F9FA;}
    div[data-testid="stExpander"] {background-color: #FFFFFF; border-radius: 10px; border: 1px solid #E0E0E0;}
    
    /* --- SIDEBAR MENÜ TASARIMI --- */
    
    /* 1. Radio Butonlarının Yuvarlaklarını (Dairelerini) Gizle */
    div[role="radiogroup"] > label > div:first-child {
        display: none !important;
    }
    
    /* 2. Menü Elemanlarını Buton Gibi Yap */
    div[role="radiogroup"] label {
        padding: 10px 15px !important;
        margin-bottom: 5px !important;
        border-radius: 8px !important;
        border: 1px solid transparent !important;
        transition: all 0.2s ease;
        background-color: transparent;
        color: #31333F;
        cursor: pointer;
        display: block !important; /* Blok yaparak tam genişlik sağlar */
    }

    /* 3. Hover (Üzerine Gelince) Efekti */
    div[role="radiogroup"] label:hover {
        background-color: #f0f2f6 !important;
        border-color: #d1d5db !important;
    }

    /* 4. Seçili Olan (Active) Menü Tasarımı */
    div[role="radiogroup"] label[data-checked="true"] {
        background-color: #E8F0FE !important; /* Açık mavi zemin */
        color: #1976D2 !important; /* Mavi yazı */
        font-weight: bold !important;
        border-left: 5px solid #1976D2 !important; /* Soluna mavi çizgi */
    }
    
    /* Logo Ortala */
    [data-testid="stSidebar"] img {
        display: block;
        margin-left: auto;
        margin-right: auto;
        margin-bottom: 20px;
        object-fit: contain;
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
        
        # 1. BAŞLIK (Sadece Sol Taraf)
        st.title(f"{shared_device.unit_name}")
        st.caption(f"Model: {shared_device.asset_model} | Seri No: {shared_device.device_id}")

        # 2. ANA İÇERİK (Harita ve Bilgi Paneli)
        col_map, col_info = st.columns([2.5, 1])
        
        with col_map:
            # Harita
            telemetry = get_device_telemetry(shared_device.device_id, limit=1)
            if telemetry:
                last_loc = [telemetry[0].latitude, telemetry[0].longitude]
                m = folium.Map(location=last_loc, zoom_start=15)
                
                # --- DEVASA KIRMIZI İKON (fa-2x) ---
                folium.Marker(
                    last_loc, 
                    popup=shared_device.unit_name,
                    icon=folium.Icon(color="red", icon="truck fa-2x", prefix="fa")
                ).add_to(m)
                
                st_folium(m, height=500, use_container_width=True)
            else:
                st.warning("Konum verisi bekleniyor...")

        # --- SAĞ PANEL DÜZENİ ---
        with col_info:
            
            # A) SON DURUM
            status_color = "🟢" if shared_device.is_active else "🔴"
            status_text = "Aktif" if shared_device.is_active else "Pasif"
            
            st.markdown(f"### 📝 Son Durum : {status_color} {status_text}")
            st.write("") 
            
            # B) ADRES BİLGİSİ
            st.markdown("**📍 Güncel Adres**")
            st.info(stats["address"])
            st.write("") 
            
            # C) ÇALIŞMA BİLGİLERİ
            st.markdown("### ⏱️ Son Çalışma Bilgileri")
            
            now = datetime.now()
            end_time = now - timedelta(minutes=45) 
            start_time = end_time - timedelta(hours=1, minutes=22)
            
            st.markdown(f"""
            **Başlangıç:** {start_time.strftime('%d.%m.%Y - %H:%M')}  
            **Bitiş:** {end_time.strftime('%d.%m.%Y - %H:%M')}  
            **Süre:** 1 saat 22 dakika
            """)
            
            st.markdown("---")
            
            # D) WHATSAPP BUTONU
            current_url = f"http://localhost:8501/?token={token}"
            whatsapp_url = f"https://wa.me/?text=Makineyi%20buradan%20izleyebilirsin:%20{current_url}"
            
            st.markdown(f"""
                <a href="{whatsapp_url}" target="_blank" style="text-decoration: none;">
                    <div style="
                        background-color: #25D366; 
                        color: white; 
                        padding: 15px; 
                        border-radius: 8px; 
                        text-align: center; 
                        font-weight: bold; 
                        font-size: 18px;
                        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                        transition: transform 0.2s;">
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
        # --- LOGO & KULLANICI BİLGİSİ ---
        # Logo varsa göster, yoksa standart ikon
        if user.logo_url and os.path.exists(user.logo_url):
            st.image(user.logo_url, width=140)
        else:
            st.markdown("<h1 style='text-align: center;'>🚜</h1>", unsafe_allow_html=True)

        st.markdown(f"<div style='text-align: center; margin-bottom: 20px;'><b>{user.company_name}</b><br><span style='font-size:0.8em; color:gray;'>{user.full_name}</span></div>", unsafe_allow_html=True)
        
        # MENÜ SEÇENEKLERİ
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
        
        default_index = 0
        if "menu_selection" in st.session_state:
            try:
                target_menu = st.session_state["menu_selection"]
                default_index = list(menu_options.keys()).index(target_menu)
            except ValueError:
                default_index = 0
        
        # Radio buton (CSS ile buton gibi gözükmesi sağlandı)
        selected_menu = st.radio("Menü", list(menu_options.keys()), index=default_index, label_visibility="collapsed")
        
        if selected_menu != st.session_state.get("menu_selection"):
             st.session_state["menu_selection"] = selected_menu

        st.markdown("---")
        if st.button("Çıkış Yap", use_container_width=True): 
            st.session_state.user = None
            st.rerun()

    # SEÇİLEN SAYFAYI YÜKLE
    if selected_menu in menu_options:
        menu_options[selected_menu].load_view(user)