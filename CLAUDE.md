# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

Semantic Web university project (docs/README in Italian): an OWL ontology of video games (from Wikidata, 2010–2026) queried through natural language. A FastAPI backend turns the question into SPARQL with an OpenAI LLM, runs it on an in-memory pyoxigraph store, and a React frontend shows results as an interactive force graph. There is no test suite.

## Commands

Python (managed by `uv`, Python 3.12+; run from repo root):

```bash
uv sync
uv run uvicorn backend.main:app --reload --port 8000   # backend (API docs at /docs)
./start.ps1                                            # backend + frontend in two windows
./format.ps1                                           # isort + black + ruff --fix + frontend lint/tsc
```

Frontend (Bun, from `frontend/`): `bun install`, `bun run dev` (Vite on :5173, proxies `/api` to :8000), `bun run build`, `bun run lint` (= `tsc --noEmit`).

Ontology pipeline (offline, slow — `populate_wikidata.py` takes ~5h and its output `videogames_wikidata.owl` is not committed):

```bash
uv run python ontology/populate_wikidata.py   # Wikidata -> OWL (per year x month queries) + OWL-RL closure
uv run python ontology/prune_owl.py           # drop reflexive sameAs, descriptions, websites -> videogames_pruned.owl
uv run python ontology/prune_years.py         # year-limited subset -> videogames_pruned_2020.owl (demo)
uv run python ontology/enrich_owl.py          # add advanced TBox axioms (defined classes, property chains, disjointness)
```

`ontology/scripts/` is a separate uv project (own `pyproject.toml`/`.venv`) with TBox validation and custom CONSTRUCT reasoning; see its README.

Config comes from the root `.env` (see `.env.example`): `OPENAI_API_KEY` (required), `OPENAI_MODEL`, `ALLOWED_ORIGINS`, optional Upstash Redis vars, `VITE_API_URL` for the deployed frontend. `LOCAL_BUILD=true` makes the backend load the full `videogames_pruned.owl` instead of the 2020+ demo file.

## Architecture

- `backend/config.py` picks the ontology file with a fallback chain (pruned_2020 → wikidata → videogames.owl). Demo file is used in deployment to fit Render's 512 MB RAM.
- `backend/agents/sparql_agent.py`: `SPARQLAgent.run()` is a generate → validate (`utils/sparql_validator`) → execute loop with up to `MAX_SPARQL_RETRIES`, retrying on errors *and* empty results, feeding previous queries/errors back to the LLM. The prompt in `agents/prompts.py` embeds the schema from `OntologyService.get_ontology_schema()`, so ontology changes must stay consistent with it.
- `backend/services/ontology_service.py`: `OntologyService` is a class-level singleton wrapping a pyoxigraph `Store` (loaded in the FastAPI lifespan). Also derives labels/types for nodes (in-memory caches) and node details/stats.
- `backend/services/graph_builder.py`: converts SPARQL results / a node's neighborhood into `{nodes, links}` for the frontend; `image_cache.py` fetches cover art from Wikipedia and caches in Upstash Redis (falls back to in-memory when unset).
- `backend/routers/query.py` (`POST /api/query`) and `graph.py` (node details, cross-links, image search, stats); health at `/api/health`.
- Frontend (`frontend/src/`): `App.tsx` + `hooks/useQuery.ts`, API wrappers in `lib/`, types in `types/` (`GraphNode`/`GraphLink` must match the backend graph payload), `components/KnowledgeGraph.tsx` (react-force-graph-2d with custom canvas drawing, force/collision tuning, type filtering, context menu for expand/remove).
- Ontology namespace: `http://www.videogame-ontology.org/ontology#`. Core classes: VideoGame, Developer, Publisher, Genre, Platform, Character, Franchise, Award, GameEngine. See `docs/ontology.md` and README for properties.
- Deploy: backend on Render (`render.yaml`, `uv sync --frozen`), frontend on Vercel (`frontend/vercel.json`).

`reference/` holds course material (lecture exercises) and `docs/relazione` the LaTeX report/presentation; neither is part of the app.
