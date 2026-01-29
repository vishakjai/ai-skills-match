import os
import psycopg2
from dotenv import load_dotenv

# Load Env
load_dotenv()

DB_URL = os.getenv("SUPABASE_URL")
if not DB_URL:
    print("❌ Error: SUPABASE_URL not found in .env")
    exit(1)

# Paths to SQL files
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SCHEMA_SQL = os.path.join(BASE_DIR, "../core/graph_schema.sql")
SEED_SQL = os.path.join(BASE_DIR, "../core/ontology_seed.sql")

def run_sql_file(cursor, filepath):
    print(f"📄 Reading {filepath}...")
    with open(filepath, "r") as f:
        sql = f.read()
    
    print(f"🚀 Executing {filepath}...")
    cursor.execute(sql)
    print("✅ Done.")

def main():
    try:
        print("🔌 Connecting to Database...")
        conn = psycopg2.connect(DB_URL)
        cur = conn.cursor()
        
        # 1. Run Schema
        run_sql_file(cur, SCHEMA_SQL)
        
        # 2. Run Seed
        run_sql_file(cur, SEED_SQL)
        
        conn.commit()
        print("🎉 Database Seeded Successfully!")
        
        cur.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ Database Error: {e}")
        exit(1)

if __name__ == "__main__":
    main()
