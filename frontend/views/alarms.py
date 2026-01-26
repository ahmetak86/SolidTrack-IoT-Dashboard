# frontend/views/alarms.py (FİNAL VERSİYON)
import streamlit as st
import pandas as pd
from backend.database import get_alarms, acknowledge_alarm

def load_view(user):
    st.title("🔔 Alarm Yönetim Merkezi")
    
    # Verileri Çek
    active_alarms = get_alarms(active_only=True)
    history_alarms = get_alarms(active_only=False) # Hepsi
    
    # KPI Kartları (Üst Özet)
    c1, c2, c3 = st.columns(3)
    critical_count = len([a for a in active_alarms if a.severity == 'Critical'])
    warning_count = len([a for a in active_alarms if a.severity == 'Warning'])
    
    c1.metric("🔴 Kritik (Acil)", critical_count)
    c2.metric("🟠 Uyarı (Warning)", warning_count)
    c3.metric("🟢 Toplam Kayıt", len(history_alarms))
    
    st.markdown("---")
    
    # SEKME YAPISI
    tab1, tab2 = st.tabs(["🔥 Aktif Alarmlar (Action)", "📜 Alarm Geçmişi & Rapor"])
    
    # --- TAB 1: AKTİF ALARMLAR ---
    with tab1:
        if not active_alarms:
            st.success("🎉 Süper! Şu an müdahale bekleyen aktif bir alarm yok.")
        else:
            for alarm in active_alarms:
                # Renk Kodlaması
                color = "red" if alarm.severity == 'Critical' else "orange"
                icon = "💥" if alarm.alarm_type == 'Shock' else "🔋" if 'Battery' in alarm.alarm_type else "🚧"
                
                with st.expander(f":{color}[{icon} **{alarm.alarm_type}**] - {alarm.device.unit_name} ({alarm.timestamp.strftime('%H:%M')})", expanded=True):
                    c_a, c_b, c_c = st.columns([2, 1, 1])
                    
                    with c_a:
                        st.write(f"**Açıklama:** {alarm.description}")
                        st.write(f"**Değer:** {alarm.value}")
                        st.caption(f"Cihaz: {alarm.device.asset_model} (SN: {alarm.device_id})")
                    
                    with c_b:
                        st.write(f"**Zaman:** {alarm.timestamp.strftime('%d.%m.%Y %H:%M')}")
                        st.markdown(f"**Önem:** :{color}[{alarm.severity}]")
                        
                    with c_c:
                        # AKSİYON BUTONU
                        if st.button("👁️ Okundu İşaretle", key=f"ack_{alarm.id}", use_container_width=True):
                            acknowledge_alarm(alarm.id, user.username)
                            st.toast("Alarm arşivlendi!", icon="✅")
                            st.rerun()

    # --- TAB 2: GEÇMİŞ & EXPORT ---
    with tab2:
        st.subheader("Arşiv ve Raporlama")
        
        # DataFrame Hazırlığı
        if history_alarms:
            data = []
            for a in history_alarms:
                data.append({
                    "ID": a.id,
                    "Zaman": a.timestamp,
                    "Cihaz": a.device.unit_name,
                    "Tip": a.alarm_type,
                    "Önem": a.severity,
                    "Değer": a.value,
                    "Açıklama": a.description,
                    "Durum": "Bekliyor" if a.is_active else "Çözüldü",
                    "Çözen": a.acknowledged_by if a.acknowledged_by else "-"
                })
            
            df = pd.DataFrame(data)
            
            # Filtreleme Seçenekleri
            col_f1, col_f2 = st.columns(2)
            filter_device = col_f1.multiselect("Cihaz Filtrele", options=df['Cihaz'].unique())
            filter_type = col_f2.multiselect("Alarm Tipi Filtrele", options=df['Tip'].unique())
            
            # Filtreyi Uygula
            if filter_device:
                df = df[df['Cihaz'].isin(filter_device)]
            if filter_type:
                df = df[df['Tip'].isin(filter_type)]
            
            # Tabloyu Göster
            st.dataframe(
                df.style.map(lambda x: 'color: red' if x == 'Critical' else 'color: orange' if x == 'Warning' else '', subset=['Önem']),
                use_container_width=True,
                height=400
            )
            
            # EXPORT BUTONU (EXCEL/CSV)
            st.markdown("### 📥 Rapor İndir")
            
            @st.cache_data
            def convert_df(df):
                return df.to_csv(index=False).encode('utf-8-sig')

            csv = convert_df(df)

            st.download_button(
                label="📥 Excel (CSV) Olarak İndir",
                data=csv,
                file_name=f'Alarm_Raporu_{pd.Timestamp.now().strftime("%Y%m%d")}.csv',
                mime='text/csv',
                type="primary"
            )
        else:
            st.info("Kayıt bulunamadı.")
    st.markdown('<div style="height: 50px;"></div>', unsafe_allow_html=True)
    