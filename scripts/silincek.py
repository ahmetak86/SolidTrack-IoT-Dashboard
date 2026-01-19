import streamlit as st
import folium
from folium.plugins import MarkerCluster, Fullscreen, AntPath
from streamlit_folium import st_folium
import os
from datetime import datetime, timedelta, date
import pandas as pd
import math
from backend.database import get_user_devices, get_device_telemetry, get_all_devices_for_admin

# --- MESAFE HESAPLAMA (Haversine) ---
def calculate_distance(lat1, lon1, lat2, lon2):
    R = 6371  # Dünya yarıçapı (km)
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) * math.sin(dlat / 2) + \
        math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * \
        math.sin(dlon / 2) * math.sin(dlon / 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

# --- İKON HELPER ---
TYPE_DISPLAY_MAP = {
    "hydraulic_breaker": "Hidrolik Kırıcı", "hydraulic_auger": "Hidrolik Burgu",
    "hydraulic_shear": "Hidrolik Makas", "concrete_cutter": "Beton Kesici",
    "drum_cutter": "Tambur Kesici", "pulverizer": "Pulverizatör",
    "log_grapple": "Kütük Kıskacı", "excavator_grapple": "Ekskavatör Kıskacı",
    "hydraulic_drifter": "Hidrolik Delici", "crusher_bucket": "Kırıcı Kova",
    "ripper": "Riper", "excavator": "Ekskavatör", "truck": "Kamyon",
    "concrete_mixer": "Beton Mikseri", "mixer": "Beton Mikseri",
    "forklift": "Forklift", "generator": "Jeneratör",
    "bulldozer": "Buldozer", "dozer": "Buldozer",
    "dump_truck": "Damperli Kamyon", "tractor": "Traktör",
    "mobile_crane": "Mobil Vinç", "tower_crane": "Kule Vinç",
    "roller": "Kompaktör/Silindir", "backhoe": "Kazıcı Yükleyici (JCB)",
    "scissor_lift": "Makaslı Platform", "pickup": "Pickup", "light_tower": "Işık Kulesi"
}

def get_display_name(type_code):
    if not type_code: return "Diğer"
    code = str(type_code).lower().strip()
    return TYPE_DISPLAY_MAP.get(code, code.replace("_", " ").title())

def get_icon_path(type_code):
    if not type_code: return None
    current_dir = os.path.dirname(os.path.abspath(__file__)) 
    root_dir = os.path.dirname(os.path.dirname(current_dir))
    ICON_DIR = os.path.join(root_dir, "static", "icons")
    full_path = os.path.join(ICON_DIR, f"{type_code}.png")
    return full_path if os.path.exists(full_path) else None

def load_view(user):
    st.markdown("### 🌍 Canlı Saha Operasyonu")
    
    # --- SESSION STATE (Hafıza) ---
    # Seçili cihazı ve rotayı hafızada tutuyoruz ki sayfa titrese de kaybolmasın
    if "map_selected_device_id" not in st.session_state:
        st.session_state.map_selected_device_id = None
    if "map_route_data" not in st.session_state:
        st.session_state.map_route_data = None

    all_devices = get_all_devices_for_admin() if user.role == 'Admin' else get_user_devices(user.id)
    if not all_devices:
        st.warning("Kayıtlı cihaz yok.")
        return

    # --- FİLTRELER ---
    c_filter1, c_filter2, c_settings = st.columns([1.5, 2, 1.5])
    
    # 1. TİP FİLTRESİ
    raw_types = sorted(list(set([d.icon_type if d.icon_type else "other" for d in all_devices])))
    with c_filter1:
        selected_types = st.multiselect("1. Makine Tipi:", ["Hepsi"] + raw_types, default=["Hepsi"], 
                                        format_func=lambda x: "TÜM TİPLER" if x == "Hepsi" else get_display_name(x))
    
    final_types = raw_types if "Hepsi" in selected_types else selected_types
    devices_by_type = [d for d in all_devices if (d.icon_type if d.icon_type else "other") in final_types]
    
    # 2. MODEL FİLTRESİ
    device_names = [d.unit_name for d in devices_by_type]
    
    # Eğer haritadan bir cihaza tıklandıysa, filtrede onu otomatik seçili yap
    default_selection = []
    if st.session_state.map_selected_device_id:
        found = next((d for d in all_devices if str(d.device_id) == str(st.session_state.map_selected_device_id)), None)
        if found and found.unit_name in device_names:
            default_selection = [found.unit_name]

    with c_filter2:
        selected_units = st.multiselect("2. Makine Modeli:", ["Hepsi"] + device_names, default=default_selection, placeholder="Tüm cihazlar...")
    
    if "Hepsi" in selected_units:
        final_devices = devices_by_type
    elif selected_units:
        final_devices = [d for d in devices_by_type if d.unit_name in selected_units]
    else:
        final_devices = devices_by_type

    with c_settings:
        st.write("") 
        st.write("") 
        col_chk1, col_chk2 = st.columns(2)
        with col_chk1: enable_cluster = st.checkbox("Kümele", value=True)
        with col_chk2: show_names_permanent = st.checkbox("İsimler", value=False)

    st.markdown("---")

    # --- TEK CİHAZ MODU & TARİH SEÇİCİ ---
    is_single_device = len(final_devices) == 1
    
    if is_single_device:
        target_device = final_devices[0]
        
        # Eğer filtreyle (veya tıklamayla) cihaz değiştiyse hafızayı güncelle
        if str(target_device.device_id) != str(st.session_state.map_selected_device_id):
            st.session_state.map_selected_device_id = str(target_device.device_id)
            st.session_state.map_route_data = None # Cihaz değişti, eski rotayı sil

        st.info(f"📍 **{target_device.unit_name}** analiz ediliyor.")
        
        # Form: Sayfa sürekli yenilenmesin diye butonla kontrol ediyoruz
        with st.form("history_form"):
            c_p, c_d1, c_d2, c_b = st.columns([1.5, 1.5, 1.5, 1])
            with c_p:
                period = st.selectbox("Periyot:", ["Tarih Seç", "Bugün", "Son 1 Hafta", "Son 1 Ay", "Tüm Zamanlar"])
            
            today = datetime.now().date()
            start_def = today - timedelta(days=7)
            
            with c_d1: d_start = st.date_input("Başlangıç:", value=start_def, max_value=today)
            with c_d2: d_end = st.date_input("Bitiş:", value=today, min_value=d_start, max_value=today)
            with c_b:
                st.write("") 
                st.write("") 
                submit_btn = st.form_submit_button("Rotayı Çiz", type="primary")

        if submit_btn:
            # Periyot mantığı
            if period == "Bugün": s, e = today, today
            elif period == "Son 1 Hafta": s, e = today - timedelta(days=7), today
            elif period == "Son 1 Ay": s, e = today - timedelta(days=30), today
            elif period == "Tüm Zamanlar": s, e = date(2020, 1, 1), today
            else: s, e = d_start, d_end # "Tarih Seç" ise inputları al

            # Veri Çekme
            raw = get_device_telemetry(target_device.device_id, limit=10000)
            filtered = [l for l in raw if s <= l.timestamp.date() <= e]
            filtered.sort(key=lambda x: x.timestamp)
            st.session_state.map_route_data = filtered # Hafızaya kaydet

    else:
        st.session_state.map_route_data = None # Çoklu seçimde rota yok

    # --- HARİTA MERKEZLEME ---
    default_loc = [39.0, 35.0]
    default_zoom = 6
    start_coords = default_loc

    history_logs = st.session_state.map_route_data

    # Zoom Önceliği: 1. Rota, 2. Cihaz Konumu, 3. Genel
    if is_single_device and history_logs:
         start_coords = [history_logs[0].latitude, history_logs[0].longitude]
         default_zoom = 12
    elif is_single_device and final_devices:
         l = get_device_telemetry(final_devices[0].device_id, limit=1)
         if l:
             start_coords = [l[0].latitude, l[0].longitude]
             default_zoom = 12

    m = folium.Map(location=start_coords, zoom_start=default_zoom, tiles="CartoDB positron")
    Fullscreen().add_to(m)

    # --- ROTA ÇİZİMİ ---
    if is_single_device and history_logs:
        pts = [[l.latitude, l.longitude] for l in history_logs]
        AntPath(locations=pts, color="#225d97", weight=5, opacity=0.8, dash_array=[15, 30], delay=1000, pulse_color="#f1c232").add_to(m)
        
        start_t = history_logs[0].timestamp.strftime('%d.%m %H:%M')
        end_t = history_logs[-1].timestamp.strftime('%d.%m %H:%M')
        folium.Marker(pts[0], popup=f"🏁 Başlangıç: {start_t}", icon=folium.Icon(color="green", icon="play", prefix="fa")).add_to(m)
        folium.Marker(pts[-1], popup=f"🛑 Bitiş: {end_t}", icon=folium.Icon(color="red", icon="flag", prefix="fa")).add_to(m)

    # --- KÜMELEME ---
    cluster = MarkerCluster(name="Küme", icon_create_function="""
        function(cluster) {
            var childCount = cluster.getChildCount();
            return L.divIcon({ html: '<div style="background-color: #225d97; color: white; border-radius: 50%; width: 40px; height: 40px; display: flex; align-items: center; justify-content: center; font-weight: bold; font-family: sans-serif; border: 4px solid rgba(34, 93, 151, 0.4);"><span>' + childCount + '</span></div>', className: 'marker-cluster-custom', iconSize: new L.Point(50, 50) });
        }
    """)
    map_layer = cluster if enable_cluster else m
    if enable_cluster: cluster.add_to(m)

    # --- PİNLER ---
    lats, lons = [], []
    for d in final_devices:
        logs = get_device_telemetry(d.device_id, limit=1)
        if logs:
            l = logs[0]
            lats.append(l.latitude)
            lons.append(l.longitude)
            
            c_icon = get_icon_path(d.icon_type)
            if c_icon:
                icon_obj = folium.CustomIcon(icon_image=c_icon, icon_size=(64, 86), icon_anchor=(32, 86), popup_anchor=(0, -80))
            else:
                icon_obj = folium.Icon(color="blue", icon="wrench", prefix="fa")
            
            # --- POPUP İÇERİĞİ (İSTEKLERİNE GÖRE DÜZENLENDİ) ---
            popup_html = f"""
            <div style="font-family: sans-serif; width: 220px; color:#333;">
                <b style="font-size:14px">{d.unit_name}</b><br>
                <span style="color:gray; font-size:11px">{d.asset_model} ({get_display_name(d.icon_type)})</span>
                <hr style="margin:5px 0; border-top: 1px solid #ddd;">
                <div style="font-size:12px; line-height:1.6;">
                    📡 <b>Son Sinyal:</b> {l.timestamp.strftime('%d.%m.%Y %H:%M')}<br>
                    ⏱️ <b>Son Çalışma:</b> -- dk<br>
                    ∑ <b>Top. Çalışma:</b> -- Saat<br>
                    📍 <b>Konum:</b> {l.latitude:.5f}, {l.longitude:.5f}<br>
                    🔋 <b>Pil:</b> %--
                </div>
                <div style="margin-top:8px; font-size:11px; color:#225d97; text-align:center;">
                    <i>(Rotayı görmek için pine tıklayın)</i>
                </div>
            </div>
            """
            folium.Marker([l.latitude, l.longitude], popup=folium.Popup(popup_html, max_width=250), tooltip=d.unit_name, icon=icon_obj).add_to(map_layer)

    # Otomatik Zoom
    if is_single_device and history_logs:
         lats_h = [l.latitude for l in history_logs]
         lons_h = [l.longitude for l in history_logs]
         m.fit_bounds([[min(lats_h), min(lons_h)], [max(lats_h), max(lons_h)]], padding=(50, 50))
    elif lats and not is_single_device:
        m.fit_bounds([[min(lats), min(lons)], [max(lats), max(lons)]], padding=(50, 50))
    
    # --- HARİTA ÇIKTISI (TIKLAMA YAKALAMA) ---
    map_output = st_folium(m, height=500, use_container_width=True)

    # EĞER BİR PİNE TIKLANDIYSA -> Login sorunu olmadan cihaz seç
    if map_output.get("last_object_clicked"):
        clicked_lat = map_output["last_object_clicked"].get("lat")
        clicked_lng = map_output["last_object_clicked"].get("lng")
        
        # Koordinattan cihazı bul
        for d in final_devices:
            logs = get_device_telemetry(d.device_id, limit=1)
            if logs:
                l = logs[0]
                if abs(l.latitude - clicked_lat) < 0.0001 and abs(l.longitude - clicked_lng) < 0.0001:
                    if str(d.device_id) != str(st.session_state.map_selected_device_id):
                        st.session_state.map_selected_device_id = str(d.device_id)
                        st.session_state.map_route_data = None
                        st.rerun() # Sayfayı yenile

    # --- GÜNLÜK ÖZET TABLOSU (TEK SATIR = BİR GÜN) ---
    if is_single_device and history_logs:
        st.markdown("### 📋 Günlük Hareket Özeti")
        
        df_raw = pd.DataFrame([{
            "ts": log.timestamp,
            "lat": log.latitude,
            "lon": log.longitude,
            "battery": 0 
        } for log in history_logs])

        if not df_raw.empty:
            df_raw['date'] = df_raw['ts'].dt.date
            daily_stats = []
            cumulative_hours = 0.0 
            
            for day, group in df_raw.groupby('date'):
                group = group.sort_values('ts')
                
                # Mesafe
                day_dist = 0.0
                coords = list(zip(group['lat'], group['lon']))
                if len(coords) > 1:
                    for i in range(len(coords)-1):
                        day_dist += calculate_distance(coords[i][0], coords[i][1], coords[i+1][0], coords[i+1][1])
                
                # Süre
                start_t = group.iloc[0]['ts']
                end_t = group.iloc[-1]['ts']
                duration_hours = (end_t - start_t).total_seconds() / 3600.0
                cumulative_hours += duration_hours
                
                last_rec = group.iloc[-1]
                
                daily_stats.append({
                    "Tarih": day.strftime('%d.%m.%Y'),
                    "Günlük Çalışma": f"{duration_hours:.2f} sa",
                    "Kümülatif Çalışma": f"{cumulative_hours:.2f} sa",
                    "Pil Seviyesi": f"%{last_rec['battery']}",
                    "Mesafe (km)": f"{day_dist:.2f}",
                    "Enlem": f"{last_rec['lat']:.5f}",
                    "Boylam": f"{last_rec['lon']:.5f}"
                })
            
            df_final = pd.DataFrame(daily_stats)
            st.dataframe(df_final, use_container_width=True, hide_index=True)
            
            total_km = sum([float(x['Mesafe (km)']) for x in daily_stats])
            st.success(f"✅ Toplam {total_km:.2f} km yol kat edildi.")
        else:
            st.warning("Veri işlenemedi.")