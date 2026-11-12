"""
Populate the videogame ontology with data from Wikidata SPARQL endpoint.
Fetches video games released from 2010 onwards with their developers, publishers,
genres, platforms, and characters.
"""

import json
import logging
import re
import time
from collections import defaultdict
from pathlib import Path

from rdflib import RDF, RDFS, XSD, Graph, Literal, Namespace, URIRef
from SPARQLWrapper import JSON, POST, SPARQLWrapper
from tqdm import tqdm

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
  FILTER(YEAR(?releaseDate) = {year} && MONTH(?releaseDate) = {month})
  
  OPTIONAL {{ ?game wdt:P178 ?dev . ?dev rdfs:label ?devLabel . FILTER(LANG(?devLabel) = "en") }}
  OPTIONAL {{ ?game wdt:P123 ?pub . ?pub rdfs:label ?pubLabel . FILTER(LANG(?pubLabel) = "en") }}
  
  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
}}
LIMIT 5000
"""

# Query 2: Genres for the games
GAMES_GENRE_QUERY = """
SELECT DISTINCT ?game ?gameLabel ?genreLabel ?genre WHERE {{
  ?game wdt:P31 wd:Q7889 .
  ?game wdt:P577 ?releaseDate .
  FILTER(YEAR(?releaseDate) = {year} && MONTH(?releaseDate) = {month})
  ?game wdt:P136 ?genre .
  ?genre rdfs:label ?genreLabel . FILTER(LANG(?genreLabel) = "en")
  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
}}
LIMIT 5000
"""

# Query 3: Platforms for the games
GAMES_PLATFORM_QUERY = """
SELECT DISTINCT ?game ?gameLabel ?platformLabel ?platform WHERE {{
  ?game wdt:P31 wd:Q7889 .
  ?game wdt:P577 ?releaseDate .
  FILTER(YEAR(?releaseDate) = {year} && MONTH(?releaseDate) = {month})
  ?game wdt:P400 ?platform .
  ?platform rdfs:label ?platformLabel . FILTER(LANG(?platformLabel) = "en")
  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
}}
LIMIT 5000
"""

# Query 4: Characters
GAMES_CHARACTER_QUERY = """
SELECT DISTINCT ?game ?gameLabel ?charLabel ?char WHERE {{
  ?game wdt:P31 wd:Q7889 .
  ?game wdt:P577 ?releaseDate .
  FILTER(YEAR(?releaseDate) = {year} && MONTH(?releaseDate) = {month})
  ?game wdt:P674 ?char .
  ?char rdfs:label ?charLabel . FILTER(LANG(?charLabel) = "en")
  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
}}
LIMIT 5000
"""

# Query 5: Franchise / series
GAMES_FRANCHISE_QUERY = """
SELECT DISTINCT ?game ?gameLabel ?seriesLabel ?series WHERE {{
  ?game wdt:P31 wd:Q7889 .
  ?game wdt:P577 ?releaseDate .
  FILTER(YEAR(?releaseDate) = {year} && MONTH(?releaseDate) = {month})
  ?game wdt:P179 ?series .
  ?series rdfs:label ?seriesLabel . FILTER(LANG(?seriesLabel) = "en")
  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
}}
LIMIT 5000
"""

# Query 6: Game mode
GAMES_MODE_QUERY = """
SELECT DISTINCT ?game ?gameLabel ?modeLabel WHERE {{
  ?game wdt:P31 wd:Q7889 .
  ?game wdt:P577 ?releaseDate .
  FILTER(YEAR(?releaseDate) = {year} && MONTH(?releaseDate) = {month})
  ?game wdt:P404 ?mode .
  ?mode rdfs:label ?modeLabel . FILTER(LANG(?modeLabel) = "en")
  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
}}
LIMIT 5000
"""

# Query 7: Review scores (Metacritic)
GAMES_SCORE_QUERY = """
SELECT DISTINCT ?game ?gameLabel ?score WHERE {{
  ?game wdt:P31 wd:Q7889 .
  ?game wdt:P577 ?releaseDate .
  FILTER(YEAR(?releaseDate) = {year} && MONTH(?releaseDate) = {month})
  ?game p:P444 ?reviewStatement .
  ?reviewStatement ps:P444 ?score .
  ?reviewStatement pq:P447 wd:Q150248 .  # Metacritic
  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
}}
LIMIT 5000
"""

# Query 9: Game engines (P408)
GAMES_ENGINE_QUERY = """
SELECT DISTINCT ?game ?gameLabel ?engine ?engineLabel WHERE {{
  ?game wdt:P31 wd:Q7889 .
  ?game wdt:P577 ?releaseDate .
  FILTER(YEAR(?releaseDate) = {year} && MONTH(?releaseDate) = {month})
  ?game wdt:P408 ?engine .
  ?engine rdfs:label ?engineLabel . FILTER(LANG(?engineLabel) = "en")
  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
}}
LIMIT 5000
"""

# Query 10: Country of origin (P495)
GAMES_COUNTRY_QUERY = """
SELECT DISTINCT ?game ?gameLabel ?countryLabel WHERE {{
  ?game wdt:P31 wd:Q7889 .
  ?game wdt:P577 ?releaseDate .
  FILTER(YEAR(?releaseDate) = {year} && MONTH(?releaseDate) = {month})
  ?game wdt:P495 ?country .
  ?country rdfs:label ?countryLabel . FILTER(LANG(?countryLabel) = "en")
  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
}}
LIMIT 5000
"""

# Query 12: Awards (P166)
GAMES_AWARD_QUERY = """
SELECT DISTINCT ?game ?gameLabel ?award ?awardLabel WHERE {{
  ?game wdt:P31 wd:Q7889 .
  ?game wdt:P577 ?releaseDate .
  FILTER(YEAR(?releaseDate) = {year} && MONTH(?releaseDate) = {month})
  ?game wdt:P166 ?award .
  ?award rdfs:label ?awardLabel . FILTER(LANG(?awardLabel) = "en")
  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
}}
LIMIT 5000
"""

# Query 13: Sequels (P155 "follows" = previous game in the series)
GAMES_SEQUEL_QUERY = """
SELECT DISTINCT ?game ?gameLabel ?prevLabel WHERE {{
  ?game wdt:P31 wd:Q7889 .
  ?game wdt:P577 ?releaseDate .
  FILTER(YEAR(?releaseDate) = {year} && MONTH(?releaseDate) = {month})
  ?game wdt:P155 ?prev .
  ?prev wdt:P31 wd:Q7889 .
  ?prev rdfs:label ?prevLabel . FILTER(LANG(?prevLabel) = "en")
  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
}}
LIMIT 5000
"""


def make_uri(base: str, label: str) -> URIRef:
    """Create a safe URI from a label."""
    safe = label.strip().replace(" ", "_").replace("'", "").replace('"', "")
    safe = "".join(c for c in safe if c.isalnum() or c in "_-.")
    return URIRef(f"{base}{safe}")


def run_query(
    sparql: SPARQLWrapper,
    query: str,
    description: str,
    cache_file: Path | None = None,
) -> list:
    """Execute a SPARQL query with retry logic and an optional on-disk checkpoint.

    A cached result is returned without touching the network. If every attempt
    fails the error is raised (never an empty list), so a failed month is never
    checkpointed and the run can simply be restarted.
    """
    if cache_file is not None and cache_file.exists():
        return json.loads(cache_file.read_text(encoding="utf-8"))

    sparql.setQuery(query)
    sparql.setReturnFormat(JSON)

    last_error: Exception | None = None
    failures = throttled = 0
    while failures < 4 and throttled < 60:
        try:
            raw = sparql.query().convert()
            results: dict = raw  # type: ignore[assignment]
            bindings: list = results["results"]["bindings"]
            if cache_file is not None:
                cache_file.parent.mkdir(parents=True, exist_ok=True)
                tmp = cache_file.with_suffix(".tmp")
                tmp.write_text(json.dumps(bindings), encoding="utf-8")
                tmp.replace(cache_file)
            return bindings
        except Exception as e:
            last_error = e
            if getattr(e, "code", None) == 429:
                # Wikidata rate limit: wait as long as it asks (default 65s), retry
                # without consuming a normal attempt.
                throttled += 1
                retry_after = getattr(e, "headers", {}).get("Retry-After", "")
                wait = int(retry_after) + 1 if retry_after.isdigit() else 65
                tqdm.write(f"  rate-limited (429) on {description}: waiting {wait}s")
                time.sleep(wait)
                continue
            failures += 1
            logger.warning(f"{description}: attempt {failures} failed: {e}")
            time.sleep(15 * failures)
    raise RuntimeError(f"All attempts failed for: {description}") from last_error


QID_PATTERN = re.compile(r"^Q\d+$")

YEARS = list(range(2010, 2027))
MONTHS = list(range(1, 13))
CACHE_DIR = Path(__file__).parent / ".cache" / "wikidata"


def run_per_year_month_queries(
    sparql: SPARQLWrapper,
    query_template: str,
    key: str,
    description: str,
    years: list[int],
    cache_dir: Path,
    delay: float = 1.0,
) -> list:
    """
    Run a parameterised query for every (year, month) pair to avoid LIMIT truncation.
    Each month is checkpointed in cache_dir/<key>/<year>-<month>.json.
    """
    all_bindings = []
    pairs = [(y, m) for y in years for m in MONTHS]
    with tqdm(pairs, desc=description, unit="month") as pbar:
        for year, month in pbar:
            pbar.set_postfix(year=year, month=f"{month:02d}")
            cache_file = cache_dir / key / f"{year}-{month:02d}.json"
            cached = cache_file.exists()
            query = query_template.format(year=year, month=month)
            bindings = run_query(
                sparql, query, f"{description} ({year}-{month:02d})", cache_file
            )
            all_bindings.extend(bindings)
            if not cached:
                time.sleep(delay)
    return all_bindings


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
    Merge duplicate entities that share the same normalised name *and the same
    kind* (same name property): a game and its franchise, or a developer and a
    publisher with the same name, are different individuals and must stay apart
    (the top classes are pairwise disjoint).
    For each group of URIs with the same name (case-insensitive, stripped),
    keep the URI with the most triples (subject + object) and redirect all
    references to the others to the canonical URI.
    Returns the number of duplicates removed.
    """
    name_to_uris: dict[tuple[str, str], list[URIRef]] = defaultdict(list)

    for prop_local in _NAME_PROPS:
        prop = VG[prop_local]
        for subj, _, obj in g.triples((None, prop, None)):
            if isinstance(obj, Literal) and isinstance(subj, URIRef):
                key = (prop_local, str(obj).strip().lower())
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
            logger.debug(f"[DEDUP] Merged '{name_key[1]}': {duplicate} → {canonical}")

    return removed


def get_val(binding: dict, key: str) -> str | None:
    """Safely extract a value from a SPARQL binding."""
    if key in binding:
        return binding[key]["value"]
    return None


def is_qid_label(value: str | None) -> bool:
    """Return True if the value is a raw Wikidata QID (no proper label resolved)."""
    return value is not None and bool(QID_PATTERN.match(value))


# ---------------------------------------------------------------------------
# Label -> V2 subclass classification (keeps the ABox consistent with the TBox
# so that the platform/genre/mode defined classes can be inferred later)
# ---------------------------------------------------------------------------

# First matching rule wins, so the order matters (families are mutually exclusive).
_PLATFORM_RULES: list[tuple[str, URIRef]] = [
    (r"playstation|ps[0-9p]?|psp|vita", VG.PlayStationPlatform),
    (r"xbox", VG.XboxPlatform),
    (
        r"nintendo|switch|wii|wiiware|game ?boy|3?ds|dsi|gamecube|s?nes|n64|famicom",
        VG.NintendoPlatform,
    ),
    (r"windows", VG.WindowsPlatform),
    (r"macos|mac os|os x|macintosh|mac", VG.MacOSPlatform),
    (r"linux", VG.LinuxPlatform),
    (r"ios|iphone|ipad", VG.IOSPlatform),
    (r"android", VG.AndroidPlatform),
    (
        r"web browser|browser game|web application|web platform|web page|html5|google chrome|facebook",
        VG.BrowserPlatform,
    ),
    (r"arcade", VG.ArcadePlatform),
    (
        r"commodore|zx spectrum|amstrad|atari st|atari 8|msx|sharp x|apple ii|fm towns|bbc micro|amiga|trs-80|ti-99|pc-98|pc-88",
        VG.RetroComputerPlatform,
    ),
    (r"horizon os|quest|visionos|oculus|vr|vive|virtual reality|hololens", VG.VRPlatform),
    # other consoles (before the PC rule: "PC Engine" is a console)
    (
        r"ouya|turbografx|pc engine|neo geo|atari (2600|5200|7800|vcs|lynx|jaguar)|sega|dreamcast|genesis|mega drive|master system|sg-1000|saturn|game gear|colecovision|intellivision|3do|cd-i|zeebo|vectrex",
        VG.ConsolePlatform,
    ),
    (r"personal computer|pc|dos|steam", VG.PCPlatform),
    (
        r"mobile|phone|blackberry|symbian|java platform, micro|harmonyos|watchos",
        VG.MobilePlatform,
    ),
]

# A genre can belong to several families ("action role-playing game"): every match counts.
_GENRE_RULES: list[tuple[str, URIRef]] = [
    (r"role-playing|rpg", VG.RPGGenre),
    (r"horror", VG.HorrorGenre),
    (r"platform game|platformer", VG.PlatformerGenre),
    (r"strategy|tactic", VG.StrategyGenre),
    (r"puzzle", VG.PuzzleGenre),
    (r"simulat", VG.SimulationGenre),
    (r"sport", VG.SportsGenre),
    (r"racing|racer", VG.RacingGenre),
    (r"adventure", VG.AdventureGenre),
    (r"action|fighting|beat 'em", VG.ActionGenre),
    (r"shooter|shoot 'em up|shmup", VG.ShooterGenre),
    (r"casual|hidden object", VG.CasualGenre),
    (r"visual novel|eroge", VG.VisualNovelGenre),
]

_MODE_RULES: list[tuple[str, URIRef]] = [
    (r"massively|mmo", VG.MMOMode),
    (r"co-?op", VG.CoopMode),
    (r"multiplayer|multi-player|versus", VG.MultiplayerMode),
    (r"single", VG.SinglePlayerMode),
]

_ENGINE_RULES: list[tuple[str, URIRef]] = [(r"unreal engine", VG.UnrealEngineFamily)]
_AWARD_RULES: list[tuple[str, URIRef]] = [(r"game of the year|goty", VG.GameOfTheYearAward)]


def _classify(
    label: str, rules: list[tuple[str, URIRef]], multi: bool = False
) -> list[URIRef]:
    low = label.lower()
    hits = [cls for pattern, cls in rules if re.search(pattern, low)]
    return hits if multi else hits[:1]


def _clean(row: dict, *keys: str) -> list[str] | None:
    """Return the values for keys, or None if any is missing or a raw QID."""
    out = []
    for k in keys:
        v = get_val(row, k)
        if not v or is_qid_label(v):
            return None
        out.append(v)
    return out


# (cache key, template, label var, uri sub-path, class, name prop, link prop, rules)
_LINKS = [
    (
        "genre",
        GAMES_GENRE_QUERY,
        "genreLabel",
        "genre/",
        VG.Genre,
        VG.genreName,
        VG.hasGenre,
        _GENRE_RULES,
    ),
    (
        "platform",
        GAMES_PLATFORM_QUERY,
        "platformLabel",
        "platform/",
        VG.Platform,
        VG.platformName,
        VG.availableOn,
        _PLATFORM_RULES,
    ),
    (
        "character",
        GAMES_CHARACTER_QUERY,
        "charLabel",
        "char/",
        VG.Character,
        VG.characterName,
        VG.hasCharacter,
        None,
    ),
    (
        "franchise",
        GAMES_FRANCHISE_QUERY,
        "seriesLabel",
        "franchise/",
        VG.Franchise,
        VG.franchiseName,
        VG.belongsTo,
        None,
    ),
    (
        "engine",
        GAMES_ENGINE_QUERY,
        "engineLabel",
        "engine/",
        VG.GameEngine,
        VG.engineName,
        VG.madeWith,
        _ENGINE_RULES,
    ),
    (
        "award",
        GAMES_AWARD_QUERY,
        "awardLabel",
        "award/",
        VG.Award,
        VG.awardName,
        VG.wonAward,
        _AWARD_RULES,
    ),
]


def populate_from_wikidata(
    years: list[int] | None = None, cache_dir: Path = CACHE_DIR
) -> Graph:
    """Fetch the ABox from Wikidata (checkpointed per query x month) and return
    the graph (TBox + data, deduplicated). Reasoning is done by build_ontology.py.
    """
    years = years or YEARS
    sparql = SPARQLWrapper(WIKIDATA_ENDPOINT)
    # POST: during WDQS outages GET requests are throttled to 1 req/min at the edge
    sparql.setMethod(POST)
    sparql.addCustomHttpHeader(
        "User-Agent",
        "VideogameSemanticSearch/1.0 (university project; semantic web course)",
    )

    g = Graph()
    g.bind("vg", VG)
    g.parse(str(Path(__file__).parent / "videogames.owl"))

    games_seen: set[str] = set()
    game_earliest_date: dict[str, str] = {}
    game_devs_seen: dict[str, set] = {}
    game_pubs_seen: dict[str, set] = {}

    # --- Step 1: Core game data ---
    logger.info("STEP 1: core game data (year x month)")
    pairs = [(y, m) for y in years for m in MONTHS]
    with tqdm(pairs, desc="Core game data", unit="month") as pbar:
        for year, month in pbar:
            pbar.set_postfix(year=year, month=f"{month:02d}", games=len(games_seen))
            cache_file = cache_dir / "core" / f"{year}-{month:02d}.json"
            cached = cache_file.exists()
            query = GAMES_CORE_QUERY.format(year=year, month=month)
            bindings = run_query(
                sparql, query, f"Core game data ({year}-{month:02d})", cache_file
            )

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
                            (
                                game_uri,
                                VG.releaseDate,
                                Literal(date_str, datatype=XSD.date),
                            )
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

            if not cached:
                time.sleep(1)  # Be polite to Wikidata (between months)

    logger.info(f"Total games loaded: {len(games_seen)}")

    # --- Steps 2-7: entity links (genre, platform, character, franchise, engine, award)
    for n, (key, tpl, var, sub, cls, name_prop, link_prop, rules) in enumerate(
        _LINKS, start=2
    ):
        logger.info(f"STEP {n}: {key} data")
        rows = run_per_year_month_queries(
            sparql, tpl, key, f"{key.capitalize()} data", years, cache_dir
        )
        added = 0
        for row in rows:
            vals = _clean(row, "gameLabel", var)
            if not vals or vals[0] not in games_seen:
                continue
            game_label, label = vals
            game_uri = make_uri(str(VG), game_label)
            uri = make_uri(str(VG) + sub, label)
            g.add((uri, RDF.type, cls))
            if rules:
                for sub_cls in _classify(label, rules, multi=key == "genre"):
                    g.add((uri, RDF.type, sub_cls))
            g.add((uri, name_prop, Literal(label, datatype=XSD.string)))
            g.add((game_uri, link_prop, uri))
            added += 1
        logger.info(f"  {key} associations added: {added}")

    # --- Game modes: individuals typed with the GameMode subclasses ---
    logger.info("STEP 8: game mode data")
    rows = run_per_year_month_queries(
        sparql, GAMES_MODE_QUERY, "mode", "Game mode data", years, cache_dir
    )
    for row in rows:
        vals = _clean(row, "gameLabel", "modeLabel")
        if not vals or vals[0] not in games_seen:
            continue
        game_label, label = vals
        mode_uri = make_uri(str(VG) + "mode/", label)
        g.add((mode_uri, RDF.type, VG.GameMode))
        for mode_cls in _classify(label, _MODE_RULES):
            g.add((mode_uri, RDF.type, mode_cls))
        g.add((mode_uri, RDFS.label, Literal(label, datatype=XSD.string)))
        g.add((make_uri(str(VG), game_label), VG.hasGameMode, mode_uri))

    # --- Metacritic scores ---
    logger.info("STEP 9: Metacritic scores")
    rows = run_per_year_month_queries(
        sparql, GAMES_SCORE_QUERY, "score", "Metacritic scores", years, cache_dir
    )
    for row in rows:
        vals = _clean(row, "gameLabel")
        score = get_val(row, "score")
        if not vals or not score or vals[0] not in games_seen:
            continue
        try:
            score_num = int(score.split("/")[0])
        except ValueError:
            continue
        g.add(
            (
                make_uri(str(VG), vals[0]),
                VG.metacriticScore,
                Literal(score_num, datatype=XSD.integer),
            )
        )

    # --- Country of origin ---
    logger.info("STEP 10: country of origin")
    rows = run_per_year_month_queries(
        sparql, GAMES_COUNTRY_QUERY, "country", "Country data", years, cache_dir
    )
    for row in rows:
        vals = _clean(row, "gameLabel", "countryLabel")
        if not vals or vals[0] not in games_seen:
            continue
        g.add(
            (
                make_uri(str(VG), vals[0]),
                VG.countryOfOrigin,
                Literal(vals[1], datatype=XSD.string),
            )
        )

    # --- Sequels (sequelOf) ---
    logger.info("STEP 11: sequel relations")
    rows = run_per_year_month_queries(
        sparql, GAMES_SEQUEL_QUERY, "sequel", "Sequel data", years, cache_dir
    )
    for row in rows:
        vals = _clean(row, "gameLabel", "prevLabel")
        if not vals or vals[0] not in games_seen or vals[1] not in games_seen:
            continue
        if vals[0] != vals[1]:
            g.add(
                (
                    make_uri(str(VG), vals[0]),
                    VG.sequelOf,
                    make_uri(str(VG), vals[1]),
                )
            )

    # --- Deduplication pass ---
    removed = deduplicate_graph(g)
    logger.info(f"DEDUP: removed {removed} duplicates, graph has {len(g)} triples")
    return g
