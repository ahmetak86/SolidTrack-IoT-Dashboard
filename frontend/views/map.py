import streamlit as st
import folium
from folium.plugins import MarkerCluster, Fullscreen, AntPath
from streamlit_folium import st_folium
import os
import pandas as pd
from datetime import datetime, timedelta
from backend.database import get_user_devices, get_device_telemetry, get_all_devices_for_admin

# --- GÜNCEL İKON EŞLEŞTİRME SÖZLÜĞÜ (MAPPING) ---
# DB Kodu -> Türkçe Ekranda Yazacak İsim
TYPE_DISPLAY_MAP = {
    "hydraulic_breaker": "Hidrolik Kırıcı",
    "hydraulic_auger": "Hidrolik Burgu",
    "hydraulic_shear": "Hidrolik Makas",
    "concrete_cutter": "Beton Kesici",
    "drum_cutter": "Tambur Kesici",
    "pulverizer": "Pulverizatör",
    "log_grapple": "Kütük Kıskacı",
    "excavator_grapple": "Ekskavatör Kıskacı",
    "hydraulic_drifter": "Hidrolik Delici",
    "crusher_bucket": "Kırıcı Kova",
    "ripper": "Riper",
    "excavator": "Ekskavatör",
    "truck": "Kamyon",
    "concrete_mixer": "Beton Mikseri", "mixer": "Beton Mikseri",
    "forklift": "Forklift",
    "generator": "Jeneratör",
    "bulldozer": "Buldozer", "dozer": "Buldozer",
    "dump_truck": "Damperli Kamyon",
    "tractor": "Traktör",
    "mobile_crane": "Mobil Vinç",
    "tower_crane": "Kule Vinç",
    "roller": "Kompaktör/Silindir",
    "backhoe": "Kazıcı Yükleyici (JCB)",
    "scissor_lift": "Makaslı Platform",
    "pickup": "Pickup",
    "light_tower": "Işık Kulesi"
}

def get_display_name(type_code):
    if not type_code: return "Diğer"
    code = str(type_code).lower().strip()
    return TYPE_DISPLAY_MAP.get(code, code.replace("_", " ").title())

def get_icon_path(type_code):
    """
    Dosya yolunu bulur. 
    frontend/views/map.py -> (1 üst) frontend -> (2 üst) ROOT -> static/icons
    """
    if not type_code: return None
    
    # map.py dosyasının olduğu yer
    current_dir = os.path.dirname(os.path.abspath(__file__)) 
    
    # 2 basamak yukarı çıkıp ROOT dizini buluyoruz
    # 1. os.path.dirname(current_dir) -> frontend klasörü
    # 2. os.path.dirname(...) -> PROJE ANA KLASÖRÜ (ROOT)
    root_dir = os.path.dirname(os.path.dirname(current_dir))
    
    # Hedef yol: root/static/icons
    ICON_DIR = os.path.join(root_dir, "static", "icons")
    
    filename = f"{type_code}.png"
    full_path = os.path.join(ICON_DIR, filename)
    
    # Kontrol edelim (Debug için print açılabilir)
    # print(f"Aranan İkon Yolu: {full_path}") 
    
    if os.path.exists(full_path):
        return full_path
    else:
        return None

