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
ONTOLOGY_FILE = ONTOLOGY_DIR / "videogames_wikidata.owl"

# If populated file doesn't exist, fall back to base ontology
if not ONTOLOGY_FILE.exists():
    ONTOLOGY_FILE = ONTOLOGY_DIR / "videogames.owl"

# OpenAI
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")

# Ontology namespace
ONTOLOGY_NS = "http://www.videogame-ontology.org/ontology#"

# Agent settings
MAX_SPARQL_RETRIES = 3
