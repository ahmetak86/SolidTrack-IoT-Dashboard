# frontend/views/admin_users.py (V4 - FİNAL MASTER SÜRÜM)
import streamlit as st
import pandas as pd
import sys
import os
import uuid
from datetime import datetime

# Backend yolları
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from backend.database import (
    SessionLocal, User, get_password_hash, Device, 
    sync_devices_from_trusted_api, update_user_admin_details,
    change_user_password 
)

# --- YARDIMCI FONKSİYONLAR ---

def delete_device_permanently(device_id):
    """Veritabanından cihazı tamamen siler."""
    db = SessionLocal()
    try:
        dev = db.query(Device).filter(Device.device_id == device_id).first()
        if dev:
            db.delete(dev)
            db.commit()
            return True
        return False
    except:
        db.rollback()
        return False
    finally:
        db.close()

def delete_user_from_db(user_id):
    """Kullanıcıyı siler (Cihazı yoksa)."""
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if user:
            # Önce kullanıcının cihazlarını kontrol et
            devices = db.query(Device).filter(Device.owner_id == user_id).all()
            if devices:
                return False, f"❌ Bu kullanıcının üzerine kayıtlı {len(devices)} adet cihaz var. Önce cihazları silin veya başka kullanıcıya aktarın."
            
            db.delete(user)
            db.commit()
            return True, f"✅ Kullanıcı ({user.username}) başarıyla silindi."
        return False, "Kullanıcı bulunamadı."
    except Exception as e:
        db.rollback()
        return False, str(e)
    finally:
        db.close()

