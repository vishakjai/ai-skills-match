import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

def add_edges():
    db_url = os.environ.get("SUPABASE_URL")
    if not db_url:
        print("❌ SUPABASE_URL not set")
        return

    conn = psycopg2.connect(db_url)
    cur = conn.cursor()

    try:
        # Parent (Core) -> Child (Specific)
        # Relationship: parent_of (Core implies Child? No. Child implies Core.)
        # Logic: If I know Child, I know Parent.
        # DB Storage: (Parent, Child, 'parent_of')
        new_edges = [
            ('git', 'gitlab', 'parent_of'),
            ('git', 'bitbucket', 'parent_of'),
            ('ci_cd', 'jenkins', 'parent_of'),
            ('ci_cd', 'circleci', 'parent_of'),
            ('ci_cd', 'travis_ci', 'parent_of'),
            ('ci_cd', 'gitlab', 'parent_of'), # GitLab is also CI/CD
        ]
        
        # Note: 'github' is currently an ALIAS to 'git'. So it's not a node. 'git' is the node.
        # So we can't link ci_cd -> github.
        
        print(f"🚀 Inserting {len(new_edges)} new edges...")
        
        args_str = ','.join(cur.mogrify("(%s,%s,%s)", x).decode('utf-8') for x in new_edges)
        cur.execute("INSERT INTO skill_edges (source_slug, target_slug, relation_type) VALUES " + args_str + " ON CONFLICT (source_slug, target_slug, relation_type) DO NOTHING")
        
        conn.commit()
        print("✅ Edges added successfully!")
        
    except Exception as e:
        conn.rollback()
        print(f"❌ Failed to add edges: {e}")
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    add_edges()
