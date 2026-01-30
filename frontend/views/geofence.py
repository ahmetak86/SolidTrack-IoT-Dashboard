import streamlit as st
import pandas as pd
import folium
import time
import sys
import os
from streamlit_folium import st_folium
from geopy.geocoders import Nominatim

# 1. ÖNCE ANA KLASÖRÜ TANIT
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

# 2. SONRA DİĞER DOSYALARI ÇAĞIR
from frontend.utils import format_date_for_ui
from backend.database import (
    create_geosite, get_user_geosites, delete_geosite, update_geosite, 
    get_user_devices, update_geosite_devices,
    SessionLocal, GeoSite, update_user_settings, sync_geosites_from_trusted
)

# --- YARDIMCI: ADRES BULUCU ---
def get_address_from_coords(lat, lon):
    try:
        geolocator = Nominatim(user_agent="solidtrack_iot_v5")
        location = geolocator.reverse((lat, lon), timeout=5)
        return location.address if location else "Adres bulunamadı"
    except:
        return "Adres servisine erişilemiyor"

# --- DB GÜNCELLEME YARDIMCISI (Toggle İçin) ---
def update_geosite_field(site_id, field_name, value):
    db = SessionLocal()
    try:
        site = db.query(GeoSite).filter(GeoSite.site_id == site_id).first()
        if site:
            setattr(site, field_name, value)
            db.commit()
            return True
    except Exception as e:
        print(f"Update Error: {e}")
        db.rollback()
    finally:
        db.close()
    return False

# --- SAYFA YÜKLEYİCİ ---
def load_view(user):
    # CSS: Kart ve Buton Tasarımları
    st.markdown("""
        <style>
        .geosite-card {
            border: 1px solid #e0e0e0;
            border-radius: 12px;
            padding: 15px;
            background-color: white;
            margin-bottom: 15px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        }
        .radius-btn-group button {
            border-radius: 20px !important;
            font-size: 12px !important;
            padding: 0.25rem 0.5rem !important;
        }
        /* Leaflet attribution gizle */
        .leaflet-control-attribution {
            display: none !important;
        }
        </style>
    """, unsafe_allow_html=True)

    # State Yönetimi
    if 'page_mode' not in st.session_state: st.session_state.page_mode = 'list'
    if 'edit_site_id' not in st.session_state: st.session_state.edit_site_id = None
    if 'map_center' not in st.session_state: st.session_state.map_center = [39.9334, 32.8597] 
    if 'current_radius' not in st.session_state: st.session_state.current_radius = 500
    if 'form_name' not in st.session_state: st.session_state.form_name = ""
    if 'form_addr' not in st.session_state: st.session_state.form_addr = ""

    # Sayfa Yönlendirmesi
    if st.session_state.page_mode == 'list':
        render_list_view(user)
    else:
        render_editor_view(user)

    st.markdown('<div style="height: 50px;"></div>', unsafe_allow_html=True)
    
# ==========================================
# 1. LİSTE GÖRÜNÜMÜ (ANA EKRAN)
# ==========================================
# frontend/views/geofence.py -> render_list_view

