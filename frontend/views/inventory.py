# frontend/views/inventory.py
import streamlit as st
from datetime import datetime, timedelta
import locale
# "backend" modülünü bulabilmesi için yol ayarı
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from backend.database import get_user_devices, create_share_link, revoke_share_link, get_device_share_links, get_device_telemetry

# Dil Ayarı (Opsiyonel)
try:
    locale.setlocale(locale.LC_ALL, 'tr_TR.UTF-8')
except:
    try:
        locale.setlocale(locale.LC_ALL, 'Turkish_Turkey.1254')
    except:
        pass

def load_view(user):
    st.title("🚜 Makine Parkı ve Paylaşım Yönetimi")
    
    # --- CSS AYARLARI ---
    st.markdown("""
        <style>
        .stTextInput div[data-testid="InputInstructions"] {display: none;} 
        .stDateInput div[data-testid="InputInstructions"] {display: none;}
        
        [data-testid="stCodeBlock"] button {
            color: #d63031 !important;
            border-color: rgba(214, 48, 49, 0.3) !important;
            background-color: rgba(214, 48, 49, 0.05) !important;
            transition: all 0.3s ease;
        }
        [data-testid="stCodeBlock"] button svg {
            stroke: #d63031 !important;
            stroke-width: 3px !important;
        }
        [data-testid="stCodeBlock"] button:hover {
            background-color: #d63031 !important;
            color: white !important;
            border-color: #d63031 !important;
        }
        [data-testid="stCodeBlock"] button:hover svg {
            stroke: white !important;
        }
        </style>
    """, unsafe_allow_html=True)
    
    # --- KRİTİK NOKTA: ARTIK SADECE BU FONKSİYONU ÇAĞIRIYORUZ ---
    # get_user_devices fonksiyonu; 
    # - Serkan Bey ise hepsini, 
    # - Sen isen sadece HKM cihazlarını getirecek şekilde ayarlandı.
    devices = get_user_devices(user.id)
    
    if not devices:
        st.warning("Görüntülenecek cihaz bulunamadı.")
        return

    default_expanded = True if len(devices) <= 3 else False

    for index, d in enumerate(devices):
        is_expanded = True if (index == 0 and not default_expanded) else default_expanded
        
        with st.expander(f"🚜 {d.unit_name} | {d.asset_model}", expanded=is_expanded):
            
            c1, c2, c3 = st.columns([1.3, 2.2, 0.1])
            
            # --- SÜTUN 1: BİLGİLER ---
            with c1:
                st.info(f"📍 **Seri No:** {d.device_id}")
                st.write(f"**Durum:** {'🟢 Aktif' if d.is_active else '🔴 Pasif'}")
                
                addr_text = d.address if d.address else "Konum verisi yok."
                st.markdown(f"**Adres:** {addr_text}") 
                last_log = get_device_telemetry(d.device_id, limit=1)
                if last_log:
                    last_seen_str = last_log[0].timestamp.strftime('%d.%m.%Y, %H:%M')
                else:
                    last_seen_str = "Sinyal Yok"

                st.markdown(f"**Son Sinyal:** {last_seen_str}")
                st.write("") 
                
                if st.button("Detay Gör", key=f"det_{d.device_id}", use_container_width=True):
                    st.session_state["target_analysis_device"] = d.unit_name
                    st.session_state["menu_selection"] = "🔍 Teknik Analiz"
                    st.rerun()
            
            # --- SÜTUN 2: PAYLAŞIM ---
            with c2:
                st.markdown("#### 🔗 Paylaşım Merkezi")
                
                tab_new, tab_list = st.tabs(["➕ Yeni Link Oluştur", "📋 Aktif Paylaşımlar"])
                
                # --- TAB 1: YENİ OLUŞTUR ---
                with tab_new:
                    with st.form(key=f"form_{d.device_id}", clear_on_submit=False):
                        col_note, col_date = st.columns([1.5, 1])
                        note_text = col_note.text_input("Kime Gönderilecek?", placeholder="Örn: Mehmet Bey", key=f"note_{d.device_id}")
                        
                        tomorrow = datetime.now() + timedelta(days=1)
                        selected_date = col_date.date_input("Son Geçerlilik", value=tomorrow + timedelta(days=6), min_value=tomorrow, format="DD.MM.YYYY", key=f"date_{d.device_id}")
                        
                        submit_btn = st.form_submit_button("Link Oluştur", use_container_width=True, type="primary")
                        
                        if submit_btn:
                            if not note_text:
                                st.error("⚠️ Lütfen kime gönderileceğini yazın.")
                            else:
                                expiry_dt = datetime.combine(selected_date, datetime.max.time())
                                new_token = create_share_link(user.id, d.device_id, expiry_dt, note_text)
                                st.session_state[f"new_link_{d.device_id}"] = {
                                    "token": new_token,
                                    "date": selected_date.strftime("%d.%m.%Y")
                                }

                    if f"new_link_{d.device_id}" in st.session_state:
                        link_data = st.session_state[f"new_link_{d.device_id}"]
                        base_url = "http://localhost:8501"
                        full_link = f"{base_url}/?token={link_data['token']}"
                        
                        st.markdown("---")
                        st.markdown("""<div style="background-color:#d4edda; color:#155724; padding:5px; border-radius:5px; font-weight:bold;">✅ Link Hazır:</div>""", unsafe_allow_html=True)
                        st.code(full_link, language="text")
                        st.warning(f"Link {link_data['date']} tarihine kadar geçerlidir.")

                # --- TAB 2: LİSTE GÖRÜNÜMÜ ---
                with tab_list:
                    active_links = get_device_share_links(d.device_id)
                    if active_links:
                        for link in active_links:
                            with st.container():
                                cl1, cl2, cl3 = st.columns([1.5, 2.2, 1.0])
                                cl1.markdown(f"**{link.note if link.note else 'İsimsiz'}**")
                                cl1.caption(f"Son: {link.expires_at.strftime('%d.%m.%Y')}")
                                
                                full_url_show = f"http://localhost:8501/?token={link.token}"
                                with cl2:
                                    st.code(full_url_show, language="text")
                                
                                with cl3:
                                    if st.button("İptal Et", key=f"revoke_{link.token}", type="primary"):
                                        revoke_share_link(link.token)
                                        st.rerun()
                                st.divider()
                    else:
                        st.info("Aktif paylaşım yok.")