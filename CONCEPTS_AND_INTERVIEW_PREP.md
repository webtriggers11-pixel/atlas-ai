# Concepts & Interview Prep — Idea Atlas

Every concept used in this project, explained in plain English with a
real example from our own codebase. Read this before your interview.
Each section ends with likely interview questions and clean answers.

---

## 1. REST API

**What it is in one line:**
A set of rules for how a frontend and backend talk to each other over
the internet using simple HTTP requests.

**Real example from our project:**
When you type "transformers in AI" and press enter, the React frontend
sends this to our FastAPI backend:

```
POST /maps
{ "topic": "transformers in AI", "depth": "standard" }
```

The backend processes it and sends back a JSON object with nodes and
edges. That exchange — request and response — is a REST API call.

**The key HTTP verbs and what they mean:**
- `GET` — fetch something (read only, no side effects)
- `POST` — create something new
- `PATCH` — partially update something that already exists
- `DELETE` — remove something

In our project: `GET /maps` fetches your saved maps list. `POST /maps`
creates a new map. `PATCH /maps/{id}/nodes/{node_id}/depth` updates just
the explanation depth of one node. `DELETE /maps/{id}` removes a map.

**Interview questions:**

Q: What is a REST API and how does it differ from a regular function call?
A: A REST API lets two separate programs (frontend and backend) communicate
over HTTP using standard verbs — GET to read, POST to create, PATCH to
update, DELETE to remove. Unlike a function call in one program, a REST
API works across machines, uses JSON to pass data, and is stateless —
each request carries all the information the server needs, with no memory
of previous requests.

Q: What does stateless mean in REST?
A: Each request is self-contained. The server doesn't remember what you
asked it before. So every request must include all the context needed —
like the map_id in the URL when expanding a node — rather than relying
on the server to "remember" which map you're working on.

---

## 2. FastAPI

**What it is in one line:**
A Python web framework for building APIs quickly, with automatic
documentation and built-in data validation.

**Real example from our project:**

```python
@app.post("/maps")
def create_map(req: MapRequest):
    # req is automatically validated — FastAPI rejects bad input
    # before this function even runs
    return atlas_service.create(req.topic, req.depth)
```

One decorator (`@app.post`), one function, and FastAPI handles routing,
validation, and JSON serialization automatically. It also generates
interactive API docs at `/docs` so you can test endpoints in a browser
without writing a single test client.

**Why we chose it over Flask or Django:**
FastAPI is async-first (handles multiple requests without blocking) and
Pydantic-native (validation is built in, not bolted on). For an AI app
where LLM calls can take several seconds, async matters — the server
stays responsive to other requests while waiting for Ollama to reply.

**Interview questions:**

Q: Why FastAPI over Flask for this project?
A: FastAPI is async-native, which matters when your endpoint waits 5-8
seconds for a local LLM to respond — Flask is synchronous by default and
would block the server during that wait. FastAPI also uses Pydantic for
automatic request validation and generates OpenAPI docs automatically,
which cuts boilerplate significantly.

Q: What is a decorator in Python, and how does FastAPI use them?
A: A decorator is a function that wraps another function to add behaviour.
FastAPI uses `@app.get("/path")` and `@app.post("/path")` decorators to
register functions as HTTP route handlers — so when a GET request hits
`/maps`, FastAPI knows to call the decorated function and return its
result as JSON.

---

## 3. Pydantic

**What it is in one line:**
A Python library that validates data and converts it to the right types
automatically, using class definitions.

**Real example from our project:**

```python
class MapRequest(BaseModel):
    topic: str
    depth: str = "standard"   # default value

class NodeOut(BaseModel):
    id: str
    label: str
    parent_id: str | None
    summary: str
```

When FastAPI receives a POST request to `/maps`, it automatically parses
the JSON body into a `MapRequest` object. If `topic` is missing or isn't
a string, FastAPI returns a 422 error before our code even runs. We don't
write any if-statements to check inputs.

**Interview questions:**