def render_list_view(user):
    # 1. HEADER ALANI
    st.title("🚧 Şantiye ve Bölge Yönetimi")
    
    c_btn_new, c_btn_sync = st.columns([1, 1])
    
    # Verileri Çek
    my_sites = get_user_geosites(user.id)
    all_devices = get_user_devices(user.id)
    
    with c_btn_new:
        if st.button("➕ Yeni Şantiye Oluştur", type="primary", use_container_width=True):
            st.session_state.page_mode = 'create'
            st.session_state.edit_site_id = None
            st.session_state.form_name = ""
            st.session_state.form_addr = ""
            st.session_state.current_radius = 500
            st.session_state.map_center = [39.9334, 32.8597]
            st.rerun()
            
    with c_btn_sync:
        if st.button("🔄 Şantiyeleri Senkronize Et", use_container_width=True, help="Sunucu tarafında yapılan değişiklikleri (Yarıçap, Konum vb.) sisteme çeker."):
            with st.spinner("Sunucu ile haberleşiliyor..."):
                success, msg = sync_geosites_from_trusted(user.id)
            if success:
                st.toast(f"Senkronizasyon Başarılı: {msg}", icon="✅")
                time.sleep(1)
                st.rerun()
            else:
                st.error(f"Hata: {msg}")

    st.markdown("---")

    if not my_sites:
        st.info("👋 Henüz oluşturulmuş bir şantiye bölgesi bulunmamaktadır.")
    else:
        # AKORDEON MANTIĞI
        total_sites = len(my_sites)
        
        for index, site in enumerate(my_sites):
            is_expanded = False
            if total_sites <= 2: is_expanded = True
            elif index == 0: is_expanded = True
            
            # Başlık
            short_addr = (site.address[:50] + '...') if site.address and len(site.address) > 50 else (site.address if site.address else 'Adres Yok')
            expander_label = f"🏗️ {site.name}  —  📍 {short_addr}"

            with st.expander(expander_label, expanded=is_expanded):
                
                # --- SOL TARAFTAKİ DETAY BİLGİLERİ ---
                # Sütunları ayırmadan alt alta ve bold yazıyoruz
                
                # 1. Tam Adres (BOLD)
                st.markdown(f"**📍 Şantiye Açık Adres:** {site.address if site.address else 'Belirtilmemiş'}")
                
                # 2. Yarıçap (BOLD) - Hemen altında
                st.markdown(f"**📏 Şantiye Yarıçapı: {site.radius_meters}m**")
                
                # 3. Tarih (Gri ve küçük)
                created_str = format_date_for_ui(site.created_at, user.timezone) if site.created_at else "Bilinmiyor"
                st.caption(f"📅 Şantiye Oluşturulma Tarihi: {created_str}")

                # --- SIKIŞIK SEPERATÖR ---
                # st.markdown("---") yerine HTML ile margin'i alınmış çizgi çekiyoruz
                st.markdown("<hr style='margin-top: 5px; margin-bottom: 15px;'>", unsafe_allow_html=True)

                c_devices, c_actions = st.columns([1.5, 1])
                
                # --- SOL: CİHAZ YÖNETİMİ ---
                with c_devices:
                    st.markdown("**🚜 Makine Listesi**")
                    assigned_ids = [d.device_id for d in site.devices]
                    
                    df_data = []
                    for dev in all_devices:
                        df_data.append({
                            "Seç": dev.device_id in assigned_ids,
                            "Makine Modeli": dev.unit_name, 
                            "ID": dev.device_id 
                        })
                    
                    df = pd.DataFrame(df_data)
                    
                    edited_df = st.data_editor(
                        df,
                        column_config={
                            "Seç": st.column_config.CheckboxColumn("Ekle", width="small", default=False),
                            "Makine Modeli": st.column_config.TextColumn("Makine Modeli", width="medium", disabled=True),
                            "ID": None
                        },
                        hide_index=True,
                        key=f"editor_{site.site_id}",
                        height=150
                    )
                    
                    if st.button("💾 Listeyi Güncelle", key=f"btn_save_{site.site_id}", use_container_width=True):
                        selected_rows = edited_df[edited_df["Seç"] == True]
                        new_selected_ids = selected_rows["ID"].tolist()
                        
                        from backend.database import update_geosite_devices
                        with st.spinner("Sunucu güncelleniyor..."):
                            update_geosite_devices(site.site_id, new_selected_ids)
                        
                        st.toast("Makine listesi güncellendi!", icon="✅")
                        time.sleep(1)
                        st.rerun()

                # --- SAĞ: AKSİYONLAR ---
                with c_actions:
                    st.markdown("**⚙️ Aksiyonlar**")
                    
                    # Alarm
                    alarm_val = getattr(site, 'auto_enable_alarms', True)
                    new_alarm_val = st.toggle("🚨 Bölge İhlal Alarmı", value=alarm_val, key=f"al_main_{site.site_id}")
                    
                    if new_alarm_val != alarm_val:
                        from backend.database import toggle_geosite_alarm_status
                        toggle_geosite_alarm_status(site.site_id, new_alarm_val)
                        status = "Aktif" if new_alarm_val else "Pasif"
                        st.toast(f"Alarm: {status}", icon="🔔")
                        time.sleep(1)
                        st.rerun()

                    st.write("") 
                    st.write("") 
                    
                    # --- GÜVENLİ SİLME MEKANİZMASI ---
                    c_edit, c_del = st.columns(2)
                    
                    # Düzenle Butonu
                    if c_edit.button("✏️ Düzenle", key=f"edt_{site.site_id}", use_container_width=True):
                        st.session_state.page_mode = 'edit'
                        st.session_state.edit_site_id = site.site_id
                        st.session_state.form_name = site.name
                        st.session_state.form_addr = site.address
                        st.session_state.current_radius = site.radius_meters
                        st.session_state.map_center = [site.latitude, site.longitude]
                        st.rerun()
                    
                    # Silme Butonu (Toggle Mantığı)
                    # Her kartın kendi "Silme Modu" state'i olsun
                    del_mode_key = f"del_confirm_{site.site_id}"
                    if del_mode_key not in st.session_state:
                        st.session_state[del_mode_key] = False

                    if not st.session_state[del_mode_key]:
                        # İlk aşama: Basınca Onay Moduna geç
                        if c_del.button("🗑️ Sil", key=f"pre_del_{site.site_id}", use_container_width=True):
                            st.session_state[del_mode_key] = True
                            st.rerun()
                    else:
                        # İkinci aşama: Onay veya İptal
                        c_del.empty() # Eski butonu sil
                        col_yes, col_no = st.columns(2)
                        if col_yes.button("✅ Evet", key=f"yes_{site.site_id}", type="primary", use_container_width=True):
                            delete_geosite(site.site_id)
                            st.toast(f"Şantiye silindi.", icon="🗑️")
                            del st.session_state[del_mode_key] # State temizle
                            time.sleep(1)
                            st.rerun()
                        
                        if col_no.button("❌ İptal", key=f"no_{site.site_id}", use_container_width=True):
                            st.session_state[del_mode_key] = False # İptal et
                            st.rerun()

