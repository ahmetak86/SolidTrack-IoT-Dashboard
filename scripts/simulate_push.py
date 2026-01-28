import requests
import json
import random
from datetime import datetime

# BURAYA KENDİ NGROK ADRESİNİ YAPIŞTIR (Sonunda /api/push/trusted kalsın)
WEBHOOK_URL = "https://elfrieda-prediscountable-iconically.ngrok-free.dev/api/push/trusted"

# Test için gerçek bir cihazının seri numarasını yazarsan DB'ye de kaydeder.
# Yoksa sadece terminalde log görürsün, DB hata verebilir (önemli değil).
TEST_SERIAL = "TEST_CIHAZ_001" 

def send_fake_push():
    print(f"🚀 Simülasyon verisi hazırlanıyor: {TEST_SERIAL}")
    
    # Trusted Global Push Formatı (Position + Status)
    payload = [{
        "SerialNumber": TEST_SERIAL,
        "Timestamp": datetime.utcnow().isoformat() + "Z",
        "Latitude": 41.0082 + random.uniform(-0.01, 0.01),  # İstanbul civarı rastgele
        "Longitude": 28.9784 + random.uniform(-0.01, 0.01),
        "Speed": random.randint(0, 100),
        "BatteryLevel": random.randint(10, 100),
        "Temperature": 25,
        "MaxAcceleration": 0.5
    }]

    print(f"📡 Gönderiliyor: {WEBHOOK_URL}...")
    try:
        response = requests.post(WEBHOOK_URL, json=payload, timeout=10)
        
        if response.status_code == 200:
            print("✅ BAŞARILI! Sunucu kabul etti (200 OK).")
            print("👉 Şimdi Server terminaline bak, 'Push Alındı' yazmalı!")
        else:
            print(f"⚠️ Sunucu reddetti: {response.status_code}")
            print(f"Cevap: {response.text}")
            
    except Exception as e:
        print(f"❌ Bağlantı Hatası: {e}")

if __name__ == "__main__":
    send_fake_push()