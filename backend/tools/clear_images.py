"""
Clear the local image store.

    uv run python -m backend.tools.clear_images            # files + stored URLs + misses
    uv run python -m backend.tools.clear_images --misses   # only the "no image found" entries
"""

import argparse
import json
import shutil

from backend.config import IMAGE_DIR
from backend.services import cache
from backend.services.image_store import KEY_PREFIX


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--misses", action="store_true", help="remove only the entries without an image, to retry them")
    args = ap.parse_args()

    rows = cache.items(KEY_PREFIX)
    if args.misses:
        keys = [k for k, v in rows if _is_miss(v)]
        cache.delete(keys)
        print(f"Removed {len(keys)} 'not found' entries (kept {len(rows) - len(keys)}).")
        return

    cache.delete([k for k, _ in rows])
    files = len(list(IMAGE_DIR.glob("*"))) if IMAGE_DIR.exists() else 0
    shutil.rmtree(IMAGE_DIR, ignore_errors=True)
    print(f"Removed {len(rows)} entries and {files} image files from {IMAGE_DIR}.")


def _is_miss(value: str) -> bool:
    try:
        return bool(json.loads(value).get("miss"))
    except (ValueError, AttributeError):
        return False


if __name__ == "__main__":
    main()
