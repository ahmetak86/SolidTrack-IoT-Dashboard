# frontend/views/alarms.py (V7 - FINAL MASTER)
import streamlit as st
import pandas as pd
import io
from datetime import datetime, timedelta
from backend.database import SessionLocal, get_user_devices
from backend.models import Alarm, Device

# --- SABİT LİSTELER & İKONLAR ---
SEVERITY_LEVELS = ["Tümü", "Critical", "Warning", "Info"]
STATUS_OPTIONS = ["Tümü", "Görülmedi (Active)", "Görüldü (Resolved)"]
OPERATOR_OPTIONS = ["Tümü", "Ahmet Yılmaz", "Mehmet Demir", "Ayşe Kaya"]

ALARM_TYPES = [
    "Tümü",
    "Düşük Pil (Low Battery)",
    "Aşırı Hız (Overspeed)",
    "Hareketsizlik (Inactivity)",
    "Mesai Dışı Çalışma (After Hours)",
    "Bakım (Maintenance)", 
    "Geofence İhlali (Exit)",
    "Geofence Giriş (Entry)",
    "Hatalı Kullanım (Misuse)",
    "Haberleşme Yok (No Comm)",
    "Hareket (Motion)",
    "Darbe (Shock)"
]

# İkon ve Renk Haritası
ICON_MAP = {
    "Critical": "🔴",
    "Warning": "🟠",
    "Info": "🔵"
}

SEVERITY_TR_MAP = {
    "Critical": "KRİTİK",
    "Warning": "UYARI",
    "Info": "BİLGİ"
}

# --- YARDIMCI FONKSİYONLAR ---
def get_user_alarms_query(user_id, session):
    """Kullanıcının cihazlarına ait alarmları çeker"""
    devices = get_user_devices(user_id)
    device_ids = [d.device_id for d in devices]
    if not device_ids:
        return None, {}
    
    device_map = {d.device_id: d.unit_name for d in devices}
    return session.query(Alarm).filter(Alarm.device_id.in_(device_ids)), device_map

def apply_filters(df, f_device, f_severity, f_type, f_operator, f_status, f_date_start, f_date_end, device_map):
    if df.empty: return df

    # 1. Cihaz
    if f_device != "Tümü":
        df['Cihaz İsmi'] = df['device_id'].map(device_map).fillna(df['device_id'])
        df = df[df['Cihaz İsmi'] == f_device]
    else:
        df['Cihaz İsmi'] = df['device_id'].map(device_map).fillna(df['device_id'])

    # 2. Önem
    if f_severity != "Tümü":
        df = df[df['severity'] == f_severity]

    # 3. Tip
    if f_type != "Tümü":
        if f_type == "Bakım (Maintenance)":
            df = df[df['alarm_type'] == 'Maintenance']
        else:
            type_map = {
                "Düşük Pil (Low Battery)": "LowBattery",
                "Aşırı Hız (Overspeed)": "Overspeed",
                "Hareketsizlik (Inactivity)": "Inactivity",
                "Mesai Dışı Çalışma (After Hours)": "AfterHours",
                "Geofence İhlali (Exit)": "GeofenceExit",
                "Geofence Giriş (Entry)": "GeofenceEntry",
                "Hatalı Kullanım (Misuse)": "Misuse",
                "Haberleşme Yok (No Comm)": "NoCommunication",
                "Hareket (Motion)": "Motion",
                "Darbe (Shock)": "Shock"
            }
            db_type = type_map.get(f_type, "")
            if db_type:
                df = df[df['alarm_type'] == db_type]

    # 4. Operatör
    if f_operator != "Tümü":
        if 'operator' in df.columns:
            df = df[df['operator'] == f_operator]

    # 5. Durum
    if f_status != "Tümü":
        if f_status == "Görülmedi (Active)":
            df = df[df['status'] == 'Active']
        elif f_status == "Görüldü (Resolved)":
            df = df[df['status'] == 'Resolved']

    # 6. Tarih
    if f_date_start and f_date_end:
        if not pd.api.types.is_datetime64_any_dtype(df['start_time']):
            df['start_time'] = pd.to_datetime(df['start_time'])
        df = df[(df['start_time'].dt.date >= f_date_start) & (df['start_time'].dt.date <= f_date_end)]

    return df

def resolve_alarm_db(alarm_id):
    """Alarmı veritabanında 'Resolved' olarak günceller"""
    db = SessionLocal()
    try:
        alarm = db.query(Alarm).filter(Alarm.id == alarm_id).first()
        if alarm:
            alarm.status = 'Resolved'
            db.commit()
            return True
    except Exception as e:
        print(f"Hata: {e}")
        return False
    finally:
        db.close()

