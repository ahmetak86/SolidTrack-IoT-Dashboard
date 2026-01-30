# frontend/views/reports.py (V4 - STRING DATE FIX)
import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import sys
import os

# Ana dizin yolunu ekle (Backend ve Frontend modüllerini bulabilmesi için)
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from backend.database import get_user_devices, get_daily_utilization, get_fleet_summary_report, get_all_devices_for_admin
from frontend.utils import format_date_for_ui

# --- PDF GENERATOR MOTORU (Dahili Entegrasyon) ---
from fpdf import FPDF

class PDFReport(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 15)
        self.cell(0, 10, 'SolidTrack IoT - Operasyon Raporu', 0, 1, 'C')
        self.ln(5)
    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Sayfa {self.page_no()}', 0, 0, 'C')

def create_device_pdf_report(device_name, df_data, stats, report_type):
    pdf = PDFReport()
    pdf.add_page()
    
    # Türkçe Karakter Düzeltme
    def tr_fix(text):
        replacements = {
            'ş': 's', 'Ş': 'S', 'ı': 'i', 'İ': 'I', 'ğ': 'g', 'Ğ': 'G',
            'ü': 'u', 'Ü': 'U', 'ö': 'o', 'Ö': 'O', 'ç': 'c', 'Ç': 'C'
        }
        text = str(text)
        for k, v in replacements.items():
            text = text.replace(k, v)
        return text

    # Başlık Bilgileri
    pdf.set_font("Arial", size=12)
    pdf.cell(0, 10, tr_fix(f"Rapor Tarihi: {datetime.now().strftime('%d.%m.%Y')}"), 0, 1, 'R')
    pdf.cell(0, 10, tr_fix(f"Makine: {device_name}"), 0, 1, 'L')
    pdf.cell(0, 10, tr_fix(f"Rapor Tipi: {report_type}"), 0, 1, 'L')
    pdf.ln(5)

    # 1. Özet İstatistikler Kutusu
    pdf.set_fill_color(230, 230, 230)
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, tr_fix("1. Ozet Performans"), 0, 1, 'L', fill=True)
    pdf.ln(2)
    
    pdf.set_font("Arial", size=11)
    # Stats sözlüğünden gelen gerçek verileri yazıyoruz
    if report_type == "Verimlilik (Utilization)":
        info_text = f"Toplam Calisma: {stats['total']} Saat  |  Gunluk Ort: {stats['avg']} Saat  |  Kapasite Kullanim: %{stats['score']}"
        pdf.cell(0, 10, tr_fix(info_text), 0, 1)
    
    pdf.ln(5)

    # 2. Detaylı Tablo
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, tr_fix("2. Gunluk Detaylar"), 0, 1, 'L', fill=True)
    pdf.ln(2)

    # Tablo Başlıkları
    pdf.set_font("Arial", 'B', 10)
    col_w = 45
    pdf.cell(col_w, 10, 'Tarih', 1)
    if 'Çalışma Saati' in df_data.columns:
        pdf.cell(col_w, 10, 'Calisma (Sa)', 1)
    if 'Mesafe (km)' in df_data.columns:
        pdf.cell(col_w, 10, 'Mesafe (km)', 1)
    if 'Max Hız' in df_data.columns:
        pdf.cell(col_w, 10, 'Max Hiz', 1)
    pdf.ln()

    # Tablo Satırları
    pdf.set_font("Arial", size=10)
    for _, row in df_data.iterrows():
        # Tarih formatı zaten UI için düzeltilmiş olabilir, PDF için string basıyoruz
        pdf.cell(col_w, 10, str(row['Tarih']), 1)
        if 'Çalışma Saati' in df_data.columns:
            pdf.cell(col_w, 10, str(row['Çalışma Saati']), 1)
        if 'Mesafe (km)' in df_data.columns:
            pdf.cell(col_w, 10, str(row['Mesafe (km)']), 1)
        if 'Max Hız' in df_data.columns:
            pdf.cell(col_w, 10, str(row['Max Hız']), 1)
        pdf.ln()
    
    pdf.ln(10)
    pdf.set_font("Arial", 'I', 8)
    pdf.multi_cell(0, 5, tr_fix("Bu belge SolidTrack IoT Platformu tarafindan otomatik olarak uretilmistir."))
    
    return pdf.output(dest='S').encode('latin-1')

