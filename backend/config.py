"""
Configuration for the Videogame Semantic Search backend.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

# Load .env from project root
load_dotenv(Path(__file__).parent.parent / ".env")

# Paths
BASE_DIR = Path(__file__).parent.parent
ONTOLOGY_DIR = BASE_DIR / "ontology"
# Produced by ontology/build_ontology.py into ontology/output/ (the .ttl copy is the readable version)
ONTOLOGY_FILE = ONTOLOGY_DIR / "output" / "videogames_full.owl"

# LLM: "<provider>:<model>", e.g. openai:gpt-4.1-mini or anthropic:haiku5.5
LLM_MODEL = os.getenv("LLM_MODEL") or "openai:gpt-4.1-mini"  # empty counts as unset
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

# Ontology namespace
ONTOLOGY_NS = "http://www.videogame-ontology.org/ontology#"

# Agent settings
MAX_SPARQL_RETRIES = 3
# Limits on a query written by the LLM (the user editor has its own): the generated SPARQL
# cannot write (the validator only accepts queries) but it can be huge or slow
AGENT_MAX_ROWS = 1000
AGENT_QUERY_TIMEOUT = 30  # seconds

# Local SQLite cache (images + query results)
CACHE_DB_PATH = Path(os.getenv("CACHE_DB_PATH", BASE_DIR / "backend" / "cache.db"))

# Cache TTL in seconds
CACHE_TTL_QUERY = 60 * 60 * 24 * 14  # 14 days
CACHE_TTL_IMAGE = 60 * 60 * 24 * 30 * 6  # 6 months
IMAGE_MISS_TTL = 60 * 60 * 24 * 7  # "no image found" is remembered for a week
IMAGE_DIR = Path(os.getenv("IMAGE_DIR", BASE_DIR / "backend" / "cache" / "images"))

# CORS
CORS_ORIGINS = [
    o.strip()
    for o in os.getenv(
        "ALLOWED_ORIGINS",
        "http://localhost:5173,http://localhost:3000",
    ).split(",")
    if o.strip()
]