def load_view(current_user):
    st.markdown("## 👑 Yönetici & CRM Paneli")
    st.info("Müşterilerinizi yönetin, lisans sürelerini belirleyin ve cihazlarını senkronize edin.")

    if current_user.role != "Admin":
        st.error("⛔ Bu sayfaya erişim yetkiniz yok.")
        return

    # --- 1. MÜŞTERİ LİSTESİ VE SEÇİMİ ---
    db = SessionLocal()
    users = db.query(User).order_by(User.role.asc(), User.company_name.asc()).all()
    db.close()
    
    # Kullanıcıları Listeleme
    user_options = {f"{u.company_name} ({u.username})": u for u in users}
    
    col_list, col_detail = st.columns([1, 2])
    
    # --- SOL KOLON: LİSTE VE HIZLI EKLEME ---
    with col_list:
        st.markdown("### 📋 Müşteri Listesi")
        
        selected_option_key = st.selectbox("Yönetilecek Müşteriyi Seç:", list(user_options.keys()), index=0 if users else None)
        
        st.divider()
        st.markdown("### ➕ Hızlı Ekle")
        with st.expander("Yeni Müşteri Oluştur"):
            with st.form("create_crm_user", clear_on_submit=True):
                new_comp = st.text_input("Firma Adı")
                new_user = st.text_input("Kullanıcı Adı")
                new_pass = st.text_input("Şifre", type="password")
                new_email = st.text_input("E-Posta")
                new_gid = st.text_input("Trusted Group ID (Varsa)", value="0")
                role_select = st.selectbox("Rol", ["Client", "Admin", "SubUser"])
                
                if st.form_submit_button("Kaydet"):
                    if new_comp and new_user and new_pass:
                        db = SessionLocal()
                        try:
                            if db.query(User).filter((User.username == new_user) | (User.email == new_email)).first():
                                st.error("Bu kullanıcı zaten var!")
                            else:
                                u_id = f"u_{uuid.uuid4().hex[:8]}"
                                nu = User(
                                    id=u_id, username=new_user, email=new_email,
                                    password_hash=get_password_hash(new_pass),
                                    role=role_select, trusted_group_id=int(new_gid),
                                    company_name=new_comp, full_name=new_comp, is_active=True
                                )
                                db.add(nu)
                                db.commit()
                                st.success("Kullanıcı oluşturuldu!")
                                
                                # Otomatik Sync
                                if int(new_gid) > 0:
                                    success, msg = sync_devices_from_trusted_api(new_gid, u_id)
                                    if success: st.toast(msg)
                                    else: st.error(msg)
                                    
                                import time
                                time.sleep(1)
                                st.rerun()
                        except Exception as e:
                            st.error(f"Hata: {e}")
                        finally:
                            db.close()
                    else:
                        st.error("Eksik bilgi.")

    # --- SAĞ KOLON: DETAYLI YÖNETİM ---
    if selected_option_key:
        target_user = user_options[selected_option_key]
        
        with col_detail:
            # Başlık ve Durum Rozeti
            status_icon = "🟢" if target_user.is_active else "🔴"
            st.markdown(f"## {status_icon} {target_user.company_name}")
            st.caption(f"ID: {target_user.id} | Rol: {target_user.role} | E-Posta: {target_user.email}")

            # --- SEKMELİ YAPI ---
            tab_info, tab_crm, tab_device, tab_action = st.tabs([
                "📝 Genel Bilgiler", 
                "⚙️ CRM & Lisans", 
                "🚜 Cihaz & Sync", 
                "🕵️‍♂️ İşlemler / Sil"
            ])

            # TAB 1: GENEL BİLGİLER & ROL
            with tab_info:
                with st.form("edit_general_info"):
                    c1, c2 = st.columns(2)
                    u_active = c1.checkbox("Hesap Aktif", value=target_user.is_active)
                    
                    # ROL DEĞİŞTİRME SEÇENEĞİ
                    current_role_index = ["Client", "Admin", "SubUser"].index(target_user.role) if target_user.role in ["Client", "Admin", "SubUser"] else 0
                    u_role = c2.selectbox("Kullanıcı Rolü", ["Client", "Admin", "SubUser"], index=current_role_index)
                    
                    u_gid = st.text_input("Trusted Group ID", value=str(target_user.trusted_group_id or 0))
                    
                    st.info("Firma adı ve kullanıcı adı değişimi veritabanı bütünlüğü için kısıtlanmıştır.")
                    
                    if st.form_submit_button("💾 Genel Bilgileri Güncelle"):
                        success, msg = update_user_admin_details(target_user.id, {
                            "is_active": u_active,
                            "trusted_group_id": u_gid,
                            "role": u_role # Backend'e rolü gönderiyoruz
                        })
                        if success: st.success(msg); st.rerun()
                        else: st.error(msg)

            # TAB 2: CRM & LİSANS
            with tab_crm:
                with st.form("edit_crm_info"):
                    u_note = st.text_area("🔒 Admin Notu (Sadece siz görürsünüz)", 
                                         value=target_user.admin_note if target_user.admin_note else "",
                                         placeholder="Örn: Fatura her ayın 5'inde kesilecek.")
                    
                    c1, c2 = st.columns(2)
                    u_limit = c1.number_input("Cihaz Kotası", value=target_user.device_limit or 100, step=1)
                    
                    curr_date = target_user.subscription_end_date if target_user.subscription_end_date else None
                    u_date = c2.date_input("📅 Lisans Bitiş Tarihi", value=curr_date)

                    if st.form_submit_button("💾 CRM Bilgilerini Kaydet"):
                        final_date = datetime.combine(u_date, datetime.min.time()) if u_date else None
                        success, msg = update_user_admin_details(target_user.id, {
                            "admin_note": u_note,
                            "device_limit": u_limit,
                            "subscription_end_date": final_date
                        })
                        if success: st.success(msg); st.rerun()
                        else: st.error(msg)
                
                if target_user.last_login_at:
                    st.caption(f"👀 Son Görülme: {target_user.last_login_at.strftime('%d.%m.%Y %H:%M')}")
                else:
                    st.caption("👀 Henüz hiç giriş yapmadı.")

            # TAB 3: CİHAZ & SYNC
            with tab_device:
                st.markdown(f"**Bağlı Grup ID:** `{target_user.trusted_group_id}`")
                
                if st.button("🔄 Cihazları Şimdi Senkronize Et (Fazlalıkları Temizle)", use_container_width=True, type="primary"):
                    if target_user.trusted_group_id and target_user.trusted_group_id > 0:
                        with st.spinner("Trusted API ile konuşuluyor..."):
                            success, msg = sync_devices_from_trusted_api(target_user.trusted_group_id, target_user.id)
                            if success: st.success(msg); st.rerun()
                            else: st.error(msg)
                    else:
                        st.error("Lütfen önce geçerli bir Trusted Group ID tanımlayın.")

                st.markdown("---")
                st.markdown("### 📋 Mevcut Cihazlar")
                db = SessionLocal()
                devices = db.query(Device).filter(Device.owner_id == target_user.id).all()
                db.close()
                
                if devices:
                    df = pd.DataFrame([{
                        "Cihaz Adı": d.unit_name,
                        "ID": d.device_id,
                        "Model": d.asset_model,
                        "Tipi": "Sanal" if d.is_virtual else "IoT"
                    } for d in devices])
                    st.dataframe(df, hide_index=True, use_container_width=True)
                    
                    # MANUEL SİLME KUTUSU
                    st.markdown("#### 🗑️ Manuel Cihaz Silme")
                    dev_options = {f"{d.unit_name} ({d.device_id})": d.device_id for d in devices}
                    selected_devs_to_del = st.multiselect("Silinecek cihazları seçin:", list(dev_options.keys()))
                    
                    if selected_devs_to_del:
                        if st.button(f"Seçili {len(selected_devs_to_del)} Cihazı Kalıcı Olarak Sil", type="secondary"):
                            count = 0
                            for k in selected_devs_to_del:
                                dev_id = dev_options[k]
                                if delete_device_permanently(dev_id):
                                    count += 1
                            st.success(f"{count} cihaz başarıyla silindi.")
                            import time
                            time.sleep(1)
                            st.rerun()
                else:
                    st.info("Bu kullanıcıya ait cihaz bulunamadı.")

            # TAB 4: İŞLEMLER / SİL
            with tab_action:
                st.markdown("### 🔑 Şifre Sıfırlama")
                new_p = st.text_input("Yeni Şifre Belirle", type="password", key=f"p_{target_user.id}")
                if st.button("Şifreyi Güncelle", key=f"btn_p_{target_user.id}"):
                    if new_p:
                        db = SessionLocal()
                        u = db.query(User).filter(User.id == target_user.id).first()
                        u.password_hash = get_password_hash(new_p)
                        db.commit()
                        db.close()
                        st.success("Şifre güncellendi.")
                    else:
                        st.warning("Şifre boş olamaz.")
                
                st.divider()
                st.markdown("### 🕵️‍♂️ Gözcü Modu")
                st.write("Bu kullanıcının hesabına, şifresini bilmeden giriş yapın.")
                
                if st.button("👁️ Kullanıcı Olarak Giriş Yap (Impersonate)", type="primary"):
                    st.session_state["original_admin"] = current_user
                    st.session_state["user"] = target_user
                    st.rerun()

                st.divider()
                st.markdown("### ⚠️ Tehlikeli Bölge")
                
                if target_user.id == current_user.id:
                    st.warning("Kendinizi silemezsiniz.")
                else:
                    del_confirm = st.checkbox("Kullanıcıyı silmek istiyorum", key=f"del_chk_{target_user.id}")
                    if del_confirm:
                        if st.button("🗑️ KULLANICIYI SİL", type="primary"):
                            success, msg = delete_user_from_db(target_user.id)
                            if success:
                                st.success(msg)
                                import time
                                time.sleep(2)
                                st.rerun()
                            else:
                                st.error(msg)