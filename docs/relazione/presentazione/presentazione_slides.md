# Presentazione — Guida Slide per Slide

Guida dettagliata alla presentazione `presentazione.pdf` (15 slide di contenuto + titolo + chiusura). Per ogni slide: contenuto visivo, concetti chiave, dati tecnici, riferimenti alla relazione estesa (`relazione.pdf`) e ai file del progetto.

---

## Slide 0 — Titolo

**Contenuto visivo**: Titolo "Videogame Semantic Search", sottotitolo "Ontologia OWL 2, Reasoning e Interrogazione per il Dominio dei Videogiochi", autore "Videogame Semantic Search Project", data "Agosto 2026". Sfondo scuro (tema Metropolis).

**Cosa comunica**: Introduce il progetto come un lavoro sul Semantic Web applicato ai videogiochi, con enfasi su ontologia OWL 2 e reasoning. Il sottotitolo inquadra subito i tre pilastri: modellazione ontologica, inferenza automatica, e interfaccia utente.

**Riferimenti**: Frontespizio della relazione `relazione.pdf`.

---

## Slide 1 — Obiettivo del Progetto

**Contenuto visivo**: Blocco "Cosa abbiamo costruito" (testo introduttivo) + 3 bullet principali (Perché, Cosa offre, Casi d'uso), ciascuno con sotto-bullet.

**Concetti chiave**:
- L'obiettivo principale è costruire un'**ontologia OWL 2 di alta qualità** sul dominio videogiochi (2010–2026)
- L'ontologia è popolata con **dati reali estratti da Wikidata**
- È interrogabile in **linguaggio naturale** tramite un'interfaccia web con grafo interattivo
- **Perché**: non esisteva un'ontologia formale e validata per rappresentare la conoscenza strutturata sui videogiochi
- **Cosa offre**: 78 classi, 57 proprietà, 17 classi definite, reasoning a 2 livelli, frontend con grafo
- **Casi d'uso**: raccomandazione, analisi di mercato, esplorazione semantica, studio del dominio

**Dati tecnici**: 78 classi totali (61 primitive + 17 definite), 57 proprietà (31 object + 26 datatype), reasoning OWL 2 RL + SPARQL CONSTRUCT.

**Riferimenti**: Sezione 1 (Introduzione) di `relazione.pdf`, file `docs/relazione/sezioni/01_introduzione.tex`.

---

## Slide 2 — Architettura del Sistema

**Contenuto visivo**: Diagramma tikz a 3 livelli (Frontend → Backend → Ontologia) con frecce etichettate (REST, SPARQL). Sotto: tre colonne con lo stack tecnologico dettagliato.

**Concetti chiave**:
- Architettura **a 3 strati**: presentazione (React), logica (FastAPI), conoscenza (OWL 2)
- Il frontend comunica col backend via **REST**, il backend interroga l'ontologia via **SPARQL**
- **Deploy separato**: Vercel per il frontend, Render per il backend

**Dati tecnici**:
- Frontend: React 18 + TypeScript, Vite, Tailwind CSS, react-force-graph-2d
- Backend: FastAPI async, 6 endpoint REST, SPARQL Agent con GPT-4.1-mini, cache Upstash Redis + in-memory
- Ontologia: OWL 2 DL, pyoxigraph (Rust) per query performanti, RDFLib + owlrl per reasoning

**Riferimenti**: Sezione 2 (Architettura) di `relazione.pdf`, file `docs/relazione/sezioni/02_architettura.tex`.

---

## Slide 3 — Ontologia — Panoramica

**Contenuto visivo**: 4 bullet con descrizione del dominio, namespace, separazione schema/istanze, fonti. Tabella compatta con le statistiche dell'ontologia (2×4).

**Concetti chiave**:
- Il **dominio** copre i videogiochi 2010–2026 con tutte le entità correlate (sviluppatori, publisher, generi, piattaforme, personaggi, franchise, premi, motori grafici, modalità)
- Il **namespace** `http://www.videogame-ontology.org/ontology#` è un URI tecnico identificativo (non un URL risolvibile)
- **Separazione netta** tra schema (TBox, 945 triple in `videogames.owl`) e istanze (ABox demo, ~745k triple in `videogames_pruned_2020.owl`)
- **Fonti**: Wikidata SPARQL endpoint + allineamento con Dublin Core

**Dati tecnici**: 78 classi totali, 61 primitive, 17 definite, 31 object property, 26 datatype property, 12 blocchi AllDisjointClasses, 3 hasKey, 3 propertyChainAxiom.

**Riferimenti**: Sezione 3 (Ontologia Overview) di `relazione.pdf`, file `ontology/videogames.owl`, `docs/relazione/sezioni/03_ontologia_overview.tex`.

---

## Slide 4 — Ontologia — Gerarchia delle Classi

**Contenuto visivo**: Due colonne: sinistra con le 12 classi top-level, destra con il partizionamento gerarchico di Platform (Console → PC → Mobile, ciascuna con sottoclassi). In fondo: blocco sui due pattern modellistici (Review N-aria, GameEvent lifecycle).

**Concetti chiave**:
- Le **12 classi top-level** coprono tutte le entità del dominio: VideoGame, Developer, Publisher, Genre, Platform, Character, Franchise, Award, GameEngine, GameMode, Review, GameEvent
- **Platform è partizionata** in 3 rami: ConsolePlatform (PlayStation, Xbox, Nintendo con ~15 sottoclassi totali), PCPlatform (Windows, MacOS, Linux), MobilePlatform (iOS, Android)
- **Genre** ha 10 sottoclassi: Action, RPG, Strategy, Puzzle, Simulation, Sports, Racing, Adventure, Horror, Platformer
- Due **pattern modellistici** significativi: Review come relazione N-aria (una review collega un gioco a uno score e una fonte), GameEvent come ciclo di vita (Announcement, Release, Update, Delisting)

**Riferimenti**: Sezione 4 (Classi) di `relazione.pdf`, file `docs/relazione/sezioni/04_tbox_classi.tex`.

---

## Slide 5 — Ontologia — Proprietà e Chain Axiom

**Contenuto visivo**: Bullet sulle 31 object property con inverse, 2 transitive, 26 datatype. Blocco math con i 3 property chain axiom in notazione DL.

**Concetti chiave**:
- **31 Object Property** con inverse sistematiche: ogni proprietà direzionale ha la sua inversa (developedBy ↔ developerOf, publishedBy ↔ publisherOf, availableOn ↔ platformFor, hasGameMode ↔ modeInGame)
- **2 proprietà transitive**: sequelOf (catene di sequel), partOfFranchise (gerarchia franchise)
- **26 Datatype Property**: releaseDate, metacriticScore, steamRating, gameName, gameDescription, etc.
- **3 Property Chain Axiom** permettono a owlrl di inferire automaticamente relazioni simmetriche: sharedFranchiseWith (= belongsTo⁻ ∘ includes), sharesDeveloperWith (= developedBy ∘ developerOf), sharesPublisherWith (= publishedBy ∘ publisherOf)

**Riferimenti**: Sezione 5 (Proprietà) di `relazione.pdf`, file `docs/relazione/sezioni/05_tbox_proprieta.tex`.

---

## Slide 6 — Ontologia — Assiomi delle Proprietà (Approfondimento)

**Contenuto visivo**: 5 bullet con sotto-bullet che dettagliano: inverse sistematiche (5 esempi), transitive, asymmetric/irreflexive, property chain axiom (3), elenco di ciò che owlrl materializza.

**Concetti chiave**:
- **13 coppie inverse**: ogni object property ha `owl:inverseOf` esplicito. Esempi: hasCharacter ↔ appearsIn, belongsTo ↔ includes, wonAward ↔ awardWonBy, sequelOf ↔ hasSequel
- Le proprietà transitive **sequelOf** e **partOfFranchise** consentono inferenza su catene (es. sequel di sequel)
- La maggior parte delle object property ha caratteristiche **Asymmetric + Irreflexive** (developedBy non può essere simmetrica né riflessiva)
- I **3 property chain axiom** generano relazioni simmetriche derivate senza doverle dichiarare esplicitamente nelle istanze
- **owlrl materializza** automaticamente 8 inverse + 3 catene simmetriche: developerOf, platformFor, genreOf, awardWonBy, modeInGame, engineUsedIn, hasSequel, sharedFranchiseWith, sharesDeveloperWith, sharesPublisherWith

**Riferimenti**: Sezione 5 (Proprietà) di `relazione.pdf`, file `docs/relazione/sezioni/05_tbox_proprieta.tex`.

---

## Slide 7 — Ontologia — Classi Definite (Condizioni Sufficienti)

**Contenuto visivo**: Tabella a 2 colonne (Classe | Sintassi DL) con 9 righe che elencano le classi con `owl:equivalentClass` e `someValuesFrom`. Bullet finale sul ruolo del reasoner.

**Concetti chiave**:
- **13 classi con condizione sufficiente** (equivalentClass + someValuesFrom): AwardWinningGame, FranchiseGame, MultiplayerGame, SinglePlayerGame, CoopGame, PCGame, ConsoleGame, MobileGame, NintendoGame, PlayStationGame, XboxGame, SequelGame (più le varianti platform-specific)
- Ogni classe è definita come `VideoGame ⊓ ∃property.ClassName`
- Il reasoner **classifica automaticamente** ogni istanza che soddisfa la restrizione: se un gioco ha wonAward verso un Award, viene automaticamente inferito come AwardWinningGame
- Le classi platform-based (PCGame, ConsoleGame, MobileGame, etc.) usano `availableOn` con la gerarchia di Platform

**Dati tecnici**: Tutte usano `owl:equivalentClass` con `owl:someValuesFrom`. La classificazione avviene tramite owlrl (subClassOf materialization).

**Riferimenti**: Sezione 6 (Classi Definite) di `relazione.pdf`, file `docs/relazione/sezioni/06_tbox_classi_definite.tex`.

---

## Slide 8 — Ontologia — Classi Definite (Altri Costrutti OWL 2)

**Contenuto visivo**: Lista description con 5 classi: StandaloneGame, HighlyRatedGame, RecentGame, GameWithSingleDev, ExclusiveRelease. Ogni voce mostra l'espressione DL e il costrutto usato. Blocco con l'elenco dei costrutti OWL 2 DL impiegati.

**Concetti chiave**:
- **StandaloneGame** usa `complementOf` (negazione): `VideoGame ⊓ ¬∃sequelOf.VideoGame` — classificato dal CONSTRUCT reasoner perché fuori OWL 2 RL
- **HighlyRatedGame** e **RecentGame** usano **DatatypeRestriction**: metacriticScore ≥ 85 e releaseDate ≥ 2020-01-01 — anch'essi fuori RL, gestiti da CONSTRUCT
- **GameWithSingleDev** e **ExclusiveRelease** sono condizioni necessarie (subClassOf, non equivalentClass): `≤ 1 developedBy` e `≤ 1 availableOn` — maxQualifiedCardinality
- I costrutti OWL 2 DL utilizzati includono: someValuesFrom, complementOf, DatatypeRestriction (≥, ≤), maxQualifiedCardinality, propertyChainAxiom, hasKey, AllDisjointClasses

**Riferimenti**: Sezione 6 (Classi Definite) di `relazione.pdf`, file `docs/relazione/sezioni/06_tbox_classi_definite.tex` e appendice `app_b_dl.tex`.

---

## Slide 9 — Ontologia — Disjointness e Allineamento Esterno

**Contenuto visivo**: Due colonne. Sinistra: tabella con 7 blocchi AllDisjointClasses (Platform, ConsolePlat, PSPlatform, XboxPlatform, PCPlatform, MobilePlat, Genre). Destra: due blocchi: 4 equivalentClass con Wikidata e 3 equivalentProperty con Dublin Core.

**Concetti chiave**:
- **12 blocchi AllDisjointClasses** garantiscono che le classi siano mutualmente esclusive (es. un gioco non può essere contemporaneamente PC e Console)
- I blocchi coprono la gerarchia Platform (3 livelli) e Genre (10 sottoclassi)
- **4 allineamenti Wikidata** (equivalentClass): VideoGame ≡ wd:Q7889, Developer ≡ wd:Q210167, GameEngine ≡ wd:Q193564, Genre ≡ wd:Q65956376 — consentono il popolamento automatico da Wikidata
- **3 allineamenti Dublin Core** (equivalentProperty): releaseDate ≡ dcterms:issued, gameName ≡ dcterms:title, gameDescription ≡ dcterms:description

**Dati tecnici**: I Q-number sono verificati contro `ontology/videogames.owl` (sezione "Allineamento esterno", righe 1372–1399). Il prefisso `dcterms:` corrisponde a `http://purl.org/dc/terms/`.

**Riferimenti**: Sezioni 7 (Disjointness) e 8 (Allineamento) di `relazione.pdf`, file `docs/relazione/sezioni/07_tbox_disjointness.tex` e `08_allineamento_esterno.tex`.

---

## Slide 10 — Reasoning — Architettura a Due Livelli

**Contenuto visivo**: Colonna sinistra: diagramma tikz a 4 nodi (Grafo RDF → owlrl → CONSTRUCT → Grafo inferito). Colonna destra: bullet divisi in "owlrl materializza" e "CONSTRUCT gestisce", più spiegazione del perché servono due livelli.

**Concetti chiave**:
- **Livello 1 — owlrl (OWL 2 RL)**: materializza subClassOf, someValuesFrom, hasValue, intersectionOf, inverseOf, SymmetricProperty, TransitiveProperty, propertyChainAxiom. Su test (997 triple) → 2.680 triple inferite.
- **Livello 2 — construct_reasoner.py**: 21 regole SPARQL CONSTRUCT per costrutti fuori OWL 2 RL: classificazioni (HighlyRated, Recent, Standalone, platform/mode-derived), inverse completion, catene simmetriche aggiuntive (sharedGenreWith, sharedEngineWith)
- **Perché due livelli**: owlrl non supporta complementOf, datatype restriction, maxCardinality — questi richiedono un reasoner DL completo o regole custom

**Riferimenti**: Sezione 9 (Reasoning) di `relazione.pdf`, file `docs/relazione/sezioni/09_reasoning.tex`, `ontology/scripts/construct_reasoner.py`.

---

## Slide 11 — Bug Critico — owlrl e DatatypeProperty funzionali

**Contenuto visivo**: Alertblock rosso con la descrizione del problema. Due colonne "Prima del fix" / "Dopo il fix" con confronto. Blocco "Soluzione adottata" in fondo.

**Concetti chiave**:
- **Il bug**: owlrl inferisce `owl:sameAs` falsi tra giochi distinti quando FunctionalProperty, InverseFunctionalProperty o hasKey sono applicati a DatatypeProperty. owlrl tratta i valori letterali come individui (risorse), causando identificazione errata.
- **Impatto prima del fix**: 3 giochi classificati AwardWinningGame (errato), 2 sameAs errati tra giochi con stesso Metacritic o data, classificazioni falsate
- **Dopo il fix**: 1 solo gioco classificato AwardWinningGame (corretto), nessun sameAs spurio
- **Soluzione**: 17 assiomi "DL-only" (FunctionalProperty/InverseFunctionalProperty/hasKey su DatatypeProperty) isolati in una sezione separata dell'ontologia. Funzioni `strip_dl_only_axioms()` / `restore_dl_only_axioms()` in `enrich_owl.py` con flag `--keep-dl-axioms`. Prima del reasoning owlrl, gli assiomi vengono rimossi; dopo, ripristinati.

**Riferimenti**: Sezione 9.3 (Bug Critico) di `relazione.pdf`, file `ontology/enrich_owl.py`.

---

## Slide 12 — Popolamento e Performance

**Contenuto visivo**: Blocco "Pipeline di Popolamento" con 5 step enumerati. Tabella comparativa RDFLib vs pyoxigraph (3 operazioni con speedup).

**Concetti chiave**:
- **Pipeline**: populate_wikidata.py esegue 13 query SPARQL × 204 iterazioni (anno × mese 2010–2026), ~5 ore. Poi deduplica 4.420 entità, applica OWL-RL reasoning (~1M → ~1.4M triple), pruna ~253k triple ridondanti → ~1.17M finali. Demo: finestra 2020–2026, ~745k triple, ~68.7k giochi.
- **pyoxigraph** (Rust) è 5–62× più veloce di RDFLib: caricamento 5×, query SPARQL 62×, RAM 6× inferiore (~250MB vs ~1.5GB per 745k triple)
- **Deduplicazione**: basata su identificativo Wikidata, 4.420 entità rimosse

**Dati tecnici**: pyoxigraph è una libreria Rust con binding Python, usa lo stesso formato di RDFLib ma con performance native.

**Riferimenti**: Sezione 10 (Popolamento) di `relazione.pdf`, file `docs/relazione/sezioni/10_popolamento.tex`, `ontology/scripts/populate_wikidata.py`.

---

## Slide 13 — Validazione dello Schema

**Contenuto visivo**: Titolo con nome script, due colonne con 10 controlli enumerati (5+5). In fondo: risultato grande centrato (0 ERROR, 18 WARNING, PASS in verde).

**Concetti chiave**:
- **validate_tbox.py** esegue 10 controlli automatici sulla TBox: dangling references, unsatisfiable disjoint, circular subclass, inverse consistency, property type conflict, missing domain/range, missing labels, unused classes, restriction completeness, datatype restriction syntax
- **Risultato**: 0 ERROR, 18 WARNING (benigni), **PASS**
- I 18 warning riguardano classi leaf senza sottoclassi e label mancanti in entità ausiliarie — nessun impatto sul reasoning
- La validazione garantisce che lo schema sia **corretto, coerente e completo** prima del popolamento

**Riferimenti**: Sezione 11 (Validazione) di `relazione.pdf`, file `docs/relazione/sezioni/11_validazione.tex`, `ontology/scripts/validate_tbox.py`.

---

## Slide 14 — Frontend e Backend

**Contenuto visivo**: Due colonne compresse: sinistra "Frontend — Grafo interattivo" con 6 bullet, destra "Backend — FastAPI async" con 5 bullet.

**Concetti chiave**:
- **Frontend**: React 18 + TypeScript + Vite + Tailwind. Grafo force-directed con react-force-graph-2d: nodi colorati per tipo (blu=Gioco, verde=Sviluppatore, etc.), VideoGame come rettangoli con cover art. Feature: long-press mobile, context menu, zoom/pan, espansione ricorsiva nodi, filtri per tipo. Deploy: Vercel.
- **Backend**: FastAPI async con 6 endpoint REST (/query, /node, /stats, /image-search, /health, /cross-links). SPARQL Agent basato su GPT-4.1-mini per traduzione NL → SPARQL con retry automatico (max 3 tentativi). Cache a due livelli: Upstash Redis (persistente, TTL) + in-memory LRU (locale, immediata). Validazione sintattica delle query prima dell'esecuzione. Deploy: Render.

**Riferimenti**: Sezione 12 (Frontend e Backend) di `relazione.pdf`, file `docs/relazione/sezioni/12_frontend_backend.tex`.

---

## Slide 15 — Riepilogo e Sviluppi Futuri

**Contenuto visivo**: Due blocchi: "Riepilogo del Lavoro Svolto" con 5 bullet, "Sviluppi Futuri" con 4 bullet.

**Concetti chiave**:
- **Riepilogo**: ontologia OWL 2 evoluta da 11 a 78 classi, da 2 a 17 classi definite, da 0 a 12 blocchi disjoint. Popolamento Wikidata: ~745k triple demo, ~68.7k giochi. Reasoning a due livelli con gestione safety owlrl. Validazione automatica: 0 errori su 10 controlli. Interfaccia web completa.
- **Sviluppi futuri**:
  1. **Reasoner DL completo** (HermiT): per classificazione OWL 2 DL piena (complementOf, maxCardinality, datatype restriction) senza bisogno di regole CONSTRUCT custom
  2. **Validazione SHACL**: shape constraints per garantire coerenza delle istanze oltre allo schema
  3. **Regole SWRL**: inferenza avanzata (es. "gioco di successo" da vendite + recensioni)
  4. **Estensione pipeline**: copertura pre-2010, aggiornamento periodico automatico da Wikidata

**Riferimenti**: Sezione 13 (Conclusione) di `relazione.pdf`, file `docs/relazione/sezioni/13_conclusione.tex`.

---

## Slide Finale — Thanks

**Contenuto visivo**: Slide "standout" (sfondo scuro, testo centrato): "Grazie per l'attenzione" in grande, nome del progetto, tagline "Ontologia OWL 2 · Reasoning · Grafo interattivo".

**Cosa comunica**: Chiusura pulita che riassume i tre pilastri del progetto in una tagline memorabile. Nessun URL fittizio — il namespace è un URI tecnico identificativo, non un sito web.

---

## Riepilogo File di Progetto Referenziati

| File | Ruolo |
|------|-------|
| `ontology/videogames.owl` | Schema TBox (945 triple, 78 classi, 57 proprietà) |
| `ontology/videogames_pruned_2020.owl` | Istanze demo (2020–2026, ~745k triple) |
| `ontology/enrich_owl.py` | Enrichment con strip/restore DL-only axioms |
| `ontology/scripts/construct_reasoner.py` | 21 regole SPARQL CONSTRUCT per reasoning avanzato |
| `ontology/scripts/validate_tbox.py` | 10 controlli automatici di validazione |
| `ontology/scripts/populate_wikidata.py` | 13 query SPARQL verso Wikidata per popolamento |
| `docs/relazione/relazione.pdf` | Relazione estesa del progetto |