def load_view(user):
    st.title("🌍 Canlı Saha Operasyonu")
    
    query_params = st.query_params
    history_device_id = query_params.get("history_device", None)

    # Verileri Çek
    all_devices = get_all_devices_for_admin() if user.role == 'Admin' else get_user_devices(user.id)
    if not all_devices:
        st.warning("Kayıtlı cihaz yok.")
        return

    # --- FİLTRE ALANI ---
    with st.container():
        c_filter1, c_filter2, c_date = st.columns([1.5, 2, 2])
        
        # 1. MAKİNE TİPİ FİLTRESİ (TÜRKÇE İSİMLERLE)
        raw_types = sorted(list(set([d.icon_type if d.icon_type else "other" for d in all_devices])))
        
        with c_filter1:
            selected_types_raw = st.multiselect(
                "1. Makine Tipi:",
                options=raw_types,
                default=raw_types,
                format_func=get_display_name 
            )
        
        # Seçime göre filtrele
        devices_by_type = [d for d in all_devices if (d.icon_type if d.icon_type else "other") in selected_types_raw]
        device_names = [d.unit_name for d in devices_by_type]
        
        # History modu kontrolü
        default_dev_list = []
        if history_device_id:
            target = next((d for d in all_devices if d.device_id == history_device_id), None)
            if target and target.unit_name in device_names:
                default_dev_list = [target.unit_name]

        # 2. CİHAZ SEÇİMİ
        with c_filter2:
            selected_unit_names = st.multiselect(
                "2. Cihaz Seçimi (Detay):",
                options=device_names,
                default=default_dev_list,
                placeholder="Tüm cihazlar..."
            )
        
        if selected_unit_names:
            final_devices = [d for d in devices_by_type if d.unit_name in selected_unit_names]
        else:
            final_devices = devices_by_type

        # 3. TARİH FİLTRESİ
        is_single_device = len(final_devices) == 1
        date_range = None
        with c_date:
            if is_single_device:
                st.caption("📅 Seyahat Geçmişi")
                today = datetime.now()
                last_month = today - timedelta(days=30)
                date_range = st.date_input("Tarih Aralığı", value=(last_month, today), max_value=today, format="DD.MM.YYYY")
            else:
                st.caption("📅 Tarih filtresi için tek cihaz seçiniz.")

    st.markdown("---")

    # --- HARİTA ---
    c_check1, c_check2 = st.columns(2)
    with c_check1:
        enable_cluster = st.checkbox("Kümelemeyi (Cluster) Aç", value=True)
    with c_check2:
        show_names_permanent = st.checkbox("İsimleri Göster", value=False)

    m = folium.Map(location=[39.0, 35.0], zoom_start=6, tiles="CartoDB positron")
    Fullscreen().add_to(m)
    map_layer = MarkerCluster().add_to(m) if enable_cluster else m

    lats, lons = [], []

    for d in final_devices:
        logs = get_device_telemetry(d.device_id, limit=1)
        if logs:
            l = logs[0]
            lats.append(l.latitude)
            lons.append(l.longitude)
            
            # İKON YOLUNU AL (Düzeltilmiş Fonksiyon)
            custom_icon_path = get_icon_path(d.icon_type)
            
            if custom_icon_path:
                # Özel İkon Bulundu
                icon_obj = folium.CustomIcon(
                    icon_image=custom_icon_path, 
                    icon_size=(40, 40), 
                    icon_anchor=(20, 20), 
                    popup_anchor=(0, -20)
                )
            else:
                # İkon Bulunamadı -> Varsayılan Mavi Pin
                icon_obj = folium.Icon(color="blue", icon="wrench", prefix="fa")

            # Popup ve Diğer Bilgiler
            history_url = f"/?history_device={d.device_id}"
            start_hours = int(d.initial_hours_offset or 0)
            total_hours = start_hours + int(len(get_device_telemetry(d.device_id, limit=1000)) * 0.25)
            last_signal_time = l.timestamp.strftime('%d.%m.%Y %H:%M')
            type_tr = get_display_name(d.icon_type)

            popup_html = f"""
            <div style="font-family: sans-serif; width: 260px; color: #333;">
                <div style="background-color: #f8f9fa; padding: 10px; border-bottom: 1px solid #ddd;">
                    <strong style="font-size: 14px;">{d.unit_name}</strong><br>
                    <span style="font-size: 11px; color: #666;">{d.asset_model} ({type_tr})</span>
                </div>
                <div style="padding: 10px; font-size: 12px;">
                    <div style="display:flex; justify-content:space-between; margin-bottom:4px;">
                        <span style="color:#666;">Son Sinyal:</span><strong>{last_signal_time}</strong>
                    </div>
                    <div style="display:flex; justify-content:space-between; margin-bottom:4px;">
                        <span style="color:#666;">Toplam Kullanım:</span><strong>{total_hours} Saat</strong>
                    </div>
                    <div style="display:flex; justify-content:space-between;">
                        <span style="color:#666;">Doğruluk:</span><strong style="color:green;">Yüksek (3m)</strong>
                    </div>
                </div>
                <div style="text-align: center; margin-top: 5px;">
                    <a href="{history_url}" target="_self" style="background-color: #0d6efd; color: white; text-decoration: none; padding: 6px 12px; border-radius: 4px; font-size: 11px; font-weight: bold;">📍 Makine Yer Değiştirmeleri</a>
                </div>
            </div>
            """

            folium.Marker(
                location=[l.latitude, l.longitude],
                popup=folium.Popup(popup_html, max_width=300),
                tooltip=folium.Tooltip(d.unit_name, permanent=show_names_permanent),
                icon=icon_obj
            ).add_to(map_layer)
            
            # Rota Çizimi
            if is_single_device and date_range and len(date_range) == 2:
                s_date, e_date = date_range
                all_logs = get_device_telemetry(d.device_id, limit=500)
                pts = [[log.latitude, log.longitude] for log in all_logs if s_date <= log.timestamp.date() <= e_date]
                if pts:
                    AntPath(locations=pts, color="blue", weight=4, opacity=0.7, delay=1000).add_to(m)
                    folium.Marker(pts[-1], popup="Başlangıç", icon=folium.Icon(color="green", icon="play", prefix="fa")).add_to(m)

    if lats:
        m.fit_bounds([[min(lats), min(lons)], [max(lats), max(lons)]], padding=(50, 50))
    
    st_folium(m, height=650, use_container_width=True)

    if history_device_id:
        if st.button("🔙 Tüm Filoya Geri Dön"):
            st.query_params.clear()
            st.rerun()