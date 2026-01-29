-- 1. The Canonical Skills Table (The "Truth")
CREATE TABLE skill_nodes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    slug TEXT UNIQUE NOT NULL, -- e.g., 'apache-spark'
    canonical_name TEXT NOT NULL, -- e.g., 'Apache Spark'
    category TEXT NOT NULL, -- 'language', 'framework', 'cloud', 'concept'
    metadata JSONB DEFAULT '{}', -- store things like 'is_deprecated', 'logo_url'
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 2. The Aliases Table (The "Parser Helper")
-- Maps "JS", "ECMAScript", "NodeJS" (maybe) -> "JavaScript"
CREATE TABLE skill_aliases (
    alias TEXT NOT NULL,
    skill_id UUID REFERENCES skill_nodes(id) ON DELETE CASCADE,
    source TEXT DEFAULT 'manual', -- 'manual', 'ai_generated', 'user_submission'
    confidence FLOAT DEFAULT 1.0, -- if AI generated, we might trust it less
    PRIMARY KEY (alias, skill_id)
);

-- Index for fast lookup during extraction
CREATE INDEX idx_aliases_lower ON skill_aliases (lower(alias));

-- 3. The Graph Edges (The "Logic")
-- Defines relationships: Python -> is_parent_of -> Django
CREATE TABLE skill_edges (
    source_id UUID REFERENCES skill_nodes(id),
    target_id UUID REFERENCES skill_nodes(id),
    relation_type TEXT NOT NULL CHECK (relation_type IN ('parent_of', 'related_to', 'prerequisite_for')),
    weight FLOAT DEFAULT 1.0, -- 1.0 = strong link, 0.5 = weak link
    PRIMARY KEY (source_id, target_id, relation_type)
);

-- 4. Enable Vector Extension (for that Hybrid approach later)
CREATE EXTENSION IF NOT EXISTS vector;

-- Add embeddings to nodes for "fuzzy lookup" when Regex fails
ALTER TABLE skill_nodes ADD COLUMN embedding vector(1536);

-- FUNCTION: calculate_skill_distance
-- Returns the number of hops and the path between two skills
CREATE OR REPLACE FUNCTION get_skill_distance(candidate_skill_id UUID, job_req_skill_id UUID, max_hops INT DEFAULT 3)
RETURNS TABLE (hops INT, path_names TEXT[], aggregated_weight FLOAT) AS $$
BEGIN
    RETURN QUERY
    WITH RECURSIVE graph_traversal AS (
        -- Base Case: Start at the candidate's skill
        SELECT 
            s.id AS current_id,
            0 AS depth,
            ARRAY[s.canonical_name] AS path,
            1.0::FLOAT AS total_weight
        FROM skill_nodes s
        WHERE s.id = candidate_skill_id

        UNION ALL

        -- Recursive Step: Traverse edges
        SELECT 
            e.target_id,
            gt.depth + 1,
            gt.path || n.canonical_name,
            gt.total_weight * e.weight -- Decay score based on edge weight
        FROM skill_edges e
        JOIN graph_traversal gt ON e.source_id = gt.current_id
        JOIN skill_nodes n ON e.target_id = n.id
        WHERE gt.depth < max_hops
    )
    SELECT 
        depth, 
        path, 
        total_weight
    FROM graph_traversal
    WHERE current_id = job_req_skill_id
    ORDER BY depth ASC -- Prefer shortest path
    LIMIT 1;
END;
$$ LANGUAGE plpgsql;
