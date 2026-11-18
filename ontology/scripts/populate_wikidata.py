"""
Populate the videogame ontology with data from Wikidata SPARQL endpoint.
Fetches video games released from 2010 onwards with their developers, publishers,
genres, platforms, and characters.
"""

import hashlib
import json
import logging
import re
import shutil
import time
import unicodedata
from collections import defaultdict
from pathlib import Path

from rdflib import OWL, RDF, RDFS, XSD, Graph, Literal, Namespace, URIRef
from SPARQLWrapper import JSON, POST, SPARQLWrapper
from tqdm import tqdm

import schema_loader

logger = logging.getLogger(__name__)

# Namespaces
VG = Namespace("http://www.videogame-ontology.org/ontology#")
WD = Namespace("http://www.wikidata.org/entity/")

WIKIDATA_ENDPOINT = "https://query.wikidata.org/sparql"

# Wikidata keeps a single "mul" label (no "en") on items whose name is the same in
# every language (Fallout 4, PlayStation 5...): labels are read as en *or* mul,
# otherwise those games and platforms come back as bare QIDs / vanish from the join.
# We split into multiple queries to avoid Wikidata timeout (60s limit)
# Query 1: Core game data (name, release date, developer, publisher)
GAMES_CORE_QUERY = """
SELECT DISTINCT ?game ?gameLabel ?releaseDate ?devLabel ?pubLabel ?dev ?pub WHERE {{
  ?game wdt:P31 wd:Q7889 .          # instance of video game
  ?game wdt:P577 ?releaseDate .      # publication date
  FILTER(YEAR(?releaseDate) = {year} && MONTH(?releaseDate) = {month})
  
  OPTIONAL {{ ?game wdt:P178 ?dev . ?dev rdfs:label ?devLabel . FILTER(LANG(?devLabel) IN ("en", "mul")) }}
  OPTIONAL {{ ?game wdt:P123 ?pub . ?pub rdfs:label ?pubLabel . FILTER(LANG(?pubLabel) IN ("en", "mul")) }}
  
  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en,mul". }}
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
  ?genre rdfs:label ?genreLabel . FILTER(LANG(?genreLabel) IN ("en", "mul"))
  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en,mul". }}
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
  ?platform rdfs:label ?platformLabel . FILTER(LANG(?platformLabel) IN ("en", "mul"))
  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en,mul". }}
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
  ?char rdfs:label ?charLabel . FILTER(LANG(?charLabel) IN ("en", "mul"))
  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en,mul". }}
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
  ?series rdfs:label ?seriesLabel . FILTER(LANG(?seriesLabel) IN ("en", "mul"))
  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en,mul". }}
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
  ?mode rdfs:label ?modeLabel . FILTER(LANG(?modeLabel) IN ("en", "mul"))
  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en,mul". }}
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
  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en,mul". }}
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
  ?engine rdfs:label ?engineLabel . FILTER(LANG(?engineLabel) IN ("en", "mul"))
  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en,mul". }}
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
  ?country rdfs:label ?countryLabel . FILTER(LANG(?countryLabel) IN ("en", "mul"))
  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en,mul". }}
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
  ?award rdfs:label ?awardLabel . FILTER(LANG(?awardLabel) IN ("en", "mul"))
  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en,mul". }}
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
  ?prev rdfs:label ?prevLabel . FILTER(LANG(?prevLabel) IN ("en", "mul"))
  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en,mul". }}
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
CACHE_DIR = Path(__file__).resolve().parent.parent / ".cache" / "wikidata"


def sync_query_cache(cache_dir: Path, key: str, template: str) -> None:
    """A checkpoint is only valid for the query that produced it: when the query
    text changed, move the old months to <key>.stale and fetch again."""
    d = cache_dir / key
    mark = d / "_query.sha1"
    digest = hashlib.sha1(template.encode()).hexdigest()
    if mark.exists() and mark.read_text().strip() == digest:
        return
    if d.exists() and any(d.glob("*.json")):
        stale = cache_dir / f"{key}.stale"
        shutil.rmtree(stale, ignore_errors=True)
        d.rename(stale)
        tqdm.write(f"  query '{key}' changed: old checkpoints moved to {stale.name}")
    d.mkdir(parents=True, exist_ok=True)
    mark.write_text(digest)


def prefer_en_labels(rows: list, *pairs: tuple[str, str]) -> list:
    """One label per entity: the same item can come back with an "en" and a "mul"
    label that differ (Xbox Series X and Series S / Xbox Series X/S), which would
    create two nodes for it. pairs = (label column, uri column); "en" wins."""
    for lab, uri in pairs:
        best: dict[str, dict] = {}
        for r in rows:
            if lab in r and uri in r:
                u = r[uri]["value"]
                if u not in best or r[lab].get("xml:lang") == "en":
                    best[u] = r[lab]
        for r in rows:
            if lab in r and uri in r:
                r[lab] = best[r[uri]["value"]]
    return rows


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
    sync_query_cache(cache_dir, key, query_template)
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


# Near-duplicates of platforms, developers and publishers. Companies are compared
# without punctuation, case and legal form ("Netflix, Inc." = "Netflix"); words such as
# Games/Studios stay, because Rockstar Games and Rockstar Studios are different entities.
_LEGAL = re.compile(
    r"\b(?:inc|incorporated|ltd|limited|llc|gmbh|co|corp|corporation|plc|ab|bv|oy|srl|kk|pty|ag|company|the)\b"
)
# the same thing under another name (Wikidata aliases and renamed companies)
_ALIASES = {
    "platformName": {"ps5": "playstation 5"},
    "developerName": {"konami digital entertainment": "konami", "marvelous entertainment": "marvelous"},
    "publisherName": {"konami digital entertainment": "konami", "marvelous entertainment": "marvelous"},
}


def dedup_name(prop_local: str, name: str) -> str:
    low = " ".join(name.lower().split())  # case and runs of spaces never make a different entity
    low = _ALIASES.get(prop_local, {}).get(low, low)
    if prop_local not in ("developerName", "publisherName"):
        # "Talking Tom & Friends" = "Talking Tom and Friends" (not for games: "&" can be part of a title)
        return low if prop_local == "gameName" else low.replace(" & ", " and ")
    n = unicodedata.normalize("NFKC", low).replace("&", " and ")
    n = _LEGAL.sub(" ", re.sub(r"[^\w ]", " ", n))
    return "".join(n.split()) or low


def clean_functional(g: Graph) -> int:
    """Games merged by name (a remake or a port shares the title of the original) end up with several
    values for the functional properties: keep one release date (the earliest), one Metacritic score
    (the highest) and one name; drop the sequelOf that points a game to itself (same cause)."""
    fixed = 0
    pick = {VG.releaseDate: min, VG.metacriticScore: max, VG.gameName: min}
    for prop, choose in pick.items():
        by_game: dict = defaultdict(list)
        for subj, _, obj in g.triples((None, prop, None)):
            by_game[subj].append(obj)
        for subj, values in by_game.items():
            if len(values) > 1:
                keep = choose(values, key=lambda v: (int(v) if prop == VG.metacriticScore else str(v)))
                for v in values:
                    if v != keep:
                        g.remove((subj, prop, v))
                fixed += 1
    for subj, _, obj in list(g.triples((None, VG.sequelOf, None))):
        if subj == obj:
            g.remove((subj, VG.sequelOf, obj))
            fixed += 1
    return fixed


_COMPANY_NAME_PROPS = ("developerName", "publisherName")
_NAME_PROP_URIS = {VG[n] for n in _NAME_PROPS}


def deduplicate_graph(g: Graph) -> int:
    """
    Merge duplicate entities that share the same normalised name *and the same
    kind* (same name property): a game and its franchise are different individuals
    and must stay apart (the top classes are pairwise disjoint). A developer and a
    publisher with the same name are ONE company (Company model): they share a kind,
    and the merged individual keeps both roles (types and name properties).
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
                kind = "company" if prop_local in _COMPANY_NAME_PROPS else prop_local
                key = (kind, dedup_name(prop_local, str(obj)))
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

        # Canonical URI: one declared in the schema (a nominal such as pub/Nintendo, which the
        # defined classes refer to) wins, otherwise the one with the most triples
        uris_sorted = sorted(
            uris,
            key=lambda u: ((u, RDF.type, OWL.NamedIndividual) in g, triple_count(u)),
            reverse=True,
        )
        canonical = uris_sorted[0]

        def canonical_has(pred: URIRef, canonical=canonical) -> bool:
            return any(True for _ in g.objects(canonical, pred))

        for duplicate in uris_sorted[1:]:
            if duplicate == canonical:
                continue

            # Re-point all triples where duplicate is the subject
            for pred, obj in list(g.predicate_objects(duplicate)):
                g.remove((duplicate, pred, obj))
                if pred in _NAME_PROP_URIS and canonical_has(pred):
                    continue  # keep a single name per property: the canonical one
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
    (r"playstation|\bps[0-9p]?\b|\bpsp\b|vita", VG.PlayStationPlatform),
    (r"xbox", VG.XboxPlatform),
    (
        r"nintendo|\bswitch\b|\bwii\b|wiiware|game ?boy|\b3?ds\b|dsi|gamecube|\bs?nes\b|\bn64\b|famicom",
        VG.NintendoPlatform,
    ),
    (r"windows", VG.WindowsPlatform),
    (r"macos|mac os|os x|macintosh|\bmac\b", VG.MacOSPlatform),
    (r"linux", VG.LinuxPlatform),
    (r"\bios\b|iphone|ipad", VG.IOSPlatform),
    (r"android", VG.AndroidPlatform),
    (
        r"web browser|browser game|web application|web platform|web page|html5|google chrome|facebook",
        VG.BrowserPlatform,
    ),
    (r"arcade", VG.ArcadePlatform),
    (
        r"commodore|zx spectrum|amstrad|atari st\b|atari 8|msx|sharp x|apple ii|fm towns|bbc micro|amiga|trs-80|ti-99|pc-98|pc-88",
        VG.RetroComputerPlatform,
    ),
    (r"horizon os|quest|visionos|oculus|\bvr\b|vive|virtual reality|hololens", VG.VRPlatform),
    # other consoles (before the PC rule: "PC Engine" is a console)
    (
        r"ouya|turbografx|pc engine|neo geo|atari (2600|5200|7800|vcs|lynx|jaguar)|sega|dreamcast|genesis|mega drive|master system|sg-1000|saturn|game gear|colecovision|intellivision|3do|cd-i|zeebo|vectrex",
        VG.ConsolePlatform,
    ),
    (r"personal computer|\bpc\b|\bdos\b|steam", VG.PCPlatform),
    (
        r"mobile|phone|blackberry|symbian|java platform, micro|harmonyos|watchos",
        VG.MobilePlatform,
    ),
]

