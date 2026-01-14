# frontend/views/geofence.py
import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from backend.database import create_geosite, get_user_geosites, delete_geosite, update_geosite

def load_view(user):
    st.markdown('<div class="hazard-bar"></div>', unsafe_allow_html=True) # SARI-SİYAH ŞERİT
    st.title("🚧 Şantiye ve Bölge Yönetimi")
    
    # State Başlangıçları
    if 'edit_mode' not in st.session_state: st.session_state.edit_mode = False
    if 'edit_site_id' not in st.session_state: st.session_state.edit_site_id = None
    if 'map_center' not in st.session_state: st.session_state.map_center = [39.9863, 32.7667] 
    if 'current_radius' not in st.session_state: st.session_state.current_radius = 500
    
    # Kullanıcının şantiyelerini çek
    my_sites = get_user_geosites(user.id)
    
    col_list, col_map = st.columns([1, 2.5])
    
    # --- SOL TARAF: LİSTE ---
    with col_list:
        st.subheader("📍 Şantiye Listesi")
        
        if st.button("➕ Yeni Şantiye Ekle", use_container_width=True):
            st.session_state.edit_mode = False
            st.session_state.edit_site_id = None
            st.session_state.map_center = [39.9863, 32.7667]
            st.session_state.form_name = ""
            st.session_state.form_addr = ""
            st.session_state.current_radius = 500
            st.rerun()

        st.markdown("---")

        if not my_sites:
            st.info("Henüz tanımlı şantiye yok.")
        else:
            for site in my_sites:
                with st.expander(f"🏗️ {site.name}", expanded=False):
                    st.write(f"**Adres:** {site.address}")
                    st.write(f"**Çap:** {site.radius_meters}m")
                    
                    b1, b2 = st.columns(2)
                    if b1.button("✏️ Düzenle", key=f"edit_{site.site_id}"):
                        st.session_state.edit_mode = True
                        st.session_state.edit_site_id = site.site_id
                        st.session_state.map_center = [site.latitude, site.longitude]
                        st.session_state.form_name = site.name
                        st.session_state.form_addr = site.address
                        st.session_state.current_radius = site.radius_meters
                        st.rerun()
                        
                    if b2.button("🗑️ Sil", key=f"del_{site.site_id}"):
                        delete_geosite(site.site_id)
                        st.rerun()

    # --- SAĞ TARAF: HARİTA & EDİTÖR ---
    with col_map:
        form_title = "🛠️ Şantiye Düzenle" if st.session_state.edit_mode else "➕ Yeni Şantiye Oluştur"
        st.subheader(form_title)
        
        def_name = st.session_state.get('form_name', "")
        def_addr = st.session_state.get('form_addr', "")
        
        c_name, c_addr = st.columns(2)
        site_name = c_name.text_input("Şantiye Adı", value=def_name, placeholder="Örn: Kadıköy Konut Projesi")
        site_addr = c_addr.text_input("Şantiye Adresi", value=def_addr, placeholder="Konum seçilince otomatik gelir...")

        # KOORDİNAT GİRİŞİ
        st.markdown("##### 🌐 Koordinatlar (Manuel Giriş)")
        c_lat, c_lon = st.columns(2)
        lat_val = st.session_state.map_center[0]
        lon_val = st.session_state.map_center[1]
        
        new_lat = c_lat.number_input("Enlem (Latitude)", value=lat_val, format="%.6f", step=0.0001)
        new_lon = c_lon.number_input("Boylam (Longitude)", value=lon_val, format="%.6f", step=0.0001)
        
        if new_lat != lat_val or new_lon != lon_val:
            st.session_state.map_center = [new_lat, new_lon]

        # HARİTA
        st.write("Veya haritaya tıklayarak konumu belirleyin:")
        m = folium.Map(location=st.session_state.map_center, zoom_start=15)
        folium.Marker(st.session_state.map_center, popup="Merkez", icon=folium.Icon(color="red", icon="home", prefix="fa")).add_to(m)
        folium.Circle(radius=st.session_state.current_radius, location=st.session_state.map_center, color="crimson", fill=True, fill_opacity=0.3).add_to(m)

        map_output = st_folium(m, height=400, width=800)

        if map_output and map_output.get("last_clicked"):
            clicked_lat = map_output["last_clicked"]["lat"]
            clicked_lng = map_output["last_clicked"]["lng"]
            if abs(clicked_lat - st.session_state.map_center[0]) > 0.00001:
                st.session_state.map_center = [clicked_lat, clicked_lng]
                st.session_state.form_addr = f"Seçilen Konum: {clicked_lat:.4f}, {clicked_lng:.4f}"
                st.rerun()

        # ÇAP AYARLARI
        st.markdown("---")
        st.markdown(f"#### 📏 Çap (metre) - Seçtiğiniz Şantiye: **{st.session_state.current_radius}m**")
        st.caption("Makinenin çalıştığı şantiyeden ne kadar uzaklaşabileceğini işaretleyin.")

        col_b = st.columns(6)
        btns = [500, 1000, 1500, 2000, 2500, 3000]
        for i, btn_val in enumerate(btns):
            if col_b[i].button(f"{btn_val}m", use_container_width=True):
                st.session_state.current_radius = btn_val
                st.rerun()

        col_rad1, col_rad2 = st.columns([3, 1])
        with col_rad1:
            slider_val = st.slider("Çapı Kaydırarak Belirle", 100, 100000, st.session_state.current_radius, 200, format="%d metre")
            if slider_val != st.session_state.current_radius:
                st.session_state.current_radius = slider_val
                st.rerun()

        with col_rad2:
            manual_rad = st.number_input("Çapı Manuel Belirle", value=st.session_state.current_radius, step=100)
            if manual_rad != st.session_state.current_radius:
                st.session_state.current_radius = manual_rad
                st.rerun()

        if st.session_state.current_radius > 20000: st.warning("⚠️ DİKKAT: 20 km üzerinde çap güvenlik zafiyeti oluşturabilir.")
        elif st.session_state.current_radius < 500: st.warning("⚠️ DİKKAT: 500 metre altı dar alan.")

        # GELİŞMİŞ AYARLAR
        with st.expander("⚙️ Gelişmiş Ayarlar"):
            adv_settings = {}
            if user.role == 'Admin': adv_settings['visible_to_subgroups'] = st.checkbox("Alt Gruplara Görünür Yap", value=False)
            else: st.caption("🔒 Alt grup görünürlüğü sadece Admin yetkisindedir.")
            adv_settings['apply_to_all_devices'] = st.checkbox("Mevcut tüm cihazlara uygula", value=True)
            adv_settings['auto_enable_new_devices'] = st.checkbox("Yeni cihazlar otomatik dahil olsun", value=True)
            adv_settings['auto_enable_alarms'] = st.checkbox("Alarmları aktif et", value=True)

        st.markdown("---")
        btn_text = "💾 Değişiklikleri Kaydet" if st.session_state.edit_mode else "✅ Şantiyeyi Oluştur"
        
        if st.button(btn_text, type="primary", use_container_width=True):
            if not site_name:
                st.error("Lütfen Şantiye Adı giriniz.")
            else:
                existing_sites = get_user_geosites(user.id)
                duplicate = False
                for s in existing_sites:
                    if s.name.lower() == site_name.lower():
                        if not st.session_state.edit_mode: duplicate = True
                        elif st.session_state.edit_mode and s.site_id != st.session_state.edit_site_id: duplicate = True
                
                if duplicate:
                    st.error(f"❌ '{site_name}' adında bir şantiye zaten var.")
                else:
                    final_lat = st.session_state.map_center[0]
                    final_lon = st.session_state.map_center[1]
                    final_rad = st.session_state.current_radius
                    
                    if st.session_state.edit_mode:
                        res = update_geosite(st.session_state.edit_site_id, site_name, final_lat, final_lon, final_rad, site_addr, adv_settings)
                        if res: st.success("✅ Güncellendi!"); st.session_state.edit_mode = False; st.session_state.edit_site_id = None; st.rerun()
                        else: st.error("Hata.")
                    else:
                        res = create_geosite(user.id, site_name, final_lat, final_lon, final_rad, site_addr, adv_settings)
                        if res: st.success(f"✅ Oluşturuldu!"); st.rerun()
                        else: st.error("Hata.")
    
    st.markdown('<div class="hazard-bar"></div>', unsafe_allow_html=True)