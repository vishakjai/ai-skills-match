import json
import os
import psycopg2
from psycopg2.extras import execute_values
from dotenv import load_dotenv
from slugify import slugify

# Load env vars
load_dotenv(os.path.join(os.getcwd(), ".env"))

DB_URL = os.getenv("DATABASE_URL") or os.getenv("SUPABASE_URL")
SEED_FILE = "canonical_skills_seed.jsonl"
CURATED_FILE = "curated_taxonomy.jsonl"

def connect():
    return psycopg2.connect(DB_URL, sslmode='require')

def load_jsonl(filepath):
    data = {}
    if not os.path.exists(filepath):
        return {}
    with open(filepath, "r") as f:
        for line in f:
            if line.strip():
                item = json.loads(line)
                # Use slug as key
                key = item.get("skill_id") or item.get("skill_slug")
                data[key] = item
    return data

def main():
    print("🌱 Starting Taxonomy Seeding...")
    
    # 1. Load Data
    seed_data = load_jsonl(SEED_FILE) # has aliases, name, description
    curated_data = load_jsonl(CURATED_FILE) # has parent_concepts, suggested_category
    
    print(f"📦 Loaded {len(seed_data)} seed items and {len(curated_data)} curated items.")
    
    conn = connect()
    cur = conn.cursor()
    
    # DEBUG: Check Schema & Constraints
    def ensure_unique_constraint(table, columns, constraint_name):
        try:
            cur.execute(f"""
                SELECT 1 FROM pg_constraint 
                WHERE conname = '{constraint_name}'
            """)
            if not cur.fetchone():
                print(f"⚠️ Adding unique constraint {constraint_name} to {table}...")
                cur.execute(f"""
                    ALTER TABLE {table} 
                    ADD CONSTRAINT {constraint_name} UNIQUE ({', '.join(columns)})
                """)
                conn.commit()
                print(f"✅ Added {constraint_name}.")
        except Exception as e:
            print(f"❌ Failed to add constraint {constraint_name}: {e}")
            conn.rollback()

    # Nodes (slug is usually PK, so implied unique, but double check)
    # Aliases
    ensure_unique_constraint('skill_aliases', ['skill_id', 'alias'], 'unique_skill_alias')
    # Edges
    ensure_unique_constraint('skill_edges', ['source_slug', 'target_slug', 'relation_type'], 'unique_skill_edge')

    # Drop restrictive unique alias constraint if exists (because aliases can be ambiguous in raw data)
    try:
        cur.execute("ALTER TABLE skill_aliases DROP CONSTRAINT IF EXISTS skill_aliases_alias_key")
        conn.commit()
        print("✅ Dropped restrictive constraint skill_aliases_alias_key.")
    except Exception as e:
        print(f"⚠️ Could not drop skill_aliases_alias_key (might not exist): {e}")
        conn.rollback()

    # Add metadata column check (keep existing)
    cur.execute("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'skill_nodes'")
    columns = cur.fetchall()
    print(f"🧐 Current Schema for skill_nodes: {columns}")
    
    col_names = [c[0] for c in columns]
    if "metadata" not in col_names:
        print("⚠️ Adding metadata column...")
        try:
            cur.execute("ALTER TABLE skill_nodes ADD COLUMN metadata JSONB DEFAULT '{}'")
            conn.commit()
            print("✅ Added metadata column.")
        except Exception as e:
            print(f"❌ Failed to alter table: {e}")
            conn.rollback()

    nodes_to_insert = []
    aliases_to_insert = []
    edges_to_insert = []
    
    # 2. Prepare Nodes & Edges
    # We only insert items that are in seed_data (source of truth for metadata)
    # But we update them with curated info if available.
    
    for slug, seed_item in seed_data.items():
        # strict validation: if curated exists and marked invalid, skip
        curated = curated_data.get(slug)
        if curated and not curated.get("is_valid_tech", True):
            print(f"⏭️ Skipping invalid tech: {slug}")
            continue
            
        # Merge fields
        name = seed_item["canonical_name"]
        category = seed_item["category"]
        description = seed_item.get("metadata", {}).get("description", "")
        
        # Override category if curated has better one
        if curated and curated.get("suggested_category"):
            category = curated["suggested_category"]
            
        # Nodes
        # (slug, name, category, tier, description)
        nodes_to_insert.append((slug, name, category, "verified", description))
        
        # Aliases
        # (skill_id, alias)
        if seed_item.get("aliases"):
            for alias in seed_item["aliases"]:
                aliases_to_insert.append((slug, alias))
                
        # Edges (from Curated)
        if curated and curated.get("parent_concepts"):
            for parent_ref in curated["parent_concepts"]:
                parent_slug = slugify(parent_ref)
                # Ensure parent exists? For now, we might insert edges to non-existent parents 
                # if we don't insert parents first. 
                # Ideally we should insert parents as implicit nodes if they don't exist.
                # Let's just track edges and insert them. Foreign key constraint might fail if parent doesn't exist.
                # FIX: We will add parents to nodes_to_insert if missing? 
                # That's complex. Let's just insert edges and handle failures or 
                # insert "stub" parents first.
                
                # Check if parent is in our main list to insert
                # (For the dry run/batch, many parents like 'javascript' won't be in the seed list 
                # if we only scraped 'languages' starting with 'A' etc. 
                # Actually we scraped everything but only curated 60.)
                
                # Relation Mapping:
                # LLM says Parent -> Child (Narrower)
                # DB expects 'parent_of'
                
                edges_to_insert.append((parent_slug, slug, "parent_of")) # Parent -> parent_of -> Child

    # 3. Handle Missing Parents (Stubbing)
    # We need to ensure all parents in edges exist in nodes
    known_slugs = set([n[0] for n in nodes_to_insert])
    edge_parents = set([e[0] for e in edges_to_insert])
    missing_parents = edge_parents - known_slugs
    
    print(f"🧩 Found {len(missing_parents)} implied parents (stubs) to create.")
    for p_slug in missing_parents:
        # Create a stub node
        nodes_to_insert.append((p_slug, p_slug.replace("-", " ").title(), "concept", "implied", "Auto-generated parent"))

    # 4. Execute Inserts
    try:
        # A. Nodes
        node_query = """
            INSERT INTO skill_nodes (slug, name, category, metadata)
            VALUES %s
            ON CONFLICT (slug) DO UPDATE 
            SET category = EXCLUDED.category, 
                metadata = skill_nodes.metadata || EXCLUDED.metadata
        """
        # Pack metadata into json
        nodes_final = []
        for n in nodes_to_insert:
            slug, name, cat, tier, desc = n
            meta = {"description": desc, "tier": tier} # Tier moved to metadata
            nodes_final.append((slug, name, cat, json.dumps(meta)))
            
        execute_values(cur, node_query, nodes_final)
        print(f"✅ Upserted {len(nodes_final)} nodes.")
        
        # B. Aliases
        if aliases_to_insert:
            alias_query = """
                INSERT INTO skill_aliases (skill_id, alias)
                VALUES %s
                ON CONFLICT (skill_id, alias) DO NOTHING
            """
            execute_values(cur, alias_query, aliases_to_insert)
            print(f"✅ Upserted {len(aliases_to_insert)} aliases.")

        # C. Edges
        if edges_to_insert:
            edge_query = """
                INSERT INTO skill_edges (source_slug, target_slug, relation_type, weight)
                VALUES %s
                ON CONFLICT (source_slug, target_slug, relation_type) DO NOTHING
            """
            # Add default weight 1.0
            edges_final = [(e[0], e[1], e[2], 1.0) for e in edges_to_insert]
            execute_values(cur, edge_query, edges_final)
            print(f"✅ Upserted {len(edges_final)} edges.")
            
        conn.commit()
        print("🎉 Database successfully seeded!")
        
    except Exception as e:
        print(f"❌ Database Error: {e}")
        conn.rollback()
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    main()
