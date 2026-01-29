import os
import psycopg2
from pathlib import Path
from urllib.parse import urlparse, unquote

def init_db():
    env_path = Path(__file__).parent.parent / ".env"
    db_url_raw = None
    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                if line.startswith("SUPABASE_URL="):
                    db_url_raw = line.strip().split("=", 1)[1]
                    break
    
    if not db_url_raw:
        print("Error: SUPABASE_URL not found in backend/.env")
        return

    # Robust Parsing
    # remove prefix
    if db_url_raw.startswith("postgresql://"):
        core = db_url_raw[len("postgresql://"):]
    else:
        core = db_url_raw

    # Split into Creds and Host (Split from RIGHT to handle @ in password)
    # format: user:password@host:port/dbname
    try:
        creds, host_part = core.rsplit("@", 1)
        user, password = creds.split(":", 1)
        
        # Check if password needs unquoting? Usually raw in .env means raw.
        # But psycopg2 expects a DSN or kwargs.
        # We will pass kwargs to be safe.
        
        # Parse Host Part
        if "/" in host_part:
            host_port, dbname = host_part.split("/", 1)
        else:
            host_port = host_part
            dbname = "postgres"
            
        if ":" in host_port:
            host, port = host_port.split(":", 1)
        else:
            host = host_port
            port = 5432
            
    except ValueError:
       print("❌ Could not parse connection string. Please check format.")
       return

    print(f"Connecting to DB Host: {host} as user: {user}...")
    
    try:
        conn = psycopg2.connect(
            dbname=dbname,
            user=user,
            password=password,
            host=host,
            port=port
        )
        cur = conn.cursor()
        
        schema_path = Path(__file__).parent.parent / "supabase_schema.sql"
        print(f"Reading schema from {schema_path}...")
        with open(schema_path, "r") as f:
            schema_sql = f.read()
            
        print("Executing Schema...")
        cur.execute(schema_sql)
        conn.commit()
        
        cur.close()
        conn.close()
        print("✅ Database initialized successfully!")
        
    except Exception as e:
        print(f"❌ Database initialization failed: {e}")

if __name__ == "__main__":
    init_db()
