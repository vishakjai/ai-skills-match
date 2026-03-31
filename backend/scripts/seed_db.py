import csv
import re
import json
import psycopg2
from psycopg2.extras import execute_values
from pathlib import Path

def normalize_db_url():
    env_path = Path(__file__).parent.parent / ".env"
    with open(env_path) as f:
        for line in f:
            if line.startswith("SUPABASE_URL="):
                raw = line.strip().split("=", 1)[1]
                if raw.startswith("postgresql://"):
                    raw = raw[len("postgresql://"):]
                creds, host_part = raw.rsplit("@", 1)
                user, password = creds.split(":", 1)
                if "/" in host_part:
                    host_port, dbname = host_part.split("/", 1)
                else:
                    host_port, dbname = host_part, "postgres"
                if ":" in host_port:
                    host, port = host_port.split(":", 1)
                else:
                    host, port = host_port, 5432
                return dbname, user, password, host, port
    return None

def slugify(text: str) -> str:
    text = (text or "").strip().lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    text = re.sub(r"-+", "-", text).strip("-")
    return text[:200]

def upsert_node_by_slug(cur, name: str, category: str) -> str | None:
    """
    Current DB schema:
      skill_nodes(slug TEXT, name TEXT, category TEXT)
    Returns slug.
    """
    slug = slugify(name)
    if not slug:
        return None

    # Upsert by slug (assumes slug is UNIQUE or PRIMARY KEY)
    cur.execute(
        """
        INSERT INTO skill_nodes (slug, name, category)
        VALUES (%s, %s, %s)
        ON CONFLICT (slug) DO UPDATE
          SET name = EXCLUDED.name,
              category = EXCLUDED.category
        """,
        (slug, name.strip(), category)
    )
    return slug

def seed_demo_skills(cur):
    print("🌱 Seeding demo skills (slug-based schema)...")

    skills = [
        ("python", "Python", "language"),
        ("react", "React", "framework"),
        ("docker", "Docker", "tool"),
        ("kubernetes", "Kubernetes", "tool"),
        ("fastapi", "FastAPI", "framework"),
    ]

    for slug, name, cat in skills:
        cur.execute(
            """
            INSERT INTO skill_nodes (slug, name, category)
            VALUES (%s, %s, %s)
            ON CONFLICT (slug) DO UPDATE SET name = EXCLUDED.name, category = EXCLUDED.category
            """,
            (slug, name, cat),
        )

    # skill_aliases schema:
    # id UUID, skill_id TEXT (slug), alias TEXT
    aliases = [
        ("React.js", "react"),
        ("ReactJS", "react"),
        ("k8s", "kubernetes"),
        ("K8s", "kubernetes"),
        ("Py", "python"),
    ]

    for alias, slug in aliases:
        cur.execute(
            """
            INSERT INTO skill_aliases (skill_id, alias)
            VALUES (%s, %s)
            ON CONFLICT DO NOTHING
            """,
            (slug, alias),
        )

def seed_ontology_csv(cur, csv_path: Path):
    if not csv_path.exists():
        print(f"⚠️ Ontology CSV not found at: {csv_path}. Skipping ontology seed.")
        return

    print(f"🌿 Seeding ontology from: {csv_path}")

    edge_rows = []   # (source_slug, target_slug, relation_type, weight)
    alias_rows = []  # (skill_id (slug), alias)
    BATCH = 10000

    def flush():
        nonlocal edge_rows, alias_rows
        if edge_rows:
            execute_values(
                cur,
                """
                INSERT INTO skill_edges (source_slug, target_slug, relation_type, weight)
                VALUES %s
                ON CONFLICT DO NOTHING
                """,
                edge_rows,
                page_size=2000,
            )
            edge_rows = []
        if alias_rows:
            execute_values(
                cur,
                """
                INSERT INTO skill_aliases (skill_id, alias)
                VALUES %s
                ON CONFLICT DO NOTHING
                """,
                alias_rows,
                page_size=2000,
            )
            alias_rows = []

    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            raise ValueError("Ontology.csv has no header row")

        # Identify ROLE_K columns and sort by numeric suffix (10 -> 17000)
        role_cols = []
        for c in reader.fieldnames:
            m = re.match(r"ROLE_K(\d+)$", c.strip())
            if m:
                role_cols.append((int(m.group(1)), c.strip()))
        role_cols.sort(key=lambda x: x[0])  # broad -> specific
        role_cols = [c for _, c in role_cols]

        if len(role_cols) < 2:
            raise ValueError(f"Not enough ROLE_K columns found. Found: {role_cols}")

        processed = 0
        for row in reader:
            chain = []
            for col in role_cols:
                v = (row.get(col) or "").strip()
                if v:
                    chain.append(v)

            # Remove immediate duplicates case-insensitively
            dedup = []
            for v in chain:
                if not dedup or dedup[-1].lower() != v.lower():
                    dedup.append(v)

            if len(dedup) < 2:
                continue

            slugs = []
            for role_name in dedup:
                s = upsert_node_by_slug(cur, role_name, category="role")
                if s:
                    slugs.append(s)
                    # Add normalized lowercase alias to help extraction
                    alias_rows.append((s, role_name.strip().lower()))

            # parent_of edges broad -> specific
            for parent_slug, child_slug in zip(slugs[:-1], slugs[1:]):
                edge_rows.append((parent_slug, child_slug, "parent_of", 1.0))

            processed += 1
            if (len(edge_rows) + len(alias_rows)) >= BATCH:
                flush()

        flush()
        print(f"✅ Ontology rows processed: {processed}")

def seed_db():
    try:
        dbname, user, password, host, port = normalize_db_url()
        conn = psycopg2.connect(dbname=dbname, user=user, password=password, host=host, port=port)
        cur = conn.cursor()

        print("🌱 Seeding Database (current schema)...")

        # existing behavior
        seed_demo_skills(cur)

        # ontology seeding
        csv_path = Path(__file__).parent.parent / "Ontology.csv"
        seed_ontology_csv(cur, csv_path)

        conn.commit()
        cur.close()
        conn.close()
        print("✅ Database seeded successfully!")

    except Exception as e:
        print(f"❌ Seeding failed: {e}")

if __name__ == "__main__":
    seed_db()
