-- ==========================================
-- SKILL NODES (The Entities)
-- ==========================================

-- 1. Frontend Web
INSERT INTO skill_nodes (slug, name, category) VALUES
('javascript', 'JavaScript', 'frontend'),
('typescript', 'TypeScript', 'frontend'),
('react', 'React', 'frontend'),
('vue_js', 'Vue.js', 'frontend'),
('angular', 'Angular', 'frontend'),
('html_css', 'HTML/CSS', 'frontend'),
('redux', 'Redux', 'frontend'),
('tailwind_css', 'Tailwind CSS', 'frontend'),
('next_js', 'Next.js', 'frontend')
ON CONFLICT (slug) DO NOTHING;

-- 2. Backend
INSERT INTO skill_nodes (slug, name, category) VALUES
('python', 'Python', 'backend'),
('java', 'Java', 'backend'),
('golang', 'Go', 'backend'),
('fastapi', 'FastAPI', 'backend'),
('django', 'Django', 'backend'),
('spring_boot', 'Spring Boot', 'backend'),
('node_js', 'Node.js', 'backend'),
('rest_api', 'REST API', 'backend'),
('graphql', 'GraphQL', 'backend'),
('postgresql', 'PostgreSQL', 'backend'),
('mongodb', 'MongoDB', 'backend')
ON CONFLICT (slug) DO NOTHING;

-- 3. Data Engineering
INSERT INTO skill_nodes (slug, name, category) VALUES
('sql', 'SQL', 'data'),
('apache_spark', 'Apache Spark', 'data'),
('apache_kafka', 'Apache Kafka', 'data'),
('airflow', 'Apache Airflow', 'data'),
('snowflake', 'Snowflake', 'data'),
('databricks', 'Databricks', 'data'),
('dbt', 'dbt', 'data'),
('etl_pipelines', 'ETL Pipelines', 'data')
ON CONFLICT (slug) DO NOTHING;

-- 4. DevOps/Cloud
INSERT INTO skill_nodes (slug, name, category) VALUES
('aws', 'AWS', 'devops'),
('azure', 'Azure', 'devops'),
('gcp', 'GCP', 'devops'),
('docker', 'Docker', 'devops'),
('kubernetes', 'Kubernetes', 'devops'),
('terraform', 'Terraform', 'devops'),
('ci_cd', 'CI/CD', 'devops'),
('ci_cd', 'CI/CD', 'devops'),
('linux', 'Linux', 'devops'),
('pulumi', 'Pulumi', 'devops'),
('git', 'Git', 'devops'),
('html5', 'HTML5', 'frontend'),
('agile', 'Agile Methodology', 'devops'),
('scrum', 'Scrum', 'devops'),
('jira', 'Jira', 'devops'),
('http', 'HTTP', 'backend')
ON CONFLICT (slug) DO NOTHING;

-- 5. Machine Learning
INSERT INTO skill_nodes (slug, name, category) VALUES
('pytorch', 'PyTorch', 'ml'),
('tensorflow', 'TensorFlow', 'ml'),
('huggingface', 'HuggingFace', 'ml'),
('scikit_learn', 'scikit-learn', 'ml'),
('pandas', 'Pandas', 'ml'),
('numpy', 'NumPy', 'ml'),
('nlp', 'NLP', 'ml'),
('computer_vision', 'Computer Vision', 'ml')
ON CONFLICT (slug) DO NOTHING;

-- 6. Concepts / Metaskills
INSERT INTO skill_nodes (slug, name, category) VALUES
('sdlc', 'Software Development Life Cycle', 'concept'),
('version_control', 'Version Control Systems', 'concept')
ON CONFLICT (slug) DO NOTHING;

-- 7. Extended DevOps & Data (Added via Bugfix)
INSERT INTO skill_nodes (slug, name, category) VALUES
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
('logstash', 'Logstash', 'data')
ON CONFLICT (slug) DO NOTHING;

-- ==========================================
-- SKILL EDGES (The Intelligence)
-- ==========================================

-- PARENT_OF (Hierarchy/Implied Knowledge)

