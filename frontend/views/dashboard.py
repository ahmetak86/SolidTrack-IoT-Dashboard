import streamlit as st
import pandas as pd
from backend.database import get_user_devices, get_device_telemetry, get_all_devices_for_admin

def load_view(user):
    devices = get_all_devices_for_admin() if user.role == 'Admin' else get_user_devices(user.id)
    st.title(f"📊 {user.company_name} - Operasyon Merkezi")
    
    active_count = len([d for d in devices if d.is_active])
    service_alert = len([d for d in devices if (d.next_service_hours or 0) < 50])
    
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Toplam Filo", len(devices))
    k2.metric("Sahada Aktif", active_count)
    k3.metric("Kritik Alarm", "2", delta="Yeni")
    k4.metric("Filo Verimliliği", "%85", delta="Artışta")

    st.subheader("Son Aktiviteler")
    data = []
    for d in devices:
        logs = get_device_telemetry(d.device_id, limit=1)
        last = logs[0] if logs else None
        status = "🟢" if d.is_active else "🔴"
        data.append({
            "Durum": status, "Makine": d.unit_name, "Model": d.asset_model, 
            "Son Sinyal": last.timestamp.strftime("%H:%M") if last else "-"
        })
    st.dataframe(pd.DataFrame(data).head(5), use_container_width=True)