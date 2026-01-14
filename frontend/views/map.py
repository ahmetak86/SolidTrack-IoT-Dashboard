import streamlit as st
import pandas as pd
from backend.database import get_user_devices, get_device_telemetry, get_all_devices_for_admin

def load_view(user):
    st.title("🌍 Canlı Filo Takibi")
    devices = get_all_devices_for_admin() if user.role == 'Admin' else get_user_devices(user.id)
    map_data = []
    for d in devices:
        logs = get_device_telemetry(d.device_id, limit=1)
        if logs:
            l = logs[0]
            status = "Çalışıyor" if l.speed_kmh > 0 else "Park"
            map_data.append({
                "lat": l.latitude, "lon": l.longitude,
                "name": f"{d.unit_name} ({status})", "hız": f"{l.speed_kmh} km/s"
            })
    if map_data:
        st.map(pd.DataFrame(map_data))
    else:
        st.info("Cihazlardan konum verisi bekleniyor.")