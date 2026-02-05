# fix_db_v2.py
import sqlite3

DB_NAME = "backend/solidtrack.db"

def add_column_if_not_exists(cursor, table, col_name, col_type):
    try:
        cursor.execute(f"ALTER TABLE {table} ADD COLUMN {col_name} {col_type}")
        print(f"✅ {col_name} eklendi.")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e):
            print(f"ℹ️ {col_name} zaten var.")
        else:
            print(f"❌ Hata ({col_name}): {e}")

conn = sqlite3.connect(DB_NAME)
cursor = conn.cursor()

print("Veritabanı V2 Güncellemesi Başlıyor...")

# User Tablosuna Yeni Sütunlar
add_column_if_not_exists(cursor, "users", "parent_id", "TEXT")
add_column_if_not_exists(cursor, "users", "tax_no", "TEXT")
add_column_if_not_exists(cursor, "users", "tax_office", "TEXT")
add_column_if_not_exists(cursor, "users", "billing_address", "TEXT")
add_column_if_not_exists(cursor, "users", "phone", "TEXT")
add_column_if_not_exists(cursor, "users", "company_address", "TEXT")

conn.commit()
conn.close()
print("🎉 Güncelleme Tamamlandı! Artık uygulamayı çalıştırabilirsin.")