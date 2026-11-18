# Ontologia dei Videogiochi — Documentazione Tecnica

## Panoramica

L'ontologia **Video Game Ontology** (`vg:`) modella il dominio dei videogiochi pubblicati dal 2010 in poi. È definita in OWL 2 e serializzata in formato RDF/XML.

- **Namespace:** `http://www.videogame-ontology.org/ontology#`
- **Prefisso:** `vg:`
- **File schema:** `ontology/videogames.owl` (radice che importa i moduli in `ontology/schema/`, vedi sotto)
- **File popolato:** `ontology/output/videogames_full.owl` (generato da `ontology/build_ontology.py`, caricato a runtime) e la copia leggibile `ontology/output/videogames_full.ttl`

---

## Architettura dei file OWL

| File                    | Ruolo                                                                                    | Cancellabile?                                |
| ----------------------- | ---------------------------------------------------------------------------------------- | -------------------------------------------- |
| `videogames.owl`        | **Schema/TBox** — radice con `owl:imports` dei moduli in `schema/`. NON contiene dati.   | ❌ Mai cancellare                            |
| `schema/*.owl`          | Moduli dello schema: `classes` (gerarchia e disgiunzioni), `object-properties`, `data-properties`, `defined-classes`, `individuals` (nominali), `alignments` (Wikidata, Dublin Core), `dl-axioms` (funzionali e chiavi, solo OWL 2 DL). | ❌ Mai cancellare |
| `rules/*.rq`            | Le 23 regole di classificazione e inferenza, una query SPARQL CONSTRUCT per file (ordine = prefisso numerico). | ❌ Mai cancellare |
| `schema/swrl-rules.owl` | 4 regole SWRL (inverso di sequel, sviluppatore condiviso, ConsoleGame, HighlyRatedGame) per un reasoner DL come HermiT. Solo documentazione: importa lo schema ma non è importato, e l'app non le esegue (le stesse inferenze le fanno le regole CONSTRUCT). | ❌ Mai cancellare |
| `catalog-v001.xml`      | Catalogo Protégé: associa l'IRI di ogni modulo al file (apri `videogames.owl` e gli import si risolvono). | ❌ Mai cancellare |
| `output/videogames_full.owl` | **TBox + ABox + inferenze** (RDF/XML) — l'unico file caricato dal backend a runtime.     | ✅ Si rigenera con `build_ontology.py`       |
| `output/videogames_full.ttl` | Stessa ontologia in Turtle, per la lettura umana.                                        | ✅ Si rigenera con `build_ontology.py`       |
| `output/videogames.ttl`, `output/tbox_validation_report.json` | Copia Turtle leggibile dello schema e report di validazione. | ✅ Si rigenerano |
| `scripts/`              | Moduli della pipeline (`populate_wikidata`, `enrich_owl`, `construct_reasoner`, `validate_tbox`, `schema_loader`, `schema_ttl`). | ❌ Mai cancellare |
| `.cache/`               | Checkpoint del fetch (un JSON per query × mese) e stati intermedi della pipeline.        | ✅ Cancellare per rifare il fetch da zero    |

### Workflow di rigenerazione

Si esegue una sola volta, dalla root del repository:

```bash
uv run python ontology/build_ontology.py                      # tutto: fetch → reasoning → validazione → .owl + .ttl
uv run python ontology/build_ontology.py --years 2020-2026    # sottoinsieme di anni
uv run python ontology/build_ontology.py --from-stage reason  # riusa il fetch già fatto
```

Lo script mostra barre `tqdm` per ogni fase. Fasi:

1. **fetch** (`populate_wikidata.py`): carica `videogames.owl` e interroga Wikidata per anno × mese con 11 tipologie di query. Ogni risposta è salvata in `ontology/.cache/wikidata/<tipo>/<anno>-<mese>.json`: se il processo si interrompe, rilanciandolo riparte dai mesi mancanti. Su HTTP 429 (rate limit) attende il tempo indicato da Wikidata e riprova; una query che fallisce definitivamente solleva un errore invece di salvare un mese vuoto. Assegna alle istanze le sottoclassi V2 (es. `PlayStationPlatform`, `RPGGenre`, `SinglePlayerMode`) in base all'etichetta, crea le modalità di gioco come individui `vg:GameMode` e deduplica le entità omonime.
2. **reason**: applica gli assiomi V2 (`enrich_owl.py`), rimuove gli assiomi solo-DL (`strip_dl_only_axioms`), esegue la chiusura **OWL-RL** (`owlrl`), poi la materializzazione mirata di `enrich_owl.py` (classi definite, catene `shared*With`) e infine le regole **SPARQL CONSTRUCT** di `ontology/scripts/construct_reasoner.py` (inverse, classi di piattaforma/modalità, `shared*With`). Gli assiomi solo-DL non vengono ripristinati nell'output salvo `--keep-dl-axioms`.
3. **validate**: controlli sulla TBox (`validate_tbox.py`) e conteggio delle istanze delle classi inferite; le classi vuote sono segnalate con `EMPTY`.
4. **write**: scrive `videogames_full.owl` e `videogames_full.ttl`.

Opzioni: `--cache-dir`, `--output`, `--max-group N` (limite ai gruppi per i link pairwise `shared*With`, evita esplosioni combinatorie), `--keep-dl-axioms`.

`enrich_owl.py` può essere usato anche da solo su un file OWL (idempotente, `--reason` per materializzare, salta `videogames.owl`).

Non vengono più scaricati `gameDescription` e `officialWebsite` (non usati dal sistema) e non esiste più nessuno step di pruning: il backend carica l'ontologia completa.

---

## Classi

La tabella elenca le classi base e le principali classi definite. La TBox include anche le sottoclassi V2 (famiglie di piattaforme come `PlayStationPlatform`/`WindowsPlatform`, generi come `RPGGenre`, modalità `SinglePlayerMode`/`MultiplayerMode`/`CoopMode`/`MMOMode`, `Review`, `GameEvent`, ecc.), descritte nella relazione (`docs/relazione`).

| Classe               | Tipo       | Descrizione                                                             | URI                   |
| -------------------- | ---------- | ----------------------------------------------------------------------- | --------------------- |
| **VideoGame**        | Primitiva  | Un videogioco                                                           | `vg:VideoGame`        |
| **Developer**        | Primitiva  | Uno studio di sviluppo                                                  | `vg:Developer`        |
| **Publisher**        | Primitiva  | Un editore/distributore                                                 | `vg:Publisher`        |
| **Genre**            | Primitiva  | Un genere videoludico (RPG, FPS, ecc.)                                  | `vg:Genre`            |
| **Platform**         | Primitiva  | Una piattaforma di gioco (PS5, PC, Switch, ecc.)                        | `vg:Platform`         |
| **Character**        | Primitiva  | Un personaggio di un videogioco                                         | `vg:Character`        |
| **Franchise**        | Primitiva  | Una serie/franchise (Zelda, Dark Souls, ecc.)                           | `vg:Franchise`        |
| **Award**            | Primitiva  | Un premio assegnato a un gioco                                          | `vg:Award`            |
| **GameEngine**       | Primitiva  | Un motore di gioco (Unreal Engine, Unity, ecc.)                         | `vg:GameEngine`       |
| **GameMode**         | Primitiva  | Una modalità di gioco (individui tipizzati con una sottoclasse `*Mode`) | `vg:GameMode`         |
| **AwardWinningGame** | Definita ¹ | Sottoclasse di VideoGame: giochi che hanno vinto almeno un premio       | `vg:AwardWinningGame` |
| **FranchiseGame**    | Definita ¹ | Sottoclasse di VideoGame: giochi che appartengono a una serie/franchise | `vg:FranchiseGame`    |
| Altre classi definite ¹ | Definita | Per sistema operativo e famiglia di piattaforme, per publisher, per genere, per motore, per paese, premio, multipiattaforma: elenco in §11 | — |

