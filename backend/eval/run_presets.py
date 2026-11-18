"""Check, without any LLM call, that the stored queries answer on the real ontology.

Runs the 26 ready-made questions of backend/presets.json and the competency questions of
backend/eval/competency.json on the pyoxigraph store (the same one the API loads), and reports
rows, latency and failures. Loading the 490 MB ontology takes under a minute.

    uv run python -m backend.eval.run_presets
"""

import json
import sys
import time
from pathlib import Path

from backend.services.ontology_service import OntologyService

HERE = Path(__file__).resolve().parent
MAX_ROWS = 1000  # same cap as the SPARQL editor


def _first_number(rows: list[dict]) -> float | None:
    """Value of the single aggregate (COUNT) of a one-row result."""
    if len(rows) != 1:
        return None
    try:
        return float(next(iter(rows[0].values())))
    except (TypeError, ValueError):
        return None


def check(item: dict, expected: bool) -> tuple[bool, str, int, float]:
    t0 = time.time()
    try:
        rows = OntologyService.execute_sparql(item["sparql"], max_rows=MAX_ROWS)
    except Exception as e:  # reported, not raised: one bad query must not stop the run
        return False, f"error: {e}", 0, time.time() - t0
    dt = time.time() - t0
    if not expected:  # a preset only has to answer
        return bool(rows), "no rows" if not rows else "", len(rows), dt
    if "min_rows" in item and len(rows) < item["min_rows"]:
        return False, f"{len(rows)} rows < {item['min_rows']}", len(rows), dt
    value = _first_number(rows)
    if "min_value" in item and not (value is not None and value >= item["min_value"]):
        return False, f"value {value} < {item['min_value']}", len(rows), dt
    if "max_value" in item and not (value is not None and value <= item["max_value"]):
        return False, f"value {value} > {item['max_value']}", len(rows), dt
    return True, "", len(rows), dt


def main() -> int:
    t0 = time.time()
    OntologyService.load()
    print(f"store loaded in {time.time() - t0:.0f}s\n")
    presets = json.loads((HERE.parent / "presets.json").read_text(encoding="utf-8"))
    competency = json.loads((HERE / "competency.json").read_text(encoding="utf-8"))
    failed = 0
    for title, items, expected in (("presets", presets, False), ("competency", competency, True)):
        print(f"== {title}")
        for it in items:
            ok, why, n, dt = check(it, expected)
            failed += not ok
            print(f"{'OK  ' if ok else 'FAIL'} {dt:6.2f}s {n:5d} rows  {it['question'][:70]} {why}")
    print(f"\n{failed} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
