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
# Produced by ontology/build_ontology.py (the .ttl copy is the readable version)
ONTOLOGY_FILE = ONTOLOGY_DIR / "videogames_full.owl"

# LLM: "<provider>:<model>", e.g. openai:gpt-4.1-mini or anthropic:haiku5.5
LLM_MODEL = os.getenv("LLM_MODEL", "openai:gpt-4.1-mini")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

# Ontology namespace
ONTOLOGY_NS = "http://www.videogame-ontology.org/ontology#"

# Agent settings
MAX_SPARQL_RETRIES = 3

# Local SQLite cache (images + query results)
CACHE_DB_PATH = Path(os.getenv("CACHE_DB_PATH", BASE_DIR / "backend" / "cache.db"))

# Cache TTL in seconds
CACHE_TTL_QUERY = 60 * 60 * 24 * 14  # 14 days
CACHE_TTL_IMAGE = 60 * 60 * 24 * 30 * 6  # 6 months

# CORS
CORS_ORIGINS = [
    o.strip()
    for o in os.getenv(
        "ALLOWED_ORIGINS",
        "http://localhost:5173,http://localhost:3000",
    ).split(",")
    if o.strip()
]
