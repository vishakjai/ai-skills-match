import json
import re
import time
from datetime import datetime
from SPARQLWrapper import SPARQLWrapper, JSON
from slugify import slugify

# --- CONFIGURATION ---
WIKIDATA_ENDPOINT = "https://query.wikidata.org/sparql"
OUTPUT_FILE = "canonical_skills_seed.jsonl"
USER_AGENT = "TalienceSkillBot/1.0 (contact: admin@talience.ai)"

# The "Big List" of Tech Categories (Wikidata Q-IDs)
# We use these to categorize the skills automatically.
CATEGORIES = {
    "Q9143": "language",          # Programming language
    "Q188860": "library",         # Software library
    "Q133036": "framework",       # Software framework
    "Q193446": "database",        # Database management system
    "Q9135": "os",                # Operating system
    "Q29007469": "cloud",         # Cloud computing platform
    "Q1130645": "data_structure", # Data structure
    "Q80006": "algorithm",        # Algorithm
    "Q1126661": "tool",           # Software tool
    "Q234966": "format",          # Markup language
    "Q3220391": "protocol",       # Network protocol
    "Q14656": "concept"           # Software engineering concept
}

def get_sparql_query_for_category(qid):
    """
    Constructs a query for a single category.
    Optimized: No GROUP_CONCAT. Returns multiple rows for aliases.
    """
    return f"""
    SELECT DISTINCT ?item ?itemLabel ?itemDescription ?alias
    WHERE {{
        # 1. Start from the specific category (Direct instances only)
        ?item wdt:P31 wd:{qid} .
        
        # 2. Filter out items without an English label
        ?item rdfs:label ?itemLabel . 
        FILTER(LANG(?itemLabel) = "en")

        # 3. Get Description (Optional)
        OPTIONAL {{
            ?item schema:description ?itemDescription .
            FILTER(LANG(?itemDescription) = "en")
        }}

        # 4. Get Aliases (One row per alias)
        OPTIONAL {{
            ?item skos:altLabel ?alias .
            FILTER(LANG(?alias) = "en")
        }}
    }}
    LIMIT 1000 # Safety limit per category
    """

def clean_aliases(alias_str):
    """Parses comma-separated alias string into a clean list."""
    if not alias_str:
        return []
    # Split, strip, and remove exact duplicates of the main label
    return list(set([a.strip() for a in alias_str.split(",") if a.strip()]))

def normalize_category(wikidata_url):
    """Maps the raw Wikidata Q-ID URL back to our simple category slug."""
    qid = wikidata_url.split("/")[-1]
    return CATEGORIES.get(qid, "uncategorized")

def fetch_data():
    all_items = {} # Dict to deduplicate and aggregate: {qid: {data}}
    sparql = SPARQLWrapper(WIKIDATA_ENDPOINT, agent=USER_AGENT)
    sparql.setReturnFormat(JSON)

    for qid, category_slug in CATEGORIES.items():
        print(f"📡 Fetching data for category: {category_slug} ({qid})...")
        query = get_sparql_query_for_category(qid)
        sparql.setQuery(query)
        
        try:
            results = sparql.query().convert()
            bindings = results["results"]["bindings"]
            print(f"   ✅ Fetched {len(bindings)} rows for {category_slug}.")
            
            for b in bindings:
                item_uri = b["item"]["value"]
                
                if item_uri not in all_items:
                    all_items[item_uri] = {
                        "item": b["item"],
                        "itemLabel": b["itemLabel"],
                        "itemDescription": b.get("itemDescription", {}),
                        "category": {"value": qid},
                        "aliases_set": set()
                    }
                
                # Add alias if present
                if "alias" in b:
                    all_items[item_uri]["aliases_set"].add(b["alias"]["value"])
            
            time.sleep(1)
            
        except Exception as e:
            print(f"   ❌ Error fetching category {category_slug}: {e}")
            continue

    # Convert back to list format expected by processor
    processed_list = []
    for item in all_items.values():
        # Join aliases for compatibility or keep as list
        # function clean_aliases splits by comma, so let's just make a comma string
        # OR update process_and_save to handle list? 
        # Let's keep existing process_and_save logic which expects "aliases" in binding as a string
        # Or better -> Update process_and_save.
        # But for minimal diff, let's fake the binding structure.
        
        alias_str = ", ".join(item["aliases_set"])
        
        entry = {
            "item": item["item"],
            "itemLabel": item["itemLabel"],
            "itemDescription": item["itemDescription"],
            "category": item["category"],
            "aliases": {"value": alias_str}
        }
        processed_list.append(entry)

    print(f"📦 Total unique entities fetched: {len(processed_list)}")
    return processed_list

def process_and_save(raw_data):
    count = 0
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        for entry in raw_data:
            # 1. Extract Fields
            label = entry["itemLabel"]["value"]
            description = entry.get("itemDescription", {}).get("value", "")
            wiki_url = entry["item"]["value"]
            raw_aliases = entry.get("aliases", {}).get("value", "")
            raw_category = entry["category"]["value"]

            # 2. Skip single-character garbage or excessively long titles
            if len(label) < 2 or len(label) > 50:
                continue

            # 3. Canonical Slug (The ID used in your graph)
            # "C++" -> "cpp", "Node.js" -> "node-js"
            safe_slug = slugify(label, replacements=[['+', 'p'], ['.', '-']])
            
            # 4. Construct the Node
            skill_node = {
                "skill_id": safe_slug,
                "canonical_name": label,
                "category": normalize_category(raw_category),
                "aliases": clean_aliases(raw_aliases),
                "metadata": {
                    "description": description,
                    "wikidata_uri": wiki_url,
                    "source": "wikidata_automated_ingest",
                    "ingested_at": datetime.now().isoformat()
                }
            }
            
            # 5. Write to file
            f.write(json.dumps(skill_node) + "\n")
            count += 1
            
    print(f"🎉 Successfully saved {count} curated skills to {OUTPUT_FILE}")

if __name__ == "__main__":
    data = fetch_data()
    if data:
        process_and_save(data)
