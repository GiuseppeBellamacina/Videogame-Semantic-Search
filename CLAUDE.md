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

Ontology pipeline (offline, run once; several hours for the full fetch):

```bash
uv run python ontology/build_ontology.py                      # fetch -> reason -> validate -> write .owl + .ttl
uv run python ontology/build_ontology.py --years 2024         # quick subset
uv run python ontology/build_ontology.py --from-stage reason  # reuse the checkpointed fetch
```

Fetch is checkpointed per query x month in `ontology/.cache/` (restart resumes; Wikidata 429s are waited out). Stages: `populate_wikidata.py` (fetch + V2 subclass typing + dedup) -> `enrich_owl.py` (V2 axioms, strip DL-only axioms, `_materialise`) with owlrl in between -> `scripts/construct_reasoner.py` (CONSTRUCT rules, one `.rq` per file in `ontology/rules/`) -> `validate_tbox`. The schema is modular: `ontology/videogames.owl` only `owl:imports` the modules in `ontology/schema/` (resolved through `catalog-v001.xml` by `ontology/scripts/schema_loader.py`). Output: `ontology/output/videogames_full.owl` (loaded by the backend) and `.ttl` (readable copy). All pipeline modules live in `ontology/scripts/` and use the root uv environment.

Config comes from the root `.env` (see `.env.example`): `LLM_MODEL` as `provider:model` (`openai:gpt-4.1-mini`, `anthropic:haiku5.5`), `OPENAI_API_KEY` / `ANTHROPIC_API_KEY`, `ALLOWED_ORIGINS`, `VITE_API_URL`.

## Architecture

- `backend/config.py` points at `ontology/output/videogames_full.owl` (no pruned/demo variants).
- `backend/agents/sparql_agent.py`: `SPARQLAgent.run()` is a generate -> validate (`utils/sparql_validator`) -> execute loop with up to `MAX_SPARQL_RETRIES`, retrying on errors *and* empty results. The LLM picks CONSTRUCT for relationship questions (rows become subject/predicate/object, `graph_builder.build_graph` links them) and SELECT for rankings, counts and value lists; the query builder offers both outputs. LLM calls go through `agents/llm.py` (`parse_model`, `LLM.generate`) so OpenAI and Anthropic are interchangeable. The prompt in `agents/prompts.py` embeds `OntologyService.get_ontology_schema()`; keep both in sync with the TBox.
- `backend/services/ontology_service.py`: `OntologyService` is a class-level singleton wrapping a pyoxigraph `Store` (loaded in the FastAPI lifespan). Node types are derived by mapping any rdf:type through the `rdfs:subClassOf` closure to a base type (`BASE_TYPES`); also labels, node details, stats.
- `backend/services/graph_builder.py`: converts SPARQL results / a node's neighborhood into `{nodes, links}` for the frontend; `services/cache.py` is a SQLite key/value cache with TTL (`backend/cache.db`) used by `services/image_store.py` and the query cache in `routers/query.py` (keys are namespaced by the ontology file mtime). `image_store.resolve(name, type)` returns an entity picture: local file in `backend/cache/images/` -> stored URL (downloaded) -> Wikipedia search by type (companies, platforms and series fall back to the Wikidata logo, P154); a "not found" is stored (short TTL) only when the whole search ran without errors; 429/5xx/network failures raise `Transient` and are never stored. Requests to Wikimedia go through two async pools (API calls: 3 workers, one start every 0.25 s; picture downloads: 5 workers, every 0.12 s; all the title variants of an entity are asked in one API call) and a 429 pauses both for 30 s (doubling up to 5 min); `POST /api/images` then answers `retry` for the keys it could not settle and `lib/imageQueue.ts` asks again later instead of marking them as having no picture. Endpoints: `POST /api/images` (batch), `GET /api/image-file/{file}`, `GET /api/image-search`. `POST /api/images/retry` picks the next Wikipedia candidate for an entity (the "Riprova copertina" button). Clear with `uv run python -m backend.tools.clear_images [--misses]`.
- `services/search_index.py` + `services/query_builder.py` + `routers/search.py`: autosuggest (`/api/suggest`, label index built at load) and the assisted query builder (`/api/builder/*`, whitelisted fields -> generated SPARQL, no LLM).
- `backend/presets.json` (26 ready-made questions with a stored SPARQL: `routers/query.py` answers them without the LLM, matching typos of up to 2 edits; the frontend `SUGGESTIONS` are presets), `backend/routers/query.py` (`POST /api/query`, and `POST /api/query/stream` which streams agent progress as server-sent events) and `graph.py` (node details, cross-links, image search, stats); health at `/api/health`.
- Frontend (`frontend/src/`): dark editorial theme, tokens in `tailwind.config.ts` and `lib/theme.ts` (the single source of node colours/labels). `App.tsx` + `hooks/useQuery.ts` (reads the SSE stream), `lib/imageQueue.ts` (batched, rate-limited image requests) + `hooks/useImage.ts` + `components/Thumb.tsx`, `components/SearchBar.tsx` (live status), `components/QueryBuilder.tsx` (sentence of chips, live count via `/api/builder/count`), `components/KnowledgeGraph.tsx` (react-force-graph-2d: images on nodes, hover focus, legend, find, freeze; click a relation to see what two nodes share via `GET /api/relation`, click a second node to label the relations between the pair, shift+click multi-select with isolate / hide / delete, a "Disponi" panel that pins chosen node types on a grid or in one band per type, a toggle for the dashed derived relations, smooth fit capped at 1.8x), `components/Dropdown.tsx` (themed listbox), `components/SparqlEditor.tsx` (free read-only SPARQL via `POST /api/sparql`: standard prefixes added, 1000-row and 30 s caps; "Modifica" in `SparqlViewer` loads any shown query into it).
- Ontology namespace: `http://www.videogame-ontology.org/ontology#`. Core classes: VideoGame, Developer, Publisher, Genre, Platform, Character, Franchise, Award, GameEngine. See `docs/ontology.md` and README for properties.
- Local only: no deploy configs (Render/Vercel removed).

`reference/` holds course material (lecture exercises) and `docs/relazione` the LaTeX report/presentation; neither is part of the app.
