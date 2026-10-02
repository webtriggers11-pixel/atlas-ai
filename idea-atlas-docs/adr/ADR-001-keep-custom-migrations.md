# ADR-001: Keep our custom migration system (not Alembic)

- **Status:** Accepted
- **Date:** 2026-10-02

## Context

The backend has its own migration system in `backend/migrations/`:

1. `SchemaComparator` compares SQLAlchemy models (`Base.metadata`) with the
   live database.
2. `SQLGenerator` turns the differences into PostgreSQL DDL.
3. `MigrationManager` writes the SQL to a timestamped `.sql` file, applies it,
   and records it in the `schema_migrations` table.

It runs on startup when `AUTO_MIGRATE=true`, or manually through
`migrations/migrate.py`.

Alembic, the usual SQLAlchemy migration tool, was considered for V2.

## Decision

Keep the custom system. It already manages the production schema, the team
knows it, and switching tools would add a migration-of-the-migrations step
with no product benefit. V2 extends it instead of replacing it.

## Changes V2 needs from the system (Phase 1)

| Need | Why | Change |
|---|---|---|
| Enable extensions | pgvector must exist before any `vector` column is created | run `CREATE EXTENSION IF NOT EXISTS vector` before the generated DDL |
| `vector(384)` type | chunk embeddings move from a float array to pgvector | map `pgvector.sqlalchemy.Vector` in `SQLGenerator._pg_type` and `SchemaComparator` type normalization |
| HNSW / GIN indexes | fast vector search and full-text search | emit `CREATE INDEX ... USING hnsw (embedding vector_cosine_ops)` / `USING gin (tsv)` from the index's `postgresql_using` / `postgresql_ops` options |
| Enum and `tsvector` columns | finding status, full-text search | type mapping for both |

## Known risks and how we handle them

- **Destructive DDL.** The generator can emit `DROP COLUMN` when a model field
  is removed or renamed. A rename therefore looks like "drop old + add new" and
  loses data. Mitigation: never rename a column by editing the model alone.
  Write the rename SQL by hand, and review the printed diff before applying.
- **Generated SQL is not in git** (`migrations/auto_generated/` is ignored).
  Each environment keeps its own history in `schema_migrations`. Mitigation:
  review the diff summary that `generate_migration()` prints before applying in
  production.
- **Production startup.** With `AUTO_MIGRATE=true`, a deploy applies schema
  changes without review. Recommended: `AUTO_MIGRATE=false` in production and
  run `migrations/migrate.py` deliberately after checking the diff.

## Consequences

- No Alembic dependency or `alembic/` folder.
- Phase 1 includes extending `backend/migrations/` for pgvector, with unit
  tests for the new type and index SQL.
- Interview angle: being able to explain how schema diffing works (model
  metadata vs `information_schema`, the order of DDL, why renames are dangerous)
  is a stronger answer than "I ran `alembic upgrade head`".
