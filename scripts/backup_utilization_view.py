import streamlit as st
import pandas as pd
import plotly.express as px
from backend.database import SessionLocal, get_all_devices_for_admin, get_user_devices
from backend.models import UtilizationEvent
from datetime import datetime, timedelta, date
import io

# --- PDF GENERATOR (Senin gönderdiğin kodun entegrasyonu) ---
from fpdf import FPDF
class PDFReport(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 15)
        self.cell(0, 10, 'SolidTrack IoT - Filo Performans Raporu', 0, 1, 'C')
        self.ln(5)
    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Sayfa {self.page_no()}', 0, 0, 'C')

def create_device_pdf(device_name, df_data, stats):
    pdf = PDFReport()
    pdf.add_page()
    def tr_fix(text):
        replacements = {
            'ş': 's', 'Ş': 'S', 'ı': 'i', 'İ': 'I', 'ğ': 'g', 'Ğ': 'G',
            'ü': 'u', 'Ü': 'U', 'ö': 'o', 'Ö': 'O', 'ç': 'c', 'Ç': 'C'
        }
        for k, v in replacements.items():
            text = str(text).replace(k, v)
        return text

    pdf.set_font("Arial", size=12)
    pdf.cell(0, 10, tr_fix(f"Rapor Tarihi: {datetime.now().strftime('%d.%m.%Y')}"), 0, 1, 'R')
    pdf.cell(0, 10, tr_fix(f"Makine: {device_name}"), 0, 1, 'L')
    pdf.ln(5)

    pdf.set_fill_color(200, 220, 255)
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, tr_fix("1. Ozet Istatistikler"), 0, 1, 'L', fill=True)
    pdf.ln(2)
    pdf.set_font("Arial", size=11)
    txt = f"Toplam Calisma: {stats['total']}  |  Ortalama: {stats['avg']}  |  Verim: %{stats['score']}"
    pdf.cell(0, 10, tr_fix(txt), 0, 1)
    pdf.ln(5)

    pdf.set_fill_color(200, 220, 255)
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, tr_fix("2. Gunluk Calisma Ozet"), 0, 1, 'L', fill=True)
    pdf.ln(2)

    # Basit bir tablo başlığı
    pdf.set_font("Arial", 'B', 10)
    pdf.cell(60, 10, 'Tarih', 1)
    pdf.cell(60, 10, 'Calisma Suresi', 1)
    pdf.ln()

    # Tablo Satırları
    pdf.set_font("Arial", size=10)
    if isinstance(df_data, list):
        for row in df_data:
            pdf.cell(60, 10, str(row['Tarih']), 1)
            pdf.cell(60, 10, tr_fix(str(row['Çalışma Saati'])), 1)
            pdf.ln()
    
    pdf.ln(10)
    pdf.set_font("Arial", 'I', 8)
    pdf.multi_cell(0, 5, tr_fix("Bu rapor SolidTrack IoT sisteminden otomatik olarak uretilmistir."))
    return pdf.output(dest='S').encode('latin-1')

# --- RENK PALETİ ---
COLOR_MAP = {
    "İdeal Çalışma (0-20s)": "#00C853",      # YEŞİL
    "Riskli Çalışma (21-40s)": "#FFAB00",    # TURUNCU
    "Uç Şişirme Riski (41-80s)": "#D50000",  # KIRMIZI
    "Operatör Hatası (81-180s)": "#AA00FF",  # MOR
    "Nakliye / Uzun Hareket": "#000000",     # SİYAH
    "Boşta Bekleme (Idle)": "#E0E0E0"        # GRİ
}

# Sıralama (Yeşil en üstte olsun diye ters çevireceğiz)
CATEGORY_ORDER = [
    "İdeal Çalışma (0-20s)", 
    "Riskli Çalışma (21-40s)", 
    "Uç Şişirme Riski (41-80s)", 
    "Operatör Hatası (81-180s)"
]

