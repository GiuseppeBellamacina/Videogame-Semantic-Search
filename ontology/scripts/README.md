# Ontology Tools

Python scripts for TBox enrichment, custom CONSTRUCT reasoning, and validation of the videogame ontology.

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
uv run python construct_reasoner.py ../videogames_pruned.owl --output ../videogames_inferred.owl
```
