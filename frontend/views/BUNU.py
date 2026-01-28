import streamlit as st
import pandas as pd
import plotly.express as px
from backend.database import SessionLocal, get_all_devices_for_admin, get_user_devices
from backend.models import UtilizationEvent
from datetime import datetime, timedelta, date
import io

# --- 1. KURAL SETİ ---
RULES = [
    {
        "key": "good", 
        "min": 0, "max": 20, 
        "color": "#00C853", "label": "İdeal Çalışma (0-20s)", 
        "desc": "Verimli kullanım.", "type": "work"
    },
    {
        "key": "risk", 
        "min": 21, "max": 40, 
        "color": "#FFAB00", "label": "Riskli Çalışma (21-40s)", 
        "desc": "Riskli uzunlukta çalışma. Uç ısınabilir.", "type": "work"
    },
    {
        "key": "mushroom", 
        "min": 41, "max": 60, 
        "color": "#D50000", "label": "Uç Şişirme Riski (41-60s)", 
        "desc": "Kritik seviye!", "type": "bad_usage"
    },
    {
        "key": "operator_error", 
        "min": 61, "max": 180, 
        "color": "#AA00FF", "label": "Operatör Hatası (61-180s)", 
        "desc": "Kırıcıyı kanırtma/zorlama.", "type": "bad_usage"
    },
    {
        "key": "transport", 
        "min": 181, "max": 99999999, 
        "color": "#212121", "label": "Nakliye (>180s)", 
        "desc": "Cihaz vuruş yapmıyor, taşınıyor.", "type": "transport"
    }
]

def get_category_info(duration_sec):
    """Süreye göre hangi kategoriye girdiğini bulur."""
    for rule in RULES:
        if rule["min"] <= duration_sec <= rule["max"]:
            return rule
    # Hiçbir kurala uymuyorsa (örn: negatif süre) en güvenli olan 'Good' dönelim.
    return RULES[0]

def format_duration_tr(seconds):
    """Saniyeyi 'X sa Y dk' formatına çevirir."""
    if not seconds:
        return "0 sa 0 dk"
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    return f"{hours} sa {minutes} dk"

