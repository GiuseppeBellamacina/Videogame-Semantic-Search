"""
Populate the videogame ontology with data from Wikidata SPARQL endpoint.
Fetches video games released from 2010 onwards with their developers, publishers,
genres, platforms, and characters.
"""

import logging
import re
import time
from collections import defaultdict
from pathlib import Path

from rdflib import RDF, XSD, Graph, Literal, Namespace, URIRef
from SPARQLWrapper import JSON, SPARQLWrapper

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Namespaces
VG = Namespace("http://www.videogame-ontology.org/ontology#")
WD = Namespace("http://www.wikidata.org/entity/")

WIKIDATA_ENDPOINT = "https://query.wikidata.org/sparql"

# We split into multiple queries to avoid Wikidata timeout (60s limit)
# Query 1: Core game data (name, release date, developer, publisher)
GAMES_CORE_QUERY = """
SELECT DISTINCT ?game ?gameLabel ?releaseDate ?devLabel ?pubLabel ?dev ?pub WHERE {{
  ?game wdt:P31 wd:Q7889 .          # instance of video game
  ?game wdt:P577 ?releaseDate .      # publication date
  FILTER(YEAR(?releaseDate) = {year})
  
  OPTIONAL {{ ?game wdt:P178 ?dev . ?dev rdfs:label ?devLabel . FILTER(LANG(?devLabel) = "en") }}
  OPTIONAL {{ ?game wdt:P123 ?pub . ?pub rdfs:label ?pubLabel . FILTER(LANG(?pubLabel) = "en") }}
  
  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
}}
LIMIT 5000
"""

# Query 2: Genres for the games
GAMES_GENRE_QUERY = """
SELECT DISTINCT ?game ?gameLabel ?genreLabel ?genre WHERE {
  ?game wdt:P31 wd:Q7889 .
  ?game wdt:P577 ?releaseDate .
  FILTER(YEAR(?releaseDate) >= 2010 && YEAR(?releaseDate) <= 2026)
  ?game wdt:P136 ?genre .
  ?genre rdfs:label ?genreLabel . FILTER(LANG(?genreLabel) = "en")
  SERVICE wikibase:label { bd:serviceParam wikibase:language "en". }
}
LIMIT 30000
"""

# Query 3: Platforms for the games
GAMES_PLATFORM_QUERY = """
SELECT DISTINCT ?game ?gameLabel ?platformLabel ?platform WHERE {
  ?game wdt:P31 wd:Q7889 .
  ?game wdt:P577 ?releaseDate .
  FILTER(YEAR(?releaseDate) >= 2010 && YEAR(?releaseDate) <= 2026)
  ?game wdt:P400 ?platform .
  ?platform rdfs:label ?platformLabel . FILTER(LANG(?platformLabel) = "en")
  SERVICE wikibase:label { bd:serviceParam wikibase:language "en". }
}
LIMIT 40000
"""

# Query 4: Characters
GAMES_CHARACTER_QUERY = """
SELECT DISTINCT ?game ?gameLabel ?charLabel ?char WHERE {
  ?game wdt:P31 wd:Q7889 .
  ?game wdt:P577 ?releaseDate .
  FILTER(YEAR(?releaseDate) >= 2010 && YEAR(?releaseDate) <= 2026)
  ?game wdt:P674 ?char .
  ?char rdfs:label ?charLabel . FILTER(LANG(?charLabel) = "en")
  SERVICE wikibase:label { bd:serviceParam wikibase:language "en". }
}
LIMIT 20000
"""

# Query 5: Franchise / series
GAMES_FRANCHISE_QUERY = """
SELECT DISTINCT ?game ?gameLabel ?seriesLabel ?series WHERE {
  ?game wdt:P31 wd:Q7889 .
  ?game wdt:P577 ?releaseDate .
  FILTER(YEAR(?releaseDate) >= 2010 && YEAR(?releaseDate) <= 2026)
  ?game wdt:P179 ?series .
  ?series rdfs:label ?seriesLabel . FILTER(LANG(?seriesLabel) = "en")
  SERVICE wikibase:label { bd:serviceParam wikibase:language "en". }
}
LIMIT 15000
"""

