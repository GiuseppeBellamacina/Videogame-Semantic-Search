# Presentazione — Guida Slide per Slide

Guida dettagliata a `presentazione.pdf`: titolo, 14 slide di contenuto e chiusura. Il filo conduttore è l'**ontologia**; architettura software e popolamento compaiono solo nella penultima slide, come contesto. Per ogni slide la guida riporta il contenuto visivo, i concetti chiave, i dati tecnici e i riferimenti alla relazione estesa (`relazione.pdf`) e ai file del progetto.

Struttura:

| # | Slide | Blocco |
|---|-------|--------|
| 0 | Titolo | — |
| 1 | Obiettivo del Progetto | Introduzione |
| 2–10 | Panoramica, gerarchia, proprietà, catene e chiavi, classi definite, costrutti avanzati, Turtle, disjointness, allineamento e profilo DL | Ontologia |
| 11–12 | Reasoning a due livelli, esempio d'inferenza | Reasoning |
| 13 | Query SPARQL | Uso dell'ontologia |
| 14 | Popolamento e contesto applicativo | Contesto |
| — | Grazie | Chiusura |

---

## Slide 0 — Titolo

**Contenuto visivo**: titolo "Videogame Semantic Search" e sottotitolo "Un'ontologia OWL 2 DL per il dominio dei videogiochi — Modellazione, reasoning e interrogazione".

**Cosa comunica**: il soggetto della presentazione è l'ontologia. Il sottotitolo annuncia i tre temi: come è modellata, come si ragiona su di essa e come si interroga.

---

## Slide 1 — Obiettivo del Progetto

**Contenuto visivo**: blocco "Cosa abbiamo costruito" e tre bullet: Perché, Cosa contiene, Come si usa.

**Concetti chiave**:
- Un'**ontologia OWL 2 DL** sui videogiochi 2010–2026, popolata da Wikidata e interrogabile via SPARQL.
- **Contenuto**: 78 classi (15 definite), 57 proprietà, 12 blocchi di disjointness, 3 property chain, 3 `hasKey`, allineamento a Wikidata e Dublin Core.
- **Uso**: il reasoning a due livelli classifica le istanze; l'applicazione web (NL → SPARQL, grafo) è citata in una sola riga.

**Riferimenti**: Sezione 1 (Introduzione), `sezioni/01_introduzione.tex`.

---

## Slide 2 — Ontologia — Panoramica

**Contenuto visivo**: tre bullet (dominio, namespace, separazione schema/istanze) e una tabella 2×6 di metriche.

**Dati tecnici**:
- Schema `videogames.owl`: 934 triple. Istanze demo `videogames_pruned_2020.owl`: ~745k triple.
- Classi: 78 = 61 primitive + 15 definite (`owl:equivalentClass`) + 2 con vincolo di cardinalità (solo condizioni necessarie).
- Proprietà: 31 object e 26 datatype, 12 coppie inverse, 3 transitive.
- Assiomi: 12 blocchi `AllDisjointClasses`, 3 `propertyChainAxiom`, 3 `hasKey`.
- Allineamenti: 4 `equivalentClass` verso Wikidata e 3 `equivalentProperty` verso Dublin Core.
- Namespace `http://www.videogame-ontology.org/ontology#` (prefisso `vg:`): è un URI identificativo, non un URL risolvibile.

