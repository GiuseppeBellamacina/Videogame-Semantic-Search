# Schema generato vs schema scritto a mano

Questo file confronta `schema_generated.ttl`, prodotto da `generate_schema.py`, con lo schema modulare scritto a mano in `ontology/videogames.owl` e `ontology/schema/*.owl`.

Per rifare il confronto basta eseguire `uv run python protege/generate_schema.py --diff`: una query SPARQL elenca le classi e le proprietà aggiunte e tolte rispetto allo schema scritto a mano (`ontology/output/videogames.ttl`). Le differenze negli assiomi delle entità rimaste sono quelle elencate qui sotto.

Tutte le differenze sono volute.

| Differenza | Perché |
|---|---|
| `releaseDate` passa da `xsd:date` a `xsd:dateTime`, e così il facet di `RecentGame` (`"2020-01-01T00:00:00"`) | `xsd:date` non fa parte della datatype map di OWL 2, e HermiT rifiuta il file. |
| `VideoGame` ha una sola `hasKey` (`hasWikidataId`) invece di due | Con `hasSteamAppId`, che non è mai popolata, se ne va anche la sua chiave. |
| Rimosse `AAAGame`, `IndieGame`, `ReleasedGame`, `EarlyAccessGame`, `CancelledGame`, `DelistedGame`, `First/ThirdPartyDeveloper`, `First/ThirdPartyPublisher`, `IndieDeveloper`, `PlayerCharacter`, `NonPlayerCharacter`, `ProprietaryEngine`, `OpenSourceEngine`, `IndustryAward`, `EditorialAward`, `UserAward`, `SubFranchise`, `MMOMode` | Sono classi primitive senza istanze, che non si possono ricavare dai dati Wikidata. Insieme a loro spariscono i blocchi di disjointness che le contenevano, compreso quello degli stati del ciclo di vita. |
| Rimosse `Review`, `GameEvent` (con `AnnouncementEvent`, `ReleaseEvent`, `UpdateEvent`, `DelistingEvent`) e le loro proprietà (`hasReview`, `reviewOf`, `reviewedGame`, `reviewer`, `reviewDate`, `reviewScore`, `reviewerName`, `hasEvent`, `eventFor`, `eventDate`), insieme alla `hasKey` di `Review` | Nei dati non hanno istanze. Il brief le permetteva solo se popolate a mano, e si è preferito toglierle. Il blocco di disjointness delle classi principali perde così due membri. |
| Rimosse le datatype property `budgetTier`, `playerCount`, `hasSteamAppId`, `hasIGDBId`, `officialWebsite`, `gameDescription`, `description` e `awardYear`, e la object property `partOfFranchise` | Nel build Wikidata non hanno nessun valore. |
| Rimosse `ExclusiveRelease`, `GameWithSingleDeveloper` (≤1, solo condizione necessaria) e `StandaloneGame` (complemento) | Dai dati non ricevono mai istanze: le prime due solo se asserite, la terza solo con la chiusura del mondo. Il test di cardinalità usa ora una restrizione anonima (`availableOn max 1`). |
| `subsidiaryOf` resta e si aggiungono `manufacturedBy`/`manufacturerOf` (Wikidata P176) e `publishedByGroup`, super-proprietà di `publishedBy` e catena `publishedBy ∘ subsidiaryOf` | Sono popolate nella demo con fatti verificati e servono alle deduzioni su gruppi e console. |
| Aggiunte `PlatformHolder`, `FirstPartyGame`, `LongRunningFranchise` e `FranchiseWithStudioChange` | Sono deduzioni a livello di azienda e di serie, ricavate dai giochi. |
| Aggiunte `LateEntry`, `LongRunningOriginal` e `AcclaimedSequel` | Sono classi definite "a strati" per mostrare inferenze non banali: sfruttano la transitività di `sequelOf` e le classi definite su altre classi definite. |
| Aggiunte `SelfPublishedGame`, `SequelByDifferentStudio`, `FirstPartyOnRivalConsole`, `MustPlayGame` e `CouchCoopCandidate` | Sono le classi di arrivo delle regole SWRL in `swrl_rules.ttl`. |

## Cosa resta invariato

Tutto il resto coincide con lo schema scritto a mano:
- gerarchia e partizioni delle piattaforme;
- generi e modalità;
- tutte le altre classi definite (template per piattaforma, genere, modalità, publisher nominale e paese, più cardinalità minime, `Developer`/`Publisher` come ruoli);
- inverse, transitive (`sequelOf`, `subsidiaryOf`), symmetric, irreflexive e asymmetric;
- le 3 catene di proprietà;
- le datatype property funzionali, cioè gli assiomi DL-only, che qui si **tengono** perché servono a HermiT;
- gli allineamenti `skos:closeMatch` con Wikidata e Dublin Core.