> ¹ **Classi definite** — istanze materializzate dalla pipeline di reasoning (`build_ontology.py`: OWL-RL, `enrich_owl._materialise`, regole CONSTRUCT).
> Nel grafo di visualizzazione appaiono come normali `VideoGame` (stessa icona e colore); sottoclassi di piattaforme, generi e modalità sono ricondotte al tipo base tramite `rdfs:subClassOf`.

---

## Object Properties (relazioni tra entità)

| Proprietà                  | Dominio → Range           | Inversa / Chain             | Caratteristiche                                       |
| -------------------------- | ------------------------- | --------------------------- | ----------------------------------------------------- |
| `vg:developedBy`           | VideoGame → Developer     | `vg:developerOf`            | Asimmetrica, Irriflessiva                             |
| `vg:developerOf`           | Developer → VideoGame     | `vg:developedBy`            | Asimmetrica, Irriflessiva                             |
| `vg:publishedBy`           | VideoGame → Publisher     | `vg:publisherOf`            | Asimmetrica, Irriflessiva                             |
| `vg:publisherOf`           | Publisher → VideoGame     | `vg:publishedBy`            | Asimmetrica, Irriflessiva                             |
| `vg:hasGenre`              | VideoGame → Genre         | `vg:genreOf`                         | Irriflessiva                                          |
| `vg:availableOn`           | VideoGame → Platform      | `vg:platformFor`                         | Irriflessiva                                          |
| `vg:hasCharacter`          | VideoGame → Character     | `vg:appearsIn`              | Asimmetrica, Irriflessiva                             |
| `vg:appearsIn`             | Character → VideoGame     | `vg:hasCharacter`           | Asimmetrica, Irriflessiva                             |
| `vg:belongsTo`             | VideoGame → Franchise     | `vg:includes`               | Asimmetrica, Irriflessiva                             |
| `vg:includes`              | Franchise → VideoGame     | `vg:belongsTo`              | Asimmetrica, Irriflessiva                             |
| `vg:wonAward`              | VideoGame → Award         | `vg:awardWonBy`                         | Irriflessiva                                          |
| `vg:sequelOf`              | VideoGame → VideoGame     | `vg:hasSequel`              | Transitiva, Asimmetrica, Irriflessiva                           |
| `vg:madeWith`              | VideoGame → GameEngine    | `vg:engineUsedIn`                         | Irriflessiva                                          |
| `vg:hasGameMode`           | VideoGame → GameMode      | `vg:modeInGame`             | Irriflessiva (individui `GameMode`, non stringhe)     |
| `vg:sameCompanyAs`         | Developer ↔ Publisher     | —                           | Simmetrica (3.360 aziende, 6.720 triple)              |
| `vg:sharedFranchiseWith` ² | VideoGame ↔ VideoGame     | `belongsTo ∘ includes`      | Simmetrica, property chain inferita                   |
| `vg:sharesDeveloperWith` ² | VideoGame ↔ VideoGame     | `developedBy ∘ developerOf` | Simmetrica, property chain inferita                   |
| `vg:sharesPublisherWith` ² | VideoGame ↔ VideoGame     | `publishedBy ∘ publisherOf` | Simmetrica, property chain inferita                   |

> ² **Proprietà inferite** — triple materializzate dalla pipeline di reasoning. (`sharedGenreWith` e `sharedEngineWith` esistono come regole CONSTRUCT ma non sono eseguite sul dataset completo: il numero di coppie cresce col quadrato dei giochi per genere o motore).
> Permettono query dirette senza join espliciti (es. "tutti i giochi della stessa serie").

---

## Data Properties (attributi)