# Query 6: Game mode
GAMES_MODE_QUERY = """
SELECT DISTINCT ?game ?gameLabel ?modeLabel WHERE {
  ?game wdt:P31 wd:Q7889 .
  ?game wdt:P577 ?releaseDate .
  FILTER(YEAR(?releaseDate) >= 2010 && YEAR(?releaseDate) <= 2026)
  ?game wdt:P404 ?mode .
  ?mode rdfs:label ?modeLabel . FILTER(LANG(?modeLabel) = "en")
  SERVICE wikibase:label { bd:serviceParam wikibase:language "en". }
}
LIMIT 30000
"""

# Query 7: Review scores (Metacritic)
GAMES_SCORE_QUERY = """
SELECT DISTINCT ?game ?gameLabel ?score WHERE {
  ?game wdt:P31 wd:Q7889 .
  ?game wdt:P577 ?releaseDate .
  FILTER(YEAR(?releaseDate) >= 2010 && YEAR(?releaseDate) <= 2026)
  ?game p:P444 ?reviewStatement .
  ?reviewStatement ps:P444 ?score .
  ?reviewStatement pq:P447 wd:Q150248 .  # Metacritic
  SERVICE wikibase:label { bd:serviceParam wikibase:language "en". }
}
LIMIT 10000
"""

# Query 9: Game engines (P408)
GAMES_ENGINE_QUERY = """
SELECT DISTINCT ?game ?gameLabel ?engine ?engineLabel WHERE {
  ?game wdt:P31 wd:Q7889 .
  ?game wdt:P577 ?releaseDate .
  FILTER(YEAR(?releaseDate) >= 2010 && YEAR(?releaseDate) <= 2026)
  ?game wdt:P408 ?engine .
  ?engine rdfs:label ?engineLabel . FILTER(LANG(?engineLabel) = "en")
  SERVICE wikibase:label { bd:serviceParam wikibase:language "en". }
}
LIMIT 15000
"""

# Query 10: Country of origin (P495)
GAMES_COUNTRY_QUERY = """
SELECT DISTINCT ?game ?gameLabel ?countryLabel WHERE {
  ?game wdt:P31 wd:Q7889 .
  ?game wdt:P577 ?releaseDate .
  FILTER(YEAR(?releaseDate) >= 2010 && YEAR(?releaseDate) <= 2026)
  ?game wdt:P495 ?country .
  ?country rdfs:label ?countryLabel . FILTER(LANG(?countryLabel) = "en")
  SERVICE wikibase:label { bd:serviceParam wikibase:language "en". }
}
LIMIT 20000
"""

# Query 11: Official website (P856)
GAMES_WEBSITE_QUERY = """
SELECT DISTINCT ?game ?gameLabel ?website WHERE {
  ?game wdt:P31 wd:Q7889 .
  ?game wdt:P577 ?releaseDate .
  FILTER(YEAR(?releaseDate) >= 2010 && YEAR(?releaseDate) <= 2026)
  ?game wdt:P856 ?website .
  SERVICE wikibase:label { bd:serviceParam wikibase:language "en". }
}
LIMIT 15000
"""

# Query 12: Awards (P166)
GAMES_AWARD_QUERY = """
SELECT DISTINCT ?game ?gameLabel ?award ?awardLabel WHERE {
  ?game wdt:P31 wd:Q7889 .
  ?game wdt:P577 ?releaseDate .
  FILTER(YEAR(?releaseDate) >= 2010 && YEAR(?releaseDate) <= 2026)
  ?game wdt:P166 ?award .
  ?award rdfs:label ?awardLabel . FILTER(LANG(?awardLabel) = "en")
  SERVICE wikibase:label { bd:serviceParam wikibase:language "en". }
}
LIMIT 20000
"""

# Query 13: Description (schema:description)
GAMES_DESC_QUERY = """
SELECT DISTINCT ?game ?gameLabel ?desc WHERE {
  ?game wdt:P31 wd:Q7889 .
  ?game wdt:P577 ?releaseDate .
  FILTER(YEAR(?releaseDate) >= 2010 && YEAR(?releaseDate) <= 2026)
  ?game schema:description ?desc .
  FILTER(LANG(?desc) = "en")
  SERVICE wikibase:label { bd:serviceParam wikibase:language "en". }
}
LIMIT 20000
"""


def make_uri(base: str, label: str) -> URIRef:
    """Create a safe URI from a label."""
    safe = label.strip().replace(" ", "_").replace("'", "").replace('"', "")
    safe = "".join(c for c in safe if c.isalnum() or c in "_-.")
    return URIRef(f"{base}{safe}")


