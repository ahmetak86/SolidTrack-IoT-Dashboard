import streamlit as st
import pandas as pd
from datetime import datetime
from backend.database import get_user_devices, get_device_telemetry, get_all_devices_for_admin

def calculate_time_diff(last_time):
    if not last_time: return "-"
    diff = datetime.utcnow() - last_time
    minutes = int(diff.total_seconds() / 60)
    if minutes < 60: return f"{minutes} dk önce"
    hours = int(minutes / 60)
    if hours < 24: return f"{hours} sa önce"
    return f"{int(hours/24)} gün önce"

def load_view(user):
    st.title("🚜 Makine Parkı ve Envanter")
    devices = get_all_devices_for_admin() if user.role == 'Admin' else get_user_devices(user.id)
    inventory_data = []
    for d in devices:
        logs = get_device_telemetry(d.device_id, limit=1)
        last = logs[0] if logs else None
        speed = last.speed_kmh if last else 0
        inventory_data.append({
            "Makine Adı": d.unit_name, "Marka / Model": d.asset_model, "Seri No": d.device_id,
            "Son Sinyal": calculate_time_diff(last.timestamp) if last else "-",
            "Kontak": "🟢 AÇIK" if speed > 0 else "⭕ KAPALI",
            "Adres": "Ostim OSB, Ankara", "Durum": "Aktif" if d.is_active else "Pasif"
        })
    st.dataframe(pd.DataFrame(inventory_data), use_container_width=True)