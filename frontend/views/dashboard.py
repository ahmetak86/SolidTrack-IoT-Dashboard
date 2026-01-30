# frontend/views/dashboard.py (V5 - TEMP ADDED)
import streamlit as st
import pandas as pd
import sys
import os

# Backend ve Frontend yollarını tanıt
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from backend.database import get_user_devices, get_alarms, get_device_telemetry, get_fleet_efficiency_metrics
from frontend.utils import format_date_for_ui

def load_view(user):
    st.title(f"📊 {user.company_name} - Operasyon Merkezi")
    
    # --- 1. KULLANICIYA ÖZEL CİHAZLARI ÇEK ---
    devices = get_user_devices(user.id)
    devices = [d for d in devices if not d.is_virtual]
    
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
    
    # Gerçek Verimlilik Hesabı
    eff_score, eff_trend = get_fleet_efficiency_metrics(user.id)
    
    c4.metric(
        "Filo Verimliliği", 
        f"%{eff_score}", 
        f"{eff_trend:+.1f}%", 
        delta_color="normal"
    )
    
    st.markdown("---")
    
    # --- SON AKTİVİTELER TABLOSU ---
    st.subheader("Son Aktiviteler")
    
    if not devices:
        st.info("Henüz sisteme kayıtlı cihazınız yok.")
    else:
        device_data = []
        for d in devices:
            try:
                # --- GERÇEK VERİ ÇEKME BLOĞU ---
                last_logs = get_device_telemetry(d.device_id, limit=1)
                
                if last_logs:
                    # 1. Saat Formatı (UTC Ayarlı)
                    signal_time = format_date_for_ui(last_logs[0].timestamp, user.timezone, include_offset=True)
                    
                    # 2. Sıcaklık Verisi (YENİ EKLENDİ)
                    raw_temp = last_logs[0].temp_c
                    if raw_temp is not None:
                        temp_str = f"{int(raw_temp)} °C"
                    else:
                        temp_str = "-"
                else:
                    signal_time = "-"
                    temp_str = "-"
                # -------------------------------

                device_data.append({
                    "Durum": "🟢" if d.is_active else "🔴",
                    "Makine": d.unit_name,
                    "Model": d.asset_model,
                    "Sıcaklık": temp_str,  # <-- Tabloya Eklendi
                    "Son Sinyal": signal_time 
                })
            except Exception as e:
                print(f"Dashboard Row Error ({d.unit_name}): {e}")
                device_data.append({
                    "Durum": "⚠️",
                    "Makine": d.unit_name,
                    "Model": "Veri Hatası",
                    "Sıcaklık": "-",
                    "Son Sinyal": "-"
                })
            
        df = pd.DataFrame(device_data)
        
        # Tabloyu göster (Sütun yapılandırması güncellendi)
        st.dataframe(
            df, 
            use_container_width=True,
            column_config={
                "Durum": st.column_config.TextColumn("Durum", width="small", help="Aktiflik Durumu"),
                "Sıcaklık": st.column_config.TextColumn("Sıcaklık", width="small"), # <-- Başlık ayarlandı
                "Son Sinyal": st.column_config.TextColumn("Son Sinyal Zamanı", width="medium")
            },
            hide_index=True
        )