import streamlit as st
import google.generativeai as genai
import os

# --- AYARLAR ---
GEMINI_API_KEY = "AIzaSyAYuLs3D4rwMW3CxAdSI-QvuInjVHfJay0" 

# Bilgi Bankasını İçe Aktar (Eğer varsa)
try:
    from frontend.data.hkm_products import HKM_KNOWLEDGE_BASE
except ImportError:
    HKM_KNOWLEDGE_BASE = "Genel hidrolik prensipleri geçerlidir."

# --- SİSTEM TALİMATI ---
SYSTEM_INSTRUCTION = f"""
### KİMLİK VE ROL
Sen, Solidus (www.solidus.work) firmasına ait "SolidTrack" filo yönetim sisteminin Uzman Yapay Zeka Asistanısın. İsmin "SolidAI". Solidus ve HKM Hidrolik kardeş firmalardır.
Görevin; kullanıcılara hidrolik kırıcılar, ataşmanlar ve SolidTrack yazılımı hakkında teknik destek vermek, verileri yorumlamak ve bakım tavsiyeleri sunmaktır.

### BİLGİ BANKASI (REFERANS KAYNAĞIN)
{HKM_KNOWLEDGE_BASE}

### DİL VE TON
* **Adaptasyon:** Kullanıcı hangi dilde sorarsa o dilde cevap ver.
* **Ton:** Profesyonel, teknik, yardımsever ve kurumsal. Asla laubali olma.

### YETKİ VE BİLGİ ALANLARI
1.  **SolidTrack Yazılımı:** Harita takibi, geçmiş rota, raporlama, alarm yönetimi.
2.  **Kırıcı ve Ataşman Bakımı:** Gresleme, uç değişimi, azot gazı, burç kontrolü.
3.  **Operasyonel İpuçları:** Boşa vurma (blank firing) önleme, doğru çalışma açısı.
4.  **Veri Analizi:** Operasyonel verilerin verimlilik yorumlaması.

### KISITLAMALAR
* Politika, spor, yemek tarifi gibi konulara nazikçe cevap veremeyeceğini belirt.
* Rakip markalar hakkında yorum yapma.
* Bakım konularında kesin yargı yerine "kontrol edilmelidir" dilini kullan.
"""

def load_view(user):
    # --- SAYFA STİLİ ---
    st.markdown("""
        <style>
        .stChatMessage {
            padding: 1rem;
            border-radius: 10px;
            margin-bottom: 10px;
        }
        .stChatMessage[data-testid="chat-message-user"] {
            background-color: #f0f2f6;
            border-left: 5px solid #333;
        }
        .stChatMessage[data-testid="chat-message-assistant"] {
            background-color: #e8f0fe;
            border-left: 5px solid #1976D2;
        }
        </style>
    """, unsafe_allow_html=True)

    # --- HEADER ---
    c1, c2, c3 = st.columns([1, 6, 2])
    with c1:
        st.write("🤖") # İstersen buraya resim linki de koyabilirsin
    with c2:
        st.title("SolidAI Asistan")
        st.caption("HKM & Solidus Teknik Bilgi Merkezi")
    with c3:
        if st.button("🗑️ Sohbeti Temizle", use_container_width=True):
            st.session_state.chat_history = []
            st.rerun()

    st.markdown("---")

    # --- API KEY KONTROLÜ ---
    if "GEMINI_API_KEY" in os.environ:
        api_key = os.environ["GEMINI_API_KEY"]
    else:
        api_key = GEMINI_API_KEY

    if not api_key or "BURAYA" in api_key:
        st.warning("⚠️ API Anahtarı eksik.")
        return

    # --- GEMINI BAĞLANTISI ---
    try:
        genai.configure(api_key=api_key)
        generation_config = {"temperature": 0.3, "max_output_tokens": 8192}
        
        # En stabil model seçimi
        model = genai.GenerativeModel(
            model_name="gemini-flash-latest", 
            generation_config=generation_config,
            system_instruction=SYSTEM_INSTRUCTION
        )
    except Exception as e:
        st.error(f"Bağlantı Hatası: {e}")
        return

    # --- SOHBET GEÇMİŞİ BAŞLAT ---
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
        
        # DÜZELTİLEN KISIM BURASI 👇
        welcome = "Merhaba! 👋 Ben SolidAI. SolidTrack sistemi, hidrolik kırıcı bakımı veya operasyonel verilerinizle ilgili size nasıl yardımcı olabilirim?"
        
        st.session_state.chat_history.append({"role": "assistant", "content": welcome})

    # --- MESAJLARI GÖSTER ---
    for message in st.session_state.chat_history:
        role = message["role"]
        avatar = "👤" if role == "user" else "🤖"
        
        with st.chat_message(role, avatar=avatar):
            st.markdown(message["content"])

    # --- SORU ALAN KISMI ---
    if prompt := st.chat_input("Bir soru sorun..."):
        
        # 1. Kullanıcı Mesajı
        st.session_state.chat_history.append({"role": "user", "content": prompt})
        with st.chat_message("user", avatar="👤"):
            st.markdown(prompt)

        # 2. AI Cevabı
        with st.chat_message("assistant", avatar="🤖"):
            message_placeholder = st.empty()
            full_response = ""
            
            try:
                # Geçmişi formatla
                history_model = []
                for msg in st.session_state.chat_history:
                    role_api = "user" if msg["role"] == "user" else "model"
                    history_model.append({"role": role_api, "parts": [msg["content"]]})
                
                chat = model.start_chat(history=history_model[:-1])
                response = chat.send_message(prompt, stream=True)
                
                for chunk in response:
                    if chunk.text:
                        full_response += chunk.text
                        message_placeholder.markdown(full_response + "▌")
                
                message_placeholder.markdown(full_response)
                
                # Cevabı kaydet
                st.session_state.chat_history.append({"role": "assistant", "content": full_response})

            except Exception as e:
                err_msg = str(e)
                if "429" in err_msg:
                    st.error("⚠️ Çok fazla istek gönderildi. Lütfen biraz bekleyin.")
                else:
                    st.error(f"Hata: {err_msg}")