def run_query(sparql: SPARQLWrapper, query: str, description: str) -> list:
    """Execute a SPARQL query with retry logic."""
    sparql.setQuery(query)
    sparql.setReturnFormat(JSON)

    for attempt in range(3):
        try:
            logger.info(f"Executing query: {description} (attempt {attempt + 1})")
            results = sparql.query().convert()
            bindings = results["results"]["bindings"]
            logger.info(f"  -> Got {len(bindings)} results")
            return bindings
        except Exception as e:
            logger.warning(f"  -> Attempt {attempt + 1} failed: {e}")
            if attempt < 2:
                wait = 10 * (attempt + 1)
                logger.info(f"  -> Retrying in {wait}s...")
                time.sleep(wait)
            else:
                logger.error(f"  -> All attempts failed for: {description}")
                return []


QID_PATTERN = re.compile(r"^Q\d+$")


# Name properties used to identify entities by label for deduplication
_NAME_PROPS = [
    "gameName",
    "developerName",
    "publisherName",
    "genreName",
    "platformName",
    "characterName",
    "franchiseName",
    "awardName",
    "engineName",
]


def deduplicate_graph(g: Graph) -> int:
    """
    Merge duplicate entities that share the same normalised name.
    For each group of URIs with the same name (case-insensitive, stripped),
    keep the URI with the most triples (subject + object) and redirect all
    references to the others to the canonical URI.
    Returns the number of duplicates removed.
    """
    name_to_uris: dict[str, list[URIRef]] = defaultdict(list)

    for prop_local in _NAME_PROPS:
        prop = VG[prop_local]
        for subj, _, obj in g.triples((None, prop, None)):
            if isinstance(obj, Literal) and isinstance(subj, URIRef):
                key = str(obj).strip().lower()
                if subj not in name_to_uris[key]:
                    name_to_uris[key].append(subj)

    removed = 0
    for name_key, uris in name_to_uris.items():
        if len(uris) < 2:
            continue

        # Count triples where each URI appears as subject or object
        def triple_count(uri: URIRef) -> int:
            return sum(1 for _ in g.triples((uri, None, None))) + sum(
                1 for _ in g.triples((None, None, uri))
            )

        # Sort: most triples first → that is the canonical URI
        uris_sorted = sorted(uris, key=triple_count, reverse=True)
        canonical = uris_sorted[0]

        for duplicate in uris_sorted[1:]:
            if duplicate == canonical:
                continue

            # Re-point all triples where duplicate is the subject
            for pred, obj in list(g.predicate_objects(duplicate)):
                g.remove((duplicate, pred, obj))
                # Add to canonical only if not already present
                if (canonical, pred, obj) not in g:
                    g.add((canonical, pred, obj))

            # Re-point all triples where duplicate is the object
            for subj, pred in list(g.subject_predicates(duplicate)):
                g.remove((subj, pred, duplicate))
                if (subj, pred, canonical) not in g:
                    g.add((subj, pred, canonical))

            removed += 1
            logger.debug(f"[DEDUP] Merged '{name_key}': {duplicate} → {canonical}")

    return removed


def get_val(binding: dict, key: str) -> str | None:
    """Safely extract a value from a SPARQL binding."""
    if key in binding:
        return binding[key]["value"]
    return None


def is_qid_label(value: str | None) -> bool:
    """Return True if the value is a raw Wikidata QID (no proper label resolved)."""
    return value is not None and bool(QID_PATTERN.match(value))


