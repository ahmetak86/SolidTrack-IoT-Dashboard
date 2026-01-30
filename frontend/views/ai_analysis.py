# frontend/views/ai_analysis.py (FİNAL DÜZELTİLMİŞ)
import sys
import os

# 1. ÖNCE YOL TANIMI (En tepede olmalı)
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

import streamlit as st
import pandas as pd
import plotly.express as px
from backend.database import get_user_devices, get_device_telemetry
from frontend.utils import convert_to_user_time # Saat çevirici

def load_view(user):
    st.title("🔍 Makine Sağlık Raporu")
    devices = get_user_devices(user.id)
    
    if devices:
        selected_name = st.selectbox("Analiz Edilecek Makine:", [d.unit_name for d in devices])
        # Seçilen cihazı bul
        device = next((d for d in devices if d.unit_name == selected_name), None)
        
        if not device:
            st.error("Cihaz bulunamadı.")
            return

        logs = get_device_telemetry(device.device_id, limit=50)
        
        if logs:
            last = logs[0]
            c1, c2, c3, c4 = st.columns(4)
            
            # None kontrolü yaparak veri gösterimi
            bat_val = int(last.battery_pct) if last.battery_pct is not None else 0
            temp_val = int(last.temp_c) if last.temp_c is not None else 0
            shock_val = last.max_shock_g if last.max_shock_g is not None else 0.0

            c1.metric("Pil Seviyesi", f"%{bat_val}")
            c2.metric("Motor Isısı", f"{temp_val} °C")
            c3.metric("Max Darbe", f"{shock_val} G", delta_color="inverse")
            
            # HIZ VERİSİ NONE KONTROLÜ (Hata veren yer burasıydı)
            current_speed = last.speed_kmh if last.speed_kmh is not None else 0.0
            
            st.write(f"**Kontak Durumu:** {'🟢 ÇALIŞIYOR' if current_speed > 0 else '⭕ KAPALI'}")
            st.progress(bat_val / 100)

            tab_a, tab_b = st.tabs(["📉 Darbe Grafiği", "🔥 Isı Grafiği"])
            
            # Grafik verisi hazırlarken saat dönüşümü
            df_logs = pd.DataFrame([
                {
                    'Zaman': convert_to_user_time(l.timestamp, user.timezone), # Yerel saat
                    'Darbe': l.max_shock_g if l.max_shock_g else 0, 
                    'Isı': l.temp_c if l.temp_c else 0
                 } 
                for l in logs
            ])
            
            with tab_a: st.plotly_chart(px.bar(df_logs, x='Zaman', y='Darbe', title="Darbe Geçmişi", color='Darbe'), use_container_width=True)
            with tab_b: st.plotly_chart(px.area(df_logs, x='Zaman', y='Isı', title="Sıcaklık Trendi"), use_container_width=True)
        else:
            st.warning("Bu cihaz için henüz veri oluşmamış.")
    else:
        st.info("Sisteme kayıtlı cihazınız yok.")