# Ontologia dei Videogiochi — Documentazione Tecnica

## Panoramica

L'ontologia **Video Game Ontology** (`vg:`) modella il dominio dei videogiochi pubblicati dal 2010 in poi. È definita in OWL 2 e serializzata in formato RDF/XML.

- **Namespace:** `http://www.videogame-ontology.org/ontology#`
- **Prefisso:** `vg:`
- **File schema:** `ontology/videogames.owl`
- **File popolato:** `ontology/videogames_wikidata.owl` (generato dallo script di popolazione)
- **File pruned:** `ontology/videogames_pruned.owl` (generato da `prune_owl.py`, usato a runtime)

---

## Architettura dei file OWL

| File                         | Ruolo                                                                                                           | Cancellabile?                                        |
| ---------------------------- | --------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------- |
| `videogames.owl`             | **Schema/TBox** — definisce classi, proprietà e assiomi. NON contiene dati.                                     | ❌ Mai cancellare                                    |
| `videogames_wikidata.owl`    | **Dati/ABox completo** — schema + tutte le istanze (~1.427.081 triple)                                          | ✅ Si cancella e rigenera con `populate_wikidata.py` |
| `videogames_pruned.owl`      | **Dati/ABox ottimizzato** — come sopra ma senza triple inutili (~1.173.959 triple, 2010–2026)                   | ✅ Si cancella e rigenera con `prune_owl.py`         |
| `videogames_pruned_2020.owl` | **Dati/ABox demo** — solo giochi dal 2020 in poi (~745.400 triple, ~68.700 giochi). Usato nella demo su Render. | ✅ Si cancella e rigenera con `prune_years.py`       |

### Workflow di rigenerazione

```bash
cd ontology/

# 1. Popolazione (~5 ore, richiede connessione internet)
uv run python populate_wikidata.py

# 2. Pruning predicati (pochi minuti, rimuove triple inutili a runtime)
uv run python prune_owl.py

# 3. Pruning temporale (per la demo, rimuove giochi 2010-2019)
uv run python prune_years.py

# 4. Arricchimento ontologia con classi/proprietà inferite (opzionale)
#    Aggiunge assiomi OWL avanzati. Con --reason materializza le triple inferite.
uv run python enrich_owl.py videogames_pruned_2020.owl
uv run python enrich_owl.py --reason videogames_pruned_2020.owl
```

Lo script di popolazione:

1. Carica `videogames.owl` (schema)
2. Interroga Wikidata con 13 query SPARQL (per anno × mese)
3. Applica OWL-RL reasoning con `owlrl` (materializza proprietà inverse)
4. Produce `videogames_wikidata.owl` (schema + dati, ~1.4M triple)

Lo script di pruning predicati (`prune_owl.py`):

1. Carica `videogames_wikidata.owl`
2. Rimuove triple `owl:sameAs` (tutte riflessive, A sameAs A)
3. Rimuove `vg:gameDescription` (non usato a runtime)
4. Rimuove `vg:officialWebsite` (non usato a runtime)
5. Produce `videogames_pruned.owl` (~1.17M triple, -253k)

Lo script di pruning temporale (`prune_years.py`):

1. Carica `videogames_pruned.owl`
2. Rimuove tutti i giochi con `releaseDate` dal 2010 al 2019
3. Rimuove le entità orfane (developer, publisher, ecc. non più collegati a nessun gioco)
4. Produce `videogames_pruned_2020.owl` (~745k triple, -429k)

Lo script di arricchimento (`enrich_owl.py`):