# --- SAYFA GÖRÜNÜMÜ ---
def load_view(user):
    st.title("📈 Operasyonel Raporlar")
    st.markdown("Cihazlarınızın verimliliğini, çalışma sürelerini ve saha performansını analiz edin.")

    # Cihazları Getir (Yetkiye Göre)
    devices = get_all_devices_for_admin() if user.role == 'Admin' else get_user_devices(user.id)
    if not devices:
        st.warning("Raporlanacak cihaz bulunamadı.")
        return

    device_names = [d.unit_name for d in devices]
    
    # --- ÜST FİLTRE ALANI ---
    with st.container():
        c1, c2, c3 = st.columns([2, 1, 1])
        selected_device_name = c1.selectbox("Analiz Edilecek Makine Seçin:", device_names)
        days_back = c2.selectbox("Zaman Aralığı", [7, 14, 30], format_func=lambda x: f"Son {x} Gün")
        report_type = c3.selectbox("Rapor Tipi", ["Verimlilik (Utilization)", "Yakıt & Mesafe"])

    # Seçilen cihaz objesini bul
    selected_device = next(d for d in devices if d.unit_name == selected_device_name)
    
    st.markdown("---")

    # --- RAPOR 1: VERİMLİLİK (DAILY UTILIZATION) ---
    if report_type == "Verimlilik (Utilization)":
        st.subheader(f"⏱️ {selected_device_name} - Günlük Çalışma Analizi")
        
        # Veriyi Çek
        data = get_daily_utilization(selected_device.device_id, days=days_back)
        df = pd.DataFrame(data)

        if not df.empty and 'Tarih' in df.columns:
            # --- TARİH DÜZELTME (BURASI KRİTİK DÜZELTME) ---
            # 1. String olarak gelen tarihi önce datetime objesine çeviriyoruz (pd.to_datetime)
            # Böylece 'tzinfo' hatası almadan formatlayabiliriz.
            df['Tarih_Ham'] = pd.to_datetime(df['Tarih'])
            
            # 2. UI Gösterimi için formatla
            df['Tarih'] = df['Tarih_Ham'].apply(lambda x: format_date_for_ui(x, user.timezone, include_offset=False))
            
            # GERÇEK KPI HESAPLAMA
            total_hours = df["Çalışma Saati"].sum()
            avg_hours = df["Çalışma Saati"].mean()
            
            # Kapasite Kullanım Oranı
            shift_hours = 8
            utilization_score = int((avg_hours / shift_hours) * 100)
            if utilization_score > 100: utilization_score = 100

            # Kartlar
            k1, k2, k3 = st.columns(3)
            k1.metric("Toplam Çalışma", f"{total_hours:.1f} Saat")
            k2.metric("Günlük Ortalama", f"{avg_hours:.1f} Saat")
            
            # Dinamik Renk ve Mesaj
            delta_msg = "Normal"
            if utilization_score > 80: delta_msg = "Yüksek Verim"
            elif utilization_score < 30: delta_msg = "Düşük Verim"
            
            k3.metric("Kapasite Kullanımı (8s)", f"%{utilization_score}", delta=delta_msg)
            
            # GRAFİK (BAR CHART)
            # Grafikte X ekseni olarak formatlanmış tarihi ('Tarih') kullanıyoruz
            fig = px.bar(
                df, x="Tarih", y="Çalışma Saati",
                title=f"Günlük Çalışma Süreleri (Son {days_back} Gün)",
                text="Çalışma Saati",
                color="Çalışma Saati",
                color_continuous_scale="Blues"
            )
            fig.update_traces(textposition='outside')
            fig.update_layout(yaxis_title="Saat", xaxis_title="Tarih")
            
            fig.add_hline(y=8, line_dash="dot", annotation_text="Vardiya Hedefi (8s)", annotation_position="top right", line_color="red")
            
            st.plotly_chart(fig, use_container_width=True)
            
            # DETAY TABLOSU
            with st.expander("📄 Detaylı Günlük Tabloyu Göster"):
                # Tabloda ham tarih sütununu gizleyelim
                st.dataframe(df.drop(columns=['Tarih_Ham']), use_container_width=True)
                
        else:
            st.info("Bu tarih aralığı için veri bulunamadı.")

    # --- RAPOR 2: YAKIT & MESAFE ---
    elif report_type == "Yakıt & Mesafe":
        st.subheader(f"⛽ {selected_device_name} - Mesafe ve Tahmini Tüketim")
        
        data = get_daily_utilization(selected_device.device_id, days=days_back)
        df = pd.DataFrame(data)
        
        if not df.empty:
            # Tarih düzeltme (Yakıt raporunda da yapıyoruz)
            if 'Tarih' in df.columns:
                df['Tarih_Ham'] = pd.to_datetime(df['Tarih']) # String -> Datetime
                df['Tarih'] = df['Tarih_Ham'].apply(lambda x: format_date_for_ui(x, user.timezone, include_offset=False))

            # İki Eksenli Grafik (Mesafe vs Hız)
            fig = px.line(df, x="Tarih", y="Mesafe (km)", markers=True, title="Günlük Kat Edilen Mesafe")
            fig.add_bar(x=df["Tarih"], y=df["Max Hız"], name="Max Hız (km/s)", opacity=0.3)
            st.plotly_chart(fig, use_container_width=True)
            
            st.info("ℹ️ Yakıt verisi CAN-BUS entegrasyonu tamamlandığında burada görünecektir. Şu an mesafe bazlı tahmin yürütülmektedir.")
        else:
            st.info("Veri yok.")
    
    # --- FİLO ÖZETİ (SAĞ TARAF / ALT KISIM) ---
    st.markdown("---")
    st.subheader("📋 Filo Hızlı Bakış (Bugün)")
    fleet_data = get_fleet_summary_report(user_id=user.id)
    df_fleet = pd.DataFrame(fleet_data)
    if not df_fleet.empty:
        st.dataframe(df_fleet, use_container_width=True)
    else:
        st.caption("Filo verisi yok.")

    # --- EXPORT ALANI ---
    st.markdown("---")
    c_ex1, c_ex2 = st.columns([3, 1])
    
    with c_ex1:
        st.info("💡 Raporu indirmek için yandaki butonu kullanabilirsiniz.")

    with c_ex2:
        # PDF Oluşturma Mantığı
        if report_type == "Verimlilik (Utilization)" and 'df' in locals() and not df.empty:
            
            stats_for_pdf = {
                "total": f"{total_hours:.1f}",
                "avg": f"{avg_hours:.1f}",
                "score": f"{utilization_score}" 
            }
            
            pdf_bytes = create_device_pdf_report(selected_device_name, df, stats_for_pdf, report_type)
            
            st.download_button(
                label="📥 Raporu PDF İndir",
                data=pdf_bytes,
                file_name=f"SolidTrack_{selected_device_name}_Rapor.pdf",
                mime="application/pdf",
                use_container_width=True,
                type="primary"
            )
        elif report_type == "Yakıt & Mesafe" and 'df' in locals() and not df.empty:
             stats_for_pdf = {"total": "-", "avg": "-", "score": "-"}
             pdf_bytes = create_device_pdf_report(selected_device_name, df, stats_for_pdf, report_type)
             st.download_button(
                label="📥 Raporu PDF İndir",
                data=pdf_bytes,
                file_name=f"SolidTrack_Mesafe_{selected_device_name}.pdf",
                mime="application/pdf",
                use_container_width=True,
                type="primary"
            )
        else:
            st.download_button(
                label="📥 Raporu PDF İndir",
                data="Veri seçilmedi.",
                disabled=True,
                use_container_width=True
            )