def load_view(user):
    st.markdown("## 🚨 Alarm Merkezi")
    
    # --- SESSION STATE (Filtre Hafızası) ---
    if "f_severity" not in st.session_state: st.session_state.f_severity = "Tümü"
    if "f_status" not in st.session_state: st.session_state.f_status = "Görülmedi (Active)" # Default Aktifler gelsin

    db = SessionLocal()
    query, device_map = get_user_alarms_query(user.id, db)
    
    if not query:
        st.info("Hesabınıza tanımlı cihaz bulunamadı.")
        db.close()
        return

    all_alarms = query.order_by(Alarm.start_time.desc()).all()
    db.close()

    if not all_alarms:
        st.info("Kayıtlı alarm bulunmuyor. Sistem stabil.")
        return

    # DF Hazırlığı
    data = []
    for a in all_alarms:
        data.append({
            "id": a.id,
            "device_id": a.device_id,
            "alarm_type": a.alarm_type,
            "severity": a.severity,
            "status": a.status,
            "start_time": a.start_time,
            "description": a.description,
            "operator": a.operator if hasattr(a, "operator") else None
        })
    df_master = pd.DataFrame(data)

    # --- METRİKLER ---
    # Toplam Aktif = Critical + Warning + Info (Status='Active')
    active_df = df_master[df_master['status'] == 'Active']
    total_active = len(active_df)
    
    crit_count = len(active_df[active_df['severity'] == 'Critical'])
    warn_count = len(active_df[active_df['severity'] == 'Warning'])
    info_count = len(active_df[active_df['severity'] == 'Info']) # Eksik olan sayı buydu

    # Buton Stili (Kart Görünümü)
    st.markdown("""
    <style>
    div[data-testid="column"] button {
        height: 80px; width: 100%; border-radius: 10px; border: 1px solid #ddd;
    }
    .total-record-box {
        border: 2px solid #4CAF50; border-radius: 10px; padding: 15px;
        text-align: center; font-weight: bold; background-color: #f9f9f9; color: #333;
    }
    </style>
    """, unsafe_allow_html=True)

    m1, m2, m3, m4 = st.columns(4)
    
    # Butonlar: Tıklayınca filtreyi günceller ve rerun yapar
    if m1.button(f"🚨 Toplam Aktif\n{total_active}", use_container_width=True):
        st.session_state.f_severity = "Tümü"
        st.session_state.f_status = "Görülmedi (Active)"
        st.rerun()

    if m2.button(f"🔴 Kritik\n{crit_count}", use_container_width=True):
        st.session_state.f_severity = "Critical"
        st.session_state.f_status = "Görülmedi (Active)"
        st.rerun()

    if m3.button(f"🟠 Uyarı\n{warn_count}", use_container_width=True):
        st.session_state.f_severity = "Warning"
        st.session_state.f_status = "Görülmedi (Active)"
        st.rerun()

    # Sağdaki Toplam Kayıt Kutusu (Custom HTML)
    with m4:
        st.markdown(f"""
        <div class="total-record-box" style="display: flex; align-items: center; justify-content: center; gap: 10px; height: 40px;">
            <span style="font-size:16px;">✅ Toplam Kayıt:</span>
            <span style="font-size:22px; font-weight: bold;">{len(df_master)}</span>
        </div>
        """, unsafe_allow_html=True)
    
    st.divider()

    # --- FİLTRELER ---
    with st.container(border=True):
        st.markdown("### 🔍 Filtreleme Seçenekleri")
        f1, f2, f3, f4, f5, f6 = st.columns(6)
        
        # 1. Cihaz
        device_names = ["Tümü"] + sorted(list(device_map.values()))
        sel_device = f1.selectbox("Cihaz", device_names, key="filt_dev")
        
        # 2. Önem (Session State Bağlantılı)
        try: sev_idx = SEVERITY_LEVELS.index(st.session_state.f_severity)
        except: sev_idx = 0
        sel_severity = f2.selectbox("Önem", SEVERITY_LEVELS, index=sev_idx, key="f_severity")
        
        # 3. Tip
        sel_type = f3.selectbox("Alarm Tipi", ALARM_TYPES, key="filt_type")
        
        # 4. Operatör
        sel_operator = f4.selectbox("Operatör", OPERATOR_OPTIONS, key="filt_op")

        # 5. Durum (Session State Bağlantılı)
        try: stat_idx = STATUS_OPTIONS.index(st.session_state.f_status)
        except: stat_idx = 0
        sel_status = f5.selectbox("Durum", STATUS_OPTIONS, index=stat_idx, key="f_status")
        
        # 6. Tarih
        today = datetime.now().date()
        sel_dates = f6.date_input("Tarih Aralığı", (today - timedelta(days=7), today), format="DD/MM/YYYY", key="filt_date")
        start_d, end_d = sel_dates if isinstance(sel_dates, tuple) and len(sel_dates) == 2 else (None, None)

    # Filtre Uygula
    df_filtered = apply_filters(
        df_master, sel_device, sel_severity, sel_type, sel_operator, sel_status, start_d, end_d, device_map
    )

    # --- TABLAR ---
    tab_active, tab_history = st.tabs(["🔥 Aktif Alarmlar (Action)", "📜 Alarm Geçmişi & Rapor"])

    # 1. TAB: AKTİF ALARMLAR
    with tab_active:
        st.markdown("### 🔥 Müdahale Bekleyen Alarmlar")
        df_active = df_filtered[df_filtered['status'] == 'Active']
        
        if df_active.empty:
            st.success("Harika! Şu an aktif bir alarm yok.")
        else:
            for _, row in df_active.iterrows():
                # İkon ve Başlık
                sev_code = row['severity']
                icon = ICON_MAP.get(sev_code, "⚪")
                tr_sev = SEVERITY_TR_MAP.get(sev_code, sev_code)
                
                # Cihaz Adını haritadan veya direkt ID'den al
                dev_name = device_map.get(row['device_id'], row['device_id'])
                
                title = f"{icon} [{tr_sev}] - {dev_name} - {row['alarm_type']}"
                
                # Akordeon
                with st.expander(title, expanded=False):
                    # İçeriği 2 kolona böl: Detaylar | Buton
                    c_det, c_btn = st.columns([3, 1])
                    
                    with c_det:
                        # TR Saati Ayarı (UTC+3)
                        tr_time = row['start_time'] + timedelta(hours=3)
                        
                        # İstenilen Format
                        st.write(f"**📝 Açıklama:** {row['description']}")
                        
                        g1, g2 = st.columns(2)
                        with g1:
                            st.write(f"**🕒 Tarih ve Saat (TR):** {tr_time.strftime('%d.%m.%Y %H:%M')}")
                            st.write(f"**🆔 Alarm ID:** #{row['id']}")
                            st.write(f"**🚜 Cihaz:** {dev_name}")
                        with g2:
                            st.write(f"**⚡ Alarm Tipi:** {row['alarm_type']}")
                            st.write(f"**🚨 Alarm Önemi:** {tr_sev}")
                            st.write(f"**👷‍♂️ Operatör:** {row['operator'] if row['operator'] else '-'}")

                    with c_btn:
                        st.write("") # Boşluk
                        st.write("") 
                        # Butona basınca DB Update + Rerun
                        if st.button("✅ Çözüldü Olarak İşaretle", key=f"ack_{row['id']}", type="primary"):
                            if resolve_alarm_db(row['id']):
                                st.toast(f"Alarm #{row['id']} çözüldü! Listeden kaldırılıyor...")
                                import time
                                time.sleep(0.5)
                                st.rerun()
                            else:
                                st.error("Veritabanı hatası!")

    # 2. TAB: GEÇMİŞ & RAPOR
    with tab_history:
        st.markdown("### 📜 Tüm Alarm Kayıtları")
        if df_filtered.empty:
            st.info("Kayıt bulunamadı.")
        else:
            # Tablo verisini hazırla
            display_df = df_filtered.copy()
            
            # Tarihi TR Saatine Çevir
            display_df['start_time'] = display_df['start_time'] + timedelta(hours=3)
            
            # Cihaz İsmi Kolonu
            display_df['Cihaz'] = display_df['device_id'].map(device_map).fillna(display_df['device_id'])
            
            # Önem Türkçeleştirme
            display_df['severity'] = display_df['severity'].map(SEVERITY_TR_MAP).fillna(display_df['severity'])

            # Kolon Seçimi ve İsimlendirme
            final_cols = ['start_time', 'Cihaz', 'alarm_type', 'severity', 'status', 'description']
            col_names = ["Tarih (TR)", "Cihaz", "Alarm Tipi", "Alarm Önemi", "Durum", "Açıklama"]
            
            if 'operator' in display_df.columns:
                final_cols.append('operator')
                col_names.append('Operatör')
                
            display_df = display_df[final_cols]
            display_df.columns = col_names
            
            # Renklendirme
            def color_row(row):
                return ['background-color: #ffe6e6' if row['Durum'] == 'Active' else 'background-color: #e6fffa'] * len(row)

            st.dataframe(
                display_df.style.apply(color_row, axis=1),
                use_container_width=True,
                hide_index=True
            )
            
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                display_df.to_excel(writer, index=False, sheet_name='Alarmlar')
            
            # İndirme Butonu
            st.download_button(
                label="📥 Excel (.xlsx) Olarak İndir",
                data=buffer.getvalue(),
                file_name=f"Alarm_Raporu_{datetime.now().strftime('%d_%m_%Y')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )