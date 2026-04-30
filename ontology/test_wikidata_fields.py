"""
Test script: discover what properties Wikidata has for video games.
Uses lightweight queries to avoid Wikidata timeouts.
"""

import time

from SPARQLWrapper import JSON, SPARQLWrapper

sparql = SPARQLWrapper("https://query.wikidata.org/sparql")
sparql.addCustomHttpHeader(
    "User-Agent", "VideogameSemanticSearch/1.0 (university project)"
)
sparql.setReturnFormat(JSON)


def run(query, desc):
    print(f"\n{'=' * 70}")
    print(f"  {desc}")
    print(f"{'=' * 70}")
    sparql.setQuery(query)
    try:
        results = sparql.query().convert()
        return results["results"]["bindings"]
    except Exception as e:
        print(f"  ERROR: {e}")
        return []


# Query 1: All direct properties of Elden Ring (well-known game)
bindings = run(
    """
SELECT ?propLabel ?valueLabel WHERE {
  wd:Q61313312 ?p ?value .
  ?prop wikibase:directClaim ?p .
  SERVICE wikibase:label { bd:serviceParam wikibase:language "en". }
}
""",
    "All properties of Elden Ring (Q61313312)",
)

print(f"\n  Found {len(bindings)} property-value pairs:\n")
for b in bindings:
    prop = b.get("propLabel", {}).get("value", "?")
    val = b.get("valueLabel", {}).get("value", "?")[:80]
    print(f"    {prop:<40} = {val}")

time.sleep(2)

# Query 2: All direct properties of Baldur's Gate 3
bindings = run(
    """
SELECT ?propLabel ?valueLabel WHERE {
  wd:Q60553521 ?p ?value .
  ?prop wikibase:directClaim ?p .
  SERVICE wikibase:label { bd:serviceParam wikibase:language "en". }
}
""",
    "All properties of Baldur's Gate 3 (Q60553521)",
)

print(f"\n  Found {len(bindings)} property-value pairs:\n")
for b in bindings:
    prop = b.get("propLabel", {}).get("value", "?")
    val = b.get("valueLabel", {}).get("value", "?")[:80]
    print(f"    {prop:<40} = {val}")

time.sleep(2)

# Query 3: Count games with specific fields we might add
bindings = run(
    """
SELECT 
  (COUNT(DISTINCT ?g1) AS ?withEngine)
  (COUNT(DISTINCT ?g2) AS ?withImage)
  (COUNT(DISTINCT ?g3) AS ?withAward)
  (COUNT(DISTINCT ?g4) AS ?withDesc)
  (COUNT(DISTINCT ?g5) AS ?withCountry)
  (COUNT(DISTINCT ?g6) AS ?withWebsite)
WHERE {
  { ?g1 wdt:P31 wd:Q7889 . ?g1 wdt:P577 ?d1 . FILTER(YEAR(?d1)>=2015) . ?g1 wdt:P408 ?e . }
  UNION
  { ?g2 wdt:P31 wd:Q7889 . ?g2 wdt:P577 ?d2 . FILTER(YEAR(?d2)>=2015) . ?g2 wdt:P18 ?img . }
  UNION
  { ?g3 wdt:P31 wd:Q7889 . ?g3 wdt:P577 ?d3 . FILTER(YEAR(?d3)>=2015) . ?g3 wdt:P166 ?aw . }
  UNION
  { ?g4 wdt:P31 wd:Q7889 . ?g4 wdt:P577 ?d4 . FILTER(YEAR(?d4)>=2015) . ?g4 schema:description ?desc . FILTER(LANG(?desc)="en") }
  UNION
  { ?g5 wdt:P31 wd:Q7889 . ?g5 wdt:P577 ?d5 . FILTER(YEAR(?d5)>=2015) . ?g5 wdt:P495 ?co . }
  UNION
  { ?g6 wdt:P31 wd:Q7889 . ?g6 wdt:P577 ?d6 . FILTER(YEAR(?d6)>=2015) . ?g6 wdt:P856 ?web . }
}
""",
    "Counts: games (2015+) with engine/image/award/description/country/website",
)

if bindings:
    b = bindings[0]
    print(
        f"\n  Games with game engine (P408):    {b.get('withEngine', {}).get('value', '?')}"
    )
    print(
        f"  Games with image (P18):           {b.get('withImage', {}).get('value', '?')}"
    )
    print(
        f"  Games with awards (P166):         {b.get('withAward', {}).get('value', '?')}"
    )
    print(
        f"  Games with description:           {b.get('withDesc', {}).get('value', '?')}"
    )
    print(
        f"  Games with country (P495):        {b.get('withCountry', {}).get('value', '?')}"
    )
    print(
        f"  Games with website (P856):        {b.get('withWebsite', {}).get('value', '?')}"
    )

time.sleep(2)

# Query 4: Sample awards data
bindings = run(
    """
SELECT ?gameLabel ?awardLabel WHERE {
  ?game wdt:P31 wd:Q7889 .
  ?game wdt:P577 ?date . FILTER(YEAR(?date) >= 2020)
  ?game wdt:P166 ?award .
  SERVICE wikibase:label { bd:serviceParam wikibase:language "en". }
}
LIMIT 20
""",
    "Sample: games with awards (2020+)",
)

if bindings:
    print(f"\n  Sample ({len(bindings)} rows):")
    for b in bindings:
        game = b.get("gameLabel", {}).get("value", "?")
        award = b.get("awardLabel", {}).get("value", "?")
        print(f"    {game:<35} -> {award}")

time.sleep(2)

# Query 5: Sample game engine data
bindings = run(
    """
SELECT ?gameLabel ?engineLabel WHERE {
  ?game wdt:P31 wd:Q7889 .
  ?game wdt:P577 ?date . FILTER(YEAR(?date) >= 2020)
  ?game wdt:P408 ?engine .
  ?engine rdfs:label ?engineLabel . FILTER(LANG(?engineLabel) = "en")
  SERVICE wikibase:label { bd:serviceParam wikibase:language "en". }
}
LIMIT 20
""",
    "Sample: games with engine info (2020+)",
)

if bindings:
    print(f"\n  Sample ({len(bindings)} rows):")
    for b in bindings:
        game = b.get("gameLabel", {}).get("value", "?")
        engine = b.get("engineLabel", {}).get("value", "?")
        print(f"    {game:<35} -> {engine}")

print("\n\nDone!")
