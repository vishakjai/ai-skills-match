"""
Run the application-tables migration.

Usage (from backend/ with venv active):
    python -m src.scripts.migrate_app_tables
"""
import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

DB_URL = os.getenv("SUPABASE_URL")
if not DB_URL:
    print("❌ Error: SUPABASE_URL not found in .env")
    exit(1)

SQL_FILE = os.path.join(os.path.dirname(__file__), "create_app_tables.sql")

def main():
    try:
        print("🔌 Connecting to Database...")
        conn = psycopg2.connect(DB_URL)
        cur = conn.cursor()

        print(f"📄 Reading {SQL_FILE}...")
        with open(SQL_FILE, "r") as f:
            sql = f.read()

        print("🚀 Executing migration...")
        cur.execute(sql)
        conn.commit()
        print("🎉 Application tables created successfully!")

        cur.close()
        conn.close()

    except Exception as e:
        print(f"❌ Migration Error: {e}")
        exit(1)

if __name__ == "__main__":
    main()
