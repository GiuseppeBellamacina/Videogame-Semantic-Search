# Ontology Tools

Python scripts for custom CONSTRUCT reasoning and validation of the videogame ontology.

Both are normally run for you by `ontology/build_ontology.py` (the single fetch + reasoning pipeline, see the root README); use them directly only to inspect or re-run one step.

## Setup

Uses a local `.venv` managed by `uv`. Does NOT touch the global environment or the backend dependencies.

```bash
cd ontology/scripts
uv sync
```

## Scripts

- `construct_reasoner.py` — Custom SPARQL CONSTRUCT rules that complement owlrl for inferences outside OWL 2 RL (sequel/prequel inverse completion, indie classification, co-occurrence relations).
- `validate_tbox.py` — Validates the TBox: checks disjointness violations, unsatisfiable classes, missing domain/range, dangling references.

## Usage

```bash
# Validate the schema
uv run python validate_tbox.py ../videogames.owl

# Run custom CONSTRUCT reasoning on a populated ontology
uv run python construct_reasoner.py ../videogames_full.owl --output ../videogames_inferred.owl
```
