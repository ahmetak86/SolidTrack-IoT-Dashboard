# frontend/views/inventory.py (V8 - KIRMIZI & KALIN KOPYALA İKONU)
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import locale
from backend.database import get_user_devices, get_all_devices_for_admin, create_share_link, revoke_share_link, get_device_share_links

# Dil Ayarı
try:
    locale.setlocale(locale.LC_ALL, 'tr_TR.UTF-8')
except:
    try:
        locale.setlocale(locale.LC_ALL, 'Turkish_Turkey.1254')
    except:
        pass

def load_view(user):
    st.title("🚜 Makine Parkı ve Paylaşım Yönetimi")
    
    # --- CSS AYARLARI (KIRMIZI İKON BURADA) ---
    st.markdown("""
        <style>
        /* Input altı uyarıları gizle */
        .stTextInput div[data-testid="InputInstructions"] {display: none;} 
        .stDateInput div[data-testid="InputInstructions"] {display: none;}
        
        /* --- KOPYALA BUTONU ÖZELLEŞTİRME --- */
        
        /* 1. Butonun kendisi (Çerçeve ve İkon Rengi) */
        [data-testid="stCodeBlock"] button {
            color: #d63031 !important; /* Kırmızı Renk */
            border-color: rgba(214, 48, 49, 0.3) !important;
            background-color: rgba(214, 48, 49, 0.05) !important; /* Çok hafif kırmızı zemin */
            transition: all 0.3s ease;
        }

        /* 2. İkonun İçindeki Çizgiler (BOLD Efekti Burada) */
        [data-testid="stCodeBlock"] button svg {
            stroke: #d63031 !important;   /* Çizgi Rengi: Kırmızı */
            stroke-width: 3px !important; /* Çizgi Kalınlığı: BOLD */
        }

        /* 3. Üzerine Gelince (Hover) Efekti */
        [data-testid="stCodeBlock"] button:hover {
            background-color: #d63031 !important; /* Zemin Kırmızı olsun */
            color: white !important;
            border-color: #d63031 !important;
        }
        
        /* Hover durumunda ikon beyaz olsun */
        [data-testid="stCodeBlock"] button:hover svg {
            stroke: white !important;
        }
        </style>
    """, unsafe_allow_html=True)
    
    devices = get_all_devices_for_admin() if user.role == 'Admin' else get_user_devices(user.id)
    
    if not devices:
        st.warning("Hiç cihazınız yok.")
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
                st.markdown(f"**Son Sinyal:** 12.01.2026, 14:44")
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
                        note_text = col_note.text_input("Kime Gönderilecek?", placeholder="Örn: Mehmet Bey - Batı Şantiyesi", key=f"note_{d.device_id}")
                        
                        tomorrow = datetime.now() + timedelta(days=1)
                        selected_date = col_date.date_input("Son Geçerlilik", value=tomorrow + timedelta(days=6), min_value=tomorrow, format="DD.MM.YYYY", key=f"date_{d.device_id}")
                        
                        submit_btn = st.form_submit_button("Link Oluştur", use_container_width=True, type="primary")
                        
                        if submit_btn:
                            if not note_text:
                                st.error("⚠️ Lütfen 'Kime Gönderilecek' alanını doldurunuz.")
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
                        # Başlık
                        st.markdown("""<div style="background-color:#d4edda; color:#155724; padding:5px 10px; border-radius:5px; margin-bottom:5px; font-weight:bold;">✅ Linki Kopyala:</div>""", unsafe_allow_html=True)
                        # Kod bloğu (CSS ile ikonu kırmızı yaptık)
                        st.code(full_link, language="text")
                        
                        st.warning(
                            f"""
                            **DİKKAT!** Paylaşacağınız bu link ile makinenizin konumu ve son çalışma detayları paylaştığınız kişi tarafından görüntülenebilecektir.
                            Paylaşım **"{link_data['date']}"** tarihinde son bulacaktır.
                            Bu tarih öncesinde paylaşımı durdurmak isterseniz "Aktif Paylaşımlar" bölümündeki **"Paylaşımı Durdur"** butonuna basabilirsiniz.
                            """, icon="⚠️"
                        )

                # --- TAB 2: LİSTE GÖRÜNÜMÜ ---
                with tab_list:
                    active_links = get_device_share_links(d.device_id)
                    if active_links:
                        for link in active_links:
                            with st.container():
                                cl1, cl2, cl3 = st.columns([1.5, 2.2, 1.0])
                                
                                # 1. İsim
                                cl1.markdown(f"**{link.note if link.note else 'İsimsiz'}**")
                                cl1.caption(f"Son: {link.expires_at.strftime('%d.%m.%Y')}")
                                
                                # 2. Link (CSS ile Kırmızı İkonlu)
                                full_url_show = f"http://localhost:8501/?token={link.token}"
                                with cl2:
                                    st.markdown("""<span style="font-size:0.8em; color:green;">📋 Link:</span>""", unsafe_allow_html=True)
                                    st.code(full_url_show, language="text")
                                
                                # 3. Buton
                                with cl3:
                                    st.write("") 
                                    st.write("") 
                                    if st.button("Paylaşımı Durdur", key=f"revoke_{link.token}", type="primary"):
                                        revoke_share_link(link.token)
                                        st.rerun()
                                st.divider()
                    else:
                        st.info("Bu cihaz için aktif bir paylaşım bulunmuyor.")