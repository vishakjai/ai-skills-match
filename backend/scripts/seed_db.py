import os
import psycopg2
from pathlib import Path

def normalize_db_url():
    # Same logic as init_db to handle @ in password
    env_path = Path(__file__).parent.parent / ".env"
    with open(env_path) as f:
        for line in f:
            if line.startswith("SUPABASE_URL="):
                raw = line.strip().split("=", 1)[1]
                if raw.startswith("postgresql://"): raw = raw[len("postgresql://"):]
                creds, host_part = raw.rsplit("@", 1)
                user, password = creds.split(":", 1)
                if "/" in host_part: host_port, dbname = host_part.split("/", 1)
                else: host_port, dbname = host_part, "postgres"
                if ":" in host_port: host, port = host_port.split(":", 1)
                else: host, port = host_port, 5432
                return dbname, user, password, host, port
    return None

def seed_db():
    try:
        dbname, user, password, host, port = normalize_db_url()
        conn = psycopg2.connect(dbname=dbname, user=user, password=password, host=host, port=port)
        cur = conn.cursor()
        
        print("🌱 Seeding Database...")
        
        # 1. Insert Nodes
        skills = [
            ("python", "Python", "language"),
            ("react", "React", "framework"),
            ("docker", "Docker", "tool"),
            ("kubernetes", "Kubernetes", "tool"),
            ("fastapi", "FastAPI", "framework")
        ]
        
        node_map = {} # slug -> uuid
        
        for slug, name, cat in skills:
            # Upsert
            cur.execute("""
                INSERT INTO skill_nodes (slug, canonical_name, category)
                VALUES (%s, %s, %s)
                ON CONFLICT (slug) DO UPDATE SET canonical_name = EXCLUDED.canonical_name
                RETURNING id;
            """, (slug, name, cat))
            node_id = cur.fetchone()[0]
            node_map[slug] = node_id
            
        # 2. Insert Aliases
        aliases = [
            ("React.js", "react"),
            ("ReactJS", "react"),
            ("k8s", "kubernetes"),
            ("K8s", "kubernetes"),
            ("Py", "python")
        ]
        
        for alias, slug in aliases:
            if slug in node_map:
                cur.execute("""
                    INSERT INTO skill_aliases (alias, skill_id)
                    VALUES (%s, %s)
                    ON CONFLICT (alias, skill_id) DO NOTHING;
                """, (alias, node_map[slug]))
                
        conn.commit()
        cur.close()
        conn.close()
        print("✅ Database seeded successfully!")
        
    except Exception as e:
        print(f"❌ Seeding failed: {e}")

if __name__ == "__main__":
    seed_db()