Q: What is Pydantic used for and why is it useful in an API?
A: Pydantic validates incoming data against a schema defined as a Python
class. In a FastAPI endpoint, if the request body is missing a required
field or has the wrong type, Pydantic rejects it automatically and returns
a clear error — no manual validation code needed. It's also used to
define response shapes, so the API always returns consistent JSON.

---

## 4. SQLAlchemy + Alembic

**What they are in one line:**
SQLAlchemy is a Python library that lets you work with a database using
Python objects instead of raw SQL. Alembic is a tool that tracks and
applies changes to your database schema over time.

**Real example from our project:**

```python
# SQLAlchemy model — defines the "maps" table as a Python class
class Map(Base):
    __tablename__ = "maps"
    id = Column(UUID, primary_key=True, default=uuid4)
    topic = Column(Text, nullable=False)
    created_at = Column(DateTime, default=func.now())
```

Instead of writing `SELECT * FROM maps WHERE id = '...'`, you write:
`db.query(Map).filter(Map.id == map_id).first()` — Python all the way.

Alembic handles schema changes. When you add a new column to the `maps`
table, you generate a migration file: `alembic revision --autogenerate`.
Alembic tracks which migrations have run and applies only new ones. This
is critical on Railway — migrations run automatically before the new
backend starts via the pre-deploy command.

**Interview questions:**

Q: What is an ORM and why use one instead of raw SQL?
A: An ORM (Object-Relational Mapper) lets you interact with a database
using your programming language's objects instead of SQL strings. It
reduces boilerplate, prevents many SQL injection vulnerabilities (because
queries are parameterized automatically), and makes your database code
refactorable alongside your Python code. The tradeoff is that complex
queries can be harder to optimize than hand-written SQL.

Q: What is a database migration and why does it matter?
A: A migration is a versioned, repeatable script that changes the database
schema — adding a column, creating a table, adding an index. Migrations
matter because production databases have real data you can't wipe when you
update your code. Alembic tracks which migrations have run so you can apply
exactly the changes needed to go from one version to the next without
losing data.

---

## 5. Postgres + pgvector

**What it is in one line:**
PostgreSQL is a reliable, open-source relational database. pgvector is an
extension that adds the ability to store and search vector embeddings.

**Real example from our project:**
Our four tables — `maps`, `nodes`, `node_explanations`, `edges` — are
all in Postgres. The relationship between them is: one map has many nodes,
one node has many explanations (one per depth level), and one map has many
edges connecting nodes. These relationships are enforced by foreign keys:

```sql
-- node belongs to a map, cascade delete if map is deleted
FOREIGN KEY (map_id) REFERENCES maps(id) ON DELETE CASCADE
```

pgvector is in the stack for v2 — when we add embedding-based features
(like "show me maps related to this one"), embeddings will be stored in
Postgres alongside the map data rather than needing a separate vector
database.

**Interview questions:**

Q: What is a foreign key and what does cascade delete do?
A: A foreign key is a column that references the primary key of another
table, enforcing a relationship — a node's `map_id` must match a real
map's `id`. Cascade delete means if you delete the parent (the map), the
database automatically deletes all the children (nodes, edges) that
reference it, so you don't end up with orphaned rows.

Q: What is a vector embedding and why would you store it in Postgres?
A: A vector embedding is a list of numbers that represents the meaning of
a piece of text — similar meanings produce similar vectors. Storing them
in Postgres with pgvector lets you search by semantic similarity
(cosine similarity) using SQL, without spinning up a separate vector
database like Pinecone or Weaviate. For a single-user local app this is
simpler, cheaper, and has fewer moving parts.

---

## 6. Docker and Docker Compose

**What they are in one line:**
Docker packages an app and all its dependencies into a container that
runs the same way on any machine. Docker Compose runs multiple containers
together.

**Real example from our project:**
`docker compose up` starts three things at once: Postgres (database),
the FastAPI backend, and the React frontend dev server. Without Docker,
a new developer cloning the repo would have to install Postgres, configure
it, install Python, create a virtualenv, install Node, and hope their
machine's setup matches yours. With Docker, all of that is encoded in
`docker-compose.yml` and runs with one command.

