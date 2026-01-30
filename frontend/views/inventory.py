# frontend/views/inventory.py (V8 - MASTER: WHATSAPP BUTTON + TEMİZLEME BUTONU)
import streamlit as st
import locale
import sys
import os
import urllib.parse # WhatsApp linki için gerekli
from datetime import datetime, timedelta

# Yolları ekle
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from backend.database import (
    get_user_devices, create_share_link, revoke_share_link, 
    get_device_share_links, get_device_telemetry, 
    get_device_documents, upload_document_to_db, delete_document,
    get_user_storage_usage, send_admin_notification_email
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
        is_expanded = True if index < 3 else False
        
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

            # SAĞ KOLON: İŞLEMLER
            with col_ops:
                if d.is_virtual:
                    tabs = st.tabs(["📂 Dosyalar", "📤 Yükle"])
                else:
                    tabs = st.tabs(["📂 Dosyalar", "📤 Yükle", "🔗 Paylaşım Merkezi"])
                
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
                            
                            # SİLME YETKİSİ: Sadece kendi yüklediklerini silebilir
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

                # --- TAB 3: PAYLAŞIM MERKEZİ (REVİZE EDİLDİ) ---
                if not d.is_virtual:
                    with tabs[2]:
                        sub_tab_new, sub_tab_list = st.tabs(["➕ Yeni Link Oluştur", "📋 Aktif Paylaşımlar"])
                        
                        # YENİ LİNK OLUŞTURMA
                        with sub_tab_new:
                            # State Key
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
                                        # State'e kaydet
                                        st.session_state[link_state_key] = {
                                            "token": new_token, 
                                            "date": selected_date.strftime("%d.%m.%Y")
                                        }
                                        st.rerun() # Sayfayı yenile ki aşağıdaki blok çalışsın

                            # --- BAŞARILI LİNK GÖSTERİMİ (VE WHATSAPP BUTONU) ---
                            if link_state_key in st.session_state:
                                link_data = st.session_state[link_state_key]
                                base_url = "http://localhost:8501" # Canlıda domain
                                full_link = f"{base_url}/?token={link_data['token']}"
                                
                                # 1. Yeşil Başarı Kutusu
                                st.markdown("""<div style="background-color:#d4edda; color:#155724; padding:10px; border-radius:5px; font-weight:bold; margin-top:10px;">✅ Link Hazır</div>""", unsafe_allow_html=True)
                                
                                # 2. Link
                                st.code(full_link, language="text")
                                st.caption(f"Link {link_data['date']} tarihine kadar geçerlidir.")
                                
                                # 3. WhatsApp Butonu (BURAYA EKLENDİ)
                                msg_text = f"Merhaba, {d.unit_name} makinesini buradan izleyebilirsin: {full_link}"
                                encoded_msg = urllib.parse.quote(msg_text)
                                wa_url = f"https://wa.me/?text={encoded_msg}"
                                
                                st.markdown(f"""
                                    <a href="{wa_url}" target="_blank" style="text-decoration: none;">
                                        <div style="
                                            background-color: #25D366; 
                                            color: white; 
                                            padding: 10px; 
                                            border-radius: 8px; 
                                            text-align: center; 
                                            font-weight: bold; 
                                            margin-top: 5px;
                                            box-shadow: 0 2px 4px rgba(0,0,0,0.2);">
                                            📲 WhatsApp ile Gönder
                                        </div>
                                    </a>
                                """, unsafe_allow_html=True)
                                
                                st.write("")
                                # 4. Kapat / Temizle Butonu (Sorunu Çözen Kısım)
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