import streamlit as st
import folium
from folium.plugins import MarkerCluster, Fullscreen, AntPath
from streamlit_folium import st_folium
import os
from datetime import datetime, timedelta, date
import pandas as pd
import math
from backend.database import get_user_devices, get_device_telemetry, get_all_devices_for_admin

# --- YARDIMCI FONKSİYONLAR (AYNEN KORUNDU) ---

def calculate_distance_km(lat1, lon1, lat2, lon2):
    """İki koordinat arası mesafeyi KM olarak döner (Haversine)"""
    try:
        R = 6371  # Dünya yarıçapı (km)
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        a = math.sin(dlat / 2) * math.sin(dlat / 2) + \
            math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * \
            math.sin(dlon / 2) * math.sin(dlon / 2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return R * c
    except:
        return 0.0

def format_duration(hours_float):
    """Saati (2.5) -> (02 sa 30 dk) formatına çevirir"""
    if hours_float is None or hours_float == 0: return "00 sa 00 dk"
    
    total_minutes = int(hours_float * 60)
    h = total_minutes // 60
    m = total_minutes % 60
    return f"{h:02d} sa {m:02d} dk"

def get_icon_path(type_code):
    if not type_code: return None
    current_dir = os.path.dirname(os.path.abspath(__file__)) 
    root_dir = os.path.dirname(os.path.dirname(current_dir))
    ICON_DIR = os.path.join(root_dir, "static", "icons")
    full_path = os.path.join(ICON_DIR, f"{type_code}.png")
    return full_path if os.path.exists(full_path) else None

def get_display_name(type_code):
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
    if not type_code: return "Diğer"
    code = str(type_code).lower().strip()
    return TYPE_DISPLAY_MAP.get(code, code.replace("_", " ").title())

def load_view(user):
    # --- 1. CSS İLE LEAFLET YAZISINI GİZLE ---
    st.markdown("""
        <style>
            .leaflet-control-attribution { display: none !important; }
        </style>
    """, unsafe_allow_html=True)

    st.markdown("### 🌍 Canlı Saha Operasyonu")
    
    # --- SESSION STATE YÖNETİMİ ---
    if "map_selected_device_id" not in st.session_state:
        st.session_state.map_selected_device_id = None
    if "map_route_data" not in st.session_state:
        st.session_state.map_route_data = None
    if "map_prev_period" not in st.session_state:
        st.session_state.map_prev_period = None

    # URL Parametre Kontrolü
    query_params = st.query_params
    target_device_serial = query_params.get("target_device", None)

    if target_device_serial and target_device_serial != st.session_state.map_selected_device_id:
        st.session_state.map_selected_device_id = target_device_serial
        st.session_state.map_route_data = None 

    all_devices = get_all_devices_for_admin() if user.role == 'Admin' else get_user_devices(user.id)
    if not all_devices:
        st.warning("Kayıtlı cihaz yok.")
        return

    # --- FİLTRELER ---
    c_filter1, c_filter2, c_settings = st.columns([1.5, 2, 1.5])
    
    raw_types = sorted(list(set([d.icon_type if d.icon_type else "other" for d in all_devices])))
    with c_filter1:
        selected_types = st.multiselect("1. Makine Tipi:", ["Hepsi"] + raw_types, default=["Hepsi"], 
                                        format_func=lambda x: "TÜM TİPLER" if x == "Hepsi" else get_display_name(x))
    
    final_types = raw_types if "Hepsi" in selected_types else selected_types
    devices_by_type = [d for d in all_devices if (d.icon_type if d.icon_type else "other") in final_types]
    
    device_names = [d.unit_name for d in devices_by_type]
    
    default_selection = []
    if st.session_state.map_selected_device_id:
        found = next((d for d in all_devices if str(d.device_id) == str(st.session_state.map_selected_device_id)), None)
        if found and found.unit_name in device_names:
            default_selection = [found.unit_name]

    with c_filter2:
        selected_units = st.multiselect("2. Makine Modeli:", ["Hepsi"] + device_names, default=default_selection, placeholder="Tüm cihazlar...")
    
    if "Hepsi" in selected_units: final_devices = devices_by_type
    elif selected_units: final_devices = [d for d in devices_by_type if d.unit_name in selected_units]
    else: final_devices = devices_by_type

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
        
        if str(target_device.device_id) != str(st.session_state.map_selected_device_id):
            st.session_state.map_selected_device_id = str(target_device.device_id)
            st.session_state.map_route_data = None 

        st.info(f"📍 **{target_device.unit_name}** analiz ediliyor.")
        
        col_p, col_d1, col_d2, col_b = st.columns([1.5, 1.5, 1.5, 1])
        
        with col_p:
            period = st.selectbox("Periyot:", ["Tarih Seç", "Bugün", "Son 1 Hafta", "Son 1 Ay", "Tüm Zamanlar"], index=0)
        
        is_manual_mode = (period == "Tarih Seç")
        
        today = datetime.now().date()
        start_def = today - timedelta(days=7)
        
        with col_d1: 
            d_start = st.date_input("Başlangıç:", value=start_def, max_value=today, disabled=not is_manual_mode)
        with col_d2: 
            d_end = st.date_input("Bitiş:", value=today, min_value=d_start, max_value=today, disabled=not is_manual_mode)
        with col_b:
            st.write("") 
            st.write("") 
            manual_btn = st.button("Operasyonu Gör", type="primary", disabled=not is_manual_mode)

        should_fetch = False
        s, e = today, today

        if is_manual_mode:
            if manual_btn:
                s, e = d_start, d_end
                should_fetch = True
        else:
            if period != st.session_state.map_prev_period or st.session_state.map_route_data is None:
                should_fetch = True
            
            if period == "Bugün": s, e = today, today
            elif period == "Son 1 Hafta": s, e = today - timedelta(days=7), today
            elif period == "Son 1 Ay": s, e = today - timedelta(days=30), today
            elif period == "Tüm Zamanlar": s, e = date(2020, 1, 1), today

        if should_fetch:
            st.session_state.map_prev_period = period 
            raw = get_device_telemetry(target_device.device_id, limit=10000)
            filtered = [l for l in raw if s <= l.timestamp.date() <= e]
            filtered.sort(key=lambda x: x.timestamp)
            st.session_state.map_route_data = filtered
            
            if not filtered:
                st.warning("⚠️ Bu aralıkta veri yok.")

    else:
        st.session_state.map_route_data = None 
        st.session_state.map_prev_period = None

    # --- HARİTA AYARLARI ---
    default_loc = [39.0, 35.0]
    default_zoom = 6
    start_coords = default_loc
    
    history_logs = st.session_state.map_route_data

    # Zoom Önceliği
    if is_single_device and history_logs:
         start_coords = [history_logs[0].latitude, history_logs[0].longitude]
         default_zoom = 12
    elif is_single_device and final_devices:
         l = get_device_telemetry(final_devices[0].device_id, limit=1)
         if l:
             start_coords = [l[0].latitude, l[0].longitude]
             default_zoom = 12

    # --- GOOGLE MAPS ENTEGRASYONU BURADA BAŞLIYOR ---
    # tiles=None ile boş başlatıyoruz
    m = folium.Map(location=start_coords, zoom_start=default_zoom, tiles=None)

    # hl=en yaparak Kiril alfabesinden kurtuluyoruz. 
    # Türkiye'deki isimler Latin alfabesi olduğu için doğal görünecektir.
    folium.TileLayer(
        tiles='https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}&hl=en',
        attr='Google Maps',
        name='Google Uydu (Hibrit)',
        overlay=False,
        control=True
    ).add_to(m)

    folium.TileLayer(
        tiles='https://mt1.google.com/vt/lyrs=m&x={x}&y={y}&z={z}&hl=en',
        attr='Google Maps',
        name='Google Sokak',
        overlay=False,
        control=True
    ).add_to(m)

    Fullscreen().add_to(m)

    # --- ROTA ÇİZİMİ (ANTPATH - AYNEN KORUNDU) ---
    if is_single_device and history_logs:
        pts = [[l.latitude, l.longitude] for l in history_logs]
        if len(pts) > 1:
            AntPath(
                locations=pts, 
                color="#225d97",       # Solidus Mavisi
                weight=5, 
                opacity=0.8, 
                dash_array=[15, 30], 
                delay=1000, 
                pulse_color="#f1c232"  # Solidus Sarısı
            ).add_to(m)
            
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
    for d in final_devices:
        logs = get_device_telemetry(d.device_id, limit=1)
        if logs:
            l = logs[0]
            c_icon = get_icon_path(d.icon_type)
            icon_obj = folium.CustomIcon(icon_image=c_icon, icon_size=(64, 86), icon_anchor=(32, 86), popup_anchor=(0, -80)) if c_icon else folium.Icon(color="blue", icon="wrench", prefix="fa")
            
            safe_speed = int(l.speed_kmh or 0)
            safe_bat = int(l.battery_pct) if l.battery_pct is not None else '--'

            # Popup HTML
            popup_html = f"""
            <div style="font-family: sans-serif; width: 240px; color:#333;">
                <b style="font-size:14px">{d.unit_name}</b><br>
                <span style="color:gray; font-size:11px">{d.asset_model} ({get_display_name(d.icon_type)})</span>
                <hr style="margin:5px 0; border-top: 1px solid #ddd;">
                <div style="font-size:12px; line-height:1.6;">
                    📡 <b>Son Sinyal:</b> {l.timestamp.strftime('%d.%m.%Y %H:%M')}<br>
                    ⏱️ <b>Son Çalışma:</b> -- dk<br>
                    ∑ <b>Top. Çalışma:</b> -- Saat<br>
                    📍 <b>Konum:</b> {l.latitude:.5f}, {l.longitude:.5f}<br>
                    🔋 <b>Pil:</b> %{safe_bat}
                </div>
                <div style="text-align: center; margin-top: 10px;">
                    <a href="/?target_device={d.device_id}" target="_self" 
                       style="background-color: #225d97; color: white; text-decoration: none; padding: 8px 15px; border-radius: 4px; font-size: 13px; font-weight: bold; display: inline-block;">
                        🔍 Detay Görmek için Tıklayın
                    </a>
                </div>
            </div>
            """
            folium.Marker([l.latitude, l.longitude], popup=folium.Popup(popup_html, max_width=260), tooltip=d.unit_name, icon=icon_obj).add_to(map_layer)

    # Otomatik Bounds
    if is_single_device and history_logs:
         lats_h = [l.latitude for l in history_logs]
         lons_h = [l.longitude for l in history_logs]
         m.fit_bounds([[min(lats_h), min(lons_h)], [max(lats_h), max(lons_h)]], padding=(50, 50))
    elif is_single_device and final_devices:
         l = get_device_telemetry(final_devices[0].device_id, limit=1)
         if l: m.fit_bounds([[l[0].latitude, l[0].longitude], [l[0].latitude, l[0].longitude]], max_zoom=15)
    elif not is_single_device and final_devices:
         all_lats = []
         all_lons = []
         for dev in final_devices:
             last_log = get_device_telemetry(dev.device_id, limit=1)
             if last_log:
                 all_lats.append(last_log[0].latitude)
                 all_lons.append(last_log[0].longitude)
         if all_lats:
             m.fit_bounds([[min(all_lats), min(all_lons)], [max(all_lats), max(all_lons)]], padding=(50, 50))

    # --- KATMAN KONTROLÜ (Sağ üstteki buton) ---
    folium.LayerControl().add_to(m)

    # --- HARİTA ÇIKTISI ---
    st_folium(m, height=550, use_container_width=True)

    # --- ÖZET VE TABLO (AYNEN KORUNDU) ---
    if is_single_device and history_logs:
        df_raw = pd.DataFrame([
            {
                'ts': l.timestamp, 
                'lat': l.latitude, 
                'lon': l.longitude, 
                'bat': l.battery_pct
            } 
            for l in history_logs if l.latitude is not None
        ])
        
        if not df_raw.empty:
            df_raw['date'] = df_raw['ts'].dt.date
            daily_stats = []
            cumulative_hours = 0.0 
            
            for day, group in df_raw.groupby('date'):
                group = group.sort_values('ts')
                signal_count = len(group)
                day_dist_km = 0.0
                coords = list(zip(group['lat'], group['lon']))
                if len(coords) > 1:
                    for i in range(len(coords)-1):
                        day_dist_km += calculate_distance_km(coords[i][0], coords[i][1], coords[i+1][0], coords[i+1][1])
                
                start_t = group.iloc[0]['ts']
                end_t = group.iloc[-1]['ts']
                duration_hours = (end_t - start_t).total_seconds() / 3600.0
                cumulative_hours += duration_hours
                
                last_rec = group.iloc[-1]
                safe_bat_val = int(last_rec['bat'] or 0)

                daily_stats.append({
                    "Tarih": day.strftime('%d.%m.%Y'),
                    "Veri Adedi": signal_count,
                    "Günlük Çalışma": format_duration(duration_hours),
                    "Toplam Çalışma": format_duration(cumulative_hours),
                    "Pil Seviyesi": f"%{safe_bat_val}",
                    "Değiştirilen Yer (m)": f"{int(day_dist_km * 1000)}", 
                    "Konum (Enlem)": f"{last_rec['lat']:.5f}",
                    "Konum (Boylam)": f"{last_rec['lon']:.5f}",
                    "_sort_date": day 
                })
            
            st.success(f"✅ **{target_device.unit_name}** analiz edildi.")

            df_final = pd.DataFrame(daily_stats)
            if not df_final.empty:
                df_final = df_final.sort_values(by="_sort_date", ascending=False).drop(columns=["_sort_date"])
            
            st.markdown("### 📋 Günlük Özet")
            st.dataframe(df_final, use_container_width=True, hide_index=True)
            
        else:
            st.warning("Veri işlenemedi.")