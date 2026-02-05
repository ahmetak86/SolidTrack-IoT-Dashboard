# frontend/views/admin_users.py (V6 - FULL CRM & FUNCTIONAL SUB-USERS)
import streamlit as st
import pandas as pd
import sys
import os
import uuid
import time 
from datetime import datetime

# Backend yolları
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from backend.database import (
    SessionLocal, User, get_password_hash, Device, 
    sync_devices_from_trusted_api, update_user_admin_details,
    change_user_password, update_device_metadata
)
from backend.trusted_api import api_get_all_subgroups

# --- İKON LİSTESİ (EXCEL İLE UYUMLU) ---
ICON_OPTIONS = {
    "breaker": "🔨 Hidrolik Kırıcı (Hydraulic Breaker)",
    "auger": "🌀 Hidrolik Burgu (Hydraulic Auger)",
    "shear": "✂️ Hidrolik Makas (Hydraulic Shear)",
    "concrete_cutter": "🪚 Beton Kesici (Concrete Cutter)",
    "drum_cutter": "⚙️ Tambur Kesici (Drum Cutter)",
    "pulverizer": "🦷 Pulverizatör (Pulverizer)",
    "grapple": "🪝 Kıskaç (Log/Excavator Grapple)",
    "hydraulic_drifter": "🔩 Hidrolik Delici (Hydraulic Drifter)",
    "crusher_bucket": "🗑️ Kırıcı Kova (Crusher Bucket)",
    "ripper": "⛏️ Riper (Ripper)",
    "excavator": "🚜 Ekskavatör (Excavator)",
    "truck": "🚚 Kamyon (Truck)",
    "mixer": "🌀 Beton Mikseri (Concrete Mixer)",
    "forklift": "🏗️ Forklift",
    "generator": "⚡ Jeneratör (Generator)",
    "bulldozer": "🚜 Buldozer (Bulldozer)",
    "dump_truck": "🚛 Damperli Kamyon (Dump Truck)",
    "tractor": "🚜 Traktör (Tractor)",
    "mobile_crane": "🏗️ Mobil Vinç (Mobile Crane)",
    "tower_crane": "🏗️ Kule Vinç (Tower Crane)",
    "roller": "🚜 Kompaktör/Silindir (Roller)",
    "backhoe": "🚜 Kazıcı Yükleyici (Backhoe)",
    "scissor_lift": "🪜 Makaslı Platform (Scissor Lift)",
    "pickup": "🛻 Pickup",
    "light_tower": "💡 Işık Kulesi (Light Tower)",
    "bucket": "🪣 Kova (Bucket)",
    "other": "❓ Diğer / Bilinmiyor"
}

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
            
            # Alt kullanıcıları varsa onları da sil veya boşa düşür (Basitlik için siliyoruz)
            sub_users = db.query(User).filter(User.parent_id == user_id).all()
            for sub in sub_users:
                db.delete(sub)

            db.delete(user)
            db.commit()
            return True, f"✅ Kullanıcı ({user.username}) ve alt hesapları silindi."
        return False, "Kullanıcı bulunamadı."
    except Exception as e:
        db.rollback()
        return False, str(e)
    finally:
        db.close()

def create_sub_user(parent_user, username, password, email, full_name):
    """Mevcut bir kullanıcıya bağlı alt hesap oluşturur."""
    db = SessionLocal()
    try:
        if db.query(User).filter((User.username == username) | (User.email == email)).first():
            return False, "Kullanıcı adı veya E-posta zaten kullanımda."
        
        new_sub = User(
            id=f"sub_{uuid.uuid4().hex[:8]}",
            username=username,
            email=email,
            password_hash=get_password_hash(password),
            full_name=full_name,
            role="SubUser",
            parent_id=parent_user.id, # KRİTİK NOKTA: Parent ID atanıyor
            trusted_group_id=parent_user.trusted_group_id, # Parent ile aynı grubu görür
            company_name=parent_user.company_name,
            is_active=True
        )
        db.add(new_sub)
        db.commit()
        return True, "Alt kullanıcı oluşturuldu."
    except Exception as e:
        return False, str(e)
    finally:
        db.close()

