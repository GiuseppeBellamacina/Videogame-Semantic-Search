# Analisi dell'ontologia e dei dati (2026-11-19)

I numeri vengono da `schema_generated.ttl`, `abox_demo.ttl` (ragionata con HermiT) e, per l'analisi del §4 e del §6, dal build Wikidata completo `ontology/output/videogames_full.ttl`. Su richiesta di Giuseppe l'ontologia consegnata usa **solo i dati demo**: il campione estratto dal build completo (`abox_sample.ttl`, `extract_sample.py`) è stato tolto.

## 1. Correzioni fatte

| Problema | Correzione |
|---|---|
| Il vecchio caso 3b faceva concludere che Nintendo Switch e Switch 2 sono lo stesso individuo, perché OWL non ha la Unique Name Assumption. | La demo dichiara tutte le sue piattaforme diverse a due a due (`owl:AllDifferent`), e TotK "su al più una piattaforma" su Switch e Switch 2 dà un errore (`inc3_cardinality.ttl`). Il nuovo `inc3b_sameas.ttl` mostra il `sameAs` su un caso dove è corretto: "NX" è il nome in codice della Switch. |
| GTA VI risultava sviluppato da "Rockstar Games", perché il P178 di Wikidata indica la casa madre. Così scattavano a torto le regole `SelfPublishedGame` e `SequelByDifferentStudio`. | GTA VI ora è sviluppato da Rockstar North, studio principale come per ogni GTA numerato dal III in poi, e pubblicato da Rockstar Games. Le due regole non scattano più. |
| Dark Souls aveva un solo editore (FromSoftware). | Ora ne ha due: FromSoftware (Giappone) e Bandai Namco Entertainment, già Namco Bandai Games (resto del mondo). Il gioco diventa anche `BandaiNamcoPublishedGame`. |
| Nel build completo alcune date sono di una riedizione: San Andreas 2010, Ocarina of Time 2026, Portal 2010. | I giochi della demo vengono presi **solo** dalla demo, letterali e link compresi. Così spariscono anche i `sequelOf` spuri del build, per esempio BotW → Tri Force Heroes e TotK → Link's Awakening. |
| `SubFranchise` aveva 0 istanze anche nel build completo. | Rimossa dallo schema. |

Dopo le correzioni `check_reasoning.py` passa **86 controlli su 86**, e il parser OWL API (quello di Protégé) legge i file e dà gli stessi risultati.

## 2. Inventario dell'ontologia (dopo la pulizia)

| Elemento | Quanti | Dettaglio |
|---|---:|---|
| Classi | **105** | 47 primitive + 58 definite |
| Classi primitive | 47 | 9 di primo livello (disgiunte), 7 famiglie e 8 sottofamiglie di piattaforma, 13 generi, 3 modalità, GameOfTheYearAward, UnrealEngineFamily, 5 classi d'arrivo SWRL |
| **Classi definite** | **58** | 14 "gioco su piattaforma", 13 "gioco di un genere", 3 "gioco con una modalità", 8 publisher nominali, 2 paesi, 18 altre (ruoli, soglie, cardinalità minime, classi a strati, PlatformHolder, FirstPartyGame, LongRunningFranchise, FranchiseWithStudioChange) |
| **Regole SWRL** | **6** | tutte DL-safe ed eseguite da HermiT: SelfPublished, SequelByDifferentStudio, FirstPartyOnRivalConsole (due versioni), CouchCoop, MustPlay (soglia come intervallo di dati `xsd:integer[> 94]`, come negli esempi del corso) |
| Object property | 27 | 11 coppie di inverse (22 proprietà), 2 transitive (`sequelOf`, `subsidiaryOf`), 3 simmetriche da catena, `publishedByGroup` (super-proprietà di `publishedBy`, catena `publishedBy∘subsidiaryOf`), 20 irriflessive e asimmetriche |
| Catene di proprietà | 4 | `sharesDeveloperWith`, `sharesPublisherWith`, `sharedFranchiseWith`, `publishedByGroup` |
| Datatype property | 14 | 11 funzionali |
| Chiavi | 1 | VideoGame(`hasWikidataId`) |
| Blocchi di disgiunzione | 6 | |
| Individui nominali nello schema | 8 | |
| Allineamenti | 6 | `skos:closeMatch`: 4 verso Wikidata, 2 verso Dublin Core |
| Test | 5 | 4 inconsistenze (disgiunzione, funzionale, cardinalità, chiave) + 1 caso `sameAs` corretto (NX = Nintendo Switch) |

