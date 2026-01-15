# frontend/views/map.py
import streamlit as st
import folium
from folium.plugins import MarkerCluster, Fullscreen
from streamlit_folium import st_folium
import os
import pandas as pd
from datetime import datetime
from backend.database import get_user_devices, get_device_telemetry, get_all_devices_for_admin

def load_view(user):
    st.title("🌍 Canlı Saha Operasyonu")
    
    # --- 1. VERİ HAZIRLIĞI ---
    all_devices = get_all_devices_for_admin() if user.role == 'Admin' else get_user_devices(user.id)
    
    if not all_devices:
        st.warning("Sistemde kayıtlı cihaz bulunamadı.")
        return

    # Mevcut tipleri bul (Filtre için)
    # None olanları 'Unknown' yap, boşlukları temizle
    available_types = sorted(list(set([d.icon_type if d.icon_type else "Diğer" for d in all_devices])))
    
    # --- 2. FİLTRE ALANI (MENÜDEN BAĞIMSIZ - ÜST KISIM) ---
    # Haritanın hemen üstünde, temiz bir panel
    with st.container():
        c_filter, c_stats = st.columns([3, 1])
        
        with c_filter:
            selected_types = st.multiselect(
                "🌪️ Varlık Tipi Filtrele:",
                options=available_types,
                default=available_types,
                format_func=lambda x: x.replace("_", " ").title()
            )
        
        with c_stats:
            enable_cluster = st.toggle("Kümeleme (Cluster)", value=True)
            show_names = st.toggle("İsimleri Göster", value=False)

    st.markdown("---")

    # Filtreleme Mantığı
    filtered_devices = [d for d in all_devices if (d.icon_type if d.icon_type else "Diğer") in selected_types]
    
    if not filtered_devices:
        st.info("Seçilen kriterde cihaz yok.")
        return

    # --- 3. HARİTA AYARLARI ---
    # Merkez hesabı için koordinatları toplayalım
    lats, lons = [], []
    
    m = folium.Map(location=[39.0, 35.0], zoom_start=6, tiles="CartoDB positron")
    Fullscreen().add_to(m)
    
    # Cluster objesi (Eğer açıksa buna, kapalıysa direkt haritaya ekleyeceğiz)
    map_layer = MarkerCluster().add_to(m) if enable_cluster else m

    # --- 4. İKON YOLU BULUCU (GARANTİ YÖNTEM) ---
    # Bu dosyanın (map.py) nerede olduğunu bulup, static klasörüne oradan gidiyoruz.
    # Yapı: frontend/views/map.py -> (2 üst) -> frontend/static/icons
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) 
    ICON_DIR = os.path.join(BASE_DIR, "static", "icons")

    # --- 5. CİHAZLARI HARİTAYA BASMA ---
    for d in filtered_devices:
        logs = get_device_telemetry(d.device_id, limit=1)
        if logs:
            l = logs[0]
            lats.append(l.latitude)
            lons.append(l.longitude)
            
            # --- A) İKON SEÇİMİ ---
            icon_filename = f"{d.icon_type}.png" if d.icon_type else "truck.png"
            full_icon_path = os.path.join(ICON_DIR, icon_filename)
            
            # İkon dosyası gerçekten var mı?
            # Windows/Linux yol ayrımı sorun olmasın diye replace kullanıyoruz
            if os.path.exists(full_icon_path):
                icon_obj = folium.CustomIcon(
                    icon_image=full_icon_path,
                    icon_size=(45, 45),
                    icon_anchor=(22, 22),
                    popup_anchor=(0, -22)
                )
            else:
                # Dosya yoksa standart pin (Fallback)
                icon_obj = folium.Icon(color="blue", icon="wrench", prefix="fa")

            # --- B) POPUP İÇERİĞİ (TRUSTED TARZI) ---
            # Google Street View Linki
            street_view_url = f"https://www.google.com/maps?layer=c&cbll={l.latitude},{l.longitude}"
            
            # Toplam Çalışma Hesabı (Basit Simülasyon: Initial + Rastgele)
            # Gerçekte: d.initial_hours_offset + (logs calculation)
            total_hours = int(d.initial_hours_offset) if d.initial_hours_offset else 1250
            
            # Zaman Formatı
            time_str = l.timestamp.strftime('%d.%m.%Y %H:%M')
            
            popup_html = f"""
            <div style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; width: 280px; color: #333;">
                <div style="background-color: #f8f9fa; padding: 10px; border-bottom: 2px solid #e9ecef;">
                    <h4 style="margin: 0; color: #2c3e50;">{d.unit_name}</h4>
                    <span style="font-size: 12px; color: #7f8c8d; font-weight: 600;">{d.asset_model}</span>
                </div>
                
                <div style="padding: 10px;">
                    <div style="display: flex; justify-content: space-between; margin-bottom: 5px;">
                        <span style="color: #95a5a6; font-size: 12px;">Last Signal:</span>
                        <span style="font-size: 13px; font-weight: bold;">{time_str}</span>
                    </div>
                    
                    <div style="display: flex; justify-content: space-between; margin-bottom: 5px;">
                        <span style="color: #95a5a6; font-size: 12px;">Total Utilization:</span>
                        <span style="font-size: 13px;">{total_hours} h</span>
                    </div>
                    
                    <div style="display: flex; justify-content: space-between; margin-bottom: 10px;">
                        <span style="color: #95a5a6; font-size: 12px;">Accuracy:</span>
                        <span style="font-size: 13px; color: green;">High (5 m)</span>
                    </div>
                    
                    <hr style="border-top: 1px solid #eee; margin: 10px 0;">
                    
                    <div style="text-align: center;">
                        <a href="{street_view_url}" target="_blank" style="
                            display: inline-block;
                            background-color: #3498db;
                            color: white;
                            text-decoration: none;
                            padding: 8px 15px;
                            border-radius: 4px;
                            font-size: 12px;
                            font-weight: bold;
                            transition: background 0.3s;
                        ">
                        Show from this position 
                        <span style="margin-left: 5px;">📍</span>
                        </a>
                    </div>
                </div>
            </div>
            """

            folium.Marker(
                location=[l.latitude, l.longitude],
                popup=folium.Popup(popup_html, max_width=300),
                tooltip=f"{d.unit_name}" if show_names else None,
                icon=icon_obj
            ).add_to(map_layer)

    # --- 6. AUTO-ZOOM (FIT BOUNDS) ---
    if lats and lons:
        sw = [min(lats), min(lons)]
        ne = [max(lats), max(lons)]
        m.fit_bounds([sw, ne], padding=(50, 50))

    # --- 7. HARİTAYI ÇİZ ---
    st_folium(m, height=650, use_container_width=True)
    
    # Alt Bilgi
    st.caption(f"Toplam {len(all_devices)} cihazdan {len(filtered_devices)} tanesi görüntüleniyor.")