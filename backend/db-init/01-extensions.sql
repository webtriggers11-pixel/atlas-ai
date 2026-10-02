-- Runs once, the first time the Postgres volume is created (docker-entrypoint-initdb.d).
-- pgvector adds the `vector` column type and similarity operators (<=>, <->, <#>).
CREATE EXTENSION IF NOT EXISTS vector;
