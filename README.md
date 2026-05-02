# Videogame Semantic Search

**[🎮 Demo live](https://videogame-semantic-search.vercel.app)**

Un progetto di Semantic Web che costruisce e interroga un'ontologia OWL sui videogiochi (dal 2010 ad oggi) tramite un'interfaccia web moderna con grafo di conoscenza interattivo.

## Ontologia — Statistiche

| Metrica                | Valore          |
| ---------------------- | --------------- |
| Periodo coperto        | 2010 – 2026     |
| Triple totali (grezzo) | ~1.019.589      |
| Triple dopo reasoning  | **~1.427.081**  |
| Entità deduplicate     | 4.420 rimosse   |
| Fonte                  | Wikidata SPARQL |

L'ontologia viene generata in circa **5 ore** di computazione (query per anno × mese per evitare i timeout di Wikidata), poi viene applicata la chiusura deduttiva OWL-RL tramite `owlrl` per materializzare le proprietà inverse e le catene `subPropertyOf`.

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
│  │                 SPARQL Agent (GPT-4.1 mini)                │ │
│  │              NL → SPARQL → Validate → Execute              │ │
│  │        (retry automatico su errore, max 3 tentativi)       │ │
│  └────────────────────────────────────────────────────────────┘ │
│  ┌─────────────────────┐  ┌───────────────────────────────────┐ │
│  │   OntologyService   │  │          GraphBuilder             │ │
│  │   (rdflib Graph)    │  │    (nodi + archi per frontend)    │ │
│  └─────────────────────┘  └───────────────────────────────────┘ │
└──────────────────────────────┬──────────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────────┐
│  Ontologia (videogames_wikidata.owl)                            │
│  Dati da: Wikidata · ~1.4M triple dopo OWL-RL reasoning         │
│  Classi: VideoGame, Developer, Publisher, Genre, Platform,      │
│          Character, Franchise, Award, GameEngine                │
└─────────────────────────────────────────────────────────────────┘
```

## Requisiti

- Python 3.12+ (gestito da uv)
- [uv](https://docs.astral.sh/uv/) (package manager Python)
- Node.js 18+
- Chiave API OpenAI (per GPT-4.1 mini)

## Setup

### 1. Clona e posizionati

```bash
cd Videogame-Semantic-Search
```

### 2. Installa dipendenze Python (con uv)

```bash
uv sync
```

### 3. Popola l'ontologia

```bash
cd ontology
uv run python populate_wikidata.py
```

> **Attenzione**: la popolazione richiede circa **5 ore** (query per anno × mese verso Wikidata + OWL-RL reasoning finale). Richiede connessione internet. Il file risultante `videogames_wikidata.owl` non è incluso nel repository per via delle dimensioni.

### 4. Configura variabili d'ambiente

Crea un file `.env` nella root del progetto (vedi `.env.example`):

```env
OPENAI_API_KEY=sk-your-api-key-here
OPENAI_MODEL=gpt-4.1-mini
```

### 5. Avvia il backend

```bash
uv run uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

### 6. Frontend

```bash
cd frontend
npm install
npm run dev
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
- **Animazione physics-based** con forze e repulsione
- **Click su nodo** → pannello dettaglio con tutte le proprietà e relazioni
- **Hover** → evidenzia connessioni dirette
- **Zoom/pan** per esplorare il grafo
- **Legenda** con colori per tipo di entità

### Agente SPARQL intelligente

- Converte NL → SPARQL automaticamente
- **Validazione sintattica** prima dell'esecuzione
- **Retry automatico** (max 3 tentativi) su errore o risultati vuoti
- Mostra la query SPARQL generata (espandibile)

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
| `officialWebsite` | VideoGame | xsd:anyURI  |
| `gameDescription` | VideoGame | xsd:string  |

### Processo di popolamento

1. **Query per anno × mese** (2010–2026) verso Wikidata per 12 tipologie di dati (core, generi, piattaforme, personaggi, franchise, game mode, Metacritic, engine, paese, sito web, premi, descrizioni)
2. **Deduplicazione** degli URI con stesso nome (normalizzato): 4.420 entità duplicate rimosse
3. **OWL-RL reasoning** con `owlrl`: materializzazione di proprietà inverse e catene subPropertyOf → da ~1M a ~1.4M triple

### Fonti dati

- **Wikidata**: tutti i dati (via SPARQL endpoint pubblico)

## Stack Tecnologico

| Layer     | Tecnologia                               |
| --------- | ---------------------------------------- |
| Frontend  | React 18, TypeScript, Vite, Tailwind CSS |
| Grafo     | react-force-graph-2d                     |
| Backend   | FastAPI, Python 3.12+                    |
| Ontologia | rdflib, OWL 2, owlrl                     |
| LLM       | OpenAI GPT-4.1 mini                      |
| Dati      | Wikidata SPARQL                          |
| Deploy    | Render (backend) + Vercel (frontend)     |

## API Endpoints

| Metodo | Endpoint          | Descrizione                    |
| ------ | ----------------- | ------------------------------ |
| POST   | `/api/query`      | Ricerca NL → risultati + grafo |
| GET    | `/api/node/{uri}` | Dettaglio nodo + sottografo    |
| GET    | `/api/stats`      | Statistiche ontologia          |
| GET    | `/api/health`     | Health check                   |
