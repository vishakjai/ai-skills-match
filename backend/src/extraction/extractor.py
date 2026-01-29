import time
import psycopg2
from flashtext import KeywordProcessor
from typing import List, Dict
from src.extraction.schemas import ExtractionResult, ExtractedEntity

class SkillExtractor:
    def __init__(self, db_url: str):
        """
        Initializes the extractor by loading the entire alias dictionary from SQL.
        """
        self.keyword_processor = KeywordProcessor(case_sensitive=True) # Mixed case strategy?
        # Actually, FlashText case_sensitive=False makes it all case insensitive.
        # Requirements said: JS (insensitive), Go (sensitive).
        # We can handle this by adding "Go" as case_sensitive to a separate processor or 
        # using the set_non_word_boundaries for specific words?
        # For simplicity in V1, let's stick to case_insensitive mostly, or handle complex logic later.
        # Let's go case_insensitive=False (default is False, meaning insensitive) but wait, 
        # case_sensitive=True means "Go" != "go".
        # Let's use case_sensitive=False for now to catch "python" vs "Python".
        self.keyword_processor = KeywordProcessor(case_sensitive=False) 
        
        self.db_url = db_url
        self._load_dictionary()

    def _load_dictionary(self):
        """
        Fetches (alias, skill_id, canonical_name) from DB.
        """
        try:
            # Use psycopg2 directly as it handles standard URIs (including %40 escaping)
            conn = psycopg2.connect(self.db_url)

            cur = conn.cursor()
            
            # Join aliases with nodes to get canonical name
            # FIX: Also load the Canonical Name itself as a keyword!
            query = """
            SELECT a.alias, s.slug, s.name 
            FROM skill_aliases a
            JOIN skill_nodes s ON a.skill_id = s.slug
            UNION
            SELECT s.name, s.slug, s.name
            FROM skill_nodes s
            """
            cur.execute(query)
            rows = cur.fetchall()
            
            count = 0
            for alias, skill_id, canonical_name in rows:
                # We store the ID and Canonical Name as the "Clean Name"
                # Format: "UUID|Canonical Name"
                clean_name = f"{skill_id}|{canonical_name}"
                self.keyword_processor.add_keyword(alias, clean_name)
                count += 1
                
            print(f"✅ Loaded {count} skill aliases into FlashText.")
            
            # ---------------------------------------------------------
            # Manual Overrides / Extensions for Common Misses
            # ---------------------------------------------------------
            # Some skills might be missing from the seed or have specific casing needs
            manual_aliases = {
                "SQL Server": "sql_server|Microsoft SQL Server",
                "Oracle": "oracle|Oracle Database",
                "CSS3": "css3|CSS3",
                "HTML5": "html5|HTML5", 
                "RESTful API": "rest_api|RESTful API",
                "REST API": "rest_api|RESTful API",
                "Restapi": "rest_api|RESTful API",
                "PostgreSQL": "postgresql|PostgreSQL",
                "Postgres": "postgresql|PostgreSQL",
                "Javscript": "javascript|JavaScript",
                "Javascript": "javascript|JavaScript",
                "NodeJS": "node_js|Node.js",
                "C#": "c_sharp|C#",
                "DotNet": "dot_net|.NET",
                "Ooad": "ooad|Object Oriented Analysis and Design"
            }
            
            for alias, clean_val in manual_aliases.items():
                self.keyword_processor.add_keyword(alias, clean_val)
                print(f"➕ Added manual alias: {alias} -> {clean_val}")

            cur.close()
            conn.close()
        except Exception as e:
            print(f"❌ Failed to load dictionary: {e}")
            # Non-blocking for testing? Or blocking?
            # Creating an empty processor if DB fails implies 0 matches.

    def extract(self, text: str) -> ExtractionResult:
        start_time = time.time()
        
        # 1. Clean Text (Basic)
        # Convert fancy quotes, etc.
        text_clean = text.replace("’", "'").replace("“", '"').replace("”", '"')
        
        # 2. FlashText Extraction
        # extract_keywords with span_info=True returns (clean_name, start, end)
        keywords_found = self.keyword_processor.extract_keywords(text_clean, span_info=True)
        
        entities: List[ExtractedEntity] = []
        
        # Deduplication Strategy?
        # FlashText handles overlapping by taking the longest match automatically.
        # e.g. "Visual Studio Code" vs "Visual Studio".
        
        for clean_name, start, end in keywords_found:
            # Parse our packed identifier
            if "|" in clean_name:
                s_id, s_name = clean_name.split("|", 1)
            else:
                s_id, s_name = "unknown", clean_name
            
            entities.append(ExtractedEntity(
                skill_id=s_id,
                canonical_name=s_name,
                verbatim_text=text_clean[start:end],
                span=(start, end),
                confidence=1.0,
                match_method="exact_dictionary"
            ))
            
        # 3. Vector Fallback (TODO)
        # if len(entities) == 0:
        #    query embedding...
        
        processing_time = (time.time() - start_time) * 1000
        
        return ExtractionResult(
            entities=entities,
            processed_text_length=len(text),
            processing_time_ms=round(processing_time, 2)
        )