def load_view(current_user):
    st.markdown("## 👑 Yönetici & CRM Paneli")
    
    if current_user.role != "Admin":
        st.error("⛔ Bu sayfaya erişim yetkiniz yok.")
        return

    # --- 1. MÜŞTERİ LİSTESİ VE SEÇİMİ ---
    db = SessionLocal()
    # Sadece ANA kullanıcıları (Parent ID'si olmayanları) listele ki liste karışmasın
    users = db.query(User).filter(User.parent_id == None).order_by(User.role.asc(), User.company_name.asc()).all()
    db.close()
    
    # Kullanıcıları Listeleme
    user_options = {f"{u.company_name} ({u.username})": u for u in users}
    option_keys = list(user_options.keys())
    
    col_list, col_detail = st.columns([1, 2])
    
    # --- SOL KOLON: LİSTE VE HIZLI EKLEME ---
    with col_list:
        st.markdown("### 📋 Müşteri Listesi")
        
        # HAFIZA KONTROLÜ
        default_index = 0
        if "last_selected_admin_user" in st.session_state:
            saved_user = st.session_state["last_selected_admin_user"]
            if saved_user in option_keys:
                default_index = option_keys.index(saved_user)
        
        selected_option_key = st.selectbox(
            "Yönetilecek Müşteriyi Seç:", 
            option_keys, 
            index=default_index if users else None
        )
        
        if selected_option_key:
            st.session_state["last_selected_admin_user"] = selected_option_key
        
        st.divider()
        st.markdown("### ➕ Hızlı Müşteri Ekle")
        with st.expander("Yeni Ana Hesap Oluştur"):
            with st.form("create_crm_user", clear_on_submit=True):
                new_comp = st.text_input("Firma Adı")
                new_user = st.text_input("Kullanıcı Adı")
                new_pass = st.text_input("Şifre", type="password")
                new_email = st.text_input("E-Posta")
                
                # --- YENİ EKLENEN KISIM: API DROPDOWN ---
                # API'den grupları çek
                from backend.trusted_api import api_get_all_subgroups
                all_groups = api_get_all_subgroups()
                
                # Listeyi hazırla
                group_opts = {g["id"]: f"{g['name']} ({g['id']})" for g in all_groups}
                
                # Multiselect kutusu
                selected_new_gids = st.multiselect(
                    "Trusted Grupları (Şantiyeler)", 
                    options=list(group_opts.keys()),
                    format_func=lambda x: group_opts[x]
                )
                
                # Seçilenleri stringe çevir (Örn: "7153, 9840")
                new_gid_str = ", ".join(selected_new_gids)
                # ----------------------------------------
                
                if st.form_submit_button("Kaydet"):
                    if new_comp and new_user and new_pass:
                        db = SessionLocal()
                        try:
                            if db.query(User).filter((User.username == new_user) | (User.email == new_email)).first():
                                st.error("Bu kullanıcı zaten var!")
                            else:
                                u_id = f"u_{uuid.uuid4().hex[:8]}"
                                
                                # Grup ID Kontrolü
                                gid_value = new_gid_str if new_gid_str.strip() else None

                                nu = User(
                                    id=u_id, username=new_user, email=new_email,
                                    password_hash=get_password_hash(new_pass),
                                    role="Client", 
                                    trusted_group_id=gid_value, 
                                    company_name=new_comp, full_name=new_comp, is_active=True
                                )
                                db.add(nu)
                                db.commit()
                                st.success("Kullanıcı oluşturuldu!")
                                
                                # Otomatik Sync
                                if gid_value:
                                    success, msg = sync_devices_from_trusted_api(gid_value, u_id)
                                    if success: st.toast(msg)
                                    else: st.warning(f"Sync Uyarısı: {msg}")
                                
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

            # --- SEKMELİ YAPI (GÜNCELLENDİ) ---
            tab_info, tab_settings, tab_sub, tab_device, tab_action = st.tabs([
                "📝 Genel Bilgiler", 
                "⚙️ Ayarlar & Bildirim", 
                "👥 Alt Kullanıcılar", 
                "🚜 Cihaz & Sync", 
                "🕵️‍♂️ İşlemler"
            ])

            # TAB 1: GENEL BİLGİLER
            with tab_info:
                st.markdown("#### 🏢 Kurumsal ve Kişisel Bilgiler")
                with st.form("edit_general_info"):
                    c1, c2 = st.columns(2)
                    
                    with c1:
                        u_company = st.text_input("Firma Adı", value=target_user.company_name or "")
                        u_username = st.text_input("Ana Kullanıcı Adı", value=target_user.username, disabled=True)
                        u_first_name = st.text_input("Ad", value=target_user.first_name or "")
                        u_last_name = st.text_input("Soyad", value=target_user.last_name or "")
                        
                    with c2:
                        u_country = st.text_input("Ülke", value=target_user.country or "Türkiye")
                        u_email = st.text_input("E-Posta", value=target_user.email, disabled=True)
                        u_phone = st.text_input("Telefon", value=target_user.phone or "")
                        u_active = st.checkbox("Hesap Aktif", value=target_user.is_active)

                    st.markdown("---")
                    st.markdown("#### 🏭 Grup / Şantiye Erişimi")
                    
                    # --- YENİ GRUP SEÇİMİ (MULTI-SELECT) ---
                    # 1. API'den tüm grupları çek
                    from backend.trusted_api import api_get_all_subgroups
                    all_groups = api_get_all_subgroups()
                    
                    # 2. Seçenekleri Hazırla
                    group_options = {g["id"]: f"{g['name']} ({g['id']})" for g in all_groups}
                    
                    # 3. Mevcut kullanıcının gruplarını listeye çevir ("7153, 9840" -> ['7153', '9840'])
                    current_gids = []
                    if target_user.trusted_group_id:
                        current_gids = [gid.strip() for gid in str(target_user.trusted_group_id).split(',') if gid.strip()]
                    
                    # Eğer listede olmayan bir ID varsa (Eski veri), manuel ekle ki hata vermesin
                    for gid in current_gids:
                        if gid not in group_options:
                            group_options[gid] = f"Bilinmeyen Grup ({gid})"

                    # 4. Multiselect Göster
                    selected_gids = st.multiselect(
                        "Erişim verilecek grupları seçin:",
                        options=list(group_options.keys()), 
                        format_func=lambda x: group_options[x],
                        default=current_gids,
                        help="Listeden şantiye seçin. İptal etmek için ismin yanındaki (X) işaretine basın."
                    )
                    
                    # 5. Kaydedilecek String ("7153, 9840")
                    u_gid_str = ", ".join(selected_gids)
                    # -------------------------------------------

                    st.markdown("---")
                    st.markdown("#### 📄 Fatura Bilgileri")
                    f1, f2 = st.columns(2)
                    with f1:
                        u_tax_office = st.text_input("Vergi Dairesi", value=target_user.tax_office or "")
                        u_tax_no = st.text_input("Vergi Numarası", value=target_user.tax_no or "")
                    with f2:
                        u_address = st.text_area("Adres", value=target_user.company_address or "", height=100)

                    if st.form_submit_button("💾 Bilgileri Güncelle", type="primary"):
                        success, msg = update_user_admin_details(target_user.id, {
                            "company_name": u_company,
                            "first_name": u_first_name,
                            "last_name": u_last_name,
                            "country": u_country,
                            "phone": u_phone,
                            "is_active": u_active,
                            "tax_office": u_tax_office,
                            "tax_no": u_tax_no,
                            "company_address": u_address,
                            "trusted_group_id": u_gid_str # <-- GÜNCELLENMİŞ ID LİSTESİ
                        })
                        if success: st.success(msg); time.sleep(0.5); st.rerun()
                        else: st.error(msg)

            # TAB 2: AYARLAR & BİLDİRİM
            with tab_settings:
                # 1. BÖLÜM: SALT OKUNUR KULLANICI TERCİHLERİ
                st.markdown("#### 🌍 Kullanıcı Tercihleri (Görüntüleme)")
                st.info(f"""
                **Dil:** {target_user.language}  
                **Saat Dilimi:** {target_user.timezone}  
                **Tarih Formatı:** {target_user.date_format}  
                
                **📏 Birimler:** Uzunluk: `{target_user.unit_length}` | Sıcaklık: `{target_user.unit_temp}`  
                Basınç: `{target_user.unit_pressure}` | Hacim: `{target_user.unit_volume}`
                """)
                
                st.divider()
                
                # 2. BÖLÜM: BİLDİRİM TERCİHLERİ (EDİTLENEBİLİR)
                st.markdown("#### 🔔 Bildirim Yönetimi")
                with st.form("edit_notifications"):
                    st.write("**Genel Erişim**")
                    n_email = st.checkbox("📧 E-Posta Bildirimleri (Genel Açık/Kapalı)", value=target_user.notification_email_enabled)
                    
                    st.write("**Hangi Durumlarda Bildirim Gitsin?**")
                    col_n1, col_n2, col_n3 = st.columns(3)
                    
                    with col_n1:
                        n_batt = st.checkbox("🔋 Düşük Pil", value=target_user.notify_low_battery)
                        n_shock = st.checkbox("💥 Kritik Darbe/Şok", value=target_user.notify_shock)
                        n_geo = st.checkbox("🚧 Bölge İhlali", value=target_user.notify_geofence)
                        
                    with col_n2:
                        n_maint = st.checkbox("🛠️ Bakım Zamanı", value=target_user.notify_maintenance)
                        n_daily = st.checkbox("📅 Günlük Rapor", value=target_user.notify_daily_report)
                    
                    with col_n3:
                        n_weekly = st.checkbox("📊 Haftalık Rapor", value=target_user.notify_weekly_report)
                        n_monthly = st.checkbox("📈 Aylık Rapor", value=target_user.notify_monthly_report)
                        
                    if st.form_submit_button("💾 Bildirim Ayarlarını Kaydet"):
                        success, msg = update_user_admin_details(target_user.id, {
                            "notification_email_enabled": n_email,
                            "notify_low_battery": n_batt,
                            "notify_shock": n_shock,
                            "notify_geofence": n_geo,
                            "notify_maintenance": n_maint,
                            "notify_daily_report": n_daily,
                            "notify_weekly_report": n_weekly,
                            "notify_monthly_report": n_monthly
                        })
                        if success: st.success("Bildirim tercihleri güncellendi."); time.sleep(0.5); st.rerun()
                        else: st.error(msg)

            # TAB 3: ALT KULLANICILAR (SUB-USERS)
            with tab_sub:
                st.markdown(f"### 🔗 {target_user.company_name} - Alt Kullanıcıları")
                st.caption("Bu firmaya bağlı çalışan personeller.")

                # Veritabanından Alt Kullanıcıları Çek
                db = SessionLocal()
                sub_users = db.query(User).filter(User.parent_id == target_user.id).all()
                db.close()

                if sub_users:
                    for sub in sub_users:
                        with st.container(border=True):
                            sc1, sc2, sc3 = st.columns([2, 2, 1])
                            sc1.write(f"👤 **{sub.full_name}** ({sub.username})")
                            sc1.caption(sub.email)
                            
                            sc2.info(f"Rol: {sub.role}")
                            if sub.is_active: sc2.caption("🟢 Aktif")
                            else: sc2.caption("🔴 Pasif")
                            
                            if sc3.button("Sil", key=f"del_sub_{sub.id}"):
                                delete_user_from_db(sub.id)
                                st.rerun()
                else:
                    st.info("Bu kullanıcıya bağlı alt hesap bulunmuyor.")
                    
                st.divider()
                st.markdown("#### ➕ Yeni Alt Kullanıcı Ekle")
                with st.form("add_sub_user_form"):
                    s_name = st.text_input("Ad Soyad")
                    s_user = st.text_input("Kullanıcı Adı (Benzersiz)")
                    s_mail = st.text_input("E-Posta")
                    s_pass = st.text_input("Şifre", type="password")
                    
                    if st.form_submit_button("Alt Kullanıcıyı Oluştur"):
                        if s_name and s_user and s_pass:
                            ok, msg = create_sub_user(target_user, s_user, s_pass, s_mail, s_name)
                            if ok: st.success(msg); time.sleep(1); st.rerun()
                            else: st.error(msg)
                        else:
                            st.warning("Lütfen tüm alanları doldurun.")

            # TAB 4: CİHAZ & SYNC
            with tab_device:
                # Sadece Bilgi Göster
                st.info(f"📂 **Tanımlı Gruplar:** `{target_user.trusted_group_id}`")
                st.caption("Grupları değiştirmek için 'Genel Bilgiler' sekmesini kullanın.")
                
                if not target_user.trusted_group_id:
                    st.warning("⚠️ Henüz bir grup tanımlanmamış.")
                
                st.divider()

                # Sync Butonu
                if st.button("🔄 Cihazları ve Geçmişi (Full) Senkronize Et", use_container_width=True, type="primary"):
                    if target_user.trusted_group_id and str(target_user.trusted_group_id).strip():
                        info_placeholder = st.empty()
                        info_placeholder.warning("⏳ İşlem Başlatıldı... (3-4 dk sürebilir)")
                        
                        with st.spinner("Trusted API ile konuşuluyor..."):
                            success, msg = sync_devices_from_trusted_api(target_user.trusted_group_id, target_user.id)
                            
                            if success:
                                info_placeholder.success(msg)
                                time.sleep(2)
                                st.rerun()
                            else:
                                info_placeholder.error(msg)
                    else:
                        st.error("Lütfen önce geçerli bir Trusted Group ID tanımlayın.")

                # MEVCUT CİHAZ TABLOSU (Aynen Devam Ediyor...)
                st.markdown("---")
                st.markdown("### 📋 Mevcut Cihazlar")
                
                db = SessionLocal()
                devices = db.query(Device).filter(Device.owner_id == target_user.id).all()
                db.close()
                
                if devices:
                    # Başlıklar
                    h1, h2, h3, h4, h5 = st.columns([2, 1.5, 1.5, 2, 0.5])
                    h1.markdown("**Cihaz Adı**")
                    h2.markdown("**Seri No**")
                    h3.markdown("**Model**")
                    h4.markdown("**Tanımlı Tip**")
                    h5.markdown("**Düz.**")
                    st.divider()

                    for dev in devices:
                        c1, c2, c3, c4, c5 = st.columns([2, 1.5, 1.5, 2, 0.5])
                        c1.write(f"**{dev.unit_name}**")
                        c2.code(dev.device_id)
                        c3.write(dev.asset_model or "-")
                        
                        label = ICON_OPTIONS.get(dev.icon_type, f"{dev.icon_type}")
                        c4.info(label)

                        with c5:
                            with st.popover("✏️", use_container_width=True):
                                st.markdown(f"**{dev.unit_name}**")
                                with st.form(key=f"edit_{dev.device_id}"):
                                    new_n = st.text_input("Ad", value=dev.unit_name)
                                    new_m = st.text_input("Model", value=dev.asset_model or "")
                                    
                                    try: curr_idx = list(ICON_OPTIONS.keys()).index(dev.icon_type)
                                    except: curr_idx = 0

                                    new_t = st.selectbox("Tip", list(ICON_OPTIONS.keys()), format_func=lambda x: ICON_OPTIONS[x], index=curr_idx)

                                    if st.form_submit_button("Kaydet"):
                                        ok, msg = update_device_metadata(dev.device_id, new_n, new_t, new_m)
                                        if ok: st.success("OK"); time.sleep(0.5); st.rerun()
                    
                    # MANUEL SİLME KUTUSU (GÜVENLİ)
                    st.divider()
                    dev_options = {f"{d.unit_name} ({d.device_id})": d.device_id for d in devices}
                    selected_devs_to_del = st.multiselect("Cihazları Kullanıcıdan Çıkar:", list(dev_options.keys()))
                    
                    if selected_devs_to_del:
                        if st.button("Kullanıcıdan Çıkar (Veriyi Sakla)", type="primary"):
                            db = SessionLocal()
                            for k in selected_devs_to_del:
                                dev_id = dev_options[k]
                                dev = db.query(Device).filter(Device.device_id == dev_id).first()
                                if dev:
                                    dev.owner_id = "s.ozsarac" # Varsayılan Admin'e at
                            db.commit()
                            db.close()
                            st.success("Cihazlar ayrıldı.")
                            time.sleep(1)
                            st.rerun()
                else:
                    st.info("Cihaz bulunamadı.")

            # TAB 5: İŞLEMLER / SİL
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
                    st.session_state["last_selected_admin_user"] = selected_option_key
                    st.session_state["original_admin"] = current_user
                    st.session_state["user"] = target_user
                    st.session_state["menu_selection"] = "👥 Müşteri Yönetimi" 
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
                                time.sleep(2)
                                st.rerun()
                            else:
                                st.error(msg)