```yaml
services:
  db:
    image: pgvector/pgvector:pg16   # exact Postgres version, always
  api:
    build: ./backend               # build from our Dockerfile
    depends_on: [db]               # starts only after db is ready
```

**Interview questions:**

Q: What problem does Docker solve?
A: "It works on my machine." Docker packages your app with its exact
dependencies, runtime, and configuration into a container image that runs
identically on your laptop, a teammate's machine, and a production server.
It eliminates environment differences as a source of bugs.

Q: What is the difference between Docker and Docker Compose?
A: Docker manages individual containers. Docker Compose orchestrates
multiple containers together — defining how they relate, what environment
variables they share, and what order they start in. In our project, Docker
runs each service (backend, frontend, Postgres) and Docker Compose wires
them together so they can find each other over a shared network.

---

## 7. React Flow

**What it is in one line:**
A React library specifically for building interactive node-and-edge graphs
— click, drag, zoom, connect, expand — all built in.

**Real example from our project:**

```jsx
import ReactFlow from '@xyflow/react';

function AtlasGraph({ nodes, edges }) {
  return (
    <ReactFlow
      nodes={nodes}          // [{ id, data: { label }, position }]
      edges={edges}          // [{ id, source, target }]
      onNodeClick={handleNodeClick}
    />
  );
}
```

React Flow handles all the rendering, zoom, pan, and drag behaviour.
We pass it nodes (the concept boxes) and edges (the connecting lines)
as JSON arrays, and it draws the graph. Our job is just to produce the
right JSON from the API response and handle the click events.

**Interview questions:**

Q: Why use React Flow instead of building the graph yourself with SVG?
A: Building an interactive, draggable, zoomable graph from scratch with
SVG and mouse events is weeks of work — handling edge routing, zoom
transforms, selection states, and performance at scale. React Flow solves
all of that, is MIT licensed, and has a clean API. The engineering effort
is better spent on the unique parts of the product — the LLM integration
and the map-generation logic.

---

## 8. Zustand (state management)

**What it is in one line:**
A minimal React state management library — like Redux but without the
ceremony.

**Real example from our project:**

```javascript
// store/atlasStore.js
const useAtlasStore = create((set) => ({
  currentMap: null,
  selectedNode: null,
  depth: 'standard',
  setSelectedNode: (node) => set({ selectedNode: node }),
  setDepth: (d) => set({ depth: d }),
}));

// In any component, anywhere in the tree:
const { selectedNode, setDepth } = useAtlasStore();
```

Without Zustand, you'd pass `selectedNode` and `setDepth` as props
through every component between the graph and the side panel — called
"prop drilling." Zustand gives any component direct access to shared
state without wiring props manually.

**Interview questions:**

Q: What is state management and why do you need a library for it?
A: State management is how a React app shares data between components
that aren't directly connected in the component tree. When the user
clicks a node in the graph, the side panel needs to know which node
was clicked — but they're siblings, not parent/child. Zustand provides
a global store that any component can read from or write to, without
passing props down through intermediate layers.

---

## 9. Ollama + Local LLMs

**What they are in one line:**
Ollama is a tool that runs open-source AI language models on your own
laptop, with no internet connection or API costs after the initial download.

**Real example from our project:**

```python
# app/llm.py
response = requests.post("http://localhost:11434/api/generate", json={
    "model": "llama3.1:8b",
    "prompt": build_prompt(topic, depth),
    "stream": False
})
```

Ollama runs locally on port 11434. Our backend sends it a prompt and
gets a text response back — exactly like calling an API, but entirely
on your machine.

**Why local models need retry logic:**
Small models (8B parameters, running on a laptop CPU without a GPU)
occasionally misformat their JSON response — they might add a sentence
before the JSON, or forget to close a bracket. A hosted model like
GPT-4 is more reliable because it's larger and fine-tuned for
instruction-following. For local models, we must parse the response,
catch failures, and retry with a stricter prompt — this is a real
engineering problem in production local-AI systems.

**Interview questions:**