# --- YARDIMCI FONKSİYONLAR ---
def format_duration_tr(seconds):
    if not seconds: return "0 sa 0 dk"
    seconds = int(seconds)
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    return f"{hours} sa {minutes} dk"

def format_seconds_detailed(seconds):
    if not seconds: return "0 sn"
    seconds = int(seconds)
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    parts = []
    if h > 0: parts.append(f"{h} sa")
    if m > 0: parts.append(f"{m} dk")
    parts.append(f"{s} sn")
    return " ".join(parts)

def get_category_label(duration, raw_activity):
    if raw_activity == 0: return "Boşta Bekleme (Idle)"
    if duration > 180: return "Nakliye / Uzun Hareket"
    elif duration <= 20: return "İdeal Çalışma (0-20s)"
    elif duration <= 40: return "Riskli Çalışma (21-40s)"
    elif duration <= 80: return "Uç Şişirme Riski (41-80s)"
    else: return "Operatör Hatası (81-180s)"

# --- AKSİYON BAR COMPONENTİ (SADE & HİZALI VERSİYON) ---
def render_bottom_action_bar(df, target_device, ratio, total_working_sec, avg_daily_sec, key_suffix=""):
    """
    Yeşil bant yok. Sadece hizalı metinler ve renkli butonlar.
    Sol: SolidAI Metni ve Kırmızı Buton
    Sağ: İndirme Metni ve Mavi Butonlar
    """
    
    # --- VERİ HAZIRLIĞI ---
    pdf_rows = []
    if not df.empty:
        daily_grp = df.groupby("Tarih")["Süre (sn)"].sum().reset_index()
        for _, row in daily_grp.iterrows():
            pdf_rows.append({
                "Tarih": row["Tarih"].strftime("%d.%m.%Y"),
                "Çalışma Saati": format_duration_tr(row["Süre (sn)"])
            })
    
    stats_summary = {
        "total": format_duration_tr(total_working_sec),
        "avg": format_duration_tr(avg_daily_sec),
        "score": f"{ratio:.1f}"
    }

    # Bu bloğu izole etmek için bir ID (CSS karışmasın diye)
    scope_id = f"clean-action-bar-{key_suffix}"

    st.markdown(f"""
    <style>
    /* Kapsayıcıya biraz üst/alt boşluk verelim */
    div#{scope_id} {{
        margin-top: 20px;
        margin-bottom: 40px;
    }}

    /* BAŞLIKLAR İÇİN STİL */
    .clean-title {{
        font-size: 16px;
        font-weight: 700;
        color: #111;
        margin-bottom: 10px;
        display: flex;
        align-items: center;
        gap: 8px;
    }}

    /* KIRMIZI BUTON (SolidAI) */
    /* Sadece bu scope içindeki primary butonları boyar */
    div[data-testid="stVerticalBlock"]:has(div#{scope_id}) button[kind="primary"] {{
        background-color: #ff4b4b !important;
        border: none !important;
        color: white !important;
        font-weight: 600 !important;
        border-radius: 6px !important;
        width: 150px !important; /* Buton genişliğini sabitledik */
    }}
    div[data-testid="stVerticalBlock"]:has(div#{scope_id}) button[kind="primary"]:hover {{
        background-color: #ef4444 !important;
    }}

    /* MAVİ BUTONLAR (PDF/Excel) */
    /* Sadece bu scope içindeki secondary butonları boyar */
    div[data-testid="stVerticalBlock"]:has(div#{scope_id}) button[kind="secondary"] {{
        background-color: #225d97 !important; /* Solidus Mavisi */
        border: none !important;
        color: white !important;
        font-weight: 600 !important;
        border-radius: 6px !important;
    }}
    div[data-testid="stVerticalBlock"]:has(div#{scope_id}) button[kind="secondary"]:hover {{
        background-color: #1a4b7c !important;
    }}
    </style>
    """, unsafe_allow_html=True)

    # --- HTML CSS KANCASI ---
    # Bu boş div sayesinde CSS sadece bu alanın altındaki butonları etkiler
    st.markdown(f'<div id="{scope_id}"></div>', unsafe_allow_html=True)

    # --- LAYOUT (Sol ve Sağ olarak ikiye ayırıyoruz) ---
    c_left, c_right = st.columns([1.5, 1.5])

    # 1. SOL TARAFA (SolidAI)
    with c_left:
        # Metin ve İkon
        st.markdown('<div class="clean-title">🤖 SolidAI ile Verilerinizi Analiz Edin!</div>', unsafe_allow_html=True)
        # Buton (Kırmızı)
        if st.button("SolidAI", type="primary", key=f"ai_btn_{key_suffix}"):
            st.session_state[f"show_ai_{key_suffix}"] = True

    # 2. SAĞ TARAFA (İndirme)
    with c_right:
        # Metin
        st.markdown('<div class="clean-title" style="justify-content: flex-start;">Verilerinizi İndirin</div>', unsafe_allow_html=True)
        
        # Butonları yan yana koymak için iç kolonlar
        d1, d2, d3 = st.columns([1, 1, 1]) # 3 parça yapıp ilk ikisini kullanıyoruz ki butonlar çok devasa olmasın
        
        with d1:
            try:
                pdf_data = create_device_pdf(target_device.unit_name, pdf_rows, stats_summary)
                st.download_button(
                    "📄 PDF", 
                    data=pdf_data,
                    file_name=f"Rapor_{target_device.unit_name}.pdf",
                    mime="application/pdf",
                    key=f"pdf_btn_{key_suffix}",
                    use_container_width=True
                )
            except:
                st.error("Hata")
        
        with d2:
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                df_export = df.drop(columns=["StartObj", "EndObj"], errors='ignore')
                df_export.to_excel(writer, index=False, sheet_name='Veri')
            st.download_button(
                "📊 Excel", 
                data=output.getvalue(), 
                file_name=f"Rapor_{target_device.unit_name}.xlsx", 
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", 
                key=f"xls_btn_{key_suffix}",
                use_container_width=True
            )

    # AI Sonuç Mesajı
    if st.session_state.get(f"show_ai_{key_suffix}"):
        st.markdown("<div style='margin-bottom: 15px;'></div>", unsafe_allow_html=True)
        st.info(f"🤖 **SolidAI Analizi:**\nCihaz bu periyotta %{ratio:.1f} verimlilikle çalışmıştır.")

