import sqlite3
import os
import pandas as pd

# Veritabanı yolunu bul
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "backend", "solidtrack.db")

def check_device(search_term):
    if not os.path.exists(DB_PATH):
        print(f"❌ HATA: Veritabanı bulunamadı: {DB_PATH}")
        return

    print(f"📂 Veritabanına Bağlanılıyor: {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    print(f"\n🔍 Arama Terimi: '{search_term}'\n" + "-"*40)

    # 1. CİHAZI BUL
    # unit_name içinde arama yapıyoruz
    cursor.execute("SELECT device_id, unit_name, owner_id, is_active FROM devices WHERE unit_name LIKE ?", (f'%{search_term}%',))
    devices = cursor.fetchall()

    if not devices:
        print("❌ CİHAZ BULUNAMADI! Veritabanında bu isimle eşleşen kayıt yok.")
        print("   -> Admin Panelinden 'Sync' yaparak cihazı tekrar oluşturmalısınız.")
    else:
        for dev in devices:
            dev_id, name, owner, active = dev
            print(f"✅ CİHAZ BULUNDU:")
            print(f"   - Adı: {name}")
            print(f"   - ID (Serial): {dev_id}")
            print(f"   - Sahibi (Owner ID): {owner} {'(⚠️ SAHİPSİZ!)' if not owner else ''}")
            print(f"   - Durum (Active): {active} {'(⚠️ PASİF!)' if not active else ''}")
            
            # 2. TELEMETRY LOGLARI (Konum, Isı vb.)
            cursor.execute("SELECT count(*), min(timestamp), max(timestamp) FROM telemetry_logs WHERE device_id = ?", (dev_id,))
            telem_count, t_min, t_max = cursor.fetchone()
            print(f"\n   📊 TELEMETRY VERİSİ (Konum/Isı):")
            print(f"      - Toplam Kayıt: {telem_count}")
            print(f"      - Tarih Aralığı: {t_min}  <-->  {t_max}")

            # 3. UTILIZATION LOGLARI (Çalışma Saatleri)
            # Tablo adı utilization_events veya utilization_logs olabilir, ikisine de bakalım
            try:
                cursor.execute("SELECT count(*), min(start_time), max(end_time) FROM utilization_events WHERE device_id = ?", (dev_id,))
                util_count, u_min, u_max = cursor.fetchone()
                print(f"\n   📈 UTILIZATION VERİSİ (Çalışma Saati):")
                print(f"      - Toplam Kayıt: {util_count}")
                print(f"      - Tarih Aralığı: {u_min}  <-->  {u_max}")
            except:
                print("\n   ⚠️ Utilization tablosu sorgulanamadı (Tablo adı farklı olabilir).")

    conn.close()
    print("\n" + "-"*40)

if __name__ == "__main__":
    # Aramak istediğin cihazın adını buraya yaz
    target_name = "TRISP"  
    check_device(target_name)