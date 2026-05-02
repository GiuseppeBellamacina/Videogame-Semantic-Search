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
ONTOLOGY_FILE = ONTOLOGY_DIR / "videogames_pruned_2020.owl"

# Fallback chain
if not ONTOLOGY_FILE.exists():
    ONTOLOGY_FILE = ONTOLOGY_DIR / "videogames_wikidata.owl"
if not ONTOLOGY_FILE.exists():
    ONTOLOGY_FILE = ONTOLOGY_DIR / "videogames.owl"

# OpenAI
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")

# Ontology namespace
ONTOLOGY_NS = "http://www.videogame-ontology.org/ontology#"

# Agent settings
MAX_SPARQL_RETRIES = 3

# Upstash Redis (optional — fallback to in-memory if not set)
UPSTASH_REDIS_REST_URL = os.getenv("UPSTASH_REDIS_REST_URL", "")
UPSTASH_REDIS_REST_TOKEN = os.getenv("UPSTASH_REDIS_REST_TOKEN", "")

# Cache TTL in seconds (7 days)
CACHE_TTL = 60 * 60 * 24 * 7
