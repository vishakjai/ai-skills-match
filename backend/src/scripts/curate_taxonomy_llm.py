import asyncio
import json
import os
import sys
from typing import List, Optional
from pydantic import BaseModel
from openai import AsyncOpenAI
from dotenv import load_dotenv

# Load env vars
load_dotenv(os.path.join(os.getcwd(), ".env"))

INPUT_FILE = "canonical_skills_seed.jsonl"
OUTPUT_FILE = "curated_taxonomy.jsonl"
BATCH_SIZE = 30  # Small batch to prevent context window overload

# --- SCHEMAS ---
class SkillEdge(BaseModel):
    parent: str
    child: str
    relation_type: str # "narrower", "is_a", "tool_for"

class SkillTagging(BaseModel):
    skill_slug: str
    is_valid_tech: bool
    suggested_category: str # "framework", "language", "tool", "concept", "garbage"
    parent_concepts: List[str] # List of parent slugs e.g. ["javascript", "web_development"]

class CurationResult(BaseModel):
    items: List[SkillTagging]

# --- SCRIPT ---

async def curate_batch(client: AsyncOpenAI, batch_skills: List[dict]) -> CurationResult:
    """
    Sends a batch of skills to LLM for taxonomy curation.
    """
    skills_txt = "\n".join([f"- {s['canonical_name']} (ID: {s['skill_id']}, Cat: {s['category']})" for s in batch_skills])
    
    prompt = f"""
    You are an expert Tech Taxonomist. Review the following list of raw skills ingested from Wikidata.
    
    Task:
    1. Validate if it is a real technical skill/concept. Mark 'is_valid_tech' = False if it's a person, company, or random noise.
    2. Suggest a strict category: 'language', 'framework', 'library', 'database', 'tool', 'concept', 'platform', 'protocol'.
    3. Identify PARENT concepts. 
       - If it's a library like 'React', parent is 'JavaScript' and 'Web Development'.
       - If it's 'PostgreSQL', parent is 'Relational Database' and 'SQL'.
       - Use common canonical names for parents (e.g. 'java', 'python', 'aws', 'azure').
    
    Skills to Review:
    {skills_txt}
    """
    
    try:
        completion = await client.beta.chat.completions.parse(
            model="gpt-4o-mini", # Switched to mini for cost efficiency (20x cheaper)
            messages=[
                {"role": "system", "content": "You are a precise data curation bot. Output JSON only."},
                {"role": "user", "content": prompt}
            ],
            response_format=CurationResult
        )
        return completion.choices[0].message.parsed
    except Exception as e:
        print(f"❌ Batch Error: {e}")
        return CurationResult(items=[])

async def main():
    print("🚀 Starting LLM Taxonomy Curation...")
    
    if not os.getenv("OPENAI_API_KEY"):
        print("❌ OPENAI_API_KEY not found in .env")
        return

    client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    # 1. Load Seed Data
    raw_skills = []
    with open(INPUT_FILE, "r") as f:
        for line in f:
            if line.strip():
                raw_skills.append(json.loads(line))
    
    print(f"📦 Loaded {len(raw_skills)} skills from seed file.")
    
    # 2. Process in Batches
    # Process ALL skills
    limit_run = len(raw_skills)
    
    curated_data = []
    
    # Iterate
    ids_processed = 0
    for i in range(0, min(len(raw_skills), limit_run), BATCH_SIZE):
        batch = raw_skills[i : i + BATCH_SIZE]
        print(f"🔄 Processing batch {i} to {i + len(batch)}...")
        
        result = await curate_batch(client, batch)
        
        if result and result.items:
            for item in result.items:
                # Merge logic: Find original to keep metadata? 
                # For now, just save the curation result linked to slug
                json_line = item.model_dump_json()
                curated_data.append(json_line)
        
        await asyncio.sleep(1) # Rate limit politeness

    # 3. Save Output
    with open(OUTPUT_FILE, "a") as f: # Append mode
        for line in curated_data:
            f.write(line + "\n")
            
    print(f"✅ Saved {len(curated_data)} curated items to {OUTPUT_FILE}")

if __name__ == "__main__":
    asyncio.run(main())
