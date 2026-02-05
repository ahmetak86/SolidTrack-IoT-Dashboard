# fix_db_v3.py
import sqlite3

DB_NAME = "backend/solidtrack.db"

def add_col(cursor, table, col_name, col_type):
    try:
        cursor.execute(f"ALTER TABLE {table} ADD COLUMN {col_name} {col_type}")
        print(f"✅ {col_name} eklendi.")
    except sqlite3.OperationalError:
        print(f"ℹ️ {col_name} zaten var.")

conn = sqlite3.connect(DB_NAME)
c = conn.cursor()

print("Veritabanı V3 Güncellemesi...")
add_col(c, "users", "first_name", "TEXT")
add_col(c, "users", "last_name", "TEXT")
add_col(c, "users", "country", "TEXT")
add_col(c, "users", "notify_weekly_report", "BOOLEAN")
add_col(c, "users", "notify_monthly_report", "BOOLEAN")

conn.commit()
conn.close()
print("🎉 Bitti!")