# frontend/views/inventory.py (DETAYLAR BUTONU GERİ GELDİ & UZUN TOKEN)
import streamlit as st
import pandas as pd
from datetime import datetime
from backend.database import get_user_devices, get_all_devices_for_admin, create_share_link, revoke_share_link

def load_view(user):
    st.title("🚜 Makine Parkı ve Paylaşım")
    
    devices = get_all_devices_for_admin() if user.role == 'Admin' else get_user_devices(user.id)
    
    if not devices:
        st.warning("Hiç cihazınız yok.")
        return

    # Akordeon Mantığı (3 veya az ise hepsi açık)
    default_expanded = True if len(devices) <= 3 else False

    for index, d in enumerate(devices):
        is_expanded = True if (index == 0 and not default_expanded) else default_expanded
        
        with st.expander(f"🚜 {d.unit_name} | {d.asset_model}", expanded=is_expanded):
            # 3 SÜTUN YAPISI: Bilgi | Paylaşım | Aksiyon
            c1, c2, c3 = st.columns([1.5, 1.5, 0.8])
            
            # --- C1: BİLGİLER ---
            with c1:
                st.markdown(f"**Seri No:** {d.device_id}")
                st.markdown(f"**Durum:** {'🟢 Aktif' if d.is_active else '🔴 Pasif'}")
                st.markdown("**Adres:**") 
                st.markdown(f"{d.address if d.address else 'Konum verisi bekleniyor...'}") 

            # --- C2: PAYLAŞIM ---
            with c2:
                st.markdown("##### 🔗 Müşteri Paylaşımı")
                if st.button("Link Oluştur", key=f"share_{d.device_id}"):
                    token = create_share_link(user.id, d.device_id, days=7)
                    st.session_state[f"token_{d.device_id}"] = token
                
                if f"token_{d.device_id}" in st.session_state:
                    token = st.session_state[f"token_{d.device_id}"]
                    base_url = "http://localhost:8501"
                    full_link = f"{base_url}/?token={token}"
                    
                    st.caption("✅ Link oluşturuldu! (7 Gün Geçerli)")
                    st.code(full_link, language="text")
                    st.error("⚠️ DİKKAT: Bu link şifresiz erişim sağlar.")

            # --- C3: AKSİYON (DETAYLAR BUTONU) ---
            with c3:
                st.markdown("##### ⚙️ İşlem")
                # Butonu biraz aşağı hizalamak için boşluk
                st.write("") 
                if st.button("🔍 Detaylar", key=f"det_{d.device_id}", use_container_width=True):
                    # Hafızaya not alıyoruz:
                    st.session_state["target_analysis_device"] = d.unit_name
                    st.success(f"{d.unit_name} seçildi! Teknik Analiz menüsüne gidebilirsin.")