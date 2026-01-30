# frontend/views/admin_documents.py (V3 - MASTER: DÖNÜŞTÜRME ÖZELLİKLİ)
import streamlit as st
import os
import sys

# Backend yollarını ekle
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from backend.database import (
    SessionLocal, User, Device, 
    create_virtual_device_in_db, 
    upload_document_to_db,
    get_device_documents,
    delete_document,
    get_user_devices,
    convert_virtual_to_real # <--- YENİ FONKSİYON
)

def load_view(current_user):
    st.markdown("## 📂 Doküman ve Varlık Yönetimi")
    st.info("Buradan müşterileriniz için dosya yükleyebilir, sanal makine oluşturabilir veya cihazları eşleştirebilirsiniz.")

    # --- 1. MÜŞTERİ SEÇİMİ ---
    db = SessionLocal()
    users = db.query(User).all()
    db.close()
    
    user_map = {u.username: u for u in users}
    selected_username = st.selectbox("1. Müşteri Seçin:", list(user_map.keys()))
    
    if selected_username:
        target_user = user_map[selected_username]
        
        # --- TABLAR ---
        tab1, tab2, tab3 = st.tabs([
            "📄 Mevcut Cihaza Dosya Yükle", 
            "➕ Yeni Sanal Makine Oluştur",
            "🔄 Sanal -> Gerçek Dönüşümü"
        ])
        
        # TAB 1: MEVCUT CİHAZ + DOSYA
        with tab1:
            user_devices = get_user_devices(target_user.id)
            
            if not user_devices:
                st.warning("Bu müşterinin henüz hiç cihazı yok. Yan sekmeden oluşturabilirsiniz.")
            else:
                # Hem Sanal Hem Gerçek Hepsi Listelenir
                dev_map = {f"{d.unit_name} ({d.device_id})": d for d in user_devices}
                selected_dev_name = st.selectbox("2. Cihaz Seçin:", list(dev_map.keys()))
                
                if selected_dev_name:
                    target_device = dev_map[selected_dev_name]
                    
                    # Cihaz Bilgisi
                    is_virt = " (Sanal)" if target_device.is_virtual else " (IoT)"
                    st.caption(f"Seçilen: {target_device.asset_model}{is_virt}")
                    
                    st.markdown("---")
                    
                    # DOSYA YÜKLEME FORMU
                    with st.form("upload_doc_form", clear_on_submit=True):
                        st.write("### 📤 Dosya Yükle")
                        
                        allowed_types = [
                            'pdf', 'png', 'jpg', 'jpeg', 
                            'mp4', 'mov', 'avi',
                            'xlsx', 'xls', 'csv',
                            'doc', 'docx', 'txt'
                        ]
                        
                        uploaded_file = st.file_uploader(
                            "Belge, Video veya Resim Seçin (Max: 250MB)", 
                            type=allowed_types
                        )
                        
                        doc_type = st.selectbox("Doküman Tipi", ["Fatura", "Servis Formu", "Kullanım Kılavuzu", "Parça Kataloğu", "Video", "Diğer"])
                        
                        if st.form_submit_button("Sisteme Yükle"):
                            if uploaded_file:
                                if uploaded_file.size > 250 * 1024 * 1024:
                                    st.error("❌ Dosya boyutu 250MB sınırını aşıyor.")
                                else:
                                    success, msg = upload_document_to_db(
                                        target_device.device_id, 
                                        uploaded_file, 
                                        doc_type, 
                                        current_user.username
                                    )
                                    if success:
                                        st.success(msg)
                                    else:
                                        st.error(msg)
                            else:
                                st.error("Lütfen dosya seçin.")
                    
                    # MEVCUT DOSYALARI LİSTELEME
                    st.markdown("### 📋 Yüklü Dokümanlar")
                    docs = get_device_documents(target_device.device_id)
                    
                    if docs:
                        for doc in docs:
                            with st.container():
                                c1, c2, c3, c4 = st.columns([3, 2, 2, 2])
                                c1.write(f"📄 {doc.file_name}")
                                c2.caption(doc.file_type)
                                c3.caption(doc.upload_date.strftime('%d.%m.%Y'))
                                
                                # SİLME ONAY MEKANİZMASI
                                delete_key = f"del_btn_{doc.id}"
                                confirm_key = f"confirm_{doc.id}"
                                
                                if confirm_key not in st.session_state:
                                    st.session_state[confirm_key] = False
                                
                                with c4:
                                    if not st.session_state[confirm_key]:
                                        if st.button("🗑️ Sil", key=delete_key):
                                            st.session_state[confirm_key] = True
                                            st.rerun()
                                    else:
                                        col_y, col_n = st.columns(2)
                                        if col_y.button("✅", key=f"yes_{doc.id}", help="Kesin Sil"):
                                            delete_document(doc.id)
                                            del st.session_state[confirm_key]
                                            st.rerun()
                                        if col_n.button("❌", key=f"no_{doc.id}", help="Vazgeç"):
                                            st.session_state[confirm_key] = False
                                            st.rerun()
                                st.divider()
                    else:
                        st.info("Henüz yüklenmiş belge yok.")

        # TAB 2: SANAL CİHAZ OLUŞTURMA
        with tab2:
            st.write("Takip cihazı olmayan bir makine için 'Varlık Kartı' oluşturun.")
            
            with st.form("create_virtual_form"):
                v_name = st.text_input("Makine Adı (Örn: MSB Kırıcı #5)")
                v_model = st.text_input("Model (Örn: MS75AT)")
                v_serial = st.text_input("Seri No (Opsiyonel)", help="Boş bırakırsanız sistem otomatik atar.")
                
                if st.form_submit_button("Sanal Makineyi Oluştur"):
                    if v_name and v_model:
                        new_id, msg = create_virtual_device_in_db(target_user.id, v_name, v_model, v_serial)
                        if new_id:
                            st.success(f"{msg} ID: {new_id}")
                        else:
                            st.error(msg)
                    else:
                        st.warning("İsim ve Model zorunludur.")

        # TAB 3: SANAL -> GERÇEK DÖNÜŞÜMÜ (YENİ)
        with tab3:
            st.markdown("### 🔄 Cihaz Eşleştirme & Dönüştürme")
            st.info("""
            Bu özellik, daha önce 'Sanal' olarak açtığınız bir karta **SolidTrack Takip Cihazı** takıldığında kullanılır.
            Eski sanal kartı silmenize gerek kalmaz; tüm faturalar ve dosyalar yeni ID'ye taşınır.
            """)
            
            # Sadece SANAL cihazları filtrele
            user_all_devices = get_user_devices(target_user.id)
            virtual_only = [d for d in user_all_devices if d.is_virtual]
            
            if not virtual_only:
                st.success("Bu müşterinin dönüştürülecek sanal cihazı yok. Hepsi zaten IoT cihazı.")
            else:
                virt_map = {f"{d.unit_name} (ID: {d.device_id})": d for d in virtual_only}
                
                with st.form("convert_dev_form"):
                    selected_virt_name = st.selectbox("Dönüştürülecek Sanal Cihaz:", list(virt_map.keys()))
                    target_virt_dev = virt_map[selected_virt_name]
                    
                    st.write("🔽")
                    
                    real_iot_id = st.text_input("Yeni Takılan SolidTrack Cihaz ID'si (Örn: 8654...)", placeholder="Cihaz üzerindeki ID'yi girin")
                    
                    st.warning(f"⚠️ DİKKAT: '{target_virt_dev.unit_name}' cihazı, '{real_iot_id}' ID'si ile birleştirilecek ve 'Sanal' özelliği kaldırılacaktır.")
                    
                    if st.form_submit_button("Dönüştürmeyi Başlat"):
                        if not real_iot_id:
                            st.error("Lütfen Gerçek Cihaz ID'sini girin.")
                        else:
                            # Backend fonksiyonunu çağır
                            success, msg = convert_virtual_to_real(target_virt_dev.device_id, real_iot_id.strip())
                            
                            if success:
                                st.success(msg)
                                st.balloons()
                                import time
                                time.sleep(2)
                                st.rerun()
                            else:
                                st.error(msg)