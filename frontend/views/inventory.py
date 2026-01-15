# frontend/views/inventory.py (V3 - FINAL UX REVİZESİ)
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from backend.database import get_user_devices, get_all_devices_for_admin, create_share_link, revoke_share_link, get_device_share_links

def load_view(user):
    st.title("🚜 Makine Parkı ve Paylaşım Yönetimi")
    
    devices = get_all_devices_for_admin() if user.role == 'Admin' else get_user_devices(user.id)
    
    if not devices:
        st.warning("Hiç cihazınız yok.")
        return

    default_expanded = True if len(devices) <= 3 else False

    for index, d in enumerate(devices):
        is_expanded = True if (index == 0 and not default_expanded) else default_expanded
        
        with st.expander(f"🚜 {d.unit_name} | {d.asset_model}", expanded=is_expanded):
            
            # --- LAYOUT: 3 SÜTUN (Sola kaydırdık) ---
            # Sol: Bilgiler + İncele Butonu | Orta: Paylaşım | Sağ: Boş (Denge için)
            c1, c2, c3 = st.columns([1.2, 2.2, 0.1])
            
            # --- SÜTUN 1: CİHAZ BİLGİLERİ ---
            with c1:
                st.info(f"📍 **Seri No:** {d.device_id}")
                
                # Durum
                st.write(f"**Durum:** {'🟢 Aktif' if d.is_active else '🔴 Pasif'}")
                
                # Adres (Bold Başlık, Normal İçerik)
                st.markdown("**Adres:**") 
                st.caption(f"{d.address}")
                
                # Son Sinyal (Bold Başlık, Normal İçerik)
                st.markdown("**Son Sinyal:**")
                st.caption("12 dk önce")
                
                st.markdown("---")
                
                # İNCELE BUTONU (Buraya alındı, sessiz çalışıyor)
                if st.button("🔍 İncele / Analiz", key=f"det_{d.device_id}", use_container_width=True):
                    st.session_state["target_analysis_device"] = d.unit_name
                    # Toast mesajı kaldırıldı. Kullanıcı menüden geçtiğinde seçili görecek.
            
            # --- SÜTUN 2: PAYLAŞIM MERKEZİ ---
            with c2:
                st.markdown("#### 🔗 Paylaşım Merkezi")
                
                tab_new, tab_list = st.tabs(["➕ Yeni Link Oluştur", "📋 Aktif Paylaşımlar"])
                
                # --- TAB 1: YENİ LİNK ---
                with tab_new:
                    with st.form(key=f"form_{d.device_id}", clear_on_submit=False):
                        col_date, col_note = st.columns([1, 1.5])
                        
                        # Tarih: DD.MM.YYYY Formatı
                        tomorrow = datetime.now() + timedelta(days=1)
                        selected_date = col_date.date_input("Son Geçerlilik", value=tomorrow + timedelta(days=6), min_value=tomorrow, format="DD.MM.YYYY", key=f"date_{d.device_id}")
                        
                        # Not Alanı (Enter uyarısını kaldırmak için form içindeyiz)
                        note_text = col_note.text_input("Kime Gönderilecek?", placeholder="Örn: Mehmet Bey - Batı Şantiyesi", key=f"note_{d.device_id}")
                        
                        # Buton
                        submit_btn = st.form_submit_button("Link Oluştur", use_container_width=True, type="primary")
                        
                        if submit_btn:
                            expiry_dt = datetime.combine(selected_date, datetime.max.time())
                            new_token = create_share_link(user.id, d.device_id, expiry_dt, note_text)
                            
                            # Session State'e kaydet ki form yenilenince gitmesin
                            st.session_state[f"new_link_{d.device_id}"] = {
                                "token": new_token,
                                "date": selected_date.strftime("%d.%m.%Y")
                            }

                    # Eğer link oluşturulduysa FORM DIŞINDA göster (Form temizlense bile kalsın)
                    if f"new_link_{d.device_id}" in st.session_state:
                        link_data = st.session_state[f"new_link_{d.device_id}"]
                        base_url = "http://localhost:8501"
                        full_link = f"{base_url}/?token={link_data['token']}"
                        
                        # 1. Linki Kopyalanabilir Yap (st.code en temiz yöntemdir)
                        st.markdown("**👇 Linki Kopyala:**")
                        st.code(full_link, language="text")
                        
                        # 2. Özel Uyarı Metni (Sarı Ünlem + Kırmızı Yazı)
                        st.markdown(
                            f"""
                            <div style="color: #d63031; font-size: 0.9em; margin-top: 10px;">
                            ⚠️ <b>DİKKAT!</b> Paylaşacağınız bu link ile makinenizin konumu ve son çalışma detayları 
                            paylaştığınız kişi tarafından görüntülenebilecektir. <br>
                            Paylaşım <b>"{link_data['date']}"</b> tarihinde son bulacaktır. <br>
                            Bu tarih öncesinde paylaşımı durdurmak isterseniz "Aktif Paylaşımlar" bölümündeki 
                            "Paylaşımı Durdur" butonuna basabilirsiniz.
                            </div>
                            """, 
                            unsafe_allow_html=True
                        )

                # --- TAB 2: AKTİF LİNKLER LİSTESİ ---
                with tab_list:
                    active_links = get_device_share_links(d.device_id)
                    
                    if active_links:
                        for link in active_links:
                            with st.container():
                                cl1, cl2, cl3 = st.columns([1.5, 2, 1.2])
                                
                                # Bilgi
                                cl1.markdown(f"**{link.note if link.note else 'İsimsiz'}**")
                                cl1.caption(f"Son: {link.expires_at.strftime('%d.%m.%Y')}")
                                
                                # Link (Kopyalanabilir Alan)
                                full_url_show = f"http://localhost:8501/?token={link.token}"
                                with cl2:
                                    st.code(full_url_show, language="text")
                                
                                # İPTAL BUTONU (Kırmızı)
                                with cl3:
                                    st.write("") # Hizalama boşluğu
                                    if st.button("⛔ Paylaşımı Durdur", key=f"revoke_{link.token}", type="primary"):
                                        revoke_share_link(link.token)
                                        st.rerun()
                                st.divider()
                    else:
                        st.info("Bu cihaz için aktif bir paylaşım bulunmuyor.")