Q: What is a language model parameter count and why does it matter?
A: Parameters are the numbers inside a neural network that were adjusted
during training to make it produce useful outputs — more parameters
generally means more capability but also more memory and compute to run.
A 7-8B parameter model fits in ~8GB RAM and runs on a consumer laptop
CPU, slowly. A 70B model needs a GPU or a powerful server. For Idea
Atlas, 8B is the practical local ceiling; for production we use Groq's
free hosted inference where the hardware constraint disappears.

Q: Why not just use OpenAI's API instead of Ollama?
A: Cost and dependency. OpenAI charges per token — for a portfolio project
with unpredictable usage, costs can add up unexpectedly. More importantly
for an open-source project, requiring users to have an OpenAI account and
pay for API access creates a barrier to running it locally. Ollama runs
the model for free on the user's own hardware, which matches the open-
source, no-cost-to-run goal of this project.

---

## 10. Embeddings and semantic similarity (v2 concept, understand now)

**What they are in one line:**
Embeddings turn a piece of text into a list of numbers where similar
meanings end up as similar lists of numbers — so you can compare ideas
mathematically.

**Real example:**
"Attention mechanism" and "self-attention in transformers" produce
vectors that are very close together. "Attention mechanism" and
"GST filing deadline" produce vectors far apart. Cosine similarity
gives you a number between -1 and 1 measuring how close two vectors
are — close to 1 means similar meaning, close to 0 means unrelated.

**Where this appears in Idea Atlas:**
In v2, when you've generated five different maps over a week, we could
use embeddings to show "maps related to this one" — by comparing the
embedding of your current map's topic against all previous maps' topic
embeddings. That's why pgvector is in the stack even for v1.

**Interview questions:**

Q: What is cosine similarity and when would you use it?
A: Cosine similarity measures how similar two vectors are by the angle
between them — 1.0 means identical direction (very similar), 0 means
perpendicular (unrelated), -1 means opposite. In NLP, it's used to
compare text embeddings: to find similar documents, recommend related
content, or score semantic relevance without exact keyword matching.

Q: What is the difference between keyword search and semantic search?
A: Keyword search finds documents containing the exact words you searched
for. Semantic search finds documents with similar *meaning* even if they
use different words — "car" and "automobile" would match semantically but
not in keyword search. Semantic search uses embeddings and cosine
similarity to measure meaning distance rather than string matching.

---

## 11. Alembic migrations in production (Railway-specific)

**The real-world problem:**
Your production database already has data. You add a new column to a
table in your code. If you deploy the new code without updating the
database schema, the app crashes the moment it tries to read or write
that column — but you can't just wipe the database because it has real
data.

**How we solve it:**
The Railway pre-deploy command runs `alembic upgrade head` before the new
backend version starts taking traffic. Alembic checks which migrations
have already run (tracked in its own `alembic_version` table), and runs
only the new ones. The schema is updated before the new code goes live —
zero-downtime schema changes.

**Interview questions:**

Q: How do you handle database schema changes without downtime?
A: Use migrations — versioned scripts that apply schema changes
incrementally. In our stack, Alembic generates migration files
automatically when SQLAlchemy models change. In production (Railway),
a pre-deploy step runs `alembic upgrade head` before the new backend
starts, so the schema is always updated before the code that depends on
it goes live.

---

## 12. CORS

**What it is in one line:**
A browser security rule that blocks a frontend on one domain from calling
a backend on a different domain — unless the backend explicitly allows it.

**Real example from our project:**
Locally, the React frontend runs on `http://localhost:5173` and the
FastAPI backend runs on `http://localhost:8000`. These are different
"origins" (different ports count). Without CORS configuration, the
browser blocks every API call the frontend makes.

```python
# In FastAPI main.py
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # local dev
    allow_methods=["*"],
    allow_headers=["*"],
)
```

In production, `allow_origins` changes to the Railway frontend URL,
read from the `CORS_ORIGINS` environment variable.

**Interview questions:**

Q: What is CORS and why does it exist?
A: CORS (Cross-Origin Resource Sharing) is a browser security mechanism
that prevents a malicious website from making API calls to another domain
using your logged-in session. Without it, if you were logged into your
bank and visited an evil site, that site could silently call your bank's
API as you. Backends explicitly allow trusted origins in their CORS
headers — the browser enforces the rest.
