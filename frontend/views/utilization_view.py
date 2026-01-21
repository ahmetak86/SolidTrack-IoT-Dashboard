import streamlit as st
import pandas as pd
import plotly.express as px
from backend.database import SessionLocal, get_all_devices_for_admin, get_user_devices
from backend.models import UtilizationEvent
from datetime import datetime, timedelta, date
import io

# --- 1. KULLANICI TANIMLI RENK VE KURAL SETİ ---
RULES = [
    {
        "key": "breaker tool good", 
        "max_sec": 20, 
        "color": "#00C853", # Yeşil
        "label": "İdeal Çalışma (0-20s)", 
        "desc": "İdeal çalışma. Verimli kullanım."
    },
    {
        "key": "breaker tool in danger", 
        "max_sec": 40, 
        "color": "#FFAB00", # Turuncu
        "label": "Riskli Çalışma (21-40s)", 
        "desc": "Riskli uzunlukta çalışma. Uç ısınabilir."
    },
    {
        "key": "mushrooming", 
        "max_sec": 60, 
        "color": "#D50000", # Kırmızı
        "label": "Uç Şişirme Riski (41-60s)", 
        "desc": "Kritik seviye! Uçta deformasyon riski."
    },
    {
        "key": "mushrooming, training needed", 
        "max_sec": 180, 
        "color": "#AA00FF", # Mor
        "label": "Operatör Hatası (61-180s)", 
        "desc": "Operatör hatası! Kırıcıyı kanırtıyor veya durmadan çalıştırıyor."
    },
    {
        "key": "transport", 
        "max_sec": 999999, # Sonsuz
        "color": "#212121", # Siyah
        "label": "Nakliye (>180s)", 
        "desc": "Nakliye ediliyor veya cihaz boşta hareket halinde."
    }
]

def get_category_info(duration_sec, raw_category=None):
    """Verilen süreye göre kural setinden uygun rengi ve etiketi bulur."""
    for rule in RULES:
        if duration_sec <= rule["max_sec"]:
            return rule
    return RULES[-1]

