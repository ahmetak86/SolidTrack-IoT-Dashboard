# backend/pdf_generator.py
from fpdf import FPDF
import pandas as pd
import os
from datetime import datetime

class PDFReport(FPDF):
    def header(self):
        # Logo ve Başlık
        self.set_font('Arial', 'B', 15)
        self.cell(0, 10, 'SolidTrack IoT - Filo Performans Raporu', 0, 1, 'C')
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Sayfa {self.page_no()}', 0, 0, 'C')

def create_device_pdf(device_name, df_data, stats):
    """
    Cihaz verilerini alıp PDF binary verisi döndürür.
    df_data: get_daily_utilization'dan gelen liste
    stats: Özet istatistikler (dict)
    """
    pdf = PDFReport()
    pdf.add_page()
    
    # Türkçe karakter desteği için font ayarı (Arial varsayılan olarak TR desteklemeyebilir,
    # basitlik adına standart ASCII kullanacağız veya karakterleri replace edeceğiz)
    # Not: Profesyonel projelerde 'DejaVuSans' fontu yüklenir. 
    # Burada hızlı çözüm için karakter düzeltmesi yapıyoruz:
    def tr_fix(text):
        replacements = {
            'ş': 's', 'Ş': 'S', 'ı': 'i', 'İ': 'I', 'ğ': 'g', 'Ğ': 'G',
            'ü': 'u', 'Ü': 'U', 'ö': 'o', 'Ö': 'O', 'ç': 'c', 'Ç': 'C'
        }
        for k, v in replacements.items():
            text = str(text).replace(k, v)
        return text

    # 1. Başlık Bilgileri
    pdf.set_font("Arial", size=12)
    pdf.cell(0, 10, tr_fix(f"Rapor Tarihi: {datetime.now().strftime('%d.%m.%Y')}"), 0, 1, 'R')
    pdf.cell(0, 10, tr_fix(f"Makine: {device_name}"), 0, 1, 'L')
    pdf.ln(5)

    # 2. KPI Kartları (Özet)
    pdf.set_fill_color(200, 220, 255)
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, tr_fix("1. Ozet Istatistikler"), 0, 1, 'L', fill=True)
    pdf.ln(2)
    
    pdf.set_font("Arial", size=11)
    # stats dict'inden verileri alalım
    txt = f"Toplam Calisma: {stats['total']} Saat  |  Ortalama: {stats['avg']} Saat/Gun  |  Verim: %{stats['score']}"
    pdf.cell(0, 10, tr_fix(txt), 0, 1)
    pdf.ln(5)

    # 3. Günlük Tablo
    pdf.set_fill_color(200, 220, 255)
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, tr_fix("2. Gunluk Detay Tablosu"), 0, 1, 'L', fill=True)
    pdf.ln(2)

    # Tablo Başlıkları
    pdf.set_font("Arial", 'B', 10)
    col_width = 45
    pdf.cell(col_width, 10, 'Tarih', 1)
    pdf.cell(col_width, 10, 'Calisma (Saat)', 1)
    pdf.cell(col_width, 10, 'Mesafe (km)', 1)
    pdf.cell(col_width, 10, 'Max Hiz (km/h)', 1)
    pdf.ln()

    # Tablo Satırları
    pdf.set_font("Arial", size=10)
    if isinstance(df_data, list):
        for row in df_data:
            pdf.cell(col_width, 10, str(row['Tarih']), 1)
            pdf.cell(col_width, 10, str(row['Çalışma Saati']), 1)
            pdf.cell(col_width, 10, str(row['Mesafe (km)']), 1)
            pdf.cell(col_width, 10, str(row['Max Hız']), 1)
            pdf.ln()
    
    # 4. Alt Bilgi / Uyarı
    pdf.ln(10)
    pdf.set_font("Arial", 'I', 8)
    pdf.multi_cell(0, 5, tr_fix("Bu rapor SolidTrack IoT sisteminden otomatik olarak uretilmistir. Veriler cihazlardan gelen ham telemetri verilerine dayanmaktadir."))

    # Binary olarak döndür
    return pdf.output(dest='S').encode('latin-1')