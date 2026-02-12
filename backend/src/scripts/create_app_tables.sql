-- ============================================================================
-- Application Tables: Users, JD Extractions, CV Extractions, Analysis Reports
-- Run AFTER graph_schema.sql (skill_nodes etc. must already exist)
-- ============================================================================

-- 1. App Users
-- Lightweight user table – stores whoever uploads / runs analysis.
-- No auth logic here; the app simply records an identifier.
CREATE TABLE IF NOT EXISTS app_users (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username    TEXT NOT NULL UNIQUE,
    email       TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 2. JD Extractions
-- Stores every extracted Job Description along with the raw input text.
CREATE TABLE IF NOT EXISTS jd_extractions (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    uploaded_by     UUID REFERENCES app_users(id) ON DELETE SET NULL,
    raw_text        TEXT NOT NULL,
    filename        TEXT,
    extracted_json  JSONB NOT NULL,          -- full JobDescription model
    model_used      TEXT,                     -- e.g. "gpt-4o-2024-08-06"
    is_valid        BOOLEAN DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_jd_extractions_user   ON jd_extractions(uploaded_by);
CREATE INDEX IF NOT EXISTS idx_jd_extractions_date   ON jd_extractions(created_at);

-- 3. CV / Resume Extractions
-- Stores every extracted Candidate Profile along with the raw input text.
CREATE TABLE IF NOT EXISTS cv_extractions (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    uploaded_by     UUID REFERENCES app_users(id) ON DELETE SET NULL,
    raw_text        TEXT NOT NULL,
    filename        TEXT,
    extracted_json  JSONB NOT NULL,          -- full CandidateProfile model
    model_used      TEXT,
    is_valid        BOOLEAN DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_cv_extractions_user   ON cv_extractions(uploaded_by);
CREATE INDEX IF NOT EXISTS idx_cv_extractions_date   ON cv_extractions(created_at);

-- 4. Analysis Reports
-- Stores the match/analysis result of a CV against a JD.
CREATE TABLE IF NOT EXISTS analysis_reports (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    jd_id           UUID NOT NULL REFERENCES jd_extractions(id) ON DELETE CASCADE,
    cv_id           UUID NOT NULL REFERENCES cv_extractions(id) ON DELETE CASCADE,
    run_by          UUID REFERENCES app_users(id) ON DELETE SET NULL,
    score           FLOAT NOT NULL,
    analysis_json   JSONB NOT NULL,          -- full MatchResult model
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_analysis_reports_jd   ON analysis_reports(jd_id);
CREATE INDEX IF NOT EXISTS idx_analysis_reports_cv   ON analysis_reports(cv_id);
CREATE INDEX IF NOT EXISTS idx_analysis_reports_user ON analysis_reports(run_by);
CREATE INDEX IF NOT EXISTS idx_analysis_reports_date ON analysis_reports(created_at);