1. Aggiunge classi definite e proprietà con catene inferenziali a qualsiasi file OWL
2. È idempotente (non duplica assiomi già presenti)
3. Con `--reason` materializza le triple inferite tramite un materializzatore mirato
   (molto più veloce dell'OWL-RL completo: applica solo le 5 regole necessarie)
4. Salta automaticamente `videogames.owl` (TBox pura, nessun dato)
5. `--max-group N` limita i gruppi per evitare esplosione combinatoria

Il backend (demo) carica a runtime `videogames_pruned_2020.owl` (con fallback a `videogames_wikidata.owl` → `videogames.owl`).

---

## Classi (11)

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
| **AwardWinningGame** | Definita ¹ | Sottoclasse di VideoGame: giochi che hanno vinto almeno un premio       | `vg:AwardWinningGame` |
| **FranchiseGame**    | Definita ¹ | Sottoclasse di VideoGame: giochi che appartengono a una serie/franchise | `vg:FranchiseGame`    |

> ¹ **Classi definite** — istanze materializzate tramite OWL-RL reasoning (`enrich_owl.py --reason`).
> Nel grafo di visualizzazione appaiono come normali `VideoGame` (stessa icona e colore).

---

## Object Properties (relazioni tra entità)

| Proprietà                  | Dominio → Range           | Inversa / Chain             | Caratteristiche                                       |
| -------------------------- | ------------------------- | --------------------------- | ----------------------------------------------------- |
| `vg:developedBy`           | VideoGame → Developer     | `vg:developerOf`            | Asimmetrica, Irriflessiva                             |
| `vg:developerOf`           | Developer → VideoGame     | `vg:developedBy`            | Asimmetrica, Irriflessiva                             |
| `vg:publishedBy`           | VideoGame → Publisher     | `vg:publisherOf`            | Asimmetrica, Irriflessiva                             |
| `vg:publisherOf`           | Publisher → VideoGame     | `vg:publishedBy`            | Asimmetrica, Irriflessiva                             |
| `vg:hasGenre`              | VideoGame → Genre         | —                           | Irriflessiva                                          |
| `vg:availableOn`           | VideoGame → Platform      | —                           | Irriflessiva                                          |
| `vg:hasCharacter`          | VideoGame → Character     | `vg:appearsIn`              | Asimmetrica, Irriflessiva                             |
| `vg:appearsIn`             | Character → VideoGame     | `vg:hasCharacter`           | Asimmetrica, Irriflessiva                             |
| `vg:belongsTo`             | VideoGame → Franchise     | `vg:includes`               | Asimmetrica, Irriflessiva                             |
| `vg:includes`              | Franchise → VideoGame     | `vg:belongsTo`              | Asimmetrica, Irriflessiva                             |
| `vg:wonAward`              | VideoGame → Award         | —                           | Irriflessiva                                          |
| `vg:sequelOf`              | VideoGame → VideoGame     | —                           | Asimmetrica, Irriflessiva                             |
| `vg:madeWith`              | VideoGame → GameEngine    | —                           | Irriflessiva                                          |
| `vg:hasGameMode`           | VideoGame → rdfs:Resource | —                           | Irriflessiva (valore letterale, e.g. "single-player") |
| `vg:sharedFranchiseWith` ² | VideoGame ↔ VideoGame     | `belongsTo ∘ includes`      | Simmetrica, property chain inferita                   |
| `vg:sharesDeveloperWith` ² | VideoGame ↔ VideoGame     | `developedBy ∘ developerOf` | Simmetrica, property chain inferita                   |
| `vg:sharesPublisherWith` ² | VideoGame ↔ VideoGame     | `publishedBy ∘ publisherOf` | Simmetrica, property chain inferita                   |

> ² **Proprietà inferite** — triple materializzate tramite `enrich_owl.py --reason`.
> Permettono query dirette senza join espliciti (es. "tutti i giochi della stessa serie").

---

## Data Properties (attributi)

| Proprietà            | Dominio    | Range       | Funzionale? | Note                             |
| -------------------- | ---------- | ----------- | ----------- | -------------------------------- |
| `vg:gameName`        | VideoGame  | xsd:string  | ✅          | Nome del gioco                   |
| `vg:releaseDate`     | VideoGame  | xsd:date    | ❌          | Formato "YYYY-MM-DD"             |
| `vg:metacriticScore` | VideoGame  | xsd:integer | ❌          | Punteggio 0–100                  |
| `vg:imageUrl`        | VideoGame  | xsd:anyURI  | ❌          | URL immagine (Wikimedia Commons) |
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

> **Nota:** `vg:gameDescription` e `vg:officialWebsite` esistono nello schema ma vengono rimossi durante il pruning perché non utilizzati a runtime (l'agente SPARQL non li interroga e il frontend non li visualizza).

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
| 8    | Immagine                                   | P18                                    |
| 9    | Motore di gioco                            | P408                                   |
| 10   | Paese d'origine                            | P495                                   |
| 11   | Sito web ufficiale                         | P856                                   |
| 12   | Premi                                      | P166                                   |
| 13   | Descrizione                                | schema:description                     |

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

- **RAM**: ~389 MB vs ~1.550 MB con rdflib (-75%)
- **Caricamento**: ~2.2s vs ~41s (-95%)
- **Query SPARQL**: 5–62× più veloci (0.08–0.37s vs 1–23s)
- **Parsing nativo** di RDF/XML, Turtle, N-Triples
- Totale compatibilità SPARQL 1.1

Il reasoning OWL-RL viene comunque eseguito offline con `owlrl` (libreria Python) durante la fase di popolazione, e le triple materializzate sono già nel file OWL caricato a runtime.

### 3. Pruning delle triple

Il file `videogames_pruned.owl` (~1.17M triple) è derivato dal file completo (~1.43M triple) rimuovendo:

- **`owl:sameAs`**: 116.820 triple, tutte riflessive (A sameAs A). Zero non-riflessive trovate, nessun rischio di perdita di informazione.
- **`vg:gameDescription`**: non visualizzato nel frontend né interrogato dall'agente SPARQL
- **`vg:officialWebsite`**: idem

Questo riduce la RAM di ~1.16 GB e velocizza il parsing senza perdere funzionalità.

### 4. Proprietà Funzionali per i nomi

Le proprietà `*Name` sono dichiarate `owl:FunctionalProperty`: ogni entità ha un solo nome canonico. Questo evita ambiguità nella visualizzazione del grafo.

### 5. Proprietà Inverse

Le coppie `developedBy/developerOf`, `publishedBy/publisherOf`, `hasCharacter/appearsIn`, `belongsTo/includes` permettono di navigare il grafo in entrambe le direzioni senza dover eseguire query specifiche.

### 6. Asimmetria e Irriflessività

Tutte le relazioni sono marcate come irriflessive (un gioco non può essere sviluppato da sé stesso) e dove appropriato asimmetriche (se A è sviluppato da B, B non è sviluppato da A).

### 7. Immagini con fallback + emoji placeholder

- **Primario:** URL da Wikidata (proprietà P18, Wikimedia Commons)
- **Fallback:** API Wikipedia (`/api/image-search?name=...`) che cerca la thumbnail della pagina Wikipedia del gioco
- **Placeholder:** Se nessuna immagine viene trovata, nel grafo viene mostrato un emoji casuale ma deterministico (basato su hash del nome del gioco) come placeholder visivo

I risultati null vengono cachati lato frontend per evitare richieste ripetute ad ogni render.

### 8. Separazione TBox/ABox

Lo schema (`videogames.owl`) è separato dai dati. Il file popolato include entrambi per semplicità di caricamento runtime, ma lo schema resta la "source of truth" per la struttura.

### 9. URI deterministiche

Le URI sono generate deterministicamente dal nome dell'entità (via `make_uri()`). Questo garantisce che:

- Lo stesso developer/genere/piattaforma venga riconosciuto come la stessa entità anche se appare in query diverse
- Non servano meccanismi di reconciliation complessi

### 10. Game Mode come letterale

`hasGameMode` usa un valore letterale (stringa) e non una classe dedicata, perché le modalità di gioco sono poche e non necessitano di proprietà aggiuntive.

### 11. Classi definite e proprietà inferite

L'ontologia include due **classi definite** (OWL 2 `equivalentClass` + `someValuesFrom`):

- `vg:AwardWinningGame` ≡ `VideoGame ⊓ (wonAward some Award)` — ogni gioco che ha vinto almeno un premio
- `vg:FranchiseGame` ≡ `VideoGame ⊓ (belongsTo some Franchise)` — ogni gioco che appartiene a una serie

E tre **proprietà con catene di composizione** (`owl:propertyChainAxiom`):

- `vg:sharedFranchiseWith` ← `belongsTo ∘ includes` (simmetrica)
- `vg:sharesDeveloperWith` ← `developedBy ∘ developerOf` (simmetrica)
- `vg:sharesPublisherWith` ← `publishedBy ∘ publisherOf` (simmetrica)

Queste strutture sono aggiunte agli ABox tramite `enrich_owl.py`. Il materializzatore mirato integrato nello script (`--reason`) applica solo le 5 regole necessarie anziché l'intera chiusura OWL-RL, riducendo drasticamente i tempi di esecuzione.

Nel frontend, `AwardWinningGame` e `FranchiseGame` vengono normalizzati a `VideoGame` per la visualizzazione (stessa icona, stesso colore), mantenendo tutta la semantica per le query SPARQL.

### 12. Cache a due livelli

- **Upstash Redis** (cloud, persistente):
  - TTL **14 giorni** per i risultati delle query SPARQL (`vg:query:*`)
  - TTL **6 mesi** per le immagini cercate via Wikipedia API (`img:*`)
- **In-memory** (Python dict): per label e tipi RDF derivati dallo store (derivati dal grafo caricato, non persistono al riavvio)

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

## Statistiche (dopo popolazione + reasoning + pruning + enrichment)

| Metrica                         | Completo (2010–2026) | Demo (2020–2026) |
| ------------------------------- | -------------------- | ---------------- |
| Giochi totali                   | ~104.000             | ~68.700          |
| Triple totali (dopo enrich_owl) | ~1.542.496           | ~885.218         |
| Triple inferite da enrich_owl   | +368.478             | +139.759         |
| Developer                       | ~13.000              | ~12.000          |
| Publisher                       | ~7.000               | ~5.500           |
| Generi                          | ~350                 | ~200             |
| Piattaforme                     | ~180                 | ~180             |
| Personaggi                      | ~7.000               | ~4.600           |
| Franchise                       | ~4.500               | ~4.000           |
| Awards                          | ~1.800               | ~1.670           |
| Game Engine                     | ~500                 | ~350             |
| RAM a runtime (pyoxigraph)      | ~389 MB              | ~250 MB          |
| Tempo di caricamento            | ~2.2s                | ~1.5s            |

> **Nota:** La demo live su Render usa il dataset 2020–2026 per rientrare nel limite RAM di 512 MB del piano gratuito. Il dataset completo è generabile localmente.
>
> Le triple inferite da `enrich_owl --reason` (classi `AwardWinningGame`/`FranchiseGame` e proprietà `shared*With`) non sono incluse nel conteggio sopra: vengono materializzate separatamente e aumentano significativamente la dimensione del file.
