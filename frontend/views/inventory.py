import streamlit as st
import locale
import sys
import os
import urllib.parse
from datetime import datetime, timedelta, time

# Yolları ekle
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from backend.database import (
    get_user_devices, create_share_link, revoke_share_link, 
    get_device_share_links, get_device_telemetry, 
    get_device_documents, upload_document_to_db, delete_document,
    get_user_storage_usage, send_admin_notification_email,
    # YENİ EKLENENLER
    get_user_operators, create_operator, 
    get_device_shifts, create_device_shift, delete_device_shift,
    add_service_record, verify_admin_password
)
from frontend.utils import format_date_for_ui

# Dil Ayarı
try: locale.setlocale(locale.LC_ALL, 'tr_TR.UTF-8')
except: pass

def load_view(user):
    # --- CSS: KOMPAKT TASARIM ---
    st.markdown("""
        <style>
        .block-container { padding-top: 1rem !important; padding-bottom: 2rem !important; }
        .streamlit-expanderHeader { padding-top: 0.5rem !important; padding-bottom: 0.5rem !important; min-height: 0px !important; }
        .streamlit-expanderContent { padding-top: 0.5rem !important; padding-bottom: 0.5rem !important; }
        h1, h2, h3 { margin-top: 0px !important; margin-bottom: 0.5rem !important; padding-top: 0px !important; }
        hr { margin-top: 0.5em !important; margin-bottom: 0.5em !important; }
        .stTextInput, .stSelectbox { margin-bottom: 0.5rem !important; }
        
        /* Metric Kutuları İçin */
        .metric-box { border: 1px solid #ddd; padding: 10px; border-radius: 8px; text-align: center; background: white; box-shadow: 0 1px 3px rgba(0,0,0,0.1); margin-bottom: 10px; }
        
        [data-testid="stCodeBlock"] button {
            color: #d63031 !important;
            border-color: rgba(214, 48, 49, 0.3) !important;
            background-color: rgba(214, 48, 49, 0.05) !important;
            transition: all 0.3s ease;
        }
        [data-testid="stCodeBlock"] button:hover {
            background-color: #d63031 !important;
            color: white !important;
        }
        </style>
    """, unsafe_allow_html=True)

    st.subheader("🚜 Makine Parkı ve Dijital Kütüphane")
    
    devices = get_user_devices(user.id)
    if not devices:
        st.warning("Görüntülenecek cihaz bulunamadı.")
        return

    # --- KOTA BİLGİSİ ---
    used_mb = get_user_storage_usage(user.id)
    limit_mb = 100.0
    percent = min(used_mb / limit_mb, 1.0)
    
    col_stat1, col_stat2 = st.columns([3, 1])
    with col_stat1:
        c1, c2, c3 = st.columns(3)
        c1.caption(f"**Toplam:** {len(devices)}")
        c2.caption(f"**SolidTrack:** {sum(1 for d in devices if not d.is_virtual)}")
        c3.caption(f"**Makine:** {sum(1 for d in devices if d.is_virtual)}")
    
    with col_stat2:
        st.caption(f"Depolama: {used_mb:.1f} / {limit_mb} MB")
        st.progress(percent)

    st.markdown("---")

    # --- CİHAZ LİSTESİ ---
    for index, d in enumerate(devices):
        icon = "📂" if d.is_virtual else "📡"
        label = f"{icon} **{d.unit_name}** | {d.asset_model}"
        is_expanded = True if index < 1 else False
        
        with st.expander(label, expanded=is_expanded):
            col_info, col_ops = st.columns([1.2, 2.3])
            
            # SOL KOLON: BİLGİ
            with col_info:
                st.caption(f"ID: {d.device_id}")
                if d.is_virtual:
                    st.warning("SolidTrack takip cihazı yoktur.")
                    st.caption("Sadece doküman yönetimi içindir.")
                else:
                    status_icon = "🟢" if d.is_active else "🔴"
                    st.write(f"**Durum:** {status_icon}")
                    
                    last_log = get_device_telemetry(d.device_id, limit=1)
                    ts = format_date_for_ui(last_log[0].timestamp, user.timezone) if last_log else "Sinyal Yok"
                    st.write(f"**Son Sinyal:** {ts}")
                    
                    st.write("")
                    if st.button("🔍 Analiz", key=f"btn_anl_{d.device_id}", use_container_width=True):
                        st.session_state["target_analysis_device"] = d.unit_name
                        st.session_state["menu_selection"] = "🔍 Teknik Analiz"
                        st.rerun()

            # SAĞ KOLON: İŞLEMLER (TABLAR)
            with col_ops:
                # Tab Başlıklarını Belirle
                tab_names = ["📂 Dosyalar", "📤 Yükle", "🔗 Paylaş", "👷 Vardiya", "🛠️ Bakım"]
                if d.is_virtual:
                    # Sanal cihazda Paylaşım ve Vardiya olmayabilir, ama Bakım olmalı (Makine bakımı)
                    tab_names = ["📂 Dosyalar", "📤 Yükle", "🛠️ Bakım"]
                
                tabs = st.tabs(tab_names)
                
                # --- TAB 1: DOSYALAR ---
                with tabs[0]:
                    docs = get_device_documents(d.device_id)
                    if docs:
                        for doc in docs:
                            c_icon, c_name, c_down, c_del = st.columns([0.1, 0.6, 0.15, 0.15])
                            
                            icon_map = {"Fatura": "💰", "Video": "🎬", "Kullanım Kılavuzu": "📖"}
                            f_icon = icon_map.get(doc.file_type, "📄")
                            
                            c_icon.write(f_icon)
                            c_name.caption(f"**{doc.file_name}**\n{doc.file_type} | {doc.upload_date.strftime('%d.%m.%y')}")
                            
                            if os.path.exists(doc.file_path):
                                with open(doc.file_path, "rb") as f:
                                    c_down.download_button("⬇️", f, file_name=doc.file_name, key=f"dl_{doc.id}")
                            else:
                                c_down.error("X")
                            
                            if doc.uploaded_by == user.username:
                                if c_del.button("🗑️", key=f"del_usr_{doc.id}", help="Dosyayı Sil"):
                                    delete_document(doc.id)
                                    st.rerun()
                            st.divider()
                    else:
                        st.caption("Henüz yüklenmiş belge yok.")

                # --- TAB 2: YÜKLEME ---
                with tabs[1]:
                    if used_mb >= limit_mb:
                        st.error("❌ Depolama kotanız doldu.")
                    else:
                        with st.form(key=f"user_up_{d.device_id}", clear_on_submit=True):
                            st.caption("Maksimum: 10MB")
                            u_file = st.file_uploader("Dosya Seç", type=['jpg','png','pdf','mp4','mov'], key=f"uf_{d.device_id}")
                            u_note = st.text_area("Not (Opsiyonel)", placeholder="Örn: Parça kırıldı.", height=60)
                            u_type = st.selectbox("Tür", ["Hasar Raporu", "Video", "Resim", "Diğer"], key=f"ut_{d.device_id}")
                            
                            if st.form_submit_button("Gönder"):
                                if u_file:
                                    if u_file.size > 10 * 1024 * 1024:
                                        st.error("❌ Dosya 10MB'dan büyük olamaz.")
                                    elif (used_mb + (u_file.size/(1024*1024))) > limit_mb:
                                        st.error("❌ Kota aşımı.")
                                    else:
                                        success, msg = upload_document_to_db(d.device_id, u_file, u_type, user.username)
                                        if success:
                                            st.success("İletildi!")
                                            send_admin_notification_email(u_type, d.unit_name, user.full_name, u_note)
                                            st.rerun()
                                        else:
                                            st.error(msg)
                                else:
                                    st.warning("Dosya seçin.")

                # --- TAB 3: PAYLAŞIM MERKEZİ (SENİN V8 KODUNUN AYNISI) ---
                if not d.is_virtual:
                    with tabs[2]:
                        sub_tab_new, sub_tab_list = st.tabs(["➕ Yeni Link Oluştur", "📋 Aktif Paylaşımlar"])
                        
                        # YENİ LİNK OLUŞTURMA
                        with sub_tab_new:
                            link_state_key = f"new_link_{d.device_id}"
                            
                            with st.form(key=f"form_share_{d.device_id}", clear_on_submit=False):
                                col_note, col_date = st.columns([1.5, 1])
                                note_text = col_note.text_input("Kime Gönderilecek?", placeholder="Örn: Mehmet Bey", key=f"note_{d.device_id}")
                                tomorrow = datetime.now() + timedelta(days=1)
                                selected_date = col_date.date_input("Son Geçerlilik", value=tomorrow + timedelta(days=6), min_value=tomorrow, format="DD.MM.YYYY", key=f"date_{d.device_id}")
                                
                                if st.form_submit_button("Link Oluştur", use_container_width=True, type="primary"):
                                    if not note_text:
                                        st.error("⚠️ İsim giriniz.")
                                    else:
                                        expiry_dt = datetime.combine(selected_date, datetime.max.time())
                                        new_token = create_share_link(user.id, d.device_id, expiry_dt, note_text)
                                        st.session_state[link_state_key] = {
                                            "token": new_token, 
                                            "date": selected_date.strftime("%d.%m.%Y")
                                        }
                                        st.rerun()

                            # BAŞARILI LİNK GÖSTERİMİ
                            if link_state_key in st.session_state:
                                link_data = st.session_state[link_state_key]
                                base_url = "http://localhost:8501" # Canlıda domain
                                full_link = f"{base_url}/?token={link_data['token']}"
                                
                                st.markdown("""<div style="background-color:#d4edda; color:#155724; padding:10px; border-radius:5px; font-weight:bold; margin-top:10px;">✅ Link Hazır</div>""", unsafe_allow_html=True)
                                st.code(full_link, language="text")
                                st.caption(f"Link {link_data['date']} tarihine kadar geçerlidir.")
                                
                                # WhatsApp Butonu
                                msg_text = f"Merhaba, {d.unit_name} makinesini buradan izleyebilirsin: {full_link}"
                                encoded_msg = urllib.parse.quote(msg_text)
                                wa_url = f"https://wa.me/?text={encoded_msg}"
                                
                                st.markdown(f"""
                                    <a href="{wa_url}" target="_blank" style="text-decoration: none;">
                                        <div style="background-color: #25D366; color: white; padding: 10px; border-radius: 8px; text-align: center; font-weight: bold; margin-top: 5px; box-shadow: 0 2px 4px rgba(0,0,0,0.2);">
                                            📲 WhatsApp ile Gönder
                                        </div>
                                    </a>
                                """, unsafe_allow_html=True)
                                
                                st.write("")
                                # Kapat / Temizle Butonu
                                if st.button("Kapat / Yeni Link", key=f"cls_{d.device_id}", use_container_width=True):
                                    del st.session_state[link_state_key]
                                    st.rerun()

                        # AKTİF LİNKLER
                        with sub_tab_list:
                            active_links = get_device_share_links(d.device_id)
                            if active_links:
                                for link in active_links:
                                    with st.container():
                                        cl1, cl2, cl3 = st.columns([1.5, 2.2, 1.0])
                                        cl1.markdown(f"**{link.note}**")
                                        cl1.caption(f"Son: {link.expires_at.strftime('%d.%m.%Y')}")
                                        full_url = f"http://localhost:8501/?token={link.token}"
                                        with cl2: st.code(full_url, language="text")
                                        with cl3:
                                            if st.button("İptal Et", key=f"revoke_{link.token}", type="primary"):
                                                revoke_share_link(link.token)
                                                st.rerun()
                                        st.divider()
                            else:
                                st.info("Aktif paylaşım yok.")

                # --- TAB 4: VARDİYA & OPERATÖR (YENİ ÖZELLİK) ---
                if not d.is_virtual:
                    with tabs[3]:
                        st.caption("Cihazın çalışma saatlerini ve operatörlerini yönetin.")
                        
                        # A. OPERATÖR SEÇİMİ / EKLEME
                        operators = get_user_operators(user.id)
                        op_options = {op.full_name: op.id for op in operators}
                        op_options["-- Yeni Ekle --"] = 0
                        
                        col_op1, col_op2 = st.columns([2, 1])
                        sel_op_name = col_op1.selectbox("Operatör Havuzu", list(op_options.keys()), key=f"sl_op_{d.device_id}")
                        
                        # Yeni Operatör Ekleme Modu
                        if sel_op_name == "-- Yeni Ekle --":
                            with st.form(key=f"new_op_form_{d.device_id}"):
                                new_op_name = st.text_input("Ad Soyad")
                                new_op_phone = st.text_input("Telefon")
                                if st.form_submit_button("Kaydet"):
                                    ok, msg = create_operator(user.id, new_op_name, new_op_phone)
                                    if ok: st.success("Eklendi!"); st.rerun()
                                    else: st.error(msg)

                        st.divider()
                        
                        # B. VARDİYA LİSTESİ VE EKLEME
                        shifts = get_device_shifts(d.device_id)
                        
                        # Vardiya Kartları
                        if shifts:
                            for shift in shifts:
                                with st.container(border=True):
                                    sc1, sc2, sc3 = st.columns([2, 2, 1])
                                    sc1.write(f"**{shift.shift_name}**")
                                    sc1.caption(f"🕒 {shift.start_time} - {shift.end_time}")
                                    op_name = next((k for k, v in op_options.items() if v == shift.operator_id), "Atanmamış")
                                    sc2.caption(f"👷‍♂️ {op_name}")
                                    if sc3.button("Sil", key=f"del_sh_{shift.id}"):
                                        delete_device_shift(shift.id)
                                        st.rerun()
                        else:
                            st.info("Tanımlı vardiya yok.")

                        # Yeni Vardiya Ekle Butonu (Popover)
                        with st.popover("➕ Vardiya Ekle", use_container_width=True):
                            # HATAYI ÇÖZEN KISIM: key parametreleri eklendi
                            s_name = st.text_input("Vardiya Adı", "Gündüz", key=f"sh_name_{d.device_id}")
                            
                            c_t1, c_t2 = st.columns(2)
                            t_start = c_t1.time_input("Başlangıç", time(8, 0), key=f"sh_start_{d.device_id}")
                            t_end = c_t2.time_input("Bitiş", time(18, 0), key=f"sh_end_{d.device_id}")
                            
                            # Operatör seç (Mevcut listeden)
                            s_op_id = None
                            if operators:
                                s_op_name = st.selectbox("Varsayılan Operatör", [o.full_name for o in operators], key=f"sh_op_sel_{d.device_id}")
                                s_op_id = op_options[s_op_name]
                            
                            if st.button("Vardiyayı Kaydet", key=f"sh_save_btn_{d.device_id}"):
                                ok, msg = create_device_shift(d.device_id, s_name, t_start, t_end, s_op_id)
                                if ok: st.success("Eklendi!"); st.rerun()
                                else: st.error(msg)

                # --- TAB 5: BAKIM & SERVİS (YENİ ÖZELLİK) ---
                # Sanal cihazlar için de bakım gerekebilir (Makine sonuçta)
                m_tab_index = 4 if not d.is_virtual else 2
                with tabs[m_tab_index]:
                    # 1. HESAPLAMALAR (Basit simülasyon, veriler telemetryden gelmeli)
                    current_total_hours = d.last_maintenance_hour + 10 # Şimdilik dummy artış
                    
                    interval = d.maintenance_interval_hours # Örn: 250
                    hours_since_maint = current_total_hours - d.last_maintenance_hour
                    remaining = interval - hours_since_maint
                    
                    # 2. METRİKLER
                    m1, m2, m3 = st.columns(3)
                    m1.markdown(f"""<div class='metric-box'><small>Toplam Saat</small><h3>{current_total_hours:.1f}</h3></div>""", unsafe_allow_html=True)
                    m2.markdown(f"""<div class='metric-box'><small>Bakım Aralığı</small><h3>{interval}</h3></div>""", unsafe_allow_html=True)
                    
                    color = "#d63031" if remaining < 20 else "#00b894"
                    m3.markdown(f"""<div class='metric-box' style='border:1px solid {color};'><small>Kalan</small><h3 style='color:{color};'>{remaining:.1f}</h3></div>""", unsafe_allow_html=True)
                    
                    st.write("")
                    
                    # 3. YENİ BAKIM GİRİŞİ (GÜVENLİ)
                    with st.expander("🛠️ Yeni Servis Kaydı Gir & Sıfırla"):
                        with st.form(key=f"srv_form_{d.device_id}"):
                            c_tech, c_part = st.columns(2)
                            tech_name = c_tech.text_input("Servis Personeli", placeholder="Ahmet Usta")
                            part_name = c_part.text_input("Değişen Parça", placeholder="Filtre Seti")
                            
                            c_desc, c_code = st.columns(2)
                            desc = c_desc.text_input("Yapılan İşlem", placeholder="250 Saat Bakımı")
                            part_no = c_code.text_input("Parça No", placeholder="HKM-101")
                            
                            notes = st.text_area("Notlar")
                            
                            st.markdown("**Güvenlik Onayı:**")
                            pass_chk = st.text_input("Yönetici Şifreniz", type="password", help="İşlemi onaylamak için şifrenizi girin.")
                            
                            if st.form_submit_button("💾 Kaydet ve Sayacı Sıfırla", type="primary"):
                                if verify_admin_password(user.id, pass_chk):
                                    if tech_name and desc:
                                        ok = add_service_record(
                                            d.device_id, tech_name, desc, 
                                            part_name, part_no, current_total_hours, notes
                                        )
                                        if ok: 
                                            st.success("Servis işlendi ve sayaç sıfırlandı!")
                                            st.rerun()
                                        else: st.error("Kayıt hatası.")
                                    else:
                                        st.warning("Personel ve İşlem alanı zorunludur.")
                                else:
                                    st.error("⛔ Hatalı Şifre!")

                    # 4. BAKIM GEÇMİŞİ TABLOSU
                    if d.service_history:
                        st.markdown("### 📜 Servis Geçmişi")
                        hist_data = []
                        for srv in d.service_history:
                            hist_data.append({
                                "Tarih": srv.service_date.strftime("%d.%m.%Y"),
                                "Personel": srv.technician_name,
                                "İşlem": srv.description,
                                "Değişen": srv.changed_part,
                                "Makine Saati": f"{srv.total_machine_hours:.1f}"
                            })
                        st.dataframe(hist_data, use_container_width=True)
                    else:
                        st.caption("Henüz servis kaydı yok.")