## 3. Cosa viene direttamente dai dati

**Da Wikidata**: uno statement per ogni triple asserita del build completo.

| Wikidata | Ontologia |
|---|---|
| P31 (istanza di videogioco) + etichetta | `VideoGame`, `gameName` |
| P577 data di pubblicazione | `releaseDate` (solo date dal 2010 in poi: vedi §6) |
| P178 sviluppatore / P123 editore | `developedBy` / `publishedBy` (+ `developerName`/`publisherName` sulla company) |
| P136 genere | `hasGenre` (+ `genreName`) |
| P400 piattaforma | `availableOn` (+ `platformName`) |
| P404 modalità | `hasGameMode` |
| P495 paese d'origine | `countryOfOrigin` |
| P408 motore | `madeWith` (+ `engineName`) |
| P674 personaggi | `hasCharacter` (+ `characterName`) |
| P179 serie | `belongsTo` (+ `franchiseName`) |
| P166 premi | `wonAward` (+ `awardName`) |
| P444 (+ P447 = Metacritic) | `metacriticScore` |
| P155 "segue" | `sequelOf`. Attenzione: P155 vuol dire "elemento precedente della serie", che non sempre è un seguito vero (BotW "segue" Tri Force Heroes). |

**Dalla pipeline**, non da Wikidata: il tipo primitivo specifico di generi, piattaforme e modalità (per esempio `ShooterGenre`, `PlayStationPlatform`), assegnato con regole sull'etichetta. Si aggiunge il tipo `GameOfTheYearAward` per i premi GOTY di The Game Awards e degli Spike VGA.

**A mano**, solo nella demo:
- le 7 serie con `sequelOf` verso il predecessore diretto;
- `hasWikidataId`;
- `owl:AllDifferent` su company e piattaforme;
- le correzioni del §1.

## 4. Triple asserite e triple dedotte

### Build completo: 4.410.582 triple

Ci sono circa 2.000 triple di TBox. Quelle di ABox sono 4.408.508, così ripartite:

| | Triple | % |
|---|---:|---:|
| **Asserite** | **934.156** | **21%** |
| link gioco → entità (una direzione per coppia) | 561.077 | |
| letterali (nomi, date, punteggi, paesi) | 249.307 | |
| tipi di base (VideoGame, Company, Platform…) | 122.737 | |
| tipi primitivi specifici | 440 | |
| `sequelOf` diretta | 595 | |
| **Dedotte** | **3.474.352** | **79%** |
| catene di proprietà (`shares*`, `sharedFranchiseWith`) | 1.870.019 | 42% di tutto il grafo |
| tipi da classi definite | 795.909 | |
| inverse | 562.326 | |
| `rdf:type owl:Thing` | 122.736 | |
| `vg:name` (super-proprietà dei nomi) | 122.708 | |
| `sequelOf` per transitività | 654 | |

Da sola `sharesPublisherWith` vale 1.464.301 triple, un terzo del grafo: un editore con N giochi produce N² coppie, compresa quella di ogni gioco con sé stesso. Sono triple dedotte e di scarso valore informativo.

### Demo (25 giochi, 88 individui), ragionata con HermiT

| | Triple |
|---|---:|
| Asserite (ABox) | 515 |
| **Dedotte** | **1.133** (69% del totale) |
| tipi da classi definite OWL | 384 |
| tipi da regole SWRL | 17 |
| tipi da superclasse, dominio e range | 51 |
| relazioni: catene (`shares*`, `publishedByGroup`) | 371 |
| relazioni: inverse (`platformFor`, `hasSequel`, `genreOf`, `manufacturerOf`, …) | 283 |
| relazioni: `sequelOf` e `subsidiaryOf` per transitività | 27 |

## 5. Elementi non popolati: eliminati

Sono stati tolti dallo schema:
- le classi `MMOMode`, `ExclusiveRelease`, `GameWithSingleDeveloper` e `StandaloneGame`;
- la proprietà `partOfFranchise`;
- le datatype property `officialWebsite`, `gameDescription`, `description` e `awardYear`.