INSERT INTO skill_edges (source_slug, target_slug, relation_type) VALUES
-- Frontend
('javascript', 'react', 'parent_of'),
('javascript', 'vue_js', 'parent_of'),
('javascript', 'angular', 'parent_of'),
('typescript', 'angular', 'parent_of'),
('react', 'next_js', 'parent_of'),
('react', 'redux', 'parent_of'),

-- Backend
('python', 'django', 'parent_of'),
('python', 'fastapi', 'parent_of'),
('java', 'spring_boot', 'parent_of'),
('javascript', 'node_js', 'parent_of'),

-- Data
('python', 'pandas', 'parent_of'),
('python', 'numpy', 'parent_of'),
('python', 'apache_spark', 'parent_of'), -- PySpark
('sql', 'dbt', 'parent_of'),
('sql', 'snowflake', 'parent_of'),

-- DevOps
('linux', 'docker', 'parent_of'),
('docker', 'kubernetes', 'parent_of'),

-- DevOps (Extended)
('git', 'gitlab', 'parent_of'),
('git', 'bitbucket', 'parent_of'),
('ci_cd', 'jenkins', 'parent_of'),
('ci_cd', 'circleci', 'parent_of'),
('ci_cd', 'travis_ci', 'parent_of'),
('ci_cd', 'gitlab', 'parent_of'),

-- ML
('python', 'pytorch', 'parent_of'),
('python', 'tensorflow', 'parent_of'),
('python', 'scikit_learn', 'parent_of'),

-- Concepts
('sdlc', 'agile', 'parent_of'), -- Agile implies knowledge of SDLC
('sdlc', 'scrum', 'parent_of'), 
('version_control', 'git', 'parent_of') -- Git implies knowledge of Version Control
ON CONFLICT (source_slug, target_slug, relation_type) DO NOTHING;

-- ALTERNATIVE_TO (Substitution/Siblings)

INSERT INTO skill_edges (source_slug, target_slug, relation_type) VALUES
-- Frontend
('react', 'vue_js', 'alternative_to'),
('react', 'angular', 'alternative_to'),
('html_css', 'html5', 'alternative_to'), -- Link generic and specific versions

-- Backend
('django', 'fastapi', 'alternative_to'),
('java', 'golang', 'alternative_to'), -- Strong assumption, but often swapped
('postgresql', 'mongodb', 'alternative_to'), -- Relational vs NoSQL, but "Database" slot

-- Data
('snowflake', 'databricks', 'alternative_to'),
('apache_spark', 'pandas', 'alternative_to'), -- Scale diff, but API similar

-- DevOps
('aws', 'azure', 'alternative_to'),
('aws', 'gcp', 'alternative_to'),
('azure', 'gcp', 'alternative_to'),
('terraform', 'pulumi', 'alternative_to'), -- Pulumi implies Terraform concepts

-- ML
('pytorch', 'tensorflow', 'alternative_to')
ON CONFLICT (source_slug, target_slug, relation_type) DO NOTHING;

-- ==========================================
-- SKILL ALIASES (The Vocabulary)
-- ==========================================

INSERT INTO skill_aliases (skill_id, alias) VALUES
-- Frontend
('html5', 'HTML'), ('html5', 'html_5'),
('react', 'ReactJS'), ('react', 'react.js'),
('vue_js', 'Vue'), ('vue_js', 'VueJS'),
('node_js', 'Node'), ('node_js', 'NodeJS'),

-- Backend
('golang', 'GoLang'),
('postgresql', 'Postgres'),
('rest_api', 'Restful'), ('rest_api', 'RESTful'), ('rest_api', 'Restful API'), ('rest_api', 'REST'), ('rest_api', 'Rest'),

-- DevOps
('git', 'GitHub'), ('git', 'Github'),
('aws', 'AWS Cloud'), ('aws', 'Amazon Web Services'),
('agile', 'Agile Methodologies'), ('agile', 'Agile Methodology'),
('scrum', 'Scrum Master'),
('scrum', 'Scrum Master'),
('sdlc', 'SDLC'), ('sdlc', 'Software Development Lifecycle'),
('version_control', 'VCS'), ('version_control', 'Source Control'),
('http', 'HTTPS'), ('http', 'Http'), ('http', 'Hyper Text Transfer Protocol')
ON CONFLICT (alias) DO NOTHING;
