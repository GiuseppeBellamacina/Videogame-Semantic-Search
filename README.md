# Videogame Semantic Search

Un progetto di Semantic Web che costruisce e interroga un'ontologia OWL sui videogiochi (dal 2015 ad oggi) tramite un'interfaccia web moderna con grafo di conoscenza interattivo.

## Architettura

```text
┌─────────────────────────────────────────────────────────────────┐
│  Frontend (React + Tailwind + react-force-graph)                │
│  ┌──────────┐  ┌──────────────┐  ┌───────────────────────────┐ │
│  │ SearchBar│  │  ResultList  │  │   Knowledge Graph (2D)    │ │
│  └──────────┘  └──────────────┘  └───────────────────────────┘ │
└────────────────────────────┬────────────────────────────────────┘
                             │ HTTP (REST API)
┌────────────────────────────▼────────────────────────────────────┐
│   Backend (FastAPI)                                             │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  SPARQL Agent (GPT-4.1 mini)                               │ │
│  │  NL → SPARQL → Validate → Execute → Explain                │ │
│  │  (retry automatico su errore, max 3 tentativi)             │ │
│  └────────────────────────────────────────────────────────────┘ │
│  ┌─────────────────────┐  ┌───────────────────────────────────┐ │
│  │  OntologyService    │  │  GraphBuilder                     │ │
│  │  (rdflib Graph)     │  │  (nodi + archi per frontend)      │ │
│  └─────────────────────┘  └───────────────────────────────────┘ │
└────────────────────────────┬────────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────────┐
│  Ontologia (videogames_wikidata.owl)                            │
│  Dati da: Wikidata                                              │
│  Classi: VideoGame, Developer, Publisher, Genre, Platform,      │
│          Character, Franchise, Award                            │
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
uv run python populate_wikidata.py    # ~5 minuti (richiede connessione internet)
```

Questo crea `videogames_wikidata.owl` con dati da Wikidata.

### 4. Configura variabili d'ambiente

Crea un file `.env` nella root del progetto:

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

| Classe      | Descrizione                            |
| ----------- | -------------------------------------- |
| `VideoGame` | Un videogioco                          |
| `Developer` | Studio di sviluppo                     |
| `Publisher` | Editore                                |
| `Genre`     | Genere (RPG, FPS, Action...)           |
| `Platform`  | Piattaforma (PS5, PC, Switch...)       |
| `Character` | Personaggio nel gioco                  |
| `Franchise` | Serie/franchise (Zelda, Dark Souls...) |
| `Award`     | Premio ricevuto                        |

### Fonti dati

- **Wikidata**: dati principali (nomi, date, developer, publisher, generi, piattaforme, personaggi, franchise, Metacritic, premi, descrizioni, game engine, country)

## Stack Tecnologico

| Layer     | Tecnologia                               |
| --------- | ---------------------------------------- |
| Frontend  | React 18, TypeScript, Vite, Tailwind CSS |
| Grafo     | react-force-graph-2d                     |
| Backend   | FastAPI, Python 3.11+                    |
| Ontologia | rdflib, OWL 2                            |
| LLM       | OpenAI GPT-4.1 mini                      |
| Dati      | Wikidata SPARQL                          |

## API Endpoints

| Metodo | Endpoint          | Descrizione                    |
| ------ | ----------------- | ------------------------------ |
| POST   | `/api/query`      | Ricerca NL → risultati + grafo |
| GET    | `/api/node/{uri}` | Dettaglio nodo + sottografo    |
| GET    | `/api/stats`      | Statistiche ontologia          |
| GET    | `/api/health`     | Health check                   |