# ==========================================
# 2. EDİTÖR GÖRÜNÜMÜ (HARİTA VE FORM)
# ==========================================
def render_editor_view(user):
    is_edit = (st.session_state.page_mode == 'edit')
    page_title = "🛠️ Şantiyeyi Düzenle" if is_edit else "➕ Yeni Şantiye Oluştur"
    
    # Navigasyon
    col_back, col_title = st.columns([1, 5])
    with col_back:
        if st.button("← Geri"):
            st.session_state.page_mode = 'list'
            st.rerun()
    with col_title:
        st.subheader(page_title)
    
    col_map_area, col_form_area = st.columns([1.8, 1.2])

    # --- SAĞ TARAF: FORM ALANI ---
    with col_form_area:
        st.markdown("### 📝 Şantiye Detayları")
        
        name_input = st.text_input("Şantiye Adı", value=st.session_state.form_name, placeholder="Örn: Kuzey Marmara Otoyolu - Kesim 4")
        
        # Manuel Koordinat
        st.markdown("##### 📍 Koordinatlar")
        c_lat, c_lon = st.columns(2)
        curr_lat, curr_lon = st.session_state.map_center
        new_lat = c_lat.number_input("Enlem", value=float(curr_lat), format="%.6f", step=0.0001)
        new_lon = c_lon.number_input("Boylam", value=float(curr_lon), format="%.6f", step=0.0001)
        
        if new_lat != curr_lat or new_lon != curr_lon:
            st.session_state.map_center = [new_lat, new_lon]
            # --- YENİ EKLENEN SATIR: Adresi de güncelle ---
            st.session_state.form_addr = get_address_from_coords(new_lat, new_lon)
            st.rerun()

        # Adres Alanı
        addr_label = "Açık Adres (Haritadan seçtiğiniz adres otomatik olarak buraya gelir.)"
        addr_input = st.text_area(addr_label, value=st.session_state.form_addr, height=80, placeholder="Konum seçilince otomatik dolar...")
        
        # --- YARIÇAP AYARI ---
        st.markdown("##### 📏 Yarıçap (Radius)")
        
        # Hızlı Butonlar
        st.markdown('<div class="radius-btn-group">', unsafe_allow_html=True)
        btn_cols = st.columns(5)
        presets = [200, 500, 1000, 2000, 5000]
        for i, val in enumerate(presets):
            if btn_cols[i].button(f"{val}m", key=f"r_btn_{val}", use_container_width=True):
                st.session_state.current_radius = val
                st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

        # Slider ve Manuel Input
        c_slide, c_man = st.columns([3, 1])
        
        range_low = list(range(200, 2001, 100))
        range_high = list(range(2500, 10001, 500))
        radius_options = sorted(list(set(range_low + range_high)))
        
        if st.session_state.current_radius not in radius_options:
            radius_options.append(st.session_state.current_radius)
            radius_options.sort()
        
        with c_slide:
            val_slider = st.select_slider(
                "Kaydırarak Belirle",
                options=radius_options,
                value=st.session_state.current_radius,
                format_func=lambda x: f"{x} m",
                label_visibility="collapsed"
            )
        
        with c_man:
            val_manual = st.number_input(
                "Manuel", 
                min_value=100, max_value=10000, 
                value=st.session_state.current_radius, 
                step=50,
                label_visibility="collapsed"
            )

        if val_slider != st.session_state.current_radius:
            st.session_state.current_radius = val_slider
            st.rerun()
        elif val_manual != st.session_state.current_radius:
            st.session_state.current_radius = val_manual
            st.rerun()

        # --- GELİŞMİŞ AYARLAR (STATE SENKRONİZASYONU) ---
        # 1. Varsayılan Değerler (Yeni oluşturma için)
        s_alarms = True
        s_all_devs = True 
        
        # 2. Eğer Düzenleme Modundaysak (is_edit=True)
        # Checkbox'ları ekranda göstermesek bile, veritabanındaki mevcut değerleri 
        # 's_alarms' ve 's_all_devs' değişkenlerine atamalıyız.
        # Böylece aşağıda 'Kaydet' butonuna bastığında eski ayarlar silinmez.
        if is_edit:
            my_sites = get_user_geosites(user.id)
            target_site = next((s for s in my_sites if s.site_id == st.session_state.edit_site_id), None)
            if target_site:
                s_alarms = target_site.auto_enable_alarms
                s_all_devs = target_site.apply_to_all_devices

        # 3. UI Gösterimi (Sadece YENİ oluştururken)
        if not is_edit:
            with st.expander("⚙️ Gelişmiş Ayarlar", expanded=True):
                # Burada s_alarms ve s_all_devs değişkenleri güncellenir
                s_alarms = st.checkbox("Bölge İhlal Alarmını Aktif Et", value=s_alarms)
                s_all_devs = st.checkbox("Tüm cihazlara otomatik uygula", value=s_all_devs)
                st.caption("Not: Bir cihaz birden fazla şantiyeye kayıt edilebilir.")

        st.markdown("---")
        
        # KAYDET
        btn_label = "💾 Değişiklikleri Kaydet" if is_edit else "✅ Şantiyeyi Oluştur"
        if st.button(btn_label, type="primary", use_container_width=True):
            if not name_input:
                st.error("Lütfen bir şantiye adı girin.")
            else:
                final_lat = st.session_state.map_center[0]
                final_lon = st.session_state.map_center[1]
                final_rad = st.session_state.current_radius
                
                # Parametreleri topla
                adv_settings = {
                    "auto_enable_alarms": s_alarms,          # Çıkış
                    "apply_to_all_devices": s_all_devs
                }

                if is_edit:
                    update_geosite(st.session_state.edit_site_id, name_input, final_lat, final_lon, final_rad, addr_input, adv_settings)
                    st.toast("Şantiye başarıyla güncellendi!", icon="✅")
                else:
                    create_geosite(user.id, name_input, final_lat, final_lon, final_rad, addr_input, adv_settings)
                    st.toast("Yeni şantiye başarıyla oluşturuldu!", icon="🎉")
                
                time.sleep(1) 
                st.session_state.page_mode = 'list'
                st.rerun()

    # --- SOL TARAF: HARİTA ---
    with col_map_area:
        lat, lon = st.session_state.map_center
        
        # HARİTA AYARLARI: OpenStreetMap YOK, DoubleClickZoom KAPALI
        m = folium.Map(
            location=[lat, lon], 
            zoom_start=15, 
            control_scale=True, 
            double_click_zoom=False,
            tiles=None  # Default OSM'yi engelle
        )
        
        # Sadece Google Katmanları
        folium.TileLayer(
            tiles='https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}',
            attr='Google',
            name='Google Uydu (Hibrit)',
            overlay=False,
            control=True
        ).add_to(m)

        folium.TileLayer(
            tiles='https://mt1.google.com/vt/lyrs=m&x={x}&y={y}&z={z}',
            attr='Google',
            name='Google Sokak',
            overlay=False,
            control=True
        ).add_to(m)

        folium.LayerControl().add_to(m)

        # Merkez İkonu
        folium.Marker(
            [lat, lon],
            popup="Şantiye Merkezi",
            icon=folium.Icon(color="red", icon="home", prefix="fa"),
            tooltip=f"{lat:.5f}, {lon:.5f}"
        ).add_to(m)

        # Yarıçap Dairesi (Interactive=False ve Popup yok -> Tıklama içinden geçer)
        folium.Circle(
            location=[lat, lon],
            radius=st.session_state.current_radius,
            color="#3388ff",
            weight=2,
            fill=True,
            fill_opacity=0.2,
            interactive=False 
            # popup parametresini sildik, artık tıklamayı engellemez
        ).add_to(m)

        map_data = st_folium(m, height=700, width="100%")

        # Tıklama ile Konum Güncelleme
        if map_data and map_data.get("last_clicked"):
            clicked_lat = map_data["last_clicked"]["lat"]
            clicked_lng = map_data["last_clicked"]["lng"]
            
            if abs(clicked_lat - lat) > 0.000001 or abs(clicked_lng - lon) > 0.000001:
                st.session_state.map_center = [clicked_lat, clicked_lng]
                found_address = get_address_from_coords(clicked_lat, clicked_lng)
                st.session_state.form_addr = found_address
                st.rerun()