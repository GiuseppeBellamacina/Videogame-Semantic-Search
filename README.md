# Videogame Semantic Search

![Videogame Semantic Search](assets/videogame-semantic.webp)

Un progetto di Semantic Web che costruisce e interroga un'ontologia OWL sui videogiochi (dal 2010 ad oggi) tramite un'interfaccia web moderna con grafo di conoscenza interattivo.

## Ontologia

L'ontologia (TBox in `ontology/videogames.owl`, descritta nella relazione in `docs/relazione`) viene popolata con i dati di Wikidata dal 2010 ad oggi e arricchita da una pipeline di reasoning in un unico script: `ontology/build_ontology.py`. L'output è `ontology/videogames_full.owl` (caricato dal backend) e `ontology/videogames_full.ttl` (stessa ontologia in Turtle, più leggibile).

Il fetch interroga Wikidata per anno × mese (per evitare i timeout) con checkpoint su disco: se si interrompe, rilanciando lo script riparte dai mesi già scaricati. Non vengono scaricati `gameDescription` e `officialWebsite`, che il sistema non usa.

## Architettura

```text
┌─────────────────────────────────────────────────────────────────┐
│         Frontend (React + Tailwind + react-force-graph)         │
│  ┌──────────┐  ┌──────────────┐  ┌───────────────────────────┐  │
│  │ SearchBar│  │  ResultList  │  │   Knowledge Graph (2D)    │  │
│  └──────────┘  └──────────────┘  └───────────────────────────┘  │
└──────────────────────────────┬──────────────────────────────────┘
                               │ HTTP (REST API)
┌──────────────────────────────▼──────────────────────────────────┐
│                        Backend (FastAPI)                        │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │                 SPARQL Agent (OpenAI / Anthropic)                │ │
│  │              NL → SPARQL → Validate → Execute              │ │
│  │        (retry automatico su errore, max 3 tentativi)       │ │
│  └────────────────────────────────────────────────────────────┘ │
│  ┌─────────────────────┐  ┌───────────────────────────────────┐ │
│  │   OntologyService   │  │          GraphBuilder             │ │
│  │    (pyoxigraph)     │  │    (nodi + archi per frontend)    │ │
│  └─────────────────────┘  └───────────────────────────────────┘ │
│  ┌─────────────────────┐  ┌───────────────────────────────────┐ │
│  │  SQLite (locale)    │  │     Wikipedia Image API           │ │
│  │  (cache persistente)│  │  (copertine, salvate in locale)   │ │
│  └─────────────────────┘  └───────────────────────────────────┘ │
└──────────────────────────────┬──────────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────────┐
│  Ontologia (videogames_full.owl / .ttl)                         │
│  Store: pyoxigraph (Rust) · reasoning materializzato            │
│  Classi: VideoGame, Developer, Publisher, Genre, Platform,      │
│          Character, Franchise, Award, GameEngine                │
└─────────────────────────────────────────────────────────────────┘
```

## Requisiti