Il test di cardinalità usa ora una restrizione anonima. `subsidiaryOf` resta, ora popolata nella demo (Wikidata P749). `hasWikidataId` resta, perché regge la chiave. `ArcadePlatform` e `GameOfTheYearAward` hanno poche istanze, ma non sono vuote.

## 6. Problemi nei dati (build completo)

1. **Date.** Il fetch prende la data che cade nella finestra 2010–2026. Per tutti i giochi usciti prima del 2010 la data è quindi quella di una riedizione (nel build c'è 1 sola data anteriore al 2010). Effetti:
   - 32 seguiti diretti su 595 risultano usciti prima del predecessore;
   - `RecentGame` e le date dei vecchi giochi non sono affidabili.

   Ci sono anche 55 date nel futuro, che sono giochi annunciati.
2. **Copertura scarsa.** L'82% dei giochi non ha sviluppatore (88.046 su 107.522) e l'80% non ha editore (85.765). Le inferenze su ruoli, catene e regole SWRL valgono quindi solo per circa un gioco su cinque. Metacritic è presente solo su 342 giochi.
3. **`sequelOf` da P155.** "Segue nella serie" non è "è il seguito di": per esempio BotW "segue" Tri Force Heroes. Con la transitività l'errore si propaga.
4. **Generi non classificati.** 434 generi su 605 non hanno una classe di genere: fantascienza, roguelike, metroidvania, MMO, musicale… Coprono però solo il 6% degli usi. Alcuni "generi" sono temi, come "video game with LGBT character".
5. **Doppioni e sporcizia.**
   - Modalità: `PvP` e `player_versus_player` (stessi 3.929 giochi; la prima senza classe), `PvE` e `player_versus_environment`, `zombie` e `zombi`.
   - Piattaforme: `Category:PlayStation 3`, "Cascading Style Sheets", "HTML5", "Discord", "Multi Theft Auto"; "Mac", "Mac operating system" e "macOS" come tre piattaforme diverse; 146 piattaforme su 311 senza famiglia (soprattutto tvOS e Playdate).
6. **Catene riflessive.** Ogni gioco "condivide lo sviluppatore con sé stesso". È corretto in OWL, perché la catena è riflessiva su chi ha uno sviluppatore, ma gonfia il grafo (vedi §4).

## 7. Deduzioni non banali (verificate)

1. **Gioco first-party.** *Mass Effect* (2007) e *Halo 4* sono giochi Microsoft. Nei dati c'è solo "pubblicato da Xbox Game Studios". Il reasoner deduce:
   - Microsoft è un `PlatformHolder`, perché costruisce la Xbox 360 (inversa più restrizione esistenziale);
   - il gioco è "pubblicato dal gruppo Microsoft" (catena `publishedBy ∘ subsidiaryOf`);
   - il gioco è `FirstPartyGame` (classe definita).
2. **First-party su console rivale** (SWRL): *Mass Effect*, gioco del gruppo Microsoft, è uscito anche su PS3, costruita da Sony. Nessun altro gioco della demo lo è.
3. **Gruppi societari per transitività.** Halo Studios (343) fa parte di Microsoft, passando per Xbox Game Studios. Rockstar North fa parte di Take-Two, passando per Rockstar Games.
4. **Serie passata di mano.** La serie Halo è `FranchiseWithStudioChange`: è una classe OWL costruita sopra una conclusione SWRL (Halo 4, 343 dopo Bungie) e sull'inversa `includes`.
5. **Serie lunghe.** GTA, Dark Souls, The Witcher e Mass Effect sono `LongRunningFranchise`, ricavata dal solo predecessore diretto: transitività → `LateEntry` → inversa. Portal, Halo e Zelda (nella demo) no.
6. **Seguiti acclamati.** GTA IV, Portal 2 e Mass Effect 2 sono `AcclaimedSequel`, intersezione di due classi definite.
7. **Multipiattaforma con distinzione.** BotW è `MultiPlatformGame` (Wii U, Switch, Switch 2, dichiarate diverse); TotK no.
8. **Errori**: disgiunzione, funzionalità, cardinalità e chiave (4 test).

**Ancora possibili**:
- la catena `developerOf ∘ belongsTo → workedOnFranchise` (quali studi hanno lavorato a una serie);
- una regola che segnali le date incoerenti (§6.1).
