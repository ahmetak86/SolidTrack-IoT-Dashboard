import streamlit as st
from backend.database import update_user_settings

def load_view(user):
    st.header("⚙️ Yapılandırma ve Ayarlar")
    tab1, tab2, tab3 = st.tabs(["👤 Profil & Firma", "🌍 Sistem & Görünüm", "🔔 Bildirimler"])
    settings = {}
    
    with st.form("settings_form"):
        with tab1:
            st.subheader("Firma Bilgileri")
            r1_c1, r1_c2 = st.columns(2)
            settings['company_name'] = r1_c1.text_input("Firma Ünvanı", value=user.company_name)
            settings['full_name'] = r1_c2.text_input("Yetkili Ad Soyad", value=user.full_name)
            r2_c1, r2_c2 = st.columns(2)
            settings['tax_office'] = r2_c1.text_input("Vergi Dairesi", value=user.tax_office)
            settings['tax_number'] = r2_c2.text_input("Vergi Numarası", value=user.tax_number)
            settings['company_address'] = st.text_area("Fatura Adresi", value=user.company_address)
            st.subheader("İletişim")
            r3_c1, r3_c2 = st.columns(2)
            settings['email'] = r3_c1.text_input("E-Posta", value=user.email)
            settings['phone'] = r3_c2.text_input("Telefon", value=user.phone)

        with tab2:
            st.subheader("Bölgesel Ayarlar")
            sys_c1, sys_c2, sys_c3 = st.columns(3)
            langs = ["Turkish", "English", "Spanish", "German"]
            l_idx = langs.index(user.language) if user.language in langs else 0
            settings['language'] = sys_c1.selectbox("Dil / Language", langs, index=l_idx)
            settings['timezone'] = sys_c2.selectbox("Saat Dilimi", ["Europe/Istanbul", "UTC", "Europe/London"], index=0)
            settings['date_format'] = sys_c3.selectbox("Tarih Formatı", ["DD.MM.YYYY", "MM/DD/YYYY", "YYYY-MM-DD"], index=0)
            st.markdown("---")
            st.subheader("Birim Tercihleri (Unit System)")
            u_row1_c1, u_row1_c2 = st.columns(2)
            settings['unit_length'] = u_row1_c1.selectbox("Uzunluk", ["Metre / Km", "Feet / Mile"], index=0)
            settings['unit_temp'] = u_row1_c2.selectbox("Sıcaklık", ["Celsius (°C)", "Fahrenheit (°F)"], index=0)
            u_row2_c1, u_row2_c2 = st.columns(2)
            settings['unit_pressure'] = u_row2_c1.selectbox("Basınç", ["Bar", "PSI"], index=0)
            settings['unit_volume'] = u_row2_c2.selectbox("Hacim", ["Litre", "Galon"], index=0)

        with tab3:
            st.subheader("Bildirim Tercihleri")
            settings['notification_email_enabled'] = st.toggle("📧 E-Posta Bildirimleri (Genel)", value=user.notification_email_enabled)
            st.markdown("---")
            b_c1, b_c2 = st.columns(2)
            with b_c1:
                settings['notify_low_battery'] = st.checkbox("Düşük Pil Uyarısı", value=user.notify_low_battery)
                settings['notify_shock'] = st.checkbox("Kritik Darbe / Şok", value=user.notify_shock)
                settings['notify_geofence'] = st.checkbox("Bölge İhlali", value=user.notify_geofence)
            with b_c2:
                settings['notify_maintenance'] = st.checkbox("Bakım Zamanı", value=user.notify_maintenance)
                settings['notify_daily_report'] = st.checkbox("Günlük Rapor", value=user.notify_daily_report)

        st.markdown("---")
        if st.form_submit_button("💾 Ayarları Kaydet", type="primary"):
            updated = update_user_settings(user.id, settings)
            if updated:
                st.session_state.user = updated
                st.success("Ayarlar başarıyla kaydedildi!")
                st.rerun()