# --- ANA EKRAN ---
def load_view(user):
    st.markdown("""
        <style>
        .block-container { padding-top: 1rem !important; }
        .stMetric { background-color: #f9f9f9; border: 1px solid #ddd; padding: 10px; border-radius: 5px; }
        .info-banner {
            background-color: #e8f5e9; padding: 15px; border-radius: 8px; color: #2e7d32;
            border-left: 5px solid #2e7d32; margin-bottom: 20px; margin-top: 10px; font-size: 15px;
        }
        /* Sayfa sonu boşluğu */
        .bottom-spacer {
            height: 50px;
        }
        </style>
    """, unsafe_allow_html=True)
    
    st.title("🔨 Kırıcı Verimlilik Analizi")

    # 1. CİHAZ VE FİLTRELER
    devices = get_all_devices_for_admin() if user.role == 'Admin' else get_user_devices(user.id)
    if not devices:
        st.warning("Cihaz bulunamadı.")
        return

    c1, c2, c3, c4 = st.columns([2, 1.5, 1.2, 1.2])
    selected_dev_name = c1.selectbox("Makine Seçin:", [d.unit_name for d in devices], index=None, placeholder="Makine Seçiniz...")
    target_device = next((d for d in devices if d.unit_name == selected_dev_name), None)

    period_options = ["Tarih Seç", "Bugün", "Son 1 Hafta", "Son 1 Ay", "Tüm Zamanlar"]
    period = c2.selectbox("Periyot:", period_options, index=0)
    
    today = datetime.now().date()
    if period == "Tarih Seç":
        default_start = today - timedelta(days=7)
        s = c3.date_input("Başlangıç:", default_start, format="DD/MM/YYYY")
        e = c4.date_input("Bitiş:", today, min_value=s, format="DD/MM/YYYY")
    elif period == "Bugün": s, e = today, today
    elif period == "Son 1 Hafta": s, e = today - timedelta(days=7), today
    elif period == "Son 1 Ay": s, e = today - timedelta(days=30), today
    elif period == "Tüm Zamanlar": s, e = date(2023, 1, 1), today

    if not target_device:
        st.info("Kullanım bilgilerinizi görüntülemek için makine seçiminizi yapın.")
        return

    s_str, e_str = s.strftime('%d.%m.%Y'), e.strftime('%d.%m.%Y')
    st.markdown(f'<div class="info-banner">📌 <b>{target_device.unit_name}</b> makinesinin <b>{s_str}</b> - <b>{e_str}</b> tarihlerindeki kullanım verileri gösterilmektedir.</div>', unsafe_allow_html=True)

    # VERİ ÇEKME
    with st.spinner(f"📡 Veriler analiz ediliyor..."):
        db = SessionLocal()
        query = db.query(UtilizationEvent).filter(
            UtilizationEvent.device_id == target_device.device_id,
            UtilizationEvent.start_time >= s,
            UtilizationEvent.start_time <= (e + timedelta(days=1))
        )
        events = query.order_by(UtilizationEvent.start_time.asc()).all()
        db.close()

    if not events:
        st.warning(f"📅 {s_str} - {e_str} aralığında veri bulunamadı.")
        return

    # VERİ İŞLEME
    data = []
    total_working_sec = 0
    total_transport_sec = 0
    sum_ideal_risk = 0 
    
    for event in events:
        if event.raw_activity == 0: continue
        cat_label = get_category_label(event.duration_sec, event.raw_activity)
        
        start_obj = event.start_time + timedelta(hours=3)
        end_obj = (event.end_time or (event.start_time + timedelta(seconds=event.duration_sec))) + timedelta(hours=3)

        if cat_label == "Nakliye / Uzun Hareket": 
            total_transport_sec += event.duration_sec
        else:
            total_working_sec += event.duration_sec
            if cat_label in ["İdeal Çalışma (0-20s)", "Riskli Çalışma (21-40s)"]: 
                sum_ideal_risk += event.duration_sec
            
            data.append({
                "Tarih": start_obj.date(),
                "StartObj": start_obj, 
                "EndObj": end_obj,     
                "Saat": start_obj.strftime("%H:%M:%S"), 
                "Süre (sn)": event.duration_sec,
                "Kategori": cat_label
            })
    
    df = pd.DataFrame(data)
    if df.empty:
        st.warning("📅 Aktif çalışma verisi bulunamadı.")
        return

    # KPI HESAPLA
    num_days = (e - s).days + 1
    avg_daily_sec = total_working_sec / num_days if num_days > 0 else 0
    ratio = (sum_ideal_risk / total_working_sec * 100) if total_working_sec > 0 else 0

    # --- 1. KPI KARTLARI ---
    st.markdown("### 📊 Operasyon Özeti")
    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    kpi1.metric("Toplam Çalışma", format_duration_tr(total_working_sec))
    kpi2.metric("Günlük Çalışma (Ortalama)", format_duration_tr(avg_daily_sec))
    kpi3.metric("Verimlilik Skoru", f"%{ratio:.1f}", delta_color="normal")
    kpi4.metric("Toplam Vuruş Adedi", f"{len(df)} Adet")
    
    # --- ÜST AKSİYON BAR ---
    render_bottom_action_bar(df, target_device, ratio, total_working_sec, avg_daily_sec, key_suffix="top")
    st.markdown("---")

    # --- 3. GRAFİKLER ---
    col_g1, col_g2 = st.columns(2)

    # 1. GÜNLÜK ÇALIŞMA GRAFİĞİ
    with col_g1:
        st.markdown("**Çalışma Süresi (Günlük)**")
        st.caption("Seçilen periyotta makinenin çalışma süresini gün bazında gösterir.")
        
        daily_df = df.groupby(["Tarih", "Kategori"])["Süre (sn)"].sum().reset_index()
        daily_df["Saat"] = daily_df["Süre (sn)"] / 3600
        daily_df["Tooltip"] = daily_df["Süre (sn)"].apply(format_seconds_detailed)

        fig_daily = px.bar(
            daily_df, x="Tarih", y="Saat", color="Kategori",
            color_discrete_map=COLOR_MAP,
            category_orders={"Kategori": CATEGORY_ORDER},
            labels={"Saat": "Süre (Saat)", "Tarih": ""},
            custom_data=["Tooltip"]
        )
        fig_daily.update_traces(hovertemplate="<b>%{y:.1f} Saat</b><br>%{customdata[0]}<extra></extra>")
        fig_daily.update_layout(
            hovermode="x unified",
            legend=dict(orientation="h", y=-0.2, x=0, xanchor="left", title=None),
            height=350, margin=dict(l=20, r=20, t=10, b=50),
            xaxis=dict(tickformat="%d/%m")
        )
        st.plotly_chart(fig_daily, use_container_width=True)

    # 2. KÜMÜLATİF ÇALIŞMA GRAFİĞİ
    with col_g2:
        st.markdown("**Çalışma Süresi (Kümülatif)**")
        st.caption("Seçilen periyotta makinenin çalışma süresinin toplamını gösterir.")

        date_range = pd.date_range(start=df['Tarih'].min(), end=df['Tarih'].max(), freq='D').date
        idx = pd.MultiIndex.from_product([date_range, CATEGORY_ORDER], names=['Tarih', 'Kategori'])
        cum_data = df.groupby(["Tarih", "Kategori"])["Süre (sn)"].sum().reindex(idx, fill_value=0).reset_index()
        
        cum_data["Kümülatif Sn"] = cum_data.groupby("Kategori")["Süre (sn)"].cumsum()
        cum_data["Kümülatif Saat"] = cum_data["Kümülatif Sn"] / 3600
        cum_data["Tooltip"] = cum_data["Kümülatif Sn"].apply(format_seconds_detailed)

        fig_cum = px.area(
            cum_data, x="Tarih", y="Kümülatif Saat", color="Kategori",
            color_discrete_map=COLOR_MAP,
            category_orders={"Kategori": CATEGORY_ORDER},
            labels={"Kümülatif Saat": "Toplam Süre (Saat)", "Tarih": ""},
            custom_data=["Tooltip"]
        )
        fig_cum.update_traces(hovertemplate="<b>%{y:.1f} Saat</b><br>Toplam: %{customdata[0]}<extra></extra>")
        fig_cum.update_layout(
            hovermode="x unified",
            legend=dict(orientation="h", y=-0.2, x=0, xanchor="left", title=None),
            height=350, margin=dict(l=20, r=20, t=10, b=50),
            xaxis=dict(tickformat="%d/%m")
        )
        st.plotly_chart(fig_cum, use_container_width=True)

    st.markdown("---")

    # --- 4. KULLANIM VERİMİ (PASTA, TABLO) ---
    st.subheader("📊 Kullanım Verimi (Süre + Verim)")
    st.caption("Seçilen periyotta makinenin çalışma verimini süre ve verimlilik oranı olarak gösterir.")
    
    total_sec = df["Süre (sn)"].sum()
    stats = df.groupby("Kategori")["Süre (sn)"].sum().reset_index()
    
    # Oran ve Süre Metni Hesapla
    stats["Oran (%)"] = (stats["Süre (sn)"] / total_sec * 100).round(1)
    stats["Süre Metni"] = stats["Süre (sn)"].apply(format_duration_tr) 
    stats["Süre Detaylı"] = stats["Süre (sn)"].apply(format_seconds_detailed) 
    
    stats["Sıra"] = stats["Kategori"].apply(lambda x: CATEGORY_ORDER.index(x) if x in CATEGORY_ORDER else 99)
    stats = stats.sort_values("Sıra")

    col_pie, col_table = st.columns([1, 1.5])

    # PASTA GRAFİK
    with col_pie:
        fig_donut = px.pie(
            stats, values="Süre (sn)", names="Kategori",
            color="Kategori", color_discrete_map=COLOR_MAP,
            hole=0.6
        )
        fig_donut.update_layout(showlegend=False, margin=dict(l=0, r=0, t=20, b=20), height=300)
        fig_donut.add_annotation(text=f"%{ratio:.1f}", x=0.5, y=0.5, font_size=28, showarrow=False, font_weight="bold", font_color="#333")
        st.plotly_chart(fig_donut, use_container_width=True)

    # TABLO
    with col_table:
        table_html = "<table style='width:100%; border-collapse:collapse; font-size:14px; font-family:sans-serif;'>"
        table_html += "<thead><tr style='border-bottom:2px solid #ddd; color:#555; text-align:left;'>"
        table_html += "<th style='padding:10px;'>Kategori</th>"
        table_html += "<th style='padding:10px;'>Süre</th>"
        table_html += "<th style='padding:10px;'>Verim</th></tr></thead><tbody>"
        
        # Toplam Satırı
        total_duration_str = format_duration_tr(total_sec)
        table_html += f"<tr style='border-bottom:2px solid #eee; background-color:#fafafa; font-weight:bold;'>"
        table_html += f"<td style='padding:10px; color:#000;'>Toplam Çalışma</td>"
        table_html += f"<td style='padding:10px;'>{total_duration_str}</td>"
        table_html += f"<td style='padding:10px;'>%100</td></tr>"

        for _, row in stats.iterrows():
            cat = row['Kategori']
            color = COLOR_MAP.get(cat, "#333")
            table_html += f"<tr style='border-bottom:1px solid #eee;'>"
            table_html += f"<td style='padding:10px; display:flex; align-items:center;'>"
            table_html += f"<span style='display:inline-block; width:12px; height:12px; background-color:{color}; margin-right:10px; border-radius:3px;'></span>"
            table_html += f"{cat}</td>"
            table_html += f"<td style='padding:10px;'>{row['Süre Metni']}</td>"
            table_html += f"<td style='padding:10px; font-weight:bold; color:#333;'>%{row['Oran (%)']}</td></tr>"
            
        table_html += "</tbody></table>"
        st.markdown(table_html, unsafe_allow_html=True)

    # --- 5. YATAY BAR GRAFİK ---
    st.markdown("<br>", unsafe_allow_html=True)
    
    tooltip_date_range = f"{s.strftime('%d.%m.%Y')} - {e.strftime('%d.%m.%Y')}"
    stats["DateRange"] = tooltip_date_range

    fig_bar = px.bar(
        stats, 
        x="Süre (sn)", 
        y=[1]*len(stats), 
        color="Kategori", 
        orientation='h',
        color_discrete_map=COLOR_MAP,
        custom_data=["DateRange", "Süre Detaylı", "Oran (%)"] 
    )
    
    fig_bar.update_traces(
        hovertemplate=(
            "<b>Tarih:</b> %{customdata[0]}<br>"
            "<b>Toplam Süre:</b> %{customdata[1]}<br>"
            "<b>Verim:</b> %%{customdata[2]}<extra></extra>"
        ),
        width=0.3
    )

    fig_bar.update_layout(
        showlegend=False, plot_bgcolor="white", paper_bgcolor="white", height=140,
        margin=dict(l=0, r=0, t=0, b=40),
        xaxis=dict(visible=False), yaxis=dict(visible=False, showticklabels=False),
        hoverlabel=dict(font_size=14, font_family="Arial")
    )

    current_sum = 0
    for _, row in stats.iterrows():
        val = row["Süre (sn)"]
        percent = row["Oran (%)"]
        if percent >= 3:
            x_pos = current_sum + (val / 2)
            fig_bar.add_annotation(
                x=x_pos, y=1, text=f"<b>%{percent}</b>", showarrow=False, yshift=-30,
                font=dict(color="#333", size=14, weight="bold") 
            )
        current_sum += val

    st.plotly_chart(fig_bar, use_container_width=True)

    # --- 6. KULLANIM DETAYI (TIMELINE) ---
    st.subheader("Kullanım Detayı")
    st.caption("Seçilen periyotta makinenin vuruş sıklığını ve vuruş sayısını gösterir.")

    # Timeline Verileri
    df["Süre Str"] = df["Süre (sn)"].astype(str) + " sn"
    df["Tarih Str"] = df["StartObj"].dt.strftime('%d.%m.%Y')
    
    # Sıralamayı TERS ÇEVİR (Yeşil Üstte olsun diye)
    # CATEGORY_ORDER normalde [Yeşil, Turuncu, Kırmızı, Mor] şeklindeydi.
    # px.timeline genellikle listeyi alttan üste dizer.
    # O yüzden listeyi TERS ÇEVİRİRSEK [Mor, Kırmızı, Turuncu, Yeşil] olur, Yeşil en üste gelir.
    timeline_order = CATEGORY_ORDER[::-1]

    fig_timeline = px.timeline(
        df, 
        x_start="StartObj", 
        x_end="EndObj", 
        y="Kategori", 
        color="Kategori",
        color_discrete_map=COLOR_MAP,
        category_orders={"Kategori": timeline_order}, # TERS LİSTE
        height=350,
        custom_data=["Tarih Str", "Saat", "Süre Str"]
    )

    fig_timeline.update_traces(
        hovertemplate=(
            "<b>Tarih:</b> %{customdata[0]}<br>"
            "<b>Saat:</b> %{customdata[1]}<br>"
            "<b>Süre:</b> %{customdata[2]}<extra></extra>"
        )
    )

    start_dt = datetime.combine(s, datetime.min.time())
    end_dt = datetime.combine(e, datetime.max.time())

   # --- X EKSENİ (00:00 SORUNU GİDERİLDİ) ---
    fig_timeline.update_layout(
        showlegend=False,
        xaxis=dict(
            title=None,
            type='date',
            range=[start_dt, end_dt],
            tickmode="auto",
            nticks=10,
            
            # FORMATLAMA KURALLARI
            tickformatstops=[
                # 1. Çok detaylı zoom (Saniye) -> Saat görünür
                dict(dtickrange=[None, 1000], value="%H:%M:%S"),
                dict(dtickrange=[1000, 60000], value="%H:%M:%S"),
                
                # 2. Dakika ve Saat zoom (KRİTİK DÜZELTME BURADA)
                # Üst sınırı 86400000 (1 gün) yerine 86399999 yaptık.
                # Böylece tam 1 gün (Günlük görünüm) buraya girmez, saat yazmaz.
                # Ama zoom yapınca (aralık küçülünce) buraya girer ve saati yazar.
                dict(dtickrange=[60000, 86399999], value="%H:%M\n%d/%m"), 
                
                # 3. GÜNLÜK MOD (Sadece Tarih)
                # Tam 1 gün ve üzeri aralıklarda sadece tarih göster.
                # 00:00 yazısı burada yer almadığı için silinmiş olur.
                dict(dtickrange=[86400000, 604800000], value="%d/%m\n%Y"), 

                # 4. Geniş Görünüm (Haftalar/Aylar) -> Sadece Tarih
                dict(dtickrange=[604800000, None], value="%d/%m\n%Y")
            ]
        ),
        yaxis=dict(
            title=None, 
            showticklabels=True, 
            tickfont=dict(size=13)
        ), 
        margin=dict(l=10, r=10, t=20, b=40),
        plot_bgcolor="white"
    )

    st.plotly_chart(fig_timeline, use_container_width=True)

    # --- ALT AKSİYON BAR ---
    render_bottom_action_bar(df, target_device, ratio, total_working_sec, avg_daily_sec, key_suffix="bottom")
    
    # SAYFA SONU 50PX Padding
    st.markdown('<div class="bottom-spacer"></div>', unsafe_allow_html=True)