# A genre can belong to several families ("action role-playing game"): every match counts.
_GENRE_RULES: list[tuple[str, URIRef]] = [
    (r"role-playing|\brpg\b", VG.RPGGenre),
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
    (r"massively|\bmmo", VG.MMOMode),
    (r"co-?op", VG.CoopMode),
    (r"multiplayer|multi-player|versus", VG.MultiplayerMode),
    (r"single", VG.SinglePlayerMode),
]

_ENGINE_RULES: list[tuple[str, URIRef]] = [(r"unreal engine", VG.UnrealEngineFamily)]
# GameOfTheYearAward = the main prize of The Game Awards (Wikidata covers 2014 onwards),
# not the many category prizes ("... for Strategy Game of the Year", "iPad Game of the Year")
# nor the GOTY of other bodies (Golden Joystick, DICE, GDC...)
_GOTY_MAIN = r"^the game awards\s*[-–−:]\s*game of the year\s*$"
# Spike Video Game Awards GOTY (the TGA's predecessor, 2010-2013): its winners are not
# linked to the games on Wikidata, so they are listed here by game name
_VGA_GOTY = {
    2010: "Red Dead Redemption",
    2011: "The Elder Scrolls V: Skyrim",
    2012: "The Walking Dead: Season One",
    2013: "Grand Theft Auto V",
}
_AWARD_RULES: list[tuple[str, URIRef]] = [(_GOTY_MAIN, VG.GameOfTheYearAward)]


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
    g += schema_loader.load_tbox()

    games_seen: set[str] = set()
    game_earliest_date: dict[str, str] = {}
    game_devs_seen: dict[str, set] = {}
    game_pubs_seen: dict[str, set] = {}

    # --- Step 1: Core game data ---
    logger.info("STEP 1: core game data (year x month)")
    sync_query_cache(cache_dir, "core", GAMES_CORE_QUERY)
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
            prefer_en_labels(bindings, ("devLabel", "dev"), ("pubLabel", "pub"))

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
        prefer_en_labels(rows, (var, var[: -len("Label")]))
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

    vga = make_uri(str(VG) + "award/", "Spike Video Game Awards - Game of the Year")
    g.add((vga, RDF.type, VG.Award))
    g.add((vga, RDF.type, VG.GameOfTheYearAward))
    g.add((vga, VG.awardName, Literal("Spike Video Game Awards - Game of the Year", datatype=XSD.string)))
    for year, name in _VGA_GOTY.items():
        if name in games_seen:
            g.add((make_uri(str(VG), name), VG.wonAward, vga))
        else:
            logger.warning(f"VGA {year} Game of the Year '{name}' not in the fetched games")

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
    logger.info(f"CLEAN: {clean_functional(g)} functional values / self-sequels fixed")
    return g
