# frontend/views/dashboard.py (V2 - REAL TIME)
import streamlit as st
import pandas as pd
import sys
import os

# Backend yolunu ekle
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from backend.database import get_user_devices, get_alarms, get_device_telemetry, get_fleet_efficiency_metrics

def load_view(user):
    st.title(f"📊 {user.company_name} - Operasyon Merkezi")
    
    # --- 1. KULLANICIYA ÖZEL CİHAZLARI ÇEK ---
    devices = get_user_devices(user.id)
    
    # İstatistikler
    total_fleet = len(devices)
    active_count = sum(1 for d in devices if d.is_active)
    
    # Alarm Sayısı (Kullanıcıya özel filtreli)
    alarms = get_alarms(active_only=True, user_id=user.id)
    critical_alarms = len([a for a in alarms if a.severity == 'Critical'])
    
    # --- METRİKLER ---
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Toplam Filo", str(total_fleet))
    c2.metric("Sahada Aktif", str(active_count))
    c3.metric("Kritik Alarm", str(critical_alarms), delta="-1" if critical_alarms < 3 else "Yeni", delta_color="inverse")
    # --- GERÇEK VERİMLİLİK HESABI ---
    eff_score, eff_trend = get_fleet_efficiency_metrics(user.id)
    
    c4.metric(
        "Filo Verimliliği", 
        f"%{eff_score}", 
        f"{eff_trend:+.1f}%", # Artı/Eksi işaretini otomatik koyar
        delta_color="normal" # Artış yeşil, azalış kırmızı olur
    )
    
    st.markdown("---")
    
    # --- SON AKTİVİTELER TABLOSU ---
    st.subheader("Son Aktiviteler")
    
    if not devices:
        st.info("Henüz sisteme kayıtlı cihazınız yok.")
    else:
        device_data = []
        for d in devices:
            # --- GERÇEK VERİ ÇEKME BLOĞU ---
            last_logs = get_device_telemetry(d.device_id, limit=1)
            
            if last_logs:
                # Dashboard için sadece saati göstermek daha temiz durur
                # Tarih de istersen: .strftime('%d.%m %H:%M') yapabilirsin
                signal_time = last_logs[0].timestamp.strftime('%H:%M')
            else:
                signal_time = "-"
            # -------------------------------

            device_data.append({
                "Durum": "🟢" if d.is_active else "🔴",
                "Makine": d.unit_name,
                "Model": d.asset_model,
                "Son Sinyal": signal_time # Artık DB'den geliyor
            })
            
        df = pd.DataFrame(device_data)
        
        # Tabloyu daha şık gösterelim
        st.dataframe(
            df, 
            use_container_width=True,
            column_config={
                "Durum": st.column_config.TextColumn("D", width="small", help="Aktiflik Durumu"),
                "Son Sinyal": st.column_config.TextColumn("Saat", width="small")
            },
            hide_index=True
        )