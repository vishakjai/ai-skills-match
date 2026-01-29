-- Skills Graph Schema

DROP TABLE IF EXISTS skill_aliases CASCADE;
DROP TABLE IF EXISTS skill_edges CASCADE;
DROP TABLE IF EXISTS skill_nodes CASCADE;

CREATE TABLE skill_nodes (
    slug TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    category TEXT NOT NULL
);

CREATE TABLE skill_edges (
    source_slug TEXT NOT NULL REFERENCES skill_nodes(slug),
    target_slug TEXT NOT NULL REFERENCES skill_nodes(slug),
    relation_type TEXT NOT NULL CHECK (relation_type IN ('parent_of', 'alternative_to')),
    weight FLOAT DEFAULT 1.0, -- 1.0 for parent, 0.5 for alternative?
    PRIMARY KEY (source_slug, target_slug, relation_type)
);

CREATE INDEX idx_skill_edges_source ON skill_edges(source_slug);
CREATE INDEX idx_skill_edges_target ON skill_edges(target_slug);

CREATE TABLE skill_aliases (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    skill_id TEXT NOT NULL REFERENCES skill_nodes(slug) ON DELETE CASCADE,
    alias TEXT NOT NULL,
    UNIQUE(alias) -- Aliases must be unique
);

CREATE INDEX idx_skill_aliases_alias ON skill_aliases(alias);
