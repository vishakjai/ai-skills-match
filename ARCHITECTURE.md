# AI Skills Match Engine - Architecture & Data Flow Documentation

## Table of Contents
1. [Project Overview](#1-project-overview)
2. [High-Level Architecture](#2-high-level-architecture)
3. [Component Breakdown](#3-component-breakdown)
4. [Data Models](#4-data-models)
5. [End-to-End Data Flow](#5-end-to-end-data-flow)
6. [Database Interaction Flow](#6-database-interaction-flow)
7. [External API Integration](#7-external-api-integration)
8. [Key Design Decisions](#8-key-design-decisions)

---

## 1. Project Overview

**Talience Core** is a deterministic, explainable Resume-to-Job Description matching engine. It uses a hybrid approach combining:

- **LLM-based extraction** (GPT-4o for structured parsing)
- **FlashText keyword extraction** (dictionary-based, fast)
- **Graph-based skill ontology** (NetworkX for semantic relationships)
- **Adversarial AI tribunal** (for career narrative analysis)

### Technology Stack

| Layer | Technology |
|-------|------------|
| Frontend | React + TypeScript + Vite + TailwindCSS |
| Backend | Python + FastAPI + Pydantic |
| Database | PostgreSQL (Supabase) |
| AI/ML | OpenAI GPT-4o, FlashText, NetworkX |

---

## 2. High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              FRONTEND (React + Vite)                            │
│  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐                     │
│  │   App.tsx      │  │ BatchDashboard │  │ JDConfigView   │                     │
│  │  Single Match  │  │  Bulk Process  │  │ Config Editor  │                     │
│  └───────┬────────┘  └───────┬────────┘  └───────┬────────┘                     │
│          │                   │                   │                              │
│          └───────────────────┼───────────────────┘                              │
│                              ▼                                                  │
│                    ┌─────────────────┐                                          │
│                    │    api.ts       │  (HTTP Client Layer)                     │
│                    └────────┬────────┘                                          │
└─────────────────────────────┼───────────────────────────────────────────────────┘
                              │ HTTP REST
                              ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                         BACKEND (FastAPI + Python)                              │
│                                                                                 │
│  ┌──────────────────────────────────────────────────────────────────────────┐   │
│  │                        API LAYER (src/api/main.py)                       │   │
│  │   /match  /extract/resume  /extract/jd  /batch/upload  /batch/{id}      │   │
│  └───────────────────────────────┬──────────────────────────────────────────┘   │
│                                  │                                              │
│  ┌───────────────────────────────┼──────────────────────────────────────────┐   │
│  │                        SERVICE LAYER                                      │   │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐           │   │
│  │  │ BatchProcessor  │  │ TribunalService │  │ GuardrailsService│          │   │
│  │  └────────┬────────┘  └────────┬────────┘  └────────┬────────┘           │   │
│  └───────────┼────────────────────┼────────────────────┼────────────────────┘   │
│              │                    │                    │                        │
│  ┌───────────┼────────────────────┼────────────────────┼────────────────────┐   │
│  │           │         EXTRACTION LAYER                │                    │   │
│  │  ┌────────▼────────┐  ┌────────▼────────┐  ┌────────▼────────┐           │   │
│  │  │ LLMExtractor    │  │ SkillExtractor  │  │ ExtractionPipeline│         │   │
│  │  │ (GPT-4o)        │  │ (FlashText)     │  │ (Hybrid Merge)    │         │   │
│  │  └─────────────────┘  └─────────────────┘  └─────────────────┘           │   │
│  └──────────────────────────────────────────────────────────────────────────┘   │
│                                                                                 │
│  ┌──────────────────────────────────────────────────────────────────────────┐   │
│  │                           CORE LAYER                                     │   │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐           │   │
│  │  │ engine.py       │  │ graph.py        │  │ models.py       │           │   │
│  │  │ (Match Scoring) │  │ (SkillsGraph)   │  │ (Pydantic)      │           │   │
│  │  └────────┬────────┘  └────────┬────────┘  └─────────────────┘           │   │
│  └───────────┼────────────────────┼─────────────────────────────────────────┘   │
│              │                    │                                             │
└──────────────┼────────────────────┼─────────────────────────────────────────────┘
               │                    │
               ▼                    ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                       DATABASE (PostgreSQL / Supabase)                          │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐                  │
│  │  skill_nodes    │  │  skill_aliases  │  │  skill_edges    │                  │
│  │  (Canonical)    │  │  (Lookup Map)   │  │  (Relationships)│                  │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Component Breakdown

### 3.1 Frontend (`frontend/src/`)

| File | Purpose |
|------|---------|
| `App.tsx` | Main entry - Single Match mode UI with Resume/JD input, extraction, and match results display |
| `BatchDashboard.tsx` | Bulk processing UI - 3-step wizard (JD Input → Configure → Upload Resumes) |
| `JDConfigurationView.tsx` | JD configuration editor for adjusting requirements, priorities, seniority levels |
| `api.ts` | HTTP client with TypeScript interfaces matching backend Pydantic models |
| `components/SkillRow.tsx` | Renders individual skill match status (matched/missing/partial) |
| `components/AnalysisCard.tsx` | Displays analysis sections (Education, Experience, Competencies) |

### 3.2 Backend API Layer (`backend/src/api/main.py`)

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/health` | GET | Health check |
| `/match` | POST | Deterministic matching between structured Candidate & JD |
| `/extract/resume` | POST | Extract resume text → CandidateProfile |
| `/extract/jd` | POST | Extract JD text → JobDescription |
| `/extract/resume/file` | POST | Upload PDF/DOCX → CandidateProfile |
| `/extract/jd/file` | POST | Upload PDF/DOCX → JobDescription |
| `/batch/upload` | POST | Submit batch job with JD + multiple resumes |
| `/batch/{batch_id}` | GET | Poll batch job status and results |
| `/utils/parse_doc` | POST | Parse document to raw text |

### 3.3 Service Layer (`backend/src/services/`)

| Service | File | Purpose |
|---------|------|---------|
| **BatchProcessor** | `batch_processor.py` | Async batch processing of multiple resumes against a JD |
| **TribunalService** | `tribunal.py` | LLM-powered adversarial debate (Skeptic vs Advocate) for career narrative analysis |
| **DocumentGuardService** | `guardrails.py` | File validation (MIME type, keyword classification to detect Resume vs JD) |
| **LocationService** | `location.py` | Geographic proximity checking for location requirements |

### 3.4 Extraction Layer (`backend/src/extraction/`)

| Component | File | Purpose |
|-----------|------|---------|
| **LLMExtractor** | `llm_extractor.py` | GPT-4o structured output parsing for JD and Resume |
| **SkillExtractor** | `extractor.py` | FlashText-based dictionary keyword extraction |
| **ExtractionPipeline** | `pipeline.py` | Hybrid merge logic (LLM + FlashText results) |
| **Mappers** | `mappers.py` | Convert extracted entities to structured models |

### 3.5 Core Layer (`backend/src/core/`)

| Component | File | Purpose |
|-----------|------|---------|
| **MatchEngine** | `engine.py` | Deterministic scoring algorithm (Education 10%, Experience 10%, Competencies 10%, Required Skills 50%, Preferred Skills 20%) |
| **SkillsGraph** | `graph.py` | NetworkX DiGraph for skill ontology (parent_of, alternative_to relationships) |
| **Models** | `models.py` | Pydantic schemas (CandidateProfile, JobDescription, Requirement, etc.) |
| **Utils** | `utils.py` | Skill normalization, slug generation |

### 3.6 Database Schema (`backend/supabase_schema.sql`)

| Table | Purpose |
|-------|---------|
| `skill_nodes` | Canonical skills (slug, name, category, optional embedding vector) |
| `skill_aliases` | Alias → skill_id mapping (e.g., "JS" → "javascript") |
| `skill_edges` | Relationships (parent_of, alternative_to, prerequisite_for) with weights |

---

## 4. Data Models

### 4.1 CandidateProfile (Resume)

```
CandidateProfile
├── id: str
├── candidate_metadata: {name, location, links[]}
├── computed_stats: {total_yoe, avg_tenure_months, management_experience_years}
├── timeline: TimelineEntry[]
│   ├── company, title_raw, start_date, end_date
│   └── extracted_skills: [{skill_id, context}]
├── skill_profile: SkillProfileEntry[]
│   └── {skill_slug, total_months, last_used, competency_level, sources[]}
├── education: EducationEntry[]
│   └── {degree, field, institution, year}
├── competencies: string[] (soft skills)
├── is_valid: bool
└── parsing_error: string?
```

### 4.2 JobDescription

```
JobDescription
├── id: str
├── job_metadata: {title, location, work_mode, clearance}
├── gating_rules: {visa_sponsorship, education_min, education_strict, location_strict}
├── requirements: Requirement[]
│   └── {req_id, skill_id, priority, level, is_hard_filter, min_years}
├── competencies: Competency[]
│   └── {name, description, priority}
├── seniority_signals: {target_level, keywords_found[]}
├── is_valid: bool
└── parsing_error: string?
```

### 4.3 MatchResult

```
MatchResult
├── score: float (0-100)
├── analysis: AnalysisSection[]
│   └── {title, status, summary, details[]}
├── technical_trace: TraceItem[]
│   └── {skill_slug, status, score, seniority_level, sources[], priority}
└── tribunal_verdict: TribunalVerdict?
    ├── skeptic_summary, advocate_summary
    ├── consensus_flags[], consensus_strengths[]
    ├── trajectory_analysis: {direction, reasoning}
    └── narrative_tag: "top_tier_potential" | "solid_performer" | "high_risk" | "mismatch"
```

---

## 5. End-to-End Data Flow

### 5.1 Single Match Flow (UI → API → DB → API → UI)

```
USER ACTION: Upload Resume PDF + Paste JD Text → Click "Analyze Match"

  ┌─────────────┐
  │  Frontend   │
  │  App.tsx    │
  └──────┬──────┘
         │ 1. User uploads Resume (PDF)
         ▼
  ┌─────────────────────────────────────────────────────────────────────┐
  │ POST /extract/resume/file                                           │
  │ Body: FormData {file: resume.pdf}                                   │
  └──────┬──────────────────────────────────────────────────────────────┘
         │
         ▼
  ┌─────────────────────────────────────────────────────────────────────┐
  │ BACKEND: DocumentGuardService.validate_upload()                     │
  │   • Magic byte check (PDF/DOCX/TXT only)                            │
  │   • Extract text from PDF (pypdf)                                   │
  │   • Keyword classification (Resume vs JD signals)                   │
  └──────┬──────────────────────────────────────────────────────────────┘
         │ ✓ Valid Resume
         ▼
  ┌─────────────────────────────────────────────────────────────────────┐
  │ BACKEND: ExtractionPipeline.extract_resume()                        │
  │                                                                     │
  │   ┌─────────────────┐     ┌─────────────────┐                       │
  │   │ LLMExtractor    │     │ SkillExtractor  │                       │
  │   │ (GPT-4o)        │     │ (FlashText)     │                       │
  │   │                 │     │                 │                       │
  │   │ • Parse text    │     │ • Load aliases  │◄────┐                 │
  │   │ • Structured    │     │   from DB       │     │                 │
  │   │   Output        │     │ • Extract       │     │                 │
  │   │                 │     │   keywords      │     │                 │
  │   └────────┬────────┘     └────────┬────────┘     │                 │
  │            │                       │              │                 │
  │            └───────────┬───────────┘              │                 │
  │                        ▼                          │                 │
  │            ┌─────────────────────┐                │                 │
  │            │ merge_profiles()    │                │                 │
  │            │ (Hybrid Merge)      │                │                 │
  │            └──────────┬──────────┘                │                 │
  └───────────────────────┼───────────────────────────┼─────────────────┘
                          │                           │
                          │                           │
         ┌────────────────┘                           │
         ▼                                            │
  ┌─────────────────────┐                    ┌────────┴────────┐
  │  CandidateProfile   │                    │   PostgreSQL    │
  │  (JSON Response)    │                    │   (Supabase)    │
  └──────────┬──────────┘                    │                 │
             │                               │ skill_nodes     │
         ◄───┘                               │ skill_aliases   │
                                             │ skill_edges     │
                                             └─────────────────┘
         │
         ▼ Response to Frontend
  ┌─────────────┐
  │  Frontend   │  2. Display extracted Candidate JSON in textarea
  │  App.tsx    │
  └──────┬──────┘
         │ 3. User pastes JD text → Clicks "Extract"
         ▼
  ┌─────────────────────────────────────────────────────────────────────┐
  │ POST /extract/jd                                                    │
  │ Body: {text: "Job Description text...", api_key: ""}               │
  └──────┬──────────────────────────────────────────────────────────────┘
         │
         ▼
  ┌─────────────────────────────────────────────────────────────────────┐
  │ BACKEND: ExtractionPipeline.extract_jd()                            │
  │   • LLMExtractor → GPT-4o structured output                         │
  │   • SkillExtractor → FlashText keyword extraction                   │
  │   • Merge: Add FlashText skills not found by LLM                    │
  │   • Normalize skill_ids via ontology.resolve_alias()                │
  └──────┬──────────────────────────────────────────────────────────────┘
         │
         ▼
  ┌─────────────────────┐
  │   JobDescription    │
  │   (JSON Response)   │
  └──────────┬──────────┘
             │
         ◄───┘
         │
         ▼ Response to Frontend
  ┌─────────────┐
  │  Frontend   │  4. Display extracted JD JSON (optionally Configure)
  │  App.tsx    │
  └──────┬──────┘
         │ 5. User clicks "ANALYZE MATCH"
         ▼
  ┌─────────────────────────────────────────────────────────────────────┐
  │ POST /match                                                         │
  │ Body: {candidate: CandidateProfile, job_description: JobDescription}│
  └──────┬──────────────────────────────────────────────────────────────┘
         │
         ▼
  ┌─────────────────────────────────────────────────────────────────────┐
  │ BACKEND: engine.calculate_match()                                   │
  │                                                                     │
  │   ┌─────────────────────────────────────────────────────────────┐   │
  │   │ 1. PRE-PROCESS CANDIDATE SKILLS                             │   │
  │   │    • Resolve aliases via ontology                           │   │
  │   │    • Merge skills from: skill_profile, timeline, skills[]   │   │
  │   └─────────────────────────────────────────────────────────────┘   │
  │                           │                                         │
  │                           ▼                                         │
  │   ┌─────────────────────────────────────────────────────────────┐   │
  │   │ 2. GRAPH MATCHING (SkillsGraph)                             │   │
  │   │    • Exact match: skill_id in candidate_skills → 1.0        │   │
  │   │    • Implied: React implies JavaScript → 1.0                │   │
  │   │    • Alternative: Vue alternative to React → 0.5            │   │
  │   │    • Fuzzy: token overlap fallback                          │   │
  │   └─────────────────────────────────────────────────────────────┘   │
  │                           │                                         │
  │                           ▼                                         │
  │   ┌─────────────────────────────────────────────────────────────┐   │
  │   │ 3. COMPOSITE SCORING                                        │   │
  │   │    ┌───────────────┬────────────┐                           │   │
  │   │    │ Component     │ Weight     │                           │   │
  │   │    ├───────────────┼────────────┤                           │   │
  │   │    │ Education     │ 10 pts     │                           │   │
  │   │    │ Experience    │ 10 pts     │                           │   │
  │   │    │ Competencies  │ 10 pts     │                           │   │
  │   │    │ Required Skills│ 50 pts    │                           │   │
  │   │    │ Preferred Skills│ 20 pts   │                           │   │
  │   │    └───────────────┴────────────┘                           │   │
  │   │    • Seniority multiplier applied per skill                 │   │
  │   │    • Hard filter penalty (cap at 40 if critical failure)    │   │
  │   └─────────────────────────────────────────────────────────────┘   │
  │                           │                                         │
  │                           ▼                                         │
  │   ┌─────────────────────────────────────────────────────────────┐   │
  │   │ 4. LOCATION ANALYSIS (Async)                                │   │
  │   │    • LocationService.check_proximity()                      │   │
  │   │    • Only if work_mode != "remote"                          │   │
  │   └─────────────────────────────────────────────────────────────┘   │
  │                           │                                         │
  │                           ▼                                         │
  │   ┌─────────────────────────────────────────────────────────────┐   │
  │   │ 5. TRIBUNAL (if score >= 60)                                │   │
  │   │    • TribunalService.evaluate_narrative()                   │   │
  │   │    • GPT-4o adversarial debate                              │   │
  │   │    • Skeptic vs Advocate analysis                           │   │
  │   │    • narrative_tag: top_tier / solid / high_risk / mismatch │   │
  │   └─────────────────────────────────────────────────────────────┘   │
  │                           │                                         │
  └───────────────────────────┼─────────────────────────────────────────┘
                              │
                              ▼
  ┌─────────────────────────────────────────────────────────────────────┐
  │                         MatchResult                                 │
  │  {                                                                  │
  │    score: 78.5,                                                     │
  │    analysis: [{title: "Education", status: "met", ...}, ...],       │
  │    technical_trace: [{skill_slug: "java", status: "matched"}, ...], │
  │    tribunal_verdict: {narrative_tag: "solid_performer", ...}        │
  │  }                                                                  │
  └──────────────────────────────┬──────────────────────────────────────┘
                                 │
                                 ▼ Response to Frontend
  ┌─────────────────────────────────────────────────────────────────────┐
  │ FRONTEND: Render Results                                            │
  │   • Circular score gauge (0-100)                                    │
  │   • Tribunal verdict badge                                          │
  │   • Deep Analysis cards (Education, Experience, Competencies)       │
  │   • Technical trace (Required/Preferred skills with match status)   │
  └─────────────────────────────────────────────────────────────────────┘
```

### 5.2 Batch Processing Flow

```
STEP 1: JD Input
  ┌─────────────────┐
  │ BatchDashboard  │  User pastes/uploads JD text
  └────────┬────────┘
           │ POST /extract/jd
           ▼
  ┌─────────────────┐
  │ JobDescription  │  Extracted structured JD
  └────────┬────────┘

STEP 2: Configure
           │
           ▼
  ┌─────────────────────────────────────────┐
  │ JDConfigurationView                     │
  │   • Edit requirements (priority, level) │
  │   • Toggle is_hard_filter               │
  │   • Add/remove competencies             │
  └────────┬────────────────────────────────┘
           │ User confirms configuration
           ▼

STEP 3: Upload & Process
  ┌─────────────────┐
  │ BatchDashboard  │  User uploads multiple resume files
  └────────┬────────┘
           │ POST /batch/upload (FormData: jd_json + files[])
           ▼
  ┌─────────────────────────────────────────────────────────────────────┐
  │ BACKEND: InMemoryBatchProcessor.submit_batch()                      │
  │                                                                     │
  │   1. Generate batch_id (UUID)                                       │
  │   2. Initialize job state (pending)                                 │
  │   3. Background Task: process_all_resumes()                         │
  │      ┌─────────────────────────────────────────────────────────┐    │
  │      │ FOR EACH resume file:                                   │    │
  │      │   • DocumentGuardService.validate_upload()              │    │
  │      │   • ExtractionPipeline.extract_resume()                 │    │
  │      │   • engine.calculate_match(candidate, jd)               │    │
  │      │   • TribunalService.evaluate_narrative()                │    │
  │      │   • Update progress (processed_count / total_files)     │    │
  │      │   • Append to candidates[] results                      │    │
  │      └─────────────────────────────────────────────────────────┘    │
  │   4. Mark job status = "completed"                                  │
  └───────────────────────────────┬─────────────────────────────────────┘
                                  │
           ◄──────────────────────┘ Returns: {batch_id, poll_url}
           │
           ▼
  ┌─────────────────────────────────────────────────────────────────────┐
  │ FRONTEND: Polling Loop (every 2 seconds)                            │
  │   GET /batch/{batch_id}                                             │
  │   Display: progress bar, processed_count / total_files              │
  └────────┬────────────────────────────────────────────────────────────┘
           │ Status = "completed"
           ▼
  ┌─────────────────────────────────────────────────────────────────────┐
  │ FRONTEND: Render Results Table                                      │
  │   • Rank | Candidate Name | Score | Tribunal | Skills | Action     │
  │   • Click row → Modal with full MatchResult details                 │
  └─────────────────────────────────────────────────────────────────────┘
```

---

## 6. Database Interaction Flow

```
ON APPLICATION STARTUP (Lifespan):
  ┌─────────────────┐
  │ main.py lifespan│
  └────────┬────────┘
           │
           ▼
  ┌─────────────────────────────────────────────────────────────────────┐
  │ 1. SkillExtractor.__init__(db_url)                                  │
  │    → Connect to PostgreSQL                                          │
  │    → SELECT alias, slug, name FROM skill_aliases JOIN skill_nodes   │
  │    → Load into FlashText KeywordProcessor (in-memory dictionary)    │
  └─────────────────────────────────────────────────────────────────────┘
           │
           ▼
  ┌─────────────────────────────────────────────────────────────────────┐
  │ 2. SkillsGraph.load_from_db(db_url)                                 │
  │    → SELECT slug FROM skill_nodes → Add nodes to NetworkX graph     │
  │    → SELECT source, target, relation, weight FROM skill_edges       │
  │      → parent_of: Add edge target→source (child implies parent)     │
  │      → alternative_to: Add bidirectional edges with weight          │
  │    → SELECT alias, skill_id FROM skill_aliases                      │
  │      → Build alias_map for runtime resolution                       │
  └─────────────────────────────────────────────────────────────────────┘

DURING MATCHING:
  ┌─────────────────┐
  │ engine.py       │
  └────────┬────────┘
           │
           ▼
  ┌─────────────────────────────────────────────────────────────────────┐
  │ ontology.resolve_alias(skill_name)                                  │
  │   → Normalize input (lowercase, replace spaces with underscores)    │
  │   → Check alias_map (loaded from DB at startup)                     │
  │   → Return canonical slug                                           │
  └─────────────────────────────────────────────────────────────────────┘
           │
           ▼
  ┌─────────────────────────────────────────────────────────────────────┐
  │ ontology.get_related_scores(req_skill, candidate_skills)            │
  │   → Check graph edges for:                                          │
  │     • Direct match → 1.0                                            │
  │     • Implied relationship (graph edge type='implies') → 1.0        │
  │     • Alternative relationship (graph edge type='alternative') → 0.5│
  └─────────────────────────────────────────────────────────────────────┘
```

### Database Schema Details

```sql
-- 1. The Canonical Skills Table (The "Truth")
CREATE TABLE skill_nodes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    slug TEXT UNIQUE NOT NULL,           -- e.g., 'apache-spark'
    canonical_name TEXT NOT NULL,        -- e.g., 'Apache Spark'
    category TEXT NOT NULL,              -- 'language', 'framework', 'cloud', 'concept'
    metadata JSONB DEFAULT '{}',         -- 'is_deprecated', 'logo_url'
    embedding vector(1536),              -- For vector search fallback
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 2. The Aliases Table (The "Parser Helper")
CREATE TABLE skill_aliases (
    alias TEXT NOT NULL,
    skill_id UUID REFERENCES skill_nodes(id) ON DELETE CASCADE,
    source TEXT DEFAULT 'manual',        -- 'manual', 'ai_generated'
    confidence FLOAT DEFAULT 1.0,
    PRIMARY KEY (alias, skill_id)
);

-- 3. The Graph Edges (The "Logic")
CREATE TABLE skill_edges (
    source_id UUID REFERENCES skill_nodes(id),
    target_id UUID REFERENCES skill_nodes(id),
    relation_type TEXT NOT NULL CHECK (relation_type IN ('parent_of', 'related_to', 'prerequisite_for')),
    weight FLOAT DEFAULT 1.0,
    PRIMARY KEY (source_id, target_id, relation_type)
);
```

---

## 7. External API Integration

| Service | Provider | Purpose | Model |
|---------|----------|---------|-------|
| LLM Extraction | OpenAI | Structured JD/Resume parsing | GPT-4o-2024-08-06 |
| Tribunal | OpenAI | Career narrative analysis | GPT-4o |
| Database | Supabase | PostgreSQL hosting | - |

### OpenAI Integration Points

1. **LLMExtractor** (`extraction/llm_extractor.py`)
   - Uses `client.beta.chat.completions.parse()` for structured outputs
   - Response format: Pydantic model (JobDescription or CandidateProfile)

2. **TribunalService** (`services/tribunal.py`)
   - Adversarial debate prompt with Skeptic vs Advocate personas
   - Uses TOON (Token-Oriented Object Notation) for efficient context
   - Response format: TribunalVerdict Pydantic model

---

## 8. Key Design Decisions

### 8.1 Hybrid Extraction
LLM provides semantic understanding; FlashText ensures no skills are missed via dictionary lookup. Results are merged with LLM taking priority.

### 8.2 Graph-based Ontology
Skills form a directed graph (NetworkX) where edges encode semantic relationships:
- `parent_of`: React → JavaScript (knowing React implies knowing JavaScript)
- `alternative_to`: Vue ↔ React (similar frameworks, partial match score)

### 8.3 Deterministic Scoring
Fixed weights ensure explainable, reproducible scores:
- Required Skills: 50%
- Preferred Skills: 20%
- Education: 10%
- Experience: 10%
- Competencies: 10%

### 8.4 Adversarial Tribunal
"Skeptic vs Advocate" debate catches career red flags (role mismatch, stagnation) that pure skill matching misses. Only runs for candidates scoring ≥60.

### 8.5 In-Memory Batch State
Batch jobs stored in Python dict for simplicity. Production would use Redis/DB persistence.

### 8.6 Guardrails
File validation prevents Resume/JD confusion and malicious uploads before LLM processing.

---

## 9. Project Structure

```
ai-skills-match/
├── backend/
│   ├── src/
│   │   ├── api/
│   │   │   └── main.py              # FastAPI endpoints
│   │   ├── core/
│   │   │   ├── engine.py            # Match scoring engine
│   │   │   ├── graph.py             # SkillsGraph (NetworkX)
│   │   │   ├── models.py            # Pydantic schemas
│   │   │   └── utils.py             # Utility functions
│   │   ├── extraction/
│   │   │   ├── extractor.py         # FlashText keyword extractor
│   │   │   ├── llm_extractor.py     # GPT-4o structured extraction
│   │   │   ├── pipeline.py          # Hybrid extraction pipeline
│   │   │   └── mappers.py           # Entity to model mappers
│   │   ├── services/
│   │   │   ├── batch_processor.py   # Async batch processing
│   │   │   ├── tribunal.py          # Career narrative analysis
│   │   │   ├── guardrails.py        # Document validation
│   │   │   └── location.py          # Geographic proximity
│   │   └── main.py                  # App entry point
│   ├── scripts/
│   │   ├── init_db.py               # Database initialization
│   │   └── seed_db.py               # Seed skill ontology
│   ├── supabase_schema.sql          # Database schema
│   └── pyproject.toml               # Python dependencies
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── SkillRow.tsx         # Skill match display
│   │   │   └── AnalysisCard.tsx     # Analysis section card
│   │   ├── App.tsx                  # Main application
│   │   ├── BatchDashboard.tsx       # Batch processing UI
│   │   ├── JDConfigurationView.tsx  # JD configuration editor
│   │   └── api.ts                   # HTTP client
│   ├── index.html
│   └── package.json
│
└── README.md
```

---

## 10. Summary

This is a **3-tier architecture** (Frontend → Backend API → Database) with sophisticated **AI/ML integration**:

- **Frontend**: React SPA with TypeScript, modern UI (TailwindCSS)
- **Backend**: FastAPI with async support, Pydantic validation
- **Database**: PostgreSQL with skill ontology (nodes, edges, aliases)
- **AI**: GPT-4o for extraction and tribunal analysis

The system provides **explainable, deterministic matching** with comprehensive analysis covering technical skills, education, experience, soft skills, and career trajectory.
