# AI Skills Match Engine - Technical Details

## Table of Contents
1. [OpenAI API Calls Summary](#1-openai-api-calls-summary)
2. [Match Scoring Engine](#2-match-scoring-engine)

---

## 1. OpenAI API Calls Summary

The application makes **up to 4 OpenAI API calls** per single match operation (depending on conditions):

| # | Service | File | Model | Purpose | When Called |
|---|---------|------|-------|---------|-------------|
| **1** | `LLMExtractor.extract_jd()` | `extraction/llm_extractor.py:27` | `gpt-4o-2024-08-06` | Parse JD text → structured `JobDescription` | Every JD extraction |
| **2** | `LLMExtractor.extract_resume()` | `extraction/llm_extractor.py:96` | `gpt-4o-2024-08-06` | Parse Resume text → structured `CandidateProfile` | Every Resume extraction |
| **3** | `TribunalService.evaluate_narrative()` | `services/tribunal.py:84` | `gpt-4o` | Adversarial career analysis (Skeptic vs Advocate) | Only if match score ≥ 60 |
| **4** | `LocationService.check_proximity()` | `services/location.py:48` | `gpt-4o-mini` | Geographic proximity check | Only if `work_mode != "remote"` |

---

### 1.1 Call Details

#### Call 1: JD Extraction (`gpt-4o-2024-08-06`)
- **Input**: Raw JD text
- **Output**: Structured `JobDescription` (requirements, competencies, gating rules)
- **Frequency**: 1 per JD
- **Method**: `client.beta.chat.completions.parse()` with Pydantic response format
- **System Prompt Role**: Expert HR Tech extraction engine that extracts job details into structured JSON
- **Post-Processing**:
  - Normalizes skill IDs via `ontology.resolve_alias()`
  - Deduplicates soft skills from technical requirements
  - Normalizes education gating rules to lowercase

#### Call 2: Resume Extraction (`gpt-4o-2024-08-06`)
- **Input**: Raw resume text
- **Output**: Structured `CandidateProfile` (timeline, skills, education)
- **Frequency**: 1 per resume
- **Method**: `client.beta.chat.completions.parse()` with Pydantic response format
- **System Prompt Role**: Expert Resume Parser that extracts skills, timeline, education, and competencies
- **Post-Processing**:
  - Runs deterministic analytics (`calculate_analytics`) on the extracted profile

#### Call 3: Tribunal Analysis (`gpt-4o`) — *Conditional*
- **Input**: Resume text (first 2000 chars) + TOON-encoded candidate/JD structured data
- **Output**: `TribunalVerdict` (skeptic/advocate summaries, narrative_tag)
- **Frequency**: Only for promising candidates (score ≥ 60)
- **Temperature**: 0.2 (low randomness for consistency)
- **Approach**: Adversarial debate between two AI personas:
  - **Skeptic**: Scrutinizes role mismatch, tenure gaps, stagnation, title inflation
  - **Advocate**: Looks for transferable skills, rapid pivots, high-potential transitions
- **Output Tags**: `top_tier_potential`, `solid_performer`, `high_risk`, `mismatch`
- **Fail-Open**: Returns neutral verdict if API fails (doesn't block matching)

#### Call 4: Location Check (`gpt-4o-mini`) — *Conditional*
- **Input**: Candidate location + Job location
- **Output**: `LocationVerdict` (is_within_range, distance_estimate, reason)
- **Frequency**: Only for non-remote jobs
- **Temperature**: 0.0 (deterministic)
- **Threshold**: ~50 miles / 80 km commuting distance
- **Fail-Open**: Returns `is_within_range=True` if API fails

---

### 1.2 Batch Processing Impact

For batch processing with **N resumes**:

| Call | Count | Notes |
|------|-------|-------|
| JD Extraction | 1 | Shared across all resumes |
| Resume Extraction | N | One per resume |
| Tribunal | 0 to N | Only for candidates scoring ≥ 60 |
| Location | 0 to N | Only for non-remote jobs |

**Worst case per batch**: `1 + 3N` calls
**Typical case**: `1 + N + ~0.3N` (assuming ~30% qualify for tribunal, remote job)

---

### 1.3 Legacy Code

`backend/src/core/extraction.py` contains sync OpenAI functions (`extract_candidate_profile`, `extract_job_description`). These appear to be **legacy/unused** — the active code uses the async `LLMExtractor` class in `extraction/llm_extractor.py` instead.

---

## 2. Match Scoring Engine

The core matching logic lives in `backend/src/core/engine.py` in the `calculate_match()` async function.

---

### 2.1 Scoring Formula (100 Points Total)

| Component | Weight | Max Points | Source Function |
|-----------|--------|------------|-----------------|
| **Education** | 10% | 10 pts | `analyze_education()` |
| **Experience** | 10% | 10 pts | `analyze_experience()` |
| **Competencies** | 10% | 10 pts | `analyze_competencies()` |
| **Required Skills** | 50% | 50 pts | JD `must_have` requirements |
| **Preferred Skills** | 20% | 20 pts | JD `nice_to_have` requirements |

---

### 2.2 Scoring Process Flow

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    calculate_match() - engine.py:39                     │
└─────────────────────────────────────────────────────────────────────────┘
                                  │
      ┌───────────────────────────┼───────────────────────────┐
      ▼                           ▼                           ▼
┌──────────────┐         ┌──────────────┐         ┌──────────────┐
│ 1. BUILD     │         │ 2. NORMALIZE │         │ 3. FILTER    │
│ CANDIDATE    │         │ JD SKILLS    │         │ BY PRIORITY  │
│ SKILLS MAP   │         │              │         │              │
└──────────────┘         └──────────────┘         └──────────────┘
      │                           │                           │
      │ Sources:                  │ ontology                  │ must_have
      │ - candidate.skills        │ .resolve_alias()          │ nice_to_have
      │ - candidate.skill_profile │                           │
      │ - candidate.timeline      │                           │
      └───────────────────────────┼───────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         SKILL MATCHING                                  │
│                                                                         │
│  get_best_match_score(req_skill, candidate_skills):                    │
│                                                                         │
│    1. EXACT MATCH        → 1.0  (skill_id == candidate skill_id)       │
│    2. GRAPH: IMPLIED     → 1.0  (React implies JavaScript)             │
│    3. GRAPH: ALTERNATIVE → 0.5  (Vue alternative to React)             │
│    4. FUZZY: SUBSTRING   → 1.0  ("java" in "java_programming")         │
│    5. FUZZY: TOKEN       → 0.9  (token overlap > 3 chars)              │
│    6. NO MATCH           → 0.0                                         │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                     SENIORITY MULTIPLIER                                │
│                                                                         │
│  Per-skill adjustment based on:                                         │
│  - JD requirement level (from req.level or job title)                   │
│  - Candidate's proven level for that skill                             │
│                                                                         │
│  Hierarchy: junior(1) → mid(2) → senior(3) → staff(4) → principal(5)   │
│                                                                         │
│  Multipliers:                                                           │
│    cand >= req  → 1.0  (meets or exceeds)                              │
│    cand = req-1 → 0.8  (one level below)                               │
│    cand < req-1 → 0.5  (two+ levels below)                             │
│    "listed" only → 0.7 (skill present but no proven context)           │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                     COMPOSITE SCORE CALCULATION                         │
│                                                                         │
│  A. Education (10 pts)                                                  │
│     met/exceeds → 10 | review_needed → 5 | not_met → 0                 │
│                                                                         │
│  B. Experience (10 pts)                                                 │
│     met/exceeds → 10 | review_needed → 5 | not_met → 0                 │
│                                                                         │
│  C. Competencies (10 pts)                                               │
│     10 × (found_soft_skills / required_soft_skills)                    │
│                                                                         │
│  D. Required Skills (50 pts)                                            │
│     FOR EACH must_have requirement:                                     │
│       weight = 50 / num_requirements                                    │
│       skill_score = get_best_match_score() × seniority_multiplier      │
│       score_required += weight × skill_score                           │
│                                                                         │
│  E. Preferred Skills (20 pts)                                           │
│     Same logic as Required, but for nice_to_have                       │
│                                                                         │
│  TOTAL = A + B + C + D + E  (capped at 100)                            │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                     CRITICAL FAILURES (Hard Filters)                    │
│                                                                         │
│  If any requirement has is_hard_filter=True and score=0:               │
│    → Add to critical_failures list                                      │
│    → CAP FINAL SCORE AT 40 (regardless of other scores)                │
│                                                                         │
│  If education_strict=True and education not met:                       │
│    → Same penalty                                                       │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                     ASYNC ENRICHMENTS                                   │
│                                                                         │
│  1. Location Analysis (if work_mode != "remote")                       │
│     → LocationService.check_proximity()                                 │
│     → Adds analysis section (met/not_met/review_needed)                │
│                                                                         │
│  2. Tribunal (if score >= 60)                                          │
│     → TribunalService.evaluate_narrative()                             │
│     → Skeptic vs Advocate career analysis                              │
│     → narrative_tag: top_tier | solid | high_risk | mismatch           │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                          MATCH RESULT                                   │
│                                                                         │
│  {                                                                      │
│    score: 78.5,                                                         │
│    analysis: [Education, Experience, Competencies, Location],          │
│    technical_trace: [                                                   │
│      {skill: "java", status: "matched", score: 1.0, level: "senior"},  │
│      {skill: "aws", status: "partial", score: 0.5, level: "mid"},      │
│      {skill: "kubernetes", status: "missing", score: 0, level: null}   │
│    ],                                                                   │
│    tribunal_verdict: {...}                                              │
│  }                                                                      │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

### 2.3 Step-by-Step Breakdown

#### Step 1: Build Candidate Skills Map

The engine consolidates candidate skills from **three sources** into a single `candidate_skills_map` (keyed by canonical slug):

1. **`candidate.skills`** — Direct skill list with evidence sources
2. **`candidate.skill_profile`** — Skills section from resume header (e.g., "Technical Skills: Java, Python, AWS")
3. **`candidate.timeline`** — Skills extracted from work experience entries

Each skill is resolved to its canonical slug via `ontology.resolve_alias()`.

For skills found in `skill_profile` or `timeline` but not in `skills`, synthetic `CandidateSkill` entries are created with inferred metadata.

#### Step 2: Normalize JD Requirements

JD requirements are split by priority:
- **`must_have`** → Required skills (50 pts pool)
- **`nice_to_have`** → Preferred skills (20 pts pool)

Each requirement's `skill_id` is also resolved via `ontology.resolve_alias()`.

#### Step 3: Skill Matching (`get_best_match_score`)

For each JD requirement, the engine finds the best match against the candidate's skills using a cascading strategy:

| Priority | Method | Score | Example |
|----------|--------|-------|---------|
| 1st | **Exact match** | 1.0 | `"react"` == `"react"` |
| 2nd | **Graph: Implied** | 1.0 | `"react"` implies `"javascript"` (parent_of edge) |
| 3rd | **Graph: Alternative** | 0.5 | `"vue"` alternative to `"react"` |
| 4th | **Fuzzy: Substring** | 1.0 | `"java"` found in `"java_programming"` |
| 5th | **Fuzzy: Token overlap** | 0.9 | Shared token > 3 chars |
| 6th | **No match** | 0.0 | — |

The highest score from any method is returned.

#### Step 4: Seniority Multiplier

Each matched skill's score is adjusted based on **seniority alignment**:

| Candidate Level vs Required Level | Multiplier |
|-----------------------------------|------------|
| Meets or exceeds | 1.0 |
| One level below | 0.8 |
| Two+ levels below | 0.5 |
| Skill only "listed" (no proven context) | 0.7 |

**Seniority hierarchy**: junior(1) → mid(2) → senior(3) → staff(4) → principal(5)

If the JD doesn't specify a level, it's inferred from the **job title** (e.g., "Senior Backend Engineer" → senior).

#### Step 5: Component Scoring

**A. Education (10 pts)**
- Matches candidate degrees against `gating_rules.education_min`
- Keyword matching: bachelor/bs/b.s., master/ms/m.s., phd/doctorate
- `met` → 10 pts, `review_needed` → 5 pts, `not_met` → 0 pts
- If `education_strict=True`, `review_needed` is downgraded to `not_met` and added to critical failures

**B. Experience (10 pts)**
- Compares `total_yoe` against seniority signals
- Senior role + < 4 years → `not_met`
- Staff role + < 8 years → `review_needed`
- Otherwise → `met`

**C. Competencies (10 pts)**
- Matches JD competencies (soft skills) against candidate competencies
- Uses substring/keyword matching (e.g., "Problem Solving" matches "Strong problem solving skills")
- Score = 10 × (found / required)

**D. Required Skills (50 pts)**
- Weight per skill = 50 / number of must_have requirements
- Per skill: `weight × match_score × seniority_multiplier`
- If `is_hard_filter=True` and score=0 → added to critical failures

**E. Preferred Skills (20 pts)**
- Same formula as Required but for nice_to_have
- Weight per skill = 20 / number of nice_to_have requirements

#### Step 6: Critical Failure Penalty

If any **critical failures** exist (hard filter skills missing or strict education failed):
- Final score is **capped at 40**, regardless of other scores

#### Step 7: Async Enrichments

**Location Analysis** (if `work_mode != "remote"`):
- Calls `LocationService.check_proximity()` (OpenAI GPT-4o-mini)
- Adds an analysis section with status: `met`, `not_met`, or `review_needed`

**Tribunal** (if `score >= 60`):
- Calls `TribunalService.evaluate_narrative()` (OpenAI GPT-4o)
- Adds `tribunal_verdict` with narrative analysis

---

### 2.4 Example Calculation

**JD**: 4 required skills, 2 preferred skills, needs Senior level

| Skill | Match Type | Match Score | Seniority Mult | Final | Weighted |
|-------|-----------|-------------|----------------|-------|----------|
| Java (req) | Exact | 1.0 | 1.0 (senior) | 1.0 | 12.5 (50/4) |
| AWS (req) | Alternative | 0.5 | 0.8 (mid) | 0.4 | 5.0 |
| K8s (req) | Missing | 0.0 | - | 0.0 | 0.0 |
| Python (req) | Exact | 1.0 | 0.7 (listed) | 0.7 | 8.75 |
| Go (pref) | Exact | 1.0 | 1.0 | 1.0 | 10.0 (20/2) |
| Rust (pref) | Missing | 0.0 | - | 0.0 | 0.0 |

**Final Score**:
- Education: 10.0 (met)
- Experience: 10.0 (met)
- Competencies: 7.5 (3/4 soft skills found)
- Required Skills: 26.25 (12.5 + 5.0 + 0.0 + 8.75)
- Preferred Skills: 10.0 (10.0 + 0.0)
- **Total: 63.75** → Tribunal triggered (≥ 60)

---

### 2.5 Key Code References

| Function | File | Line | Purpose |
|----------|------|------|---------|
| `calculate_match()` | `core/engine.py` | 39 | Main entry point (async) |
| `get_best_match_score()` | `core/engine.py` | 165 | Graph + Fuzzy matching |
| `get_seniority_multiplier()` | `core/engine.py` | 318 | Seniority adjustment |
| `analyze_education()` | `core/engine.py` | 371 | Education gating analysis |
| `analyze_experience()` | `core/engine.py` | 432 | Experience level analysis |
| `analyze_competencies()` | `core/engine.py` | 461 | Soft skills analysis |
| `create_trace_item()` | `core/engine.py` | 201 | Build per-skill trace |

---

### 2.6 Skill Resolution Pipeline

```
User Input: "ReactJS"
     │
     ▼
ontology.resolve_alias("ReactJS")
     │
     ▼ (Database lookup: skill_aliases table)
Canonical: "react"
     │
     ▼
get_best_match_score("react", candidate_skills)
     │
     ├── Exact match in candidate_skills_map? → 1.0
     │
     ├── Graph edge "react" → "javascript" (parent_of)? → 1.0 (implies)
     │
     ├── Graph edge "react" ↔ "vue" (alternative_to)? → 0.5
     │
     └── Fuzzy match (substring/token)? → 0.9-1.0
```

---

### 2.7 Analysis Section Status Values

| Status | Meaning | Score Impact |
|--------|---------|--------------|
| `met` | Requirement fully satisfied | Full points |
| `exceeds` | Exceeds requirement | Full points |
| `review_needed` | Partial match, human review recommended | 50% points |
| `not_met` | Requirement not satisfied | 0 points |
| `partial` | Skill found but level mismatch (trace only) | Variable |
| `missing` | Skill not found (trace only) | 0 points |

---

### 2.8 MatchResult Output Structure

```json
{
  "score": 63.75,
  "analysis": [
    {
      "title": "Education",
      "status": "met",
      "summary": "Matches requirement: bachelor's",
      "details": ["Detected: Bachelor's in Computer Science"]
    },
    {
      "title": "Experience",
      "status": "met",
      "summary": "Experience level appears aligned.",
      "details": ["Total Experience: 8 years", "Average Tenure: 24.0 months"]
    },
    {
      "title": "Competencies",
      "status": "review_needed",
      "summary": "Found 3 out of 4 key competencies.",
      "details": ["✅ Communication", "✅ Leadership", "✅ Problem Solving", "❌ Mentoring"]
    },
    {
      "title": "Location",
      "status": "met",
      "summary": "Remote Role",
      "details": ["Job is Remote. Check time zones if necessary."]
    }
  ],
  "technical_trace": [
    {"skill_slug": "java", "status": "matched", "score": 1.0, "seniority_level": "senior", "sources": ["experience"], "priority": "required"},
    {"skill_slug": "aws", "status": "partial", "score": 0.5, "seniority_level": "mid", "sources": ["resume_skills_section"], "priority": "required"},
    {"skill_slug": "kubernetes", "status": "missing", "score": 0.0, "seniority_level": "unknown", "sources": [], "priority": "required"},
    {"skill_slug": "python", "status": "matched", "score": 1.0, "seniority_level": "listed", "sources": ["summary"], "priority": "required"},
    {"skill_slug": "go", "status": "matched", "score": 1.0, "seniority_level": "mid", "sources": ["experience"], "priority": "preferred"},
    {"skill_slug": "rust", "status": "missing", "score": 0.0, "seniority_level": "unknown", "sources": [], "priority": "preferred"}
  ],
  "tribunal_verdict": {
    "skeptic_summary": "Candidate lacks Kubernetes experience...",
    "advocate_summary": "Strong Java and Python background with cloud exposure...",
    "consensus_flags": ["missing_k8s"],
    "consensus_strengths": ["strong_backend", "cloud_aware"],
    "trajectory_analysis": {"direction": "upward", "reasoning": "Progressive role growth..."},
    "narrative_tag": "solid_performer"
  }
}
```
