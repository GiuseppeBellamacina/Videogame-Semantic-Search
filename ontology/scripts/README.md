# Ontology Tools

Python scripts for custom CONSTRUCT reasoning and validation of the videogame ontology.

Both are normally run for you by `ontology/build_ontology.py` (the single fetch + reasoning pipeline, see the root README); use them directly only to inspect or re-run one step.

## Setup

Usa l'ambiente del progetto (`uv sync` dalla root); nessun ambiente separato.

## Scripts

- `construct_reasoner.py` — Runs the SPARQL CONSTRUCT rules stored one per file in `../rules/*.rq`; they complement owlrl for inferences outside OWL 2 RL (sequel/prequel inverse completion, indie classification, co-occurrence relations).
- `validate_tbox.py` — Validates the TBox: checks disjointness violations, unsatisfiable classes, missing domain/range, dangling references.

## Usage

```bash
# Validate the schema
uv run python ontology/scripts/validate_tbox.py ontology/videogames.owl

# Run custom CONSTRUCT reasoning on a populated ontology
uv run python ontology/scripts/construct_reasoner.py ontology/output/videogames_full.owl --output ontology/output/videogames_inferred.owl
```
