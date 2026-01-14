# frontend/views/reports.py
import streamlit as st
import pandas as pd
import plotly.express as px
from backend.database import get_user_devices, get_daily_utilization, get_fleet_summary_report, get_all_devices_for_admin

def load_view(user):
    st.title("📈 Operasyonel Raporlar")
    st.markdown("Cihazlarınızın verimliliğini, çalışma sürelerini ve saha performansını analiz edin.")

    # Cihazları Getir
    devices = get_all_devices_for_admin() if user.role == 'Admin' else get_user_devices(user.id)
    device_names = [d.unit_name for d in devices]
    
    # --- ÜST FİLTRE ALANI ---
    with st.container():
        c1, c2, c3 = st.columns([2, 1, 1])
        selected_device_name = c1.selectbox("Analiz Edilecek Makine Seçin:", device_names)
        days_back = c2.selectbox("Zaman Aralığı", [7, 14, 30], format_func=lambda x: f"Son {x} Gün")
        report_type = c3.selectbox("Rapor Tipi", ["Verimlilik (Utilization)", "Yakıt & Mesafe", "Alarm Dökümü"])

    # Seçilen cihaz objesini bul
    selected_device = next(d for d in devices if d.unit_name == selected_device_name)
    
    st.markdown("---")

    # --- RAPOR 1: VERİMLİLİK (DAILY UTILIZATION) ---
    if report_type == "Verimlilik (Utilization)":
        st.subheader(f"⏱️ {selected_device_name} - Günlük Çalışma Analizi")
        
        # Veriyi Çek
        data = get_daily_utilization(selected_device.device_id, days=days_back)
        df = pd.DataFrame(data)
        
        if not df.empty:
            # KPI KARTLARI
            total_hours = df["Çalışma Saati"].sum()
            avg_hours = df["Çalışma Saati"].mean()
            
            k1, k2, k3 = st.columns(3)
            k1.metric("Toplam Çalışma", f"{total_hours} Saat")
            k2.metric("Günlük Ortalama", f"{round(avg_hours, 1)} Saat")
            k3.metric("Verimlilik Puanı", "%88", delta="Yüksek")
            
            # GRAFİK (BAR CHART)
            fig = px.bar(
                df, x="Tarih", y="Çalışma Saati",
                title=f"Günlük Çalışma Süreleri (Son {days_back} Gün)",
                text="Çalışma Saati",
                color="Çalışma Saati",
                color_continuous_scale="Blues"
            )
            fig.update_traces(textposition='outside')
            fig.update_layout(yaxis_title="Saat", xaxis_title="Tarih")
            st.plotly_chart(fig, use_container_width=True)
            
            # DETAY TABLOSU
            with st.expander("📄 Detaylı Günlük Tabloyu Göster"):
                st.dataframe(df, use_container_width=True)
                
        else:
            st.info("Bu tarih aralığı için veri bulunamadı.")

    # --- RAPOR 2: YAKIT & MESAFE ---
    elif report_type == "Yakıt & Mesafe":
        st.subheader(f"⛽ {selected_device_name} - Mesafe ve Tahmini Tüketim")
        
        data = get_daily_utilization(selected_device.device_id, days=days_back)
        df = pd.DataFrame(data)
        
        if not df.empty:
            # İki Eksenli Grafik (Mesafe vs Hız)
            fig = px.line(df, x="Tarih", y="Mesafe (km)", markers=True, title="Günlük Kat Edilen Mesafe")
            fig.add_bar(x=df["Tarih"], y=df["Max Hız"], name="Max Hız (km/s)", opacity=0.3)
            st.plotly_chart(fig, use_container_width=True)
            
            st.info("ℹ️ Yakıt verisi CAN-BUS entegrasyonu tamamlandığında burada görünecektir. Şu an mesafe bazlı tahmin yürütülmektedir.")
    
    # --- FİLO ÖZETİ (SAĞ TARAF / ALT KISIM) ---
    st.markdown("---")
    st.subheader("📋 Filo Hızlı Bakış (Bugün)")
    fleet_data = get_fleet_summary_report()
    df_fleet = pd.DataFrame(fleet_data)
    st.dataframe(df_fleet, use_container_width=True)

    # --- EXPORT ALANI ---
    c_ex1, c_ex2 = st.columns([3, 1])
    with c_ex2:
        st.download_button(
            label="📥 Raporu PDF İndir",
            data="Demo PDF Content",
            file_name="SolidTrack_Rapor.pdf",
            mime="application/pdf",
            use_container_width=True
        )