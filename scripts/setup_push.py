import requests

# Senin güncel ngrok adresin
WEBHOOK_URL = "https://elfrieda-prediscountable-iconically.ngrok-free.dev/api/push/trusted"

def setup_push_subscription():
    # 1. Token Al (trusted_api.py'daki mantıkla aynı)
    print("🔑 Trusted API'ye giriş yapılıyor...")
    auth_payload = {
        "grant_type": "password", 
        "username": "s.ozsarac@hkm.com.tr", 
        "password": "Solid_2023"
    }
    try:
        token_res = requests.post("https://api.trusted.dk/token", data=auth_payload)
        token_res.raise_for_status()
        token = token_res.json().get("access_token")
        print("✅ Token alındı.")
    except Exception as e:
        print(f"❌ Giriş Hatası: {e}")
        return

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    # 2. Push aboneliği oluştur (push5.pdf dökümanına göre)
    # GroupId 9840 senin ana grubun
    push_config = {
        "Name": "SolidTrack_FelTech_Push",
        "Url": WEBHOOK_URL,
        "GroupId": 9840,
        "PushUtilization": True  # Kullanım verilerini de gönder
    }

    print(f"📡 Webhook adresi kaydediliyor: {WEBHOOK_URL}")
    try:
        response = requests.post(
            "https://api.trusted.dk/api/Push/Post", 
            json=push_config, 
            headers=headers
        )
        
        if response.status_code in [200, 201, 204]:
            print("🎉 BAŞARILI! Trusted artık verileri bu tünele akıtacak.")
        else:
            print(f"⚠️ API Yanıtı ({response.status_code}): {response.text}")
            
    except Exception as e:
        print(f"❌ Kayıt sırasında hata: {e}")

if __name__ == "__main__":
    setup_push_subscription()