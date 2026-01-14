import streamlit as st
import pandas as pd
import plotly.express as px
from backend.database import get_user_devices, get_device_telemetry, get_all_devices_for_admin

def load_view(user):
    st.title("🔍 Makine Sağlık Raporu")
    devices = get_all_devices_for_admin() if user.role == 'Admin' else get_user_devices(user.id)
    if devices:
        selected_name = st.selectbox("Analiz Edilecek Makine:", [d.unit_name for d in devices])
        device = next(d for d in devices if d.unit_name == selected_name)
        logs = get_device_telemetry(device.device_id, limit=50)
        
        if logs:
            last = logs[0]
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Pil Seviyesi", f"%{int(last.battery_pct)}")
            c2.metric("Motor Isısı", f"{int(last.temp_c)} °C")
            c3.metric("Max Darbe", f"{last.max_shock_g} G", delta_color="inverse")
            c4.metric("Eğim (Tilt)", f"{int(last.tilt_deg)}°")

            st.write(f"**Kontak Durumu:** {'🟢 ÇALIŞIYOR' if last.speed_kmh > 0 else '⭕ KAPALI'}")
            st.progress(int(last.battery_pct) / 100)

            tab_a, tab_b = st.tabs(["📉 Darbe Grafiği", "🔥 Isı Grafiği"])
            df_logs = pd.DataFrame([{'Zaman': l.timestamp, 'Darbe': l.max_shock_g, 'Isı': l.temp_c} for l in logs])
            with tab_a: st.plotly_chart(px.bar(df_logs, x='Zaman', y='Darbe', title="Darbe Geçmişi", color='Darbe'), use_container_width=True)
            with tab_b: st.plotly_chart(px.area(df_logs, x='Zaman', y='Isı', title="Sıcaklık Trendi"), use_container_width=True)
        else:
            st.warning("Veri yok.")