def load_view(user):
    # --- CSS ---
    st.markdown("""
        <style>
        .block-container { padding-top: 1rem !important; margin-top: 0rem !important; }
        .stMetric { background-color: #f9f9f9; border: 1px solid #ddd; padding: 10px; border-radius: 5px; }
        
        /* Ortalanmış Uyarı Mesajları */
        .center-message {
            display: flex;
            justify-content: center;
            align-items: center;
            height: 300px;
            border: 2px dashed #ddd;
            border-radius: 10px;
            background-color: #fdfdfd;
            text-align: center;
            font-weight: bold;
            font-size: 18px;
            color: #D32F2F;
        }
        
        /* Download Butonu (Solidus Mavisi) */
        div[data-testid="stDownloadButton"] > button {
            background-color: #225d97 !important;
            color: white !important;
            border: none !important;
            padding: 10px 20px !important;
        }
        div[data-testid="stDownloadButton"] > button:hover {
            background-color: #1a4b7c !important;
        }
        </style>
    """, unsafe_allow_html=True)
    
    st.subheader("🔨 Kırıcı Verimlilik Analizi")

    # --- CİHAZ VE FİLTRE ---
    devices = get_all_devices_for_admin() if user.role == 'Admin' else get_user_devices(user.id)
    if not devices:
        st.warning("Cihaz bulunamadı.")
        return

    c1, c2, c3, c4 = st.columns([2, 1.5, 1.2, 1.2])
    
    # Otomatik Seçim Mantığı
    default_index = 0 if len(devices) == 1 else None
    selected_dev_name = c1.selectbox("Makine Seçin:", [d.unit_name for d in devices], index=default_index, placeholder="Makine Seçiniz...")
    
    target_device = next((d for d in devices if d.unit_name == selected_dev_name), None)

    # Periyot Mantığı
    period = c2.selectbox("Periyot:", ["Bugün", "Son 1 Hafta", "Son 1 Ay", "Tarih Seç", "Tüm Zamanlar"], index=3) # Default Tarih Seç
    
    today = datetime.now().date()
    default_start = today - timedelta(days=7)
    
    if period == "Bugün": s, e = today, today
    elif period == "Son 1 Hafta": s, e = today - timedelta(days=7), today
    elif period == "Son 1 Ay": s, e = today - timedelta(days=30), today
    elif period == "Tüm Zamanlar": s, e = date(2020, 1, 1), today
    else:
        s = c3.date_input("Başlangıç:", default_start)
        e = c4.date_input("Bitiş:", today)

    if e < s:
        st.error("⚠️ Bitiş tarihi başlangıçtan küçük olamaz.")
        render_legend()
        return

    # --- DURUM 1: Makine Seçili Değilse ---
    if not target_device:
        st.markdown('<div class="center-message">⚠️ Kullanım bilgilerinizi görüntülemek için makine seçiminizi yapın</div>', unsafe_allow_html=True)
        render_legend()
        return

    # --- DURUM 2: Veri Çekme ---
    with st.spinner(f"📡 {target_device.unit_name} verileri analiz ediliyor..."):
        db = SessionLocal()
        query = db.query(UtilizationEvent).filter(
            UtilizationEvent.device_id == target_device.device_id,
            UtilizationEvent.start_time >= s,
            UtilizationEvent.start_time <= (e + timedelta(days=1))
        )
        all_logs = query.order_by(UtilizationEvent.start_time.asc()).all()
        db.close()

    if not all_logs:
        st.markdown(f'<div class="center-message" style="color:#555">📅 {s.strftime("%d.%m.%Y")} - {e.strftime("%d.%m.%Y")} aralığında veri bulunamadı.</div>', unsafe_allow_html=True)
        render_legend()
        return

    # --- DURUM 3: Veri İşleme (Hesaplamalar) ---
    data = []
    
    # Metrik Hesapları İçin Değişkenler
    total_working_sec = 0     # İdeal + Riskli + Mushroom + Operator Error
    total_transport_sec = 0   # Sadece Transport (>180s)
    
    sum_ideal_risk = 0        # (İdeal + Riskli) toplamı -> Oran hesabı için
    
    for l in all_logs:
        dur = l.duration_sec if l.duration_sec else 0
        info = get_category_info(dur)
        
        if info["key"] == "transport":
            # Nakliye ise SADECE nakliye toplamına ekle, çalışma süresine ekleme
            total_transport_sec += dur
        else:
            # Nakliye değilse bu bir Çalışma süresidir
            total_working_sec += dur
            
            # Hatalı Kullanım Oranı formülü payı: (İdeal + Riskli)
            if info["key"] in ["good", "risk"]:
                sum_ideal_risk += dur

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
    st.markdown(f"**⏱️ Operasyon Zaman Çizelgesi**")
    
    category_order = [r["label"] for r in RULES]
    # Renkleri sabitle
    color_map_fixed = {r["label"]: r["color"] for r in RULES}
    
    fig = px.timeline(
        df, 
        x_start="Başlangıç", 
        x_end="Bitiş", 
        y="Görünen Kategori", 
        color="Görünen Kategori",
        color_discrete_map=color_map_fixed,
        category_orders={"Görünen Kategori": category_order},
        height=350
    )
    fig.update_layout(margin=dict(l=0, r=0, t=10, b=10), showlegend=False)
    fig.update_yaxes(title="")
    st.plotly_chart(fig, use_container_width=True)

    # --- KARTLAR (METRİKLER) ---
    m1, m2, m3, m4 = st.columns(4)
    
    # 1. Toplam Çalışma (Nakliye Hariç)
    m1.metric("Toplam Çalışma", format_duration_tr(total_working_sec))
    
    # 2. Alınan Sinyal (Eski adı Olay Sayısı)
    m2.metric("Alınan Sinyal", f"{len(df)} Adet")
    
    # 3. Hatalı Kullanım Oranı (İstenen Formül: (İdeal + Riskli) / Toplam Çalışma)
    if total_working_sec > 0:
        ratio = (sum_ideal_risk / total_working_sec) * 100
    else:
        ratio = 0.0
        
    m3.metric("Hatalı Kullanım Oranı", f"%{ratio:.1f}", delta="İyi" if ratio > 80 else "Kötü")
    
    # 4. Toplam Nakliye
    m4.metric("Toplam Nakliye", format_duration_tr(total_transport_sec))

    # --- EXPORT BUTONU (ORTALI VE İÇERİK GENİŞLİĞİNDE) ---
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
    
    # Butonu ortalamak için kolonları ayarlıyoruz
    b1, b2, b3 = st.columns([5, 2, 5]) 
    with b2:
        # use_container_width=False yaparak butonu metin genişliğine çekiyoruz
        st.download_button(
            label="📥 Operasyon Detaylarını Excel Olarak İndir",
            data=excel_data,
            file_name=f"SolidTrack_Analiz_{target_device.device_id}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=False 
        )

    # --- REFERANS TABLO ---
    render_legend()

def render_legend():
    """Referans tablosunu çizen fonksiyon"""
    st.markdown("### 🗺️ Durum Referans Tablosu")
    cols = st.columns(len(RULES))
    for i, rule in enumerate(RULES):
        with cols[i]:
            st.markdown(f"""
                <div style="border-left: 6px solid {rule['color']}; padding: 8px; background-color: #f9f9f9; border-radius: 4px; min-height: 110px;">
                    <strong style="color: #333; font-size: 13px;">{rule['label']}</strong><br>
                    <span style="color: #666; font-size: 11px; line-height: 1.2;">{rule['desc']}</span>
                </div>
            """, unsafe_allow_html=True)