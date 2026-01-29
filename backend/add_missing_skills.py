import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

def add_skills():
    db_url = os.environ.get("SUPABASE_URL")
    if not db_url:
        print("❌ SUPABASE_URL not set")
        return

    conn = psycopg2.connect(db_url)
    cur = conn.cursor()

    try:
        # 1. New Skills
        new_skills = [
            ('maven', 'Maven', 'devops'),
            ('gradle', 'Gradle', 'devops'),
            ('jenkins', 'Jenkins', 'devops'),
            ('ansible', 'Ansible', 'devops'),
            ('chef', 'Chef', 'devops'),
            ('puppet', 'Puppet', 'devops'),
            ('bitbucket', 'Bitbucket', 'devops'),
            ('gitlab', 'GitLab', 'devops'),
            ('circleci', 'CircleCI', 'devops'),
            ('travis_ci', 'Travis CI', 'devops'),
            ('hashicorp_vault', 'Vault', 'devops'),
            ('prometheus', 'Prometheus', 'devops'),
            ('grafana', 'Grafana', 'devops'),
            ('elasticsearch', 'Elasticsearch', 'data'),
            ('kibana', 'Kibana', 'data'),
            ('logstash', 'Logstash', 'data'),
        ]
        
        print(f"🚀 Inserting {len(new_skills)} new skills...")
        
        args_str = ','.join(cur.mogrify("(%s,%s,%s)", x).decode('utf-8') for x in new_skills)
        cur.execute("INSERT INTO skill_nodes (slug, name, category) VALUES " + args_str + " ON CONFLICT (slug) DO NOTHING")
        
        # 2. New Aliases (Optional but good)
        # e.g. GitLab CI -> GitLab ? 
        # For now, base skills are enough.
        
        conn.commit()
        print("✅ Skills added successfully!")
        
    except Exception as e:
        conn.rollback()
        print(f"❌ Failed to add skills: {e}")
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    add_skills()
