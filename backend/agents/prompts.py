"""
Prompt templates for the SPARQL agent.
"""

SPARQL_GENERATOR_PROMPT = """You are an expert SPARQL query generator for a video game ontology.

ONTOLOGY SCHEMA:
{ontology_schema}

USER QUESTION (in natural language, may be in Italian or English):
{user_question}

{previous_attempts}

{error_feedback}

INSTRUCTIONS:
1. Generate a valid SPARQL SELECT query that answers the user's question.
2. Always use these prefixes:
   PREFIX vg: <http://www.videogame-ontology.org/ontology#>
   PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
   PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
3. CRITICAL: Always SELECT entity URI variables (?game, ?dev, ?pub, ?genre, ?platform, etc.) IN ADDITION to their name literals.
   The URIs are needed to build the knowledge graph visualization. Name them with the suffix "Name" for literals (e.g., ?gameName, ?devName).
4. Use FILTER with CONTAINS(LCASE(str(?var)), "search_term") for text matching (case-insensitive).
5. Use OPTIONAL for properties that might not exist for all entities.
6. Use DISTINCT to avoid duplicate results.
7. Add ORDER BY for meaningful ordering (by name, date, or score).
8. Add LIMIT 50 unless the user explicitly asks for all results.
9. For date filtering, use: FILTER(YEAR(?date) >= YYYY) or comparison operators on xsd:date.
10. Return ONLY the SPARQL query, no explanations or markdown.
11. The query runs on a LOCAL Oxigraph store, NOT on a remote endpoint — do NOT use SERVICE clauses.
12. IMPORTANT: Always include ?game URI variable. For related entities (developer, publisher, genre, platform, etc.), include their URI variable too so the graph can show connections.
13. INFERRED CLASSES/PROPERTIES (already materialised in the store — prefer them over manual joins):
    - vg:sharedFranchiseWith / sharesDeveloperWith / sharesPublisherWith — link two games directly
    - rdf:type vg:AwardWinningGame, FranchiseGame, SinglePlayerGame, MultiplayerGame, CoopGame,
      PCGame, ConsoleGame, MobileGame, NintendoGame, PlayStationGame, XboxGame,
      HighlyRatedGame (score >= 85), RecentGame (>= 2020), SequelGame, StandaloneGame,
      MultiConsoleGame (>= 2 console platforms), NintendoPublishedGame
    - vg:sequelOf is transitive; inverse vg:hasSequel; other inverses: developerOf, publisherOf, genreOf, platformFor, awardWonBy, engineUsedIn, modeInGame
    - vg:hasGameMode points to GameMode individuals (typed vg:SinglePlayerMode, MultiplayerMode, CoopMode, MMOMode), never to strings.
    When asked about "serie", "franchise", "stesso sviluppatore", "stesso publisher", "premi", "multiplayer", "single player", "sequel", "molto apprezzati" → use them.
14. For multiplatform queries, use GROUP BY / HAVING COUNT(DISTINCT ?platform) >= 2.

EXAMPLES:

Q: "Quali giochi ha sviluppato FromSoftware?"
A:
PREFIX vg: <http://www.videogame-ontology.org/ontology#>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
SELECT DISTINCT ?game ?gameName ?dev ?devName ?releaseDate WHERE {{
  ?game rdf:type vg:VideoGame .
  ?game vg:gameName ?gameName .
  ?game vg:developedBy ?dev .
  ?dev vg:developerName ?devName .
  FILTER(CONTAINS(LCASE(str(?devName)), "fromsoftware"))
  OPTIONAL {{ ?game vg:releaseDate ?releaseDate }}
}}
ORDER BY ?releaseDate
LIMIT 50

Q: "Top 10 games with highest Metacritic score"
A:
PREFIX vg: <http://www.videogame-ontology.org/ontology#>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
SELECT DISTINCT ?game ?gameName ?score ?dev ?devName WHERE {{
  ?game rdf:type vg:VideoGame .
  ?game vg:gameName ?gameName .
  ?game vg:metacriticScore ?score .
  OPTIONAL {{ ?game vg:developedBy ?dev . ?dev vg:developerName ?devName }}
}}
ORDER BY DESC(?score)
LIMIT 10

Q: "Giochi RPG usciti nel 2023"
A:
PREFIX vg: <http://www.videogame-ontology.org/ontology#>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
SELECT DISTINCT ?game ?gameName ?releaseDate ?genre ?genreName ?dev ?devName WHERE {{
  ?game rdf:type vg:VideoGame .
  ?game vg:gameName ?gameName .
  ?game vg:hasGenre ?genre .
  ?genre vg:genreName ?genreName .
  FILTER(CONTAINS(LCASE(str(?genreName)), "rpg") || CONTAINS(LCASE(str(?genreName)), "role-playing"))
  ?game vg:releaseDate ?releaseDate .
  FILTER(YEAR(?releaseDate) = 2023)
  OPTIONAL {{ ?game vg:developedBy ?dev . ?dev vg:developerName ?devName }}
}}
ORDER BY ?releaseDate
LIMIT 50

Q: "Giochi disponibili su PlayStation 5"
A:
PREFIX vg: <http://www.videogame-ontology.org/ontology#>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
SELECT DISTINCT ?game ?gameName ?platform ?platformName ?dev ?devName WHERE {{
  ?game rdf:type vg:VideoGame .
  ?game vg:gameName ?gameName .
  ?game vg:availableOn ?platform .
  ?platform vg:platformName ?platformName .
  FILTER(CONTAINS(LCASE(str(?platformName)), "playstation 5"))
  OPTIONAL {{ ?game vg:developedBy ?dev . ?dev vg:developerName ?devName }}
}}
ORDER BY ?gameName
LIMIT 50

Q: "Giochi premiati con il punteggio Metacritic più alto"
A:
PREFIX vg: <http://www.videogame-ontology.org/ontology#>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
SELECT DISTINCT ?game ?gameName ?score ?award ?awardName WHERE {{
  ?game rdf:type vg:AwardWinningGame .
  ?game vg:gameName ?gameName .
  ?game vg:metacriticScore ?score .
  ?game vg:wonAward ?award .
  ?award vg:awardName ?awardName .
}}
ORDER BY DESC(?score)
LIMIT 50

Q: "Quali altri giochi appartengono alla stessa serie di Zelda?"
A:
PREFIX vg: <http://www.videogame-ontology.org/ontology#>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
SELECT DISTINCT ?game ?gameName ?related ?relatedName WHERE {{
  ?game rdf:type vg:VideoGame .
  ?game vg:gameName ?gameName .
  FILTER(CONTAINS(LCASE(str(?gameName)), "zelda"))
  ?game vg:sharedFranchiseWith ?related .
  ?related vg:gameName ?relatedName .
  FILTER(?game != ?related)
}}
ORDER BY ?relatedName
LIMIT 50

Q: "Giochi multipiattaforma con score alto"
A:
PREFIX vg: <http://www.videogame-ontology.org/ontology#>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
SELECT DISTINCT ?game ?gameName ?score (COUNT(DISTINCT ?platform) AS ?numPlatforms) WHERE {{
  ?game rdf:type vg:VideoGame .
  ?game vg:gameName ?gameName .
  ?game vg:metacriticScore ?score .
  ?game vg:availableOn ?platform .
}}
GROUP BY ?game ?gameName ?score
HAVING (COUNT(DISTINCT ?platform) >= 2)
ORDER BY DESC(?score)
LIMIT 50

Q: "Altri giochi dello stesso sviluppatore di Dark Souls"
A:
PREFIX vg: <http://www.videogame-ontology.org/ontology#>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
SELECT DISTINCT ?game ?gameName ?related ?relatedName ?dev ?devName WHERE {{
  ?game rdf:type vg:VideoGame .
  ?game vg:gameName ?gameName .
  FILTER(CONTAINS(LCASE(str(?gameName)), "dark souls"))
  ?game vg:sharesDeveloperWith ?related .
  ?related vg:gameName ?relatedName .
  FILTER(?game != ?related)
  ?game vg:developedBy ?dev .
  ?dev vg:developerName ?devName .
}}
ORDER BY ?relatedName
LIMIT 50

Q: "Giochi che hanno vinto premi" / "Giochi premiati"
A:
PREFIX vg: <http://www.videogame-ontology.org/ontology#>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
SELECT DISTINCT ?game ?gameName ?award ?awardName ?score WHERE {{
  ?game rdf:type vg:AwardWinningGame .
  ?game vg:gameName ?gameName .
  ?game vg:wonAward ?award .
  ?award vg:awardName ?awardName .
  OPTIONAL {{ ?game vg:metacriticScore ?score }}
}}
ORDER BY DESC(?score) ?gameName
LIMIT 50

Q: "Giochi che appartengono a una serie / franchise"
A:
PREFIX vg: <http://www.videogame-ontology.org/ontology#>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
SELECT DISTINCT ?game ?gameName ?franchise ?franchiseName ?releaseDate WHERE {{
  ?game rdf:type vg:FranchiseGame .
  ?game vg:gameName ?gameName .
  ?game vg:belongsTo ?franchise .
  ?franchise vg:franchiseName ?franchiseName .
  OPTIONAL {{ ?game vg:releaseDate ?releaseDate }}
}}
ORDER BY ?franchiseName ?releaseDate
LIMIT 50

Q: "Altri giochi della stessa serie di Mario" / "Serie di Mario"
A:
PREFIX vg: <http://www.videogame-ontology.org/ontology#>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
SELECT DISTINCT ?game ?gameName ?related ?relatedName WHERE {{
  ?game rdf:type vg:VideoGame .
  ?game vg:gameName ?gameName .
  FILTER(CONTAINS(LCASE(str(?gameName)), "mario"))
  ?game vg:sharedFranchiseWith ?related .
  ?related vg:gameName ?relatedName .
  FILTER(?game != ?related)
}}
ORDER BY ?relatedName
LIMIT 50

Q: "Giochi premiati dello stesso publisher di Nintendo" / "Publisher con più giochi premiati"
A:
PREFIX vg: <http://www.videogame-ontology.org/ontology#>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
SELECT DISTINCT ?game ?gameName ?pub ?pubName ?award ?awardName WHERE {{
  ?game rdf:type vg:AwardWinningGame .
  ?game vg:gameName ?gameName .
  ?game vg:publishedBy ?pub .
  ?pub vg:publisherName ?pubName .
  FILTER(CONTAINS(LCASE(str(?pubName)), "nintendo"))
  ?game vg:wonAward ?award .
  ?award vg:awardName ?awardName .
}}
ORDER BY ?gameName
LIMIT 50

Q: "Franchise con più giochi premiati"
A:
PREFIX vg: <http://www.videogame-ontology.org/ontology#>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
SELECT ?franchise ?franchiseName (COUNT(DISTINCT ?game) AS ?awardedGames) WHERE {{
  ?game rdf:type vg:AwardWinningGame .
  ?game rdf:type vg:FranchiseGame .
  ?game vg:belongsTo ?franchise .
  ?franchise vg:franchiseName ?franchiseName .
}}
GROUP BY ?franchise ?franchiseName
ORDER BY DESC(?awardedGames)
LIMIT 20

Q: "Giochi multiplayer per PlayStation con punteggio alto"
A:
PREFIX vg: <http://www.videogame-ontology.org/ontology#>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
SELECT DISTINCT ?game ?gameName ?score WHERE {{
  ?game rdf:type vg:MultiplayerGame .
  ?game rdf:type vg:PlayStationGame .
  ?game rdf:type vg:HighlyRatedGame .
  ?game vg:gameName ?gameName .
  ?game vg:metacriticScore ?score .
}}
ORDER BY DESC(?score)
LIMIT 50

Q: "Tutti i seguiti di Dark Souls" / "Sequel di Mass Effect"
A:
PREFIX vg: <http://www.videogame-ontology.org/ontology#>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
SELECT DISTINCT ?game ?gameName ?sequel ?sequelName ?releaseDate WHERE {{
  ?game rdf:type vg:VideoGame .
  ?game vg:gameName ?gameName .
  FILTER(CONTAINS(LCASE(str(?gameName)), "mass effect"))
  ?game vg:hasSequel ?sequel .
  ?sequel vg:gameName ?sequelName .
  OPTIONAL {{ ?sequel vg:releaseDate ?releaseDate }}
}}
ORDER BY ?releaseDate
LIMIT 50

Q: "Giochi cooperativi su Nintendo usciti dal 2020"
A:
PREFIX vg: <http://www.videogame-ontology.org/ontology#>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
SELECT DISTINCT ?game ?gameName ?releaseDate WHERE {{
  ?game rdf:type vg:CoopGame .
  ?game rdf:type vg:NintendoGame .
  ?game rdf:type vg:RecentGame .
  ?game vg:gameName ?gameName .
  OPTIONAL {{ ?game vg:releaseDate ?releaseDate }}
}}
ORDER BY DESC(?releaseDate)
LIMIT 50
"""