def populate_from_wikidata():
    """Main population function."""
    sparql = SPARQLWrapper(WIKIDATA_ENDPOINT)
    sparql.addCustomHttpHeader(
        "User-Agent",
        "VideogameSemanticSearch/1.0 (university project; semantic web course)",
    )

    g = Graph()
    g.bind("vg", VG)
    g.parse(str(Path(__file__).parent / "videogames.owl"))

    games_seen = set()
    # game_label -> earliest release date seen (string YYYY-MM-DD)
    game_earliest_date: dict[str, str] = {}
    # game_label -> set of (dev_label, pub_label) pairs already added
    game_devs_seen: dict[str, set] = {}
    game_pubs_seen: dict[str, set] = {}

    # --- Step 1: Core game data (per-year to maximize coverage) ---
    logger.info("=" * 60)
    logger.info("STEP 1: Fetching core game data from Wikidata (year by year)...")

    for year in range(2010, 2027):
        query = GAMES_CORE_QUERY.format(year=year)
        bindings = run_query(sparql, query, f"Core game data ({year})")

        year_count = 0
        for row in bindings:
            game_uri_str = get_val(row, "game")
            game_label = get_val(row, "gameLabel")
            release_date = get_val(row, "releaseDate")

            if not game_label or not game_uri_str:
                continue
            # Skip entries where Wikidata returned a QID instead of a proper label
            if is_qid_label(game_label):
                logger.debug(f"Skipping QID label: {game_label}")
                continue

            game_uri = make_uri(str(VG), game_label)
            game_already_seen = game_label in games_seen
            games_seen.add(game_label)

            g.add((game_uri, RDF.type, VG.VideoGame))
            g.add((game_uri, VG.gameName, Literal(game_label, datatype=XSD.string)))

            if release_date:
                date_str = release_date[:10]  # YYYY-MM-DD
                # Keep only the earliest release date
                if not game_already_seen or date_str < game_earliest_date.get(
                    game_label, date_str
                ):
                    # Remove any existing releaseDate triple and replace with the earlier one
                    g.remove((game_uri, VG.releaseDate, None))
                    g.add(
                        (game_uri, VG.releaseDate, Literal(date_str, datatype=XSD.date))
                    )
                    game_earliest_date[game_label] = date_str

            dev_label = get_val(row, "devLabel")
            if dev_label and not is_qid_label(dev_label):
                if game_label not in game_devs_seen:
                    game_devs_seen[game_label] = set()
                if dev_label not in game_devs_seen[game_label]:
                    game_devs_seen[game_label].add(dev_label)
                    dev_uri = make_uri(str(VG) + "dev/", dev_label)
                    g.add((dev_uri, RDF.type, VG.Developer))
                    g.add(
                        (
                            dev_uri,
                            VG.developerName,
                            Literal(dev_label, datatype=XSD.string),
                        )
                    )
                    g.add((game_uri, VG.developedBy, dev_uri))

            pub_label = get_val(row, "pubLabel")
            if pub_label and not is_qid_label(pub_label):
                if game_label not in game_pubs_seen:
                    game_pubs_seen[game_label] = set()
                if pub_label not in game_pubs_seen[game_label]:
                    game_pubs_seen[game_label].add(pub_label)
                    pub_uri = make_uri(str(VG) + "pub/", pub_label)
                    g.add((pub_uri, RDF.type, VG.Publisher))
                    g.add(
                        (
                            pub_uri,
                            VG.publisherName,
                            Literal(pub_label, datatype=XSD.string),
                        )
                    )
                    g.add((game_uri, VG.publishedBy, pub_uri))

            year_count += 1

        logger.info(f"  {year}: {year_count} games")
        time.sleep(3)  # Be polite to Wikidata

    logger.info(f"Total games loaded: {len(games_seen)}")
    time.sleep(5)

    # --- Step 2: Genres ---
    logger.info("=" * 60)
    logger.info("STEP 2: Fetching genre data...")
    bindings = run_query(sparql, GAMES_GENRE_QUERY, "Genre data")

    genres_added = 0
    for row in bindings:
        game_label = get_val(row, "gameLabel")
        genre_label = get_val(row, "genreLabel")
        if not game_label or not genre_label:
            continue
        if is_qid_label(game_label) or is_qid_label(genre_label):
            continue
        if game_label not in games_seen:
            continue

        game_uri = make_uri(str(VG), game_label)
        genre_uri = make_uri(str(VG) + "genre/", genre_label)

        g.add((genre_uri, RDF.type, VG.Genre))
        g.add((genre_uri, VG.genreName, Literal(genre_label, datatype=XSD.string)))
        g.add((game_uri, VG.hasGenre, genre_uri))
        genres_added += 1

    logger.info(f"Genre associations added: {genres_added}")
    time.sleep(5)

    # --- Step 3: Platforms ---
    logger.info("=" * 60)
    logger.info("STEP 3: Fetching platform data...")
    bindings = run_query(sparql, GAMES_PLATFORM_QUERY, "Platform data")

    platforms_added = 0
    for row in bindings:
        game_label = get_val(row, "gameLabel")
        platform_label = get_val(row, "platformLabel")
        if not game_label or not platform_label:
            continue
        if is_qid_label(game_label) or is_qid_label(platform_label):
            continue
        if game_label not in games_seen:
            continue

        game_uri = make_uri(str(VG), game_label)
        platform_uri = make_uri(str(VG) + "platform/", platform_label)

        g.add((platform_uri, RDF.type, VG.Platform))
        g.add(
            (
                platform_uri,
                VG.platformName,
                Literal(platform_label, datatype=XSD.string),
            )
        )
        g.add((game_uri, VG.availableOn, platform_uri))
        platforms_added += 1

    logger.info(f"Platform associations added: {platforms_added}")
    time.sleep(5)

    # --- Step 4: Characters ---
    logger.info("=" * 60)
    logger.info("STEP 4: Fetching character data...")
    bindings = run_query(sparql, GAMES_CHARACTER_QUERY, "Character data")

    chars_added = 0
    for row in bindings:
        game_label = get_val(row, "gameLabel")
        char_label = get_val(row, "charLabel")
        if not game_label or not char_label:
            continue
        if is_qid_label(game_label) or is_qid_label(char_label):
            continue
        if game_label not in games_seen:
            continue

        game_uri = make_uri(str(VG), game_label)
        char_uri = make_uri(str(VG) + "char/", char_label)

        g.add((char_uri, RDF.type, VG.Character))
        g.add((char_uri, VG.characterName, Literal(char_label, datatype=XSD.string)))
        g.add((game_uri, VG.hasCharacter, char_uri))
        chars_added += 1

    logger.info(f"Character associations added: {chars_added}")
    time.sleep(5)

    # --- Step 5: Franchise ---
    logger.info("=" * 60)
    logger.info("STEP 5: Fetching franchise/series data...")
    bindings = run_query(sparql, GAMES_FRANCHISE_QUERY, "Franchise data")

    franchises_added = 0
    for row in bindings:
        game_label = get_val(row, "gameLabel")
        series_label = get_val(row, "seriesLabel")
        if not game_label or not series_label:
            continue
        if is_qid_label(game_label) or is_qid_label(series_label):
            continue
        if game_label not in games_seen:
            continue

        game_uri = make_uri(str(VG), game_label)
        series_uri = make_uri(str(VG) + "franchise/", series_label)

        g.add((series_uri, RDF.type, VG.Franchise))
        g.add(
            (
                series_uri,
                VG.franchiseName,
                Literal(series_label, datatype=XSD.string),
            )
        )
        g.add((game_uri, VG.belongsTo, series_uri))
        franchises_added += 1

    logger.info(f"Franchise associations added: {franchises_added}")
    time.sleep(5)

    # --- Step 6: Game modes ---
    logger.info("=" * 60)
    logger.info("STEP 6: Fetching game mode data...")
    bindings = run_query(sparql, GAMES_MODE_QUERY, "Game mode data")

    modes_added = 0
    for row in bindings:
        game_label = get_val(row, "gameLabel")
        mode_label = get_val(row, "modeLabel")
        if not game_label or not mode_label:
            continue
        if is_qid_label(game_label) or is_qid_label(mode_label):
            continue
        if game_label not in games_seen:
            continue

        game_uri = make_uri(str(VG), game_label)
        g.add(
            (
                game_uri,
                VG.hasGameMode,
                Literal(mode_label, datatype=XSD.string),
            )
        )
        modes_added += 1

    logger.info(f"Game mode associations added: {modes_added}")
    time.sleep(5)

    # --- Step 7: Metacritic scores ---
    logger.info("=" * 60)
    logger.info("STEP 7: Fetching Metacritic score data...")
    bindings = run_query(sparql, GAMES_SCORE_QUERY, "Metacritic scores")

    scores_added = 0
    for row in bindings:
        game_label = get_val(row, "gameLabel")
        score = get_val(row, "score")
        if not game_label or not score:
            continue
        if is_qid_label(game_label):
            continue
        if game_label not in games_seen:
            continue

        game_uri = make_uri(str(VG), game_label)
        # Metacritic scores are like "85/100", extract the number
        try:
            score_num = int(score.split("/")[0])
            g.add(
                (
                    game_uri,
                    VG.metacriticScore,
                    Literal(score_num, datatype=XSD.integer),
                )
            )
            scores_added += 1
        except (ValueError, IndexError):
            pass

    logger.info(f"Metacritic scores added: {scores_added}")
    time.sleep(5)

    # --- Step 8: Game engines ---
    logger.info("=" * 60)
    logger.info("STEP 8: Fetching game engine data...")
    bindings = run_query(sparql, GAMES_ENGINE_QUERY, "Game engine data")

    engines_added = 0
    for row in bindings:
        game_label = get_val(row, "gameLabel")
        engine_label = get_val(row, "engineLabel")
        if not game_label or not engine_label:
            continue
        if is_qid_label(game_label) or is_qid_label(engine_label):
            continue
        if game_label not in games_seen:
            continue

        game_uri = make_uri(str(VG), game_label)
        engine_uri = make_uri(str(VG) + "engine/", engine_label)

        g.add((engine_uri, RDF.type, VG.GameEngine))
        g.add((engine_uri, VG.engineName, Literal(engine_label, datatype=XSD.string)))
        g.add((game_uri, VG.madeWith, engine_uri))
        engines_added += 1

    logger.info(f"Game engine associations added: {engines_added}")
    time.sleep(5)

    # --- Step 9: Country of origin ---
    logger.info("=" * 60)
    logger.info("STEP 9: Fetching country of origin data...")
    bindings = run_query(sparql, GAMES_COUNTRY_QUERY, "Country data")

    countries_added = 0
    for row in bindings:
        game_label = get_val(row, "gameLabel")
        country_label = get_val(row, "countryLabel")
        if not game_label or not country_label:
            continue
        if is_qid_label(game_label) or is_qid_label(country_label):
            continue
        if game_label not in games_seen:
            continue

        game_uri = make_uri(str(VG), game_label)
        g.add(
            (game_uri, VG.countryOfOrigin, Literal(country_label, datatype=XSD.string))
        )
        countries_added += 1

    logger.info(f"Country associations added: {countries_added}")
    time.sleep(5)

    # --- Step 10: Official website ---
    logger.info("=" * 60)
    logger.info("STEP 10: Fetching official website data...")
    bindings = run_query(sparql, GAMES_WEBSITE_QUERY, "Website data")

    websites_added = 0
    for row in bindings:
        game_label = get_val(row, "gameLabel")
        website = get_val(row, "website")
        if not game_label or not website:
            continue
        if is_qid_label(game_label):
            continue
        if game_label not in games_seen:
            continue

        game_uri = make_uri(str(VG), game_label)
        g.add((game_uri, VG.officialWebsite, Literal(website, datatype=XSD.anyURI)))
        websites_added += 1

    logger.info(f"Websites added: {websites_added}")
    time.sleep(5)

    # --- Step 11: Awards ---
    logger.info("=" * 60)
    logger.info("STEP 11: Fetching award data...")
    bindings = run_query(sparql, GAMES_AWARD_QUERY, "Award data")

    awards_added = 0
    for row in bindings:
        game_label = get_val(row, "gameLabel")
        award_label = get_val(row, "awardLabel")
        if not game_label or not award_label:
            continue
        if is_qid_label(game_label) or is_qid_label(award_label):
            continue
        if game_label not in games_seen:
            continue

        game_uri = make_uri(str(VG), game_label)
        award_uri = make_uri(str(VG) + "award/", award_label)

        g.add((award_uri, RDF.type, VG.Award))
        g.add((award_uri, VG.awardName, Literal(award_label, datatype=XSD.string)))
        g.add((game_uri, VG.wonAward, award_uri))
        awards_added += 1

    logger.info(f"Award associations added: {awards_added}")
    time.sleep(5)

    # --- Step 12: Descriptions ---
    logger.info("=" * 60)
    logger.info("STEP 12: Fetching description data...")
    bindings = run_query(sparql, GAMES_DESC_QUERY, "Description data")

    descs_added = 0
    for row in bindings:
        game_label = get_val(row, "gameLabel")
        desc = get_val(row, "desc")
        if not game_label or not desc:
            continue
        if is_qid_label(game_label):
            continue
        if game_label not in games_seen:
            continue

        game_uri = make_uri(str(VG), game_label)
        g.add((game_uri, VG.gameDescription, Literal(desc, datatype=XSD.string)))
        descs_added += 1

    logger.info(f"Descriptions added: {descs_added}")

    # --- Deduplication pass ---
    logger.info("=" * 60)
    logger.info("DEDUP: Running deduplication pass...")
    removed = deduplicate_graph(g)
    logger.info(
        f"DEDUP: Removed {removed} duplicate entities, graph now has {len(g)} triples"
    )

    # --- Save ---
    output_path = Path(__file__).parent / "videogames_wikidata.owl"
    logger.info("=" * 60)
    logger.info(f"Saving graph with {len(g)} triples to {output_path}")
    g.serialize(str(output_path), format="xml")
    logger.info("Done! Wikidata population complete.")
    return g


if __name__ == "__main__":
    populate_from_wikidata()