| Proprietà            | Dominio    | Range       | Funzionale? | Note                             |
| -------------------- | ---------- | ----------- | ----------- | -------------------------------- |
| `vg:gameName`        | VideoGame  | xsd:string  | ✅          | Nome del gioco                   |
| `vg:releaseDate`     | VideoGame  | xsd:date    | ❌          | Formato "YYYY-MM-DD"             |
| `vg:metacriticScore` | VideoGame  | xsd:integer | ❌          | Punteggio 0–100                  |
| `vg:countryOfOrigin` | VideoGame  | xsd:string  | ❌          | Paese di produzione              |
| `vg:developerName`   | Developer  | xsd:string  | ✅          | Nome dello studio                |
| `vg:publisherName`   | Publisher  | xsd:string  | ✅          | Nome dell'editore                |
| `vg:genreName`       | Genre      | xsd:string  | ✅          | Nome del genere                  |
| `vg:platformName`    | Platform   | xsd:string  | ✅          | Nome della piattaforma           |
| `vg:characterName`   | Character  | xsd:string  | ✅          | Nome del personaggio             |
| `vg:franchiseName`   | Franchise  | xsd:string  | ✅          | Nome della serie                 |
| `vg:awardName`       | Award      | xsd:string  | ✅          | Nome del premio                  |
| `vg:awardYear`       | Award      | xsd:integer | ❌          | Anno di assegnazione             |
| `vg:engineName`      | GameEngine | xsd:string  | ✅          | Nome del motore                  |