- Python 3.12+ (gestito da uv)
- [uv](https://docs.astral.sh/uv/) (package manager Python)
- Node.js 18+ / [Bun](https://bun.sh)
- Chiave API OpenAI e/o Anthropic (a seconda di `LLM_MODEL`)

## Setup

### 1. Clona e posizionati

```bash
cd Videogame-Semantic-Search
```

### 2. Installa dipendenze Python (con uv)

```bash
uv sync
```

### 3. Costruisci l'ontologia (una volta sola)

```bash
uv run python ontology/build_ontology.py
```

Esegue in sequenza, con barre di avanzamento: fetch da Wikidata (checkpoint per mese in `ontology/.cache/`), assiomi V2, chiusura OWL-RL, materializzazione, regole CONSTRUCT, validazione e scrittura di `videogames_full.owl` e `videogames_full.ttl`. Il fetch richiede alcune ore. Opzioni utili: `--years 2020-2026` (sottoinsieme), `--from-stage reason` (riusa il fetch già fatto).

> Wikidata può rispondere con HTTP 429 (rate limit): lo script attende il tempo indicato e riprova da solo.

### 4. Configura variabili d'ambiente

Crea un file `.env` nella root del progetto:

```env
LLM_MODEL=openai:gpt-4.1-mini        # oppure anthropic:haiku5.5
OPENAI_API_KEY=sk-...                # se usi openai:
ANTHROPIC_API_KEY=sk-ant-...         # se usi anthropic:
```

### 5. Avvia il backend

```bash
uv run uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

### 6. Frontend

```bash
cd frontend
bun install
bun run dev
```

L'app sarà disponibile su [http://localhost:5173](http://localhost:5173)

## Funzionalità

### Ricerca in linguaggio naturale

Scrivi domande come:

- "Quali giochi ha sviluppato FromSoftware?"
- "Top 10 giochi con il Metacritic più alto"
- "Giochi RPG usciti nel 2023"
- "Giochi della serie Zelda disponibili su Switch"

### Grafo di conoscenza interattivo

- **Nodi colorati** per tipo (gioco, developer, genere, etc.)
- **VideoGame come rettangoli portrait** con immagine di copertina o emoji placeholder
- **Animazione physics-based** con forze e repulsione
- **Click su nodo** → pannello dettaglio con tutte le proprietà e relazioni
- **Click destro** → menu contestuale per espandere il grafo o rimuovere nodi
- **Filtro per tipo** nella legenda — click per nascondere/mostrare categorie
- **Hover** → evidenzia connessioni dirette (nodo in primo piano con z-order)
- **Zoom/pan** per esplorare il grafo
- **Recentra** button per zoom-to-fit
- **Sidebar** → click su relazione espande il nodo nel grafo

### Autosuggest e query builder

- **Autosuggest** mentre scrivi: giochi, sviluppatori, publisher, generi, piattaforme, serie, personaggi, premi, engine e modalità di gioco, sulle ultime parole digitate (tasti ↑ ↓ Invio/Tab).
- **Relazioni con CONSTRUCT**: l'agente usa `CONSTRUCT` per le domande sulle relazioni (il grafo viene costruito dalle triple restituite) e `SELECT` per classifiche, conteggi ed elenchi; anche il query builder può restituire il grafo delle relazioni.
- **Query builder assistito**: componi filtri (sviluppatore, genere, piattaforma, modalità, anno, Metacritic, categorie inferite come `HighlyRatedGame`...) con autocomplete sui valori; il backend genera il SPARQL (mostrato nel pannello) senza usare l'LLM.

### Agente SPARQL intelligente

- Converte NL → SPARQL automaticamente
- **Validazione sintattica** prima dell'esecuzione
- **Retry automatico** (max 3 tentativi) su errore o risultati vuoti
- Mostra la query SPARQL generata (espandibile)

### Cache a due livelli

- **SQLite locale** (`backend/cache.db`, persistente) per URL delle immagini, esiti "non trovato" e risultati delle query
- **Immagini**: per giochi, publisher, piattaforme, serie e motori il backend cerca la miniatura su Wikipedia in modo asincrono (un solo client HTTP, concorrenza limitata), la scarica in `backend/cache/images/` e ricorda anche gli URL. Ordine: file locale → URL salvato → ricerca. Per ripulire: `uv run python -m backend.tools.clear_images` (tutto) oppure `--misses` (solo i "non trovato", per ritentare)
- **In-memory** (Python dict) per label e tipi derivati dal grafo RDF
- Risultati null non vengono cachati (permettono retry su Wikipedia)

## Ontologia

### Classi

| Classe       | Descrizione                            |
| ------------ | -------------------------------------- |
| `VideoGame`  | Un videogioco                          |
| `Developer`  | Studio di sviluppo                     |
| `Publisher`  | Editore                                |
| `Genre`      | Genere (RPG, FPS, Action...)           |
| `Platform`   | Piattaforma (PS5, PC, Switch...)       |
| `Character`  | Personaggio nel gioco                  |
| `Franchise`  | Serie/franchise (Zelda, Dark Souls...) |
| `Award`      | Premio ricevuto                        |
| `GameEngine` | Engine usato per sviluppare il gioco   |

### Proprietà principali

| Proprietà         | Dominio   | Range       |
| ----------------- | --------- | ----------- |
| `developedBy`     | VideoGame | Developer   |
| `publishedBy`     | VideoGame | Publisher   |
| `hasGenre`        | VideoGame | Genre       |
| `availableOn`     | VideoGame | Platform    |
| `hasCharacter`    | VideoGame | Character   |
| `belongsTo`       | VideoGame | Franchise   |
| `wonAward`        | VideoGame | Award       |
| `madeWith`        | VideoGame | GameEngine  |
| `releaseDate`     | VideoGame | xsd:date    |
| `metacriticScore` | VideoGame | xsd:integer |
| `countryOfOrigin` | VideoGame | xsd:string  |

### Processo di popolamento

Tutto è eseguito da `ontology/build_ontology.py` (vedi Setup):

1. **Fetch** per anno × mese (2010–2026) da Wikidata, 11 tipologie di dati (core, generi, piattaforme, personaggi, franchise, game mode, Metacritic, engine, paese, premi, sequel), con checkpoint su disco
2. **Tipizzazione V2 e deduplicazione**: sottoclassi di piattaforme/generi/modalità in base all'etichetta, modalità di gioco come individui `GameMode`, unione delle entità con lo stesso nome normalizzato
3. **Reasoning**: assiomi V2, rimozione degli assiomi solo-DL, chiusura OWL-RL (`owlrl`), materializzazione mirata e regole SPARQL CONSTRUCT
4. **Validazione e output**: controlli sulla TBox, conteggio delle istanze per classe (stampato a fine esecuzione), scrittura di `.owl` e `.ttl`

### Fonti dati

- **Wikidata**: tutti i dati (via SPARQL endpoint pubblico)

## Stack Tecnologico

| Layer     | Tecnologia                               |
| --------- | ---------------------------------------- |
| Frontend  | React 18, TypeScript, Vite, Tailwind CSS |
| Grafo     | react-force-graph-2d                     |
| Backend   | FastAPI, Python 3.12+, async             |
| Ontologia | pyoxigraph (Rust), OWL 2, owlrl          |
| LLM       | OpenAI o Anthropic (`LLM_MODEL`)         |
| Cache     | SQLite (locale) + in-memory              |
| Dati      | Wikidata SPARQL                          |

## API Endpoints

| Metodo | Endpoint            | Descrizione                    |
| ------ | ------------------- | ------------------------------ |
| POST   | `/api/query`        | Ricerca NL → risultati + grafo |
| GET    | `/api/node/{uri}`   | Dettaglio nodo + sottografo    |
| GET    | `/api/image-search` | Cerca cover art da Wikipedia   |
| GET    | `/api/stats`        | Statistiche ontologia          |
| GET    | `/api/suggest`      | Autosuggest su nomi ed entità  |
| GET    | `/api/builder/schema` | Campi e operatori del builder |
| POST   | `/api/builder/query` | Query builder → SPARQL → grafo |
| GET    | `/api/health`       | Health check                   |
