import requests
import sqlite3
import os
import json
import uuid # <-- EKLENDİ
from datetime import datetime, timedelta

# --- AYARLAR ---
API_USERNAME = "s.ozsarac@hkm.com.tr"
API_PASSWORD = "Solid_2023"
TARGET_DEVICE_ID = "865456055312555" 

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
DB_PATH = os.path.join(BASE_DIR, "backend", "solidtrack.db")

def get_token():
    try:
        payload = {'grant_type': 'password', 'username': API_USERNAME, 'password': API_PASSWORD}
        resp = requests.post("https://api.trusted.dk/Token", data=payload, timeout=10)
        if resp.status_code == 200:
            return resp.json().get('access_token')
        print(f"❌ Token Hatası: {resp.text}")
    except Exception as e:
        print(f"❌ Bağlantı Hatası: {e}")
    return None

def setup_db(cursor):
    # Accelerometer Tablosu (Varsa dokunmaz, yoksa yaratır)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS accelerometer_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        device_id TEXT,
        timestamp DATETIME,
        x_axis REAL,
        y_axis REAL,
        z_axis REAL,
        impact_g REAL,
        raw_data TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """)

def parse_trusted_date(date_str):
    if not date_str: return None
    try:
        clean = date_str.replace("Z", "")
        if "." in clean:
            return datetime.strptime(clean, "%Y-%m-%dT%H:%M:%S.%f")
        return datetime.strptime(clean, "%Y-%m-%dT%H:%M:%S")
    except:
        return None

def run_super_recovery():
    print(f"🚀 SUPER RECOVERY BAŞLADI: {TARGET_DEVICE_ID}")
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Sanal Cihaz Kontrolü
    cursor.execute("SELECT is_virtual FROM devices WHERE device_id=?", (TARGET_DEVICE_ID,))
    row = cursor.fetchone()
    if row and row[0] == 1:
        print("🛑 UYARI: Bu bir SANAL CİHAZ. İşlem iptal.")
        conn.close()
        return

    setup_db(cursor)
    token = get_token()
    if not token: 
        conn.close() 
        return

    headers = {'Authorization': f'Bearer {token}', 'Accept': 'application/json'}
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=365)
    
    # ---------------------------------------------------------
    # A. KONUM (Positions)
    # ---------------------------------------------------------
    print("\n🌍 1/3: Konum Verileri (Positions)...")
    url = "https://api.trusted.dk/api/Positions/Get"
    params = {
        "SerialNumber": TARGET_DEVICE_ID,
        "AfterDate": start_date.strftime("%Y-%m-%dT%H:%M:%S"),
        "BeforeDate": end_date.strftime("%Y-%m-%dT%H:%M:%S"),
        "Count": 100000,
        "SortDescending": "false"
    }
    
    try:
        r = requests.get(url, headers=headers, params=params, timeout=60)
        if r.status_code == 200:
            data = r.json()
            c = 0
            if isinstance(data, list):
                for item in data:
                    ts = parse_trusted_date(item.get("Timestamp"))
                    if not ts: continue
                    
                    # Mükerrer Kontrolü (DeviceID + Timestamp)
                    cursor.execute("SELECT 1 FROM telemetry_logs WHERE device_id=? AND timestamp=?", (TARGET_DEVICE_ID, ts))
                    if not cursor.fetchone():
                        # DÜZELTME: log_id eklendi, created_at kaldırıldı, speed_kmh kullanıldı
                        new_id = str(uuid.uuid4())
                        cursor.execute("""
                            INSERT INTO telemetry_logs (
                                log_id, device_id, timestamp, latitude, longitude, speed_kmh
                            ) VALUES (?, ?, ?, ?, ?, ?)
                        """, (
                            new_id, TARGET_DEVICE_ID, ts, 
                            item.get("Latitude"), item.get("Longitude"), 
                            item.get("Speed", 0)
                        ))
                        c += 1
                conn.commit()
                print(f"✅ {c} yeni konum eklendi.")
    except Exception as e:
        print(f"❌ Konum hatası: {e}")

    # ---------------------------------------------------------
    # B. SENSÖR (Sıcaklık ve Pil)
    # ---------------------------------------------------------
    print("\n🌡️ 2/3: Sensör Verileri (Sıcaklık & Pil)...")
    url = "https://api.trusted.dk/api/SensorData/Get"
    params["Count"] = 100000
    
    try:
        r = requests.get(url, headers=headers, params=params, timeout=60)
        if r.status_code == 200:
            data = r.json()
            upd = 0
            ins = 0
            if isinstance(data, list):
                for item in data:
                    ts = parse_trusted_date(item.get("Timestamp") or item.get("ServerDate"))
                    if not ts: continue
                    
                    val_temp = None
                    val_batt = None
                    
                    stype = item.get("Type", "")
                    val = item.get("Value")
                    
                    if "Temperature" in stype: val_temp = val
                    if "Battery" in stype: val_batt = val
                    if val_temp is None: val_temp = item.get("Temperature")
                    if val_batt is None: val_batt = item.get("BatteryVoltage")

                    if val_temp is None and val_batt is None: continue

                    cursor.execute("SELECT 1 FROM telemetry_logs WHERE device_id=? AND timestamp=?", (TARGET_DEVICE_ID, ts))
                    if cursor.fetchone():
                        # UPDATE (Sütun isimleri düzeltildi: temp_c, battery_pct)
                        if val_temp: cursor.execute("UPDATE telemetry_logs SET temp_c=? WHERE device_id=? AND timestamp=?", (val_temp, TARGET_DEVICE_ID, ts))
                        if val_batt: cursor.execute("UPDATE telemetry_logs SET battery_pct=? WHERE device_id=? AND timestamp=?", (val_batt, TARGET_DEVICE_ID, ts))
                        upd += 1
                    else:
                        # INSERT (log_id eklendi, created_at silindi)
                        new_id = str(uuid.uuid4())
                        cursor.execute("""
                            INSERT INTO telemetry_logs (log_id, device_id, timestamp, temp_c, battery_pct)
                            VALUES (?, ?, ?, ?, ?)
                        """, (new_id, TARGET_DEVICE_ID, ts, val_temp, val_batt))
                        ins += 1
                conn.commit()
                print(f"✅ {upd} güncellendi, {ins} eklendi.")
    except Exception as e:
        print(f"❌ Sensör hatası: {e}")

    # ---------------------------------------------------------
    # C. DARBE (Accelerometer)
    # ---------------------------------------------------------
    print("\n💥 3/3: Kaza/Darbe Verileri...")
    url = "https://api.trusted.dk/api/SensorData/AccelerometerHistogramData"
    p_accel = {
        "serialNumber": TARGET_DEVICE_ID,
        "afterDate": params["AfterDate"],
        "beforeDate": params["BeforeDate"]
    }
    
    try:
        r = requests.get(url, headers=headers, params=p_accel, timeout=60)
        if r.status_code == 200:
            data = r.json()
            ac = 0
            if isinstance(data, list):
                for item in data:
                    ts = parse_trusted_date(item.get("Timestamp") or item.get("Date"))
                    cursor.execute("""
                        INSERT INTO accelerometer_logs (device_id, timestamp, raw_data)
                        VALUES (?, ?, ?)
                    """, (TARGET_DEVICE_ID, ts, json.dumps(item)))
                    ac += 1
                conn.commit()
                print(f"✅ {ac} darbe verisi eklendi.")
    except Exception as e:
        print(f"❌ Darbe hatası: {e}")

    conn.close()
    print("\n🎉 İŞLEM BİTTİ.")

if __name__ == "__main__":
    run_super_recovery()