> **Nota:** `vg:gameDescription` e `vg:officialWebsite` esistono nello schema ma non vengono popolati dalla pipeline, perché il sistema non li usa (l'agente SPARQL non li interroga e il frontend non li visualizza).

Tutte le proprietà `*Name` sono sotto-proprietà di `vg:name` (xsd:string).

---

## Schema delle URI

Le URI delle istanze seguono questo pattern:

```text
http://www.videogame-ontology.org/ontology#<NomeGioco>          → VideoGame
http://www.videogame-ontology.org/ontology#dev/<NomeStudio>     → Developer
http://www.videogame-ontology.org/ontology#pub/<NomeEditore>    → Publisher
http://www.videogame-ontology.org/ontology#genre/<NomeGenere>   → Genre
http://www.videogame-ontology.org/ontology#platform/<NomePlatf> → Platform
http://www.videogame-ontology.org/ontology#char/<NomePersonaggio> → Character
http://www.videogame-ontology.org/ontology#franchise/<NomeSerie>  → Franchise
http://www.videogame-ontology.org/ontology#award/<NomePremio>   → Award
http://www.videogame-ontology.org/ontology#engine/<NomeMotore>  → GameEngine
```

I nomi vengono "sanitizzati": spazi → `_`, rimozione di apostrofi/virgolette, solo caratteri alfanumerici + `_-.`.

---

## Fonte dati: Wikidata

I dati vengono recuperati dal SPARQL endpoint pubblico di Wikidata (`https://query.wikidata.org/sparql`).

### Proprietà Wikidata utilizzate

| Step | Dato                                       | Proprietà Wikidata                     |
| ---- | ------------------------------------------ | -------------------------------------- |
| 1    | Nome, data di uscita, developer, publisher | P577, P178, P123                       |
| 2    | Genere                                     | P136                                   |
| 3    | Piattaforme                                | P400                                   |
| 4    | Personaggi                                 | P674                                   |
| 5    | Franchise/serie                            | P179                                   |
| 6    | Modalità di gioco                          | P404                                   |
| 7    | Punteggio Metacritic                       | P444 + P447 (qualificatore Metacritic) |
| 8    | Motore di gioco                            | P408                                   |
| 9    | Paese d'origine                            | P495                                   |
| 10   | Premi                                      | P166                                   |
| 11   | Sequel (`sequelOf`)                        | P155                                   |

### Filtro temporale

Tutti i giochi vengono filtrati con:

```sparql
FILTER(YEAR(?releaseDate) >= 2010 && YEAR(?releaseDate) <= 2026)
```

### Deduplicazione

- Lo script usa un set `games_seen` per evitare di aggiungere entità per giochi non presenti nella query iniziale
- `rdflib` deduplica automaticamente triple identiche (set semantics)
- Il backend aggiunge ulteriore deduplicazione lato `execute_sparql()` sui risultati delle query

---

## Scelte implementative

### 1. OWL 2 DL

L'ontologia è in OWL 2 DL (Description Logic), il che permette:

- Ragionamento automatico (inversi, asimmetria)
- Validazione dei tipi (domain/range constraints)
- Compatibilità con tool standard (Protégé, reasoner)

### 2. pyoxigraph come motore RDF a runtime

Il backend usa **pyoxigraph** (binding Python di Oxigraph, scritto in Rust) anziché rdflib per:

- **Footprint ridotto**: store in Rust, molto più leggero di un grafo rdflib in memoria
- **Caricamento e query SPARQL** molto più rapidi
- **Parsing nativo** di RDF/XML, Turtle, N-Triples
- Totale compatibilità SPARQL 1.1

Il reasoning viene eseguito offline da `build_ontology.py` (owlrl + materializzazione mirata + regole CONSTRUCT), e le triple inferite sono già nel file OWL caricato a runtime. Nota: rdflib resta usato solo dalla pipeline offline.

### 3. Nessun pruning

Il backend carica l'ontologia completa e materializzata (`videogames_full.owl`): non ci sono più i sottoinsiemi `pruned` / `pruned_2020` né step di rimozione di triple. L'unica scelta di contenuto è non scaricare `gameDescription` e `officialWebsite`.

### 4. Proprietà Funzionali per i nomi

Le proprietà `*Name` sono dichiarate `owl:FunctionalProperty`: ogni entità ha un solo nome canonico. Questo evita ambiguità nella visualizzazione del grafo.

### 5. Proprietà Inverse

Le coppie `developedBy/developerOf`, `publishedBy/publisherOf`, `hasCharacter/appearsIn`, `belongsTo/includes` permettono di navigare il grafo in entrambe le direzioni senza dover eseguire query specifiche.

### 6. Asimmetria e Irriflessività

Tutte le relazioni sono marcate come irriflessive (un gioco non può essere sviluppato da sé stesso) e dove appropriato asimmetriche (se A è sviluppato da B, B non è sviluppato da A).

### 7. Immagini da Wikipedia + emoji placeholder

- **Sorgente:** API Wikipedia (`/api/image-search?name=...`) che cerca la thumbnail della pagina Wikipedia del gioco (prima il titolo esatto, poi con il suffisso "(video game)")
- **Placeholder:** Se nessuna immagine viene trovata, nel grafo viene mostrato un emoji casuale ma deterministico (basato su hash del nome del gioco)

Le immagini trovate sono salvate nella cache SQLite locale (`backend/cache.db`); i risultati null non vengono cachati, così si può riprovare.

### 8. Separazione TBox/ABox

Lo schema (`videogames.owl`) è separato dai dati. Il file `videogames_full.owl` include entrambi per semplicità di caricamento runtime, ma lo schema resta la "source of truth" per la struttura.

### 9. URI deterministiche

Le URI sono generate deterministicamente dal nome dell'entità (via `make_uri()`). Questo garantisce che:

- Lo stesso developer/genere/piattaforma venga riconosciuto come la stessa entità anche se appare in query diverse
- Non servano meccanismi di reconciliation complessi

### 10. Game Mode come individui

`hasGameMode` ha range `vg:GameMode`: ogni modalità (es. "single-player video game") è un individuo `vg:mode/<nome>` tipizzato con `GameMode` e, in base all'etichetta, con `SinglePlayerMode`, `MultiplayerMode`, `CoopMode` o `MMOMode`. Questo permette di inferire `SinglePlayerGame`, `MultiplayerGame` e `CoopGame`. Il nome leggibile è in `rdfs:label`.

### 11. Classi definite e proprietà inferite

L'ontologia include 50 classi **definite** (OWL 2 `equivalentClass` + `intersectionOf` con una restrizione), tutte non vuote sulla build completa:

- **Modalità**: `SinglePlayerGame`, `MultiplayerGame`, `CoopGame`
- **Piattaforma**: `PCGame`, `ConsoleGame`, `MobileGame`, `NintendoGame`, `PlayStationGame`, `XboxGame`; per sistema operativo `WindowsGame`, `MacOSGame`, `LinuxGame`, `AndroidGame`; per altre famiglie `BrowserGame`, `ArcadeGame`, `RetroComputerGame`, `VRGame`
- **Genere** (un genere può appartenere a più famiglie): `ActionGame`, `RPGGame`, `StrategyGame`, `SimulationGame`, `AdventureGame`, `SportsGame`, `RacingGame`, `PuzzleGame`, `HorrorGame`, `PlatformerGame`, `ShooterGame`, `CasualGame`, `VisualNovelGame`
- **Publisher** (nominali, `publishedBy value <publisher>`): `NintendoPublishedGame`, `SonyPublishedGame`, `XboxPublishedGame`, `BandaiNamcoPublishedGame`, `SquareEnixPublishedGame`, `ElectronicArtsPublishedGame`, `KonamiPublishedGame`, `CapcomPublishedGame`; ogni publisher è un individuo dichiarato nello schema con lo stesso URI generato dal fetch
- **Paese** (valore letterale): `JapaneseGame`, `AmericanGame`
- **Altro**: `AwardWinningGame`, `GOTYWinner` (vincitore di un premio `GameOfTheYearAward`: il Game of the Year di The Game Awards dal 2014 e, per il 2010-2013, quello degli Spike Video Game Awards; non le categorie né i GOTY di altri enti), `FranchiseGame`, `UnrealEngineGame` (motore di tipo `UnrealEngineFamily`), `HighlyRatedGame` (`metacriticScore ≥ 85`), `RecentGame` (`releaseDate ≥ 2020-01-01`), `SequelGame`, `StandaloneGame`
- **Cardinalità qualificata** (regola CONSTRUCT): `MultiConsoleGame` (`≥2 availableOn.ConsolePlatform`), `MultiPlatformGame` (`≥3 availableOn.Platform`)

Le istanze di piattaforme, generi, motori e premi ricevono le sottoclassi (`WindowsPlatform`, `RPGGenre`, `UnrealEngineFamily`, `GameOfTheYearAward`...) in base all'etichetta durante il fetch: la tipizzazione è in `populate_wikidata.py`, i game class sono poi inferiti da `owlrl` e dalle regole CONSTRUCT.

Proprietà con **catene di composizione** (`owl:propertyChainAxiom`) simmetriche: `sharedFranchiseWith` (`belongsTo ∘ includes`), `sharesDeveloperWith`, `sharesPublisherWith`.

Gli assiomi stanno in `videogames.owl`; le inferenze sono materializzate da `build_ontology.py` (OWL-RL + materializzazione mirata + regole CONSTRUCT). Nel frontend le classi definite dei giochi sono normalizzate a `VideoGame` per la visualizzazione, mantenendo tutta la semantica per le query SPARQL.

### 12. Cache a due livelli

- **SQLite locale** (`backend/cache.db`, persistente):
  - TTL **14 giorni** per i risultati delle query in linguaggio naturale (`vg:query:*`, invalidati quando l'ontologia viene rigenerata)
  - TTL **6 mesi** per le immagini cercate via Wikipedia API (`img:*`)
- **In-memory** (Python dict): per label e tipi RDF derivati dallo store (non persistono al riavvio)

Questa architettura evita chiamate HTTP ripetitive mantenendo bassa la RAM.

---

## Diagramma delle relazioni

```text
                        ┌──────────────┐
                        │  GameEngine  │
                        └──────┬───────┘
                               │ madeWith
                               ▼
┌───────────┐  developedBy  ┌──────────────┐  hasGenre    ┌─────────┐
│ Developer │◄──────────────│  VideoGame   │─────────────►│  Genre  │
└───────────┘               │              │              └─────────┘
                            │  gameName    │
┌───────────┐  publishedBy  │  releaseDate │  availableOn  ┌──────────┐
│ Publisher │◄──────────────│  metacritic  │──────────────►│ Platform │
└───────────┘               │  imageUrl    │              └──────────┘
                            │  country     │
┌───────────┐  belongsTo    │              │  hasCharacter ┌───────────┐
│ Franchise │◄──────────────│              │──────────────►│ Character │
└───────────┘               └──────┬───────┘              └───────────┘
                                   │
                            wonAward│  sequelOf
                                   ▼         ▼
                            ┌─────────┐  ┌──────────────┐
                            │  Award  │  │  VideoGame   │
                            └─────────┘  └──────────────┘
```

---

## Statistiche (build completa 2010–2026)

| Metrica                               | Valore             |
| ------------------------------------- | ------------------ |
| Triple scaricate da Wikidata          | 945.767            |
| Triple nel file finale                | 4.746.848          |
| Videogiochi                           | 107.522            |
| Sviluppatori / Publisher              | 5.945 / 4.158      |
| Generi / Piattaforme                  | 605 / 311          |
| Franchise / Motori / Personaggi / Premi | 1.840 / 344 / 4.884 / 448 |
| Modalità di gioco (individui)         | 40                 |

Istanze delle 50 classi definite (tutte non vuote): `StandaloneGame` 106.926, `PCGame` 100.336, `WindowsGame` 100.099, `SinglePlayerGame` 95.723, `RecentGame` 71.548, `ActionGame` 32.828, `CasualGame` 32.634, `AdventureGame` 30.568, `MacOSGame` 20.126, `MultiPlatformGame` 19.138, `MultiplayerGame` 17.142, `SimulationGame` 16.444, `StrategyGame` 15.386, `LinuxGame` 14.767, `RPGGame` 14.622, `ConsoleGame` 13.885, `CoopGame` 9.079, `NintendoGame` 8.853, `PlayStationGame` 8.546, `MultiConsoleGame` 7.703, `FranchiseGame` 5.646, `XboxGame` 5.623, `MobileGame` 5.253, `JapaneseGame` 4.089, `AndroidGame` 3.941, `SportsGame` 3.399, `RacingGame` 3.365, `AmericanGame` 3.085, `VisualNovelGame` 2.368, `ShooterGame` 1.971, `PuzzleGame` 1.839, `UnrealEngineGame` 1.783, `PlatformerGame` 1.429, `AwardWinningGame` 931, `HorrorGame` 862, `BrowserGame` 737, `SequelGame` 596, `NintendoPublishedGame` 409, `BandaiNamcoPublishedGame` 342, `ArcadeGame` 267, `SquareEnixPublishedGame` 243, `SonyPublishedGame` 242, `ElectronicArtsPublishedGame` 202, `XboxPublishedGame` 186, `RetroComputerGame` 177, `KonamiPublishedGame` 166, `CapcomPublishedGame` 119, `HighlyRatedGame` 107, `VRGame` 60, `GOTYWinner` 16.

Il reasoning sulla build completa: `owlrl` aggiunge 5,18 milioni di triple a circa 946.000 in circa 45 minuti (la pulizia successiva toglie i nodi `ErrorMessage`, 255.048 triple riflessive e 1,33 milioni di triple con nodi anonimi, sostituiti dallo schema originale), la materializzazione mirata aggiunge 178.581 triple, le regole CONSTRUCT 26.841. La fusione dei duplicati avviene solo tra entità dello stesso tipo (confronto per nome, senza maiuscole, spazi multipli e `&`; per sviluppatori e publisher anche senza punteggiatura e forma legale: «Netflix, Inc.» = «Netflix»), e i giochi fusi per titolo (remake, porting) tengono una sola data di uscita (la più antica), un solo punteggio (il più alto) e un solo nome, così le proprietà funzionali non hanno più valori multipli (prima 311 date, 90 punteggi e 99 nomi doppi). I 10.232 giochi sviluppati e pubblicati dalla stessa azienda si riconoscono dal collegamento `sameCompanyAs`. così un gioco e il franchise omonimo restano individui distinti. Le relazioni `sharesDeveloperWith` / `sharesPublisherWith` escludono i gruppi con più di 50 giochi (23 sviluppatori, 77 publisher). Lo stesso riepilogo, per le classi principali, è disponibile a runtime su `GET /api/stats`.
