import sqlite3

DB_NAME = "backend/solidtrack.db"

conn = sqlite3.connect(DB_NAME)
c = conn.cursor()

print("Veritabanı V4 (Multi-Group) Güncellemesi...")

try:
    # Mevcut kullanıcıların group_id'lerini kontrol et
    # Integer olanları String'e çevirmemiz gerekmez (SQLite otomatik yapar)
    # Ama "0" olanları temizleyebiliriz.
    
    c.execute("SELECT id, trusted_group_id FROM users")
    users = c.fetchall()
    
    count = 0
    for u_id, gid in users:
        # Eğer gid 0 veya "0" ise veya None ise
        if gid == 0 or gid == "0" or gid is None:
            c.execute("UPDATE users SET trusted_group_id = ? WHERE id = ?", ("", u_id))
            count += 1
        else:
            # Mevcut ID'yi string'e çevirip tekrar yaz (Garanti olsun)
            new_gid = str(gid)
            c.execute("UPDATE users SET trusted_group_id = ? WHERE id = ?", (new_gid, u_id))

    conn.commit()
    print(f"✅ {count} kullanıcının varsayılan ID'si (0) temizlendi.")
    print("✅ Group ID sütunu artık '7153, 9840' formatını destekliyor.")

except Exception as e:
    print(f"❌ Hata: {e}")

conn.close()