**Riferimenti**: Sezione 2 (Panoramica dell'Ontologia), `sezioni/03_ontologia_overview.tex`.

---

## Slide 3 — Ontologia — Gerarchia delle Classi

**Contenuto visivo**: a sinistra le 12 classi top-level su due colonne; a destra il partizionamento di Platform e le altre sottoclassi. In basso un blocco con tre pattern modellistici.

**Concetti chiave**:
- **12 classi top-level**, mutuamente disgiunte: VideoGame, Developer, Publisher, Genre, Platform, Character, Franchise, Award, GameEngine, GameMode, Review, GameEvent.
- **Platform** su due livelli: ConsolePlatform (PlayStation, Xbox, Nintendo), PCPlatform (Windows, MacOS, Linux), MobilePlatform (iOS, Android).
- Altre sottoclassi:
  - 10 generi, lasciati come tassonomia aperta;
  - stato di rilascio (Released, EarlyAccess, Cancelled, Delisted);
  - budget (Indie, AAA);
  - premi (Industry, Editorial, User);
  - personaggi (Player, NonPlayer);
  - motori (Proprietary, OpenSource).
- **Pattern modellistici**:
  - *Review* come relazione N-aria: `reviewedGame`, `reviewer`/`reviewerName`, `reviewScore`, `reviewDate`;
  - *GameEvent* come ciclo di vita;
  - *GameMode* come value partition (4 modalità disgiunte).

**Riferimenti**: Sezione 3 (Classi), `sezioni/04_tbox_classi.tex`.

---

## Slide 4 — Ontologia — Caratteristiche delle Proprietà

**Contenuto visivo**: tabella Caratteristica / Numero / Esempi e un alert block sul vincolo globale di OWL 2 DL.

**Dati tecnici**:
- **12 coppie** `owl:inverseOf`, per esempio developedBy/developerOf, belongsTo/includes, sequelOf/hasSequel.
- **3 transitive**: `sequelOf`, `partOfFranchise`, `subsidiaryOf`.
- **3 simmetriche**: le super-proprietà delle catene.
- **13 asimmetriche e 18 irriflessive**.
- **14 funzionali**: l'object property `reviewedGame` e 13 datatype property (nomi, `releaseDate`, `metacriticScore`, `hasSteamAppId`, `reviewScore`).
- **9 `subPropertyOf name`**.

**Concetto chiave (vincolo DL)**: le proprietà transitive e le loro inverse non sono *semplici*. OWL 2 DL non le ammette in assiomi di asimmetria, irriflessività, funzionalità, cardinalità o `hasKey`, perché altrimenti il ragionamento non sarebbe più decidibile. Per questo `sequelOf`, `hasSequel`, `partOfFranchise` e `subsidiaryOf` non sono dichiarate asimmetriche né irriflessive: l'aciclicità è un vincolo sulla qualità dei dati, non un assioma dello schema.

**Riferimenti**: Sezione 4 (Proprietà) e Sezione 8.3 (Vincoli globali di OWL 2 DL), `sezioni/05_tbox_proprieta.tex`, `sezioni/08b_profilo_dl.tex`.

---

## Slide 5 — Ontologia — Property Chain e Chiavi

**Contenuto visivo**: un blocco con le 3 catene in notazione DL, due bullet e un blocco con le 3 chiavi.

**Concetti chiave**:
- Una catena è un'**inclusione di ruoli**, non un'equivalenza:
  - `belongsTo ∘ includes ⊑ sharedFranchiseWith`
  - `developedBy ∘ developerOf ⊑ sharesDeveloperWith`
  - `publishedBy ∘ publisherOf ⊑ sharesPublisherWith`
- La composizione è ben tipata: VideoGame → Franchise → VideoGame.
- Le super-proprietà sono simmetriche. La catena produce anche la coppia riflessiva (g, g), quindi nelle query serve `FILTER(?g != ?altro)`.
- Le 3 chiavi `owl:hasKey` sono VideoGame(hasWikidataId), VideoGame(hasSteamAppId) e Review(reviewedGame, reviewerName). Valgono solo per gli individui nominati.
- L'identità dei giochi è affidata alle chiavi e non a `InverseFunctionalProperty` su datatype property, che OWL 2 DL non ammette.

**Riferimenti**: Sezioni 4.3 (Property Chain Axiom) e 4.6 (Chiavi), `sezioni/05_tbox_proprieta.tex`.

---

## Slide 6 — Ontologia — Classi Definite (Condizioni Necessarie e Sufficienti)

**Contenuto visivo**: tabella Classe / Definizione con `owl:equivalentClass`, una legenda per M e P e tre bullet.

**Concetti chiave**:
- **12 classi** sono definite come `VideoGame ⊓ ∃p.C` con `someValuesFrom` su object property: AwardWinningGame, FranchiseGame, SequelGame, Multiplayer/SinglePlayer/CoopGame, PC/Console/MobileGame, PlayStation/Xbox/NintendoGame.
- Altre 3 (HighlyRated, Recent, Standalone) usano costrutti più espressivi, per un totale di **15 classi definite**.
- La gerarchia delle piattaforme propaga la classificazione: un gioco su PS5 (PlayStationPlatform ⊑ ConsolePlatform) risulta sia PlayStationGame sia ConsoleGame.

**Riferimenti**: Sezione 5 (Classi Definite), Appendice B, `sezioni/06_tbox_classi_definite.tex`.

---

## Slide 7 — Ontologia — Negazione, Datatype e Cardinalità

**Contenuto visivo**: tabella Classe / Assioma / Costrutto su 5 righe e due bullet.

**Concetti chiave**:
- `StandaloneGame ≡ VideoGame ⊓ ¬∃sequelOf.VideoGame`: usa `complementOf`.
- `HighlyRatedGame ≡ VideoGame ⊓ ∃metacriticScore.integer[≥ 85]` e `RecentGame ≡ VideoGame ⊓ ∃releaseDate.date[≥ 2020-01-01]`: datatype restriction con facet `minInclusive`.
- `GameWithSingleDeveloper ⊑ VideoGame ⊓ ≤1 developedBy` ed `ExclusiveRelease ⊑ VideoGame ⊓ ≤1 availableOn`:
  - sono `maxCardinality` **non qualificate** e con **sole condizioni necessarie**;
  - per l'Open World Assumption un reasoner dedurrebbe ≤1 solo in presenza di assiomi di chiusura, quindi servono come vincoli di integrità e non come classificatori.
- `complementOf` e le datatype restriction non rientrano nel profilo OWL 2 RL: sono la ragione del secondo livello di reasoning.

**Riferimenti**: Sezione 5.2 (Analisi per Categoria) e Sezione 8.2 (Profili OWL 2), `sezioni/06_tbox_classi_definite.tex`.

---

## Slide 8 — Ontologia — Gli Assiomi in Turtle

**Contenuto visivo**: due listing Turtle estratti da `videogames.owl`.
- A sinistra, `HighlyRatedGame`: `owl:intersectionOf`, `owl:Restriction` e `rdfs:Datatype` con `owl:onDatatype` e `owl:withRestrictions`.
- A destra, `sharesDeveloperWith` (Symmetric e `owl:propertyChainAxiom`) e `GameWithSingleDeveloper` (`rdfs:subClassOf` verso una restrizione `owl:maxCardinality "1"^^xsd:nonNegativeInteger`).

**Cosa comunica**: come la sintassi DL delle slide precedenti diventa triple RDF concrete, compresi i nodi blank per restrizioni e liste.

**Riferimenti**: Appendice C (Assiomi dello Schema in Turtle), `ontology/videogames.owl` (RDF/XML, mostrato qui in Turtle).

---

## Slide 9 — Ontologia — Disjointness

**Contenuto visivo**: due tabelle affiancate con i 12 blocchi `AllDisjointClasses`, seguite da due bullet.

**Dati tecnici**: i 12 blocchi e il numero di classi in ciascuno.

| Blocco | Classi |
|--------|--------|
| Top-level | 12 |
| Console / PC / Mobile | 3 |
| PlayStation / Xbox / Nintendo | 3 |
| Windows / MacOS / Linux | 3 |
| iOS / Android | 2 |
| Industry / Editorial / User Award | 3 |
| Player / NonPlayer Character | 2 |
| Proprietary / OpenSource Engine | 2 |
| Released / EarlyAccess / Cancelled / Delisted | 4 |
| Indie / AAA | 2 |
| SinglePlayer / Multiplayer / Coop / MMO Mode | 4 |
| Announcement / Release / Update / Delisting Event | 4 |

**Concetti chiave**:
- SinglePlayerGame e MultiplayerGame **non** sono disgiunte, perché un gioco può supportare entrambe le modalità.
- I generi non sono chiusi in una partizione.
- Con un reasoner DL le disjointness fanno emergere i dati incoerenti.

**Riferimenti**: Sezione 6 (Disjointness), `sezioni/07_tbox_disjointness.tex`.

---

## Slide 10 — Ontologia — Allineamento Esterno e Profilo OWL 2 DL

**Contenuto visivo**: a sinistra due blocchi di allineamento, a destra il blocco "Vincoli globali OWL 2 DL sulle proprietà" e una nota su `xsd:date`.

**Dati tecnici**:
- **Wikidata**: VideoGame ≡ wd:Q7889, Developer ≡ wd:Q210167, GameEngine ≡ wd:Q193564, Genre ≡ wd:Q65956376.
- **Dublin Core**: releaseDate ≡ dcterms:issued, gameName ≡ dcterms:title, gameDescription ≡ dcterms:description.
- **Vincoli globali sulle proprietà**, 0 violazioni:
  - nessuna proprietà non semplice in assiomi di asimmetria, irriflessività, funzionalità, cardinalità o `hasKey`;
  - nessuna IFP su datatype property.
- **Nota**: `xsd:date` (range di `releaseDate`, `reviewDate`, `eventDate` e base della restrizione di `RecentGame`) non fa parte della datatype map di OWL 2, che per gli istanti temporali ammette solo `xsd:dateTime` e `xsd:dateTimeStamp`. Per usare HermiT bisogna migrare schema e dati a `xsd:dateTime`.

**Riferimenti**: Sezione 7 (Allineamento Esterno), Sezione 8 (Profilo OWL 2 ed Espressività DL), `sezioni/08_allineamento_esterno.tex`, `sezioni/08b_profilo_dl.tex`.

---

## Slide 11 — Reasoning — Architettura a Due Livelli

**Contenuto visivo**: pipeline orizzontale: Grafo RDF (~997 triple) → Livello 1 owlrl → ~2.680 triple → Livello 2 con 21 regole CONSTRUCT → 2.715 triple. Sotto, due colonne e una nota.

**Concetti chiave**:
- **owlrl (OWL 2 RL)** materializza subClassOf, intersectionOf + someValuesFrom, inverseOf, Symmetric/Transitive e propertyChainAxiom.
- **Livello 2 (CONSTRUCT)**:
  - copre ciò che RL non esprime: le datatype restriction (`FILTER(?s >= 85)`) e `complementOf`, con negation-as-failure (`FILTER NOT EXISTS`);
  - ripete, in modo ridondante rispetto a RL, le classificazioni e il completamento delle inverse.
- La restrizione ≤1 in posizione di superclasse è ammessa in RL (regola `cls-maxc2`, che identificherebbe due valori), ma non classifica nessun gioco perché le due classi hanno sole condizioni necessarie: serve solo come vincolo.
- I numeri si riferiscono all'insieme di istanze di test (3 giochi, 2 developer, piattaforme).

**Riferimenti**: Sezione 9 (Reasoning) e Sezione 8.2 (Profili OWL 2), `ontology/scripts/construct_reasoner.py`.

---

## Slide 12 — Reasoning — Un Esempio di Inferenza

**Contenuto visivo**: a sinistra le triple asserite per GameA (Elden Ring) con gli individui piattaforma tipizzati; a destra la tabella dei tipi e delle relazioni inferite con il loro motivo. Le righe in corsivo provengono dal livello CONSTRUCT.

**Concetti chiave**:
- Livello 1:
  - PlayStationGame e ConsoleGame (PS5 : PlayStationPlatform);
  - PCGame (WindowsPlatform ⊑ PCPlatform);
  - SinglePlayerGame e MultiplayerGame;
  - AwardWinningGame.
- Livello 2: HighlyRatedGame (96 ≥ 85), RecentGame (2022 ≥ 2020), StandaloneGame (nessun `sequelOf`).
- Relazioni:
  - `Dev1 developerOf GameA`, dall'inversa;
  - `GameA sharesDeveloperWith GameC`, dalla catena più la simmetria, perché anche GameC è sviluppato da Dev1.

**Riferimenti**: Sezione 9.3 (Esempio di Inferenza a Due Livelli), Appendice A (Esempio di Istanze di Test), `sezioni/app_a_abox.tex`.

---

## Slide 13 — Interrogare l'Ontologia — SPARQL

**Contenuto visivo**: due query SPARQL affiancate, ciascuna con una didascalia.

**Concetti chiave**:
- **Query 1**: `?g a vg:HighlyRatedGame, vg:MultiplayerGame, vg:PlayStationGame`. Le classi inferite sostituiscono i filtri sul punteggio, sulle modalità e sulla gerarchia delle piattaforme.
- **Query 2**: `vg:sharesDeveloperWith` a partire da "Elden Ring". La relazione non è mai asserita e deriva dalla catena; il `FILTER(?g != ?er)` elimina la coppia riflessiva.
- Entrambe le query sono sintatticamente valide (verificate con `rdflib.prepareQuery`).

**Riferimenti**: Sezione 10 (Interrogare l'Ontologia con SPARQL), `sezioni/09b_interrogazione.tex`.

---

## Slide 14 — Popolamento e Contesto Applicativo

**Contenuto visivo**: a sinistra la pipeline di popolamento in 5 passi; a destra uno schema a tre livelli dell'applicazione e una riga sulle performance.

**Dati tecnici**:
- **Popolamento**:
  - 12 tipologie di query SPARQL verso Wikidata, ciascuna su 204 finestre anno × mese (17 × 12);
  - deduplicazione di 4.420 entità;
  - chiusura OWL 2 RL da ~1M a ~1.4M triple;
  - pruning fino a ~1.17M triple;
  - demo 2020–2026 con ~745k triple e ~68.7k giochi.
- **Applicazione**: frontend React con grafo interattivo, backend FastAPI con agente NL → SPARQL, store pyoxigraph.
- **Performance** (riferimento generico): pyoxigraph rispetto a rdflib ha query 5–62× più veloci, caricamento in ~2 s invece di ~41 s e circa 4× meno RAM.

**Riferimenti**: Sezione 11 (Popolamento), Sezioni 12 e 13 (Architettura, Frontend e Backend).

---

## Slide Finale — Grazie

**Contenuto visivo**: slide "standout" con "Grazie per l'attenzione", il nome del progetto e la tagline "Ontologia OWL 2 DL · Reasoning · Interrogazione SPARQL".

---

## Riepilogo File di Progetto Referenziati

| File | Ruolo |
|------|-------|
| `ontology/videogames.owl` | Schema (934 triple, 78 classi, 57 proprietà, sezione DL-only con 16 assiomi) |
| `ontology/videogames_pruned_2020.owl` | Istanze demo (2020–2026, ~745k triple) |
| `ontology/enrich_owl.py` | Arricchimento e gestione strip/restore degli assiomi DL-only |
| `ontology/scripts/construct_reasoner.py` | 21 regole SPARQL CONSTRUCT (livello 2 del reasoning) |
| `ontology/populate_wikidata.py` | 12 tipologie di query SPARQL verso Wikidata |
| `docs/relazione/relazione/relazione.pdf` | Relazione estesa del progetto |
