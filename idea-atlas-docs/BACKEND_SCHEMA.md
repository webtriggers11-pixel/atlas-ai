# Backend schema — Idea Atlas

Companion to `TRD.md`. PostgreSQL schema, defined here in plain terms; the
actual source of truth once building starts should be the SQLAlchemy models
+ Alembic migrations, not this document — update this file if the real
schema diverges.

## 1. Entity overview

```
maps (1) ──< nodes (many)
nodes (1) ──< nodes (many, self-referencing via parent_id)
nodes (1) ──< node_explanations (many, one per depth level)
maps (1) ──< edges (many)
```

A map is a topic the user generated. Nodes belong to a map and optionally
have a parent node (for expansions). Each node can have up to three cached
explanations, one per depth level. Edges are stored explicitly (not just
inferred from parent_id) so the graph can support non-tree relationships
later (e.g. a node related to two different parents) without a schema change.

## 2. Tables

### `maps`

| Column | Type | Notes |
|---|---|---|
| id | UUID, primary key | |
| topic | text | the original user input |
| title | text | display title, can equal topic or be cleaned up by the LLM |
| created_at | timestamptz | default now() |
| updated_at | timestamptz | updated on any node/edge change within this map |

### `nodes`

| Column | Type | Notes |
|---|---|---|
| id | UUID, primary key | |
| map_id | UUID, foreign key -> maps.id | cascade delete |
| parent_id | UUID, foreign key -> nodes.id, nullable | null for the root/center node |
| label | text | short concept name, e.g. "Attention mechanism" |
| position_x | float, nullable | for persisting manual drag positions |
| position_y | float, nullable | |
| is_root | boolean | true only for the center node of a map |
| created_at | timestamptz | default now() |

### `node_explanations`

| Column | Type | Notes |
|---|---|---|
| id | UUID, primary key | |
| node_id | UUID, foreign key -> nodes.id | cascade delete |
| depth | text | one of `gist`, `standard`, `expert` — enforce via check constraint or enum |
| content | text | the explanation text |
| created_at | timestamptz | default now() |

Unique constraint on `(node_id, depth)` — one cached explanation per depth
per node, so a `PATCH .../depth` request can upsert cleanly.

### `edges`

| Column | Type | Notes |
|---|---|---|
| id | UUID, primary key | |
| map_id | UUID, foreign key -> maps.id | cascade delete |
| source_node_id | UUID, foreign key -> nodes.id | |
| target_node_id | UUID, foreign key -> nodes.id | |
| created_at | timestamptz | default now() |

## 3. Indexes

- `nodes(map_id)` — fetching all nodes for a map is the most common query
- `nodes(parent_id)` — fetching children of a node during expansion
- `node_explanations(node_id, depth)` — covered by the unique constraint above, but worth confirming it's used as an index too
- `edges(map_id)` — fetching all edges for a map alongside its nodes

## 4. Example rows (for "transformers in AI")

`maps`: one row, `topic = "transformers in AI"`.

`nodes`: one root node (`label = "Transformers in AI"`, `is_root = true`,
`parent_id = null`), plus 6-8 child nodes (`label = "Attention mechanism"`,
`"Tokenization"`, etc., `parent_id` = the root node's id).

`node_explanations`: for the root node and each child, at least one row with
`depth = "standard"` (generated at creation time). Rows for `gist` or
`expert` only get created the first time a user actually requests that
depth — don't pre-generate all three for every node, that's wasted LLM calls.

`edges`: one edge per root-to-child relationship at creation time. When a
child node is later expanded, new edges connect it to its own new children.

## 5. Things to decide during implementation, not before

- Whether to use Postgres native `enum` for `depth` or a plain text column
  with a check constraint — either is fine, pick whichever SQLAlchemy makes
  less painful to migrate later
- Whether `position_x`/`position_y` should default to a computed layout on
  the backend or always be null until the user drags a node (frontend
  auto-layout fills the gap either way) — start with null, let React Flow's
  auto-layout handle initial positioning client-side