def load_view(user):
    # --- CSS: UI DÜZENLEMELERİ VE BUTON RENKLERİ ---
    st.markdown("""
        <style>
        .block-container { padding-top: 1rem !important; margin-top: 0rem !important; }
        .stMetric { background-color: #f9f9f9; border: 1px solid #ddd; padding: 10px; border-radius: 5px; }
        
        /* Ortalanmış Uyarı Mesajları için Stil */
        .center-message {
            display: flex;
            justify-content: center;
            align-items: center;
            height: 300px; /* Grafik yüksekliği kadar */
            border: 2px dashed #ddd;
            border-radius: 10px;
            background-color: #fdfdfd;
            text-align: center;
            font-weight: bold;
            font-size: 18px;
        }
        
        /* Download Butonunu Solidus Mavisi Yapma */
        div[data-testid="stDownloadButton"] > button {
            background-color: #225d97 !important;
            color: white !important;
            border: none !important;
        }
        div[data-testid="stDownloadButton"] > button:hover {
            background-color: #1a4b7c !important;
            color: white !important;
        }
        </style>
    """, unsafe_allow_html=True)
    
    st.subheader("🔨 Kırıcı Verimlilik Analizi")

    # --- CİHAZ LİSTESİ ---
    devices = get_all_devices_for_admin() if user.role == 'Admin' else get_user_devices(user.id)
    if not devices:
        st.warning("Cihaz bulunamadı.")
        return

    # --- FİLTRE PANELİ ---
    c1, c2, c3, c4 = st.columns([2, 1.5, 1.2, 1.2])
    
    # 1. MAKİNE SEÇİM MANTIĞI
    # Tek makine varsa otomatik seç (index=0), çoksa boş gelsin (index=None)
    default_dev_index = 0 if len(devices) == 1 else None
    
    selected_dev_name = c1.selectbox(
        "Makine Seçin:", 
        [d.unit_name for d in devices], 
        index=default_dev_index,
        placeholder="Makine Seçiniz..."
    )
    
    # Seçilen makine objesini bul
    target_device = None
    if selected_dev_name:
        target_device = next((d for d in devices if d.unit_name == selected_dev_name), None)

    # 2. PERİYOT VE TARİH MANTIĞI
    # Default: "Tarih Seç" (Listede 3. sırada: 0:Bugün, 1:Hafta, 2:Ay, 3:Tarih Seç, 4:Tüm)
    period = c2.selectbox("Periyot:", ["Bugün", "Son 1 Hafta", "Son 1 Ay", "Tarih Seç", "Tüm Zamanlar"], index=3)
    
    today = datetime.now().date()
    
    # Default Tarihler (Son 1 Hafta)
    default_start = today - timedelta(days=7)
    default_end = today

    if period == "Bugün": s, e = today, today
    elif period == "Son 1 Hafta": s, e = today - timedelta(days=7), today
    elif period == "Son 1 Ay": s, e = today - timedelta(days=30), today
    elif period == "Tüm Zamanlar": s, e = date(2020, 1, 1), today # Temsili milat
    else:
        # Tarih Seç Modu
        s = c3.date_input("Başlangıç:", default_start)
        e = c4.date_input("Bitiş:", default_end)

    # 3. TARİH VALIDASYONU
    if e < s:
        st.error("⚠️ Hata: Bitiş tarihi başlangıç tarihinden küçük olamaz!")
        # Legend'i yine de gösterip çıkalım
        render_legend()
        return

    # --- ANA AKIŞ KONTROLÜ ---

    # DURUM 1: Makine Seçilmemişse
    if not target_device:
        st.markdown("""
            <div class="center-message" style="color: #D32F2F;">
                ⚠️ Kullanım bilgilerinizi görüntülemek için makine seçiminizi yapın
            </div>
        """, unsafe_allow_html=True)
        render_legend()
        return

    # DURUM 2: Makine Seçili -> Veri Çekme (Spinner ile)
    with st.spinner(f"📡 {target_device.unit_name} verileri analiz ediliyor..."):
        db = SessionLocal()
        query = db.query(UtilizationEvent).filter(
            UtilizationEvent.device_id == target_device.device_id,
            UtilizationEvent.start_time >= s,
            UtilizationEvent.start_time <= (e + timedelta(days=1))
        )
        all_logs = query.order_by(UtilizationEvent.start_time.asc()).all()
        db.close()

    # DURUM 3: Veri Yoksa
    if not all_logs:
        st.markdown(f"""
            <div class="center-message" style="color: #555;">
                📅 {s.strftime('%d.%m.%Y')} - {e.strftime('%d.%m.%Y')} tarih aralığında veri bulunamadı.
            </div>
        """, unsafe_allow_html=True)
        render_legend()
        return

    # DURUM 4: Veri Var -> İşle ve Göster
    data = []
    for l in all_logs:
        dur = l.duration_sec if l.duration_sec else 0
        info = get_category_info(dur, l.category)
        
        data.append({
            "Başlangıç": l.start_time + timedelta(hours=3),
            "Bitiş": (l.end_time or l.start_time) + timedelta(hours=3),
            "Görünen Kategori": info["label"],
            "Ham Kategori": l.category,
            "Süre (sn)": dur,
            "Renk": info["color"]
        })
    
    df = pd.DataFrame(data)

    # --- GRAFİK ---
    st.markdown(f"**⏱️ Operasyon Zaman Çizelgesi** ({len(df)} Kayıt)")
    
    category_order = [r["label"] for r in RULES]
    
    fig = px.timeline(
        df, 
        x_start="Başlangıç", 
        x_end="Bitiş", 
        y="Görünen Kategori", 
        color="Görünen Kategori",
        color_discrete_map={row["Görünen Kategori"]: row["Renk"] for _, row in df.iterrows()},
        category_orders={"Görünen Kategori": category_order},
        height=350
    )
    fig.update_layout(margin=dict(l=0, r=0, t=10, b=10), showlegend=False)
    fig.update_yaxes(title="")
    st.plotly_chart(fig, use_container_width=True)

    # --- METRİKLER ---
    m1, m2, m3 = st.columns(3)
    total_h = df["Süre (sn)"].sum() / 3600
    m1.metric("Toplam Çalışma", f"{total_h:.1f} Saat")
    m2.metric("Olay Sayısı", f"{len(df)} Adet")
    
    bad_usage_sec = df[df["Süre (sn)"] > 40]["Süre (sn)"].sum()
    ratio = (bad_usage_sec / df["Süre (sn)"].sum() * 100) if not df.empty else 0
    m3.metric("Hatalı Kullanım Oranı", f"%{ratio:.1f}", delta="-Yüksek" if ratio > 10 else "Normal", delta_color="inverse")

    # --- EXPORT ---
    st.markdown("---")
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df_export = df[["Başlangıç", "Bitiş", "Görünen Kategori", "Süre (sn)"]].copy()
        df_export.columns = ["Başlangıç Zamanı", "Bitiş Zamanı", "Durum", "Süre (Saniye)"]
        df_export["Başlangıç Zamanı"] = df_export["Başlangıç Zamanı"].dt.strftime('%d.%m.%Y %H:%M:%S')
        df_export["Bitiş Zamanı"] = df_export["Bitiş Zamanı"].dt.strftime('%d.%m.%Y %H:%M:%S')
        df_export.to_excel(writer, index=False, sheet_name='Verimlilik_Raporu')
        worksheet = writer.sheets['Verimlilik_Raporu']
        worksheet.set_column('A:C', 25)
    
    excel_data = output.getvalue()
    
    st.download_button(
        label="📥 Detaylı Raporu İndir (.xlsx)",
        data=excel_data,
        file_name=f"SolidTrack_Analiz_{target_device.device_id}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True
    )

    # --- REFERANS TABLO (HER ZAMAN GÖSTERİLİR) ---
    render_legend()

def render_legend():
    """Referans tablosunu çizen yardımcı fonksiyon"""
    st.markdown("---")
    st.markdown("### 🗺️ Durum Referans Tablosu")
    cols = st.columns(len(RULES))
    for i, rule in enumerate(RULES):
        with cols[i]:
            st.markdown(f"""
                <div style="border-left: 6px solid {rule['color']}; padding: 8px; background-color: #f9f9f9; border-radius: 4px; min-height: 100px;">
                    <strong style="color: #333; font-size: 13px;">{rule['label']}</strong><br>
                    <span style="color: #666; font-size: 11px; line-height: 1.2;">{rule['desc']}</span>
                </div>
            """, unsafe_allow_html=True)