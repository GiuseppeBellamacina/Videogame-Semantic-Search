# Ontologia dei videogiochi per Protégé

## File

Tutti i file `.ttl` sono generati da script Python con rdflib (`Graph.add`, `BNode`, `Collection`, `serialize`); nessuno è scritto a mano.

| File | Contenuto |
|---|---|
| `schema.ttl` | **Lo schema vuoto**: classi, proprietà e assiomi, nessun gioco. Generato da `generate_schema.py`. |
| `regole.ttl` | Le regole SWRL. Generate da `generate_schema.py`. |
| `dati.ttl` | **Solo le asserzioni**: 95 giochi (11 serie e 6 titoli singoli), 28 nuove edizioni, PEGI, personaggi, persone, aziende e piattaforme. Nessuna conclusione. Generato da `build_data.py`. |
| `videogiochi.ttl` | **Il file da aprire in Protégé**: importa schema, dati e regole. Generato da `generate_tests.py`. |
| `test/` | Cinque errori da far trovare a HermiT e un caso di `sameAs` corretto. Generati da `generate_tests.py`. |
| `fonti/dataset.json` | Il dataset revisionato da cui nasce `dati.ttl`. |
| `fonti/correzioni.json` | Correzioni manuali, ognuna con l'URL della fonte (per esempio i PEGI presi da pegi.info). |
| `fonti/wikidata/` | Le risposte di Wikidata salvate da `fetch_wikidata.py`. |
| `fonti/agente/` | I fatti di trama estratti da `research_agent.py`, con URL e citazione per ciascuno. |
| `check_reasoning.py` | Strumento extra: lancia HermiT da Python e controlla le deduzioni attese (quanti, lo scrive in `relazione/controlli.tex`). |
| `relazione/` | La relazione LaTeX; appendici e numeri (`numeri.tex`, `controlli.tex`) sono generati dagli script. |

```bash
uv run python protege/generate_schema.py      # schema.ttl, regole.ttl, relazione/appendice.tex
uv run python protege/build_data.py           # dati.ttl da fonti/dataset.json + fonti/correzioni.json
uv run python protege/generate_tests.py       # videogiochi.ttl e test/
uv run --with owlready2==0.46 python protege/check_reasoning.py
```

### Da dove vengono i dati

1. **Wikidata.** `uv run python protege/fetch_wikidata.py` scarica con una sola query SPARQL i dati strutturati di tutti i giochi (date, studi, piattaforme, registi, motori, PEGI, Metacritic, premi, seguiti), li salva in `fonti/wikidata/` ed elenca dove il dataset differisce da Wikidata.
2. **Trama, con un agente.** Personaggi, uccisioni e natura dei personaggi non sono su Wikidata. `research_agent.py` è un agente [LangChain](https://docs.langchain.com/oss/python/langchain/agents) (`create_agent`) con due strumenti, `find_game` (Wikidata) e `read_plot` (la sezione della trama di Wikipedia), e risposta strutturata (pydantic). Tre limiti ne tengono sotto controllo il costo: al più 5 chiamate al modello (`ModelCallLimitMiddleware`), `recursion_limit` 12 (il valore predefinito di `create_agent` è 9.999) e 6.000 token in uscita. Una prova con deepagents, senza limiti stretti, non si fermava (574.000 token in ingresso per un solo gioco). Funziona così:
   - **la lista dei giochi** la prende dall'ontologia, con una query SPARQL su `dati.ttl`; per giochi nuovi basta un file con un titolo per riga;
   - **per ogni gioco** l'agente riceve il titolo, l'identificativo Wikidata e la pagina Wikipedia (per un gioco nuovo li trova con `find_game`), legge la trama con `read_plot` (sottosezioni comprese, al massimo 20.000 caratteri) e restituisce un JSON in cui ogni fatto ha l'URL e una frase citata alla lettera; riceve anche i nomi dei personaggi già presenti nella serie;
   - **lo script controlla** che ogni citazione compaia davvero nel testo scaricato, che il personaggio compaia nella pagina (con Dark Souls il modello aveva scritto "Ashen One", il protagonista di un altro gioco, citando una frase vera) e riporta i nomi a quelli già nel dataset ("Gwyn" diventa "Gwyn, Lord of Sunlight"); scarta i fatti non verificabili, le uccisioni che dipendono dal finale e i suicidi; il risultato va in `fonti/agente/<qid>.json`, con l'elenco dei fatti scartati;
   - **`--applica`** porta i fatti nel dataset; per un gioco nuovo aggiunge anche i dati strutturati di Wikidata (date, studi, piattaforme, PEGI, Metacritic, registi, motore).
   ```bash
   # nel file .env alla radice: OPENAI_API_KEY=... (o ANTHROPIC_API_KEY=... con RESEARCH_MODEL=anthropic:<modello>)
   uv run python protege/research_agent.py                    # tutti i giochi dell'ontologia non ancora analizzati
   uv run python protege/research_agent.py Q796529            # un solo gioco (Far Cry 3)
   uv run python protege/research_agent.py --nuovi lista.txt  # giochi nuovi, un titolo per riga
   uv run python protege/research_agent.py --applica
   uv run python protege/build_data.py
   ```
3. **Correzioni.** Ciò che le fonti sbagliano o non hanno va in `fonti/correzioni.json`, sempre con l'URL della fonte.

## Giochi

- **The Legend of Zelda (21):** dal primo (1986) a Echoes of Wisdom (2024).
- **Super Mario (13):** da Super Mario Bros. (1985) a Wonder (2023).
- **Assassin's Creed (14):** dal primo (2007) a Shadows (2025).
- **Fallout (6):** 1, 2, 3, New Vegas, 4, 76.
- **Grand Theft Auto (8):** dal primo (1997) a GTA VI (2026).
- **The Witcher (3):** 1, 2, 3.
- **Mass Effect (3):** 1, 2, 3.
- **Dark Souls (3):** I, II, III.
- **Portal (2):** Portal, Portal 2.
- **Halo (8):** Combat Evolved, 2, 3, ODST, Reach, 4, 5: Guardians, Infinite.
- **Far Cry (8):** Far Cry, 2, 3, 4, Primal, 5, New Dawn, 6.
- **Giochi singoli (6):** Dispatch, Elden Ring, Cyberpunk 2077, Clair Obscur: Expedition 33, Minecraft, The Walking Dead.
- **Nuove edizioni (28):** remaster, remake e raccolte, tra cui Halo: Campaign Evolved (2026) e il remake di Ocarina of Time per Switch 2 (5 novembre 2026).

L'elenco completo, con anno e sviluppatore, è nell'appendice della relazione.

## Usare HermiT in Protégé

1. **Aprire l'ontologia.** Avvia `Protege-5.6.9-win/Protege-5.6.9/Protege.exe`, poi File > Open > `protege/videogiochi.ttl`. Il tab *Active ontology* mostra le tre ontologie importate. Con *File > Open* di `schema.ttl` si vede lo schema da solo.
2. **Avviare il ragionamento.**
   - Nel menu Reasoner seleziona HermiT, poi scegli Start reasoner (richiede pochi secondi).
   - Dopo ogni modifica scegli Reasoner > Synchronize reasoner.
   - Per vedere anche le relazioni dedotte, controlla che in Reasoner > Configure… > *Displayed inferences* siano spuntate "Class assertions" e "Object property assertions".
3. **Distinguere asserito e dedotto.**
   - **Individui** (tab *Entities > Individuals*): le righe con lo sfondo giallo sono dedotte da HermiT, le altre sono scritte in `dati.ttl`. Il "?" accanto a una riga gialla apre la *spiegazione*, cioè gli assiomi da cui segue.
   - **Classi** (tab *Entities > Classes*): il menu sopra l'albero passa da "Asserted" a "Inferred". Nella vista inferita le classi definite compaiono al loro posto, e il tab *Instances* di una classe elenca anche gli individui dedotti.
   - **DL Query** (Window > Tabs > DL Query): scrivi il nome di una classe o un'espressione, per esempio `FirstPartyGame and SequelGame`, e spunta "Instances". Il risultato include ciò che il reasoner ha dedotto.
   - **Tutto ciò che è stato dedotto, in un file:** File > Export inferred axioms as ontology…, scegliendo i tipi di assiomi. Il file salvato contiene solo le conclusioni e si può confrontare con `dati.ttl`.
4. **Che cosa HermiT non deduce, e perché:**
   - le negazioni: con il mondo aperto, "non scritto" non significa "falso";
   - l'uguaglianza tra individui dichiarati diversi;
   - le relazioni nel tempo: OWL non sa che Bethesda è di Microsoft solo dal 2021;
   - dentro le regole SWRL, i valori ottenuti da catene o transitività. Per questo "pubblicato da un costruttore di console o da una sua controllata" è una classe OWL (`FirstPartyGame`), mentre `FirstPartyOnRivalConsole`, che deve confrontare due aziende, usa le regole `PublisherGroup` e `ParentGroup` per salire la catena delle controllanti un passo alla volta.

## Deduzioni da mostrare (dove cliccare)

Le classi si cercano nel tab *Classes*, sezione *Instances*; gli individui nel tab *Individuals*.

| Individuo o classe | Cosa compare in giallo | Perché |
|---|---|---|
| `character/Gwyn_Lord_of_Sunlight` | `DeceasedCharacter`, `DefeatedVillain` | Nei dati c'è un `Killing` con vittima Gwyn e assassino il Prescelto. `DeceasedCharacter ≡ Character ⊓ ∃victimIn.Killing` (si vede in "Equivalent To"); la regola `DefeatedVillain` lo rende cattivo sconfitto dall'eroe. |
| `character/Chosen_Undead` | `Killer` | Lo stesso fatto, letto dall'altra parte: `Killer ≡ Character ⊓ ∃killerIn.Killing`. |
| `character/Jason_Brody`, `character/Link` | `MultipleKiller` | Hanno ucciso almeno due personaggi (inversa `kills`, cardinalità ≥ 2). |
| `Far_Cry_3`, `The_Legend_of_Zelda_Twilight_Princess` | `ViolentStoryGame` | Ha almeno un `Killing` con `inGame` uguale al gioco: l'uccisione conta solo nel gioco in cui avviene. |
| `Grand_Theft_Auto_IV` | `RealisticViolenceGame` | Ha uccisioni nella trama ed è PEGI 16 o 18. |
| `character/Cortana` | `Synthetic`, `RogueAI` | Nei dati c'è solo `builtBy` Catherine Halsey: chi è costruito da qualcuno è `Synthetic`. In Halo 5 è l'antagonista, quindi IA ribelle. Lo stesso per GLaDOS e Wheatley (Aperture Science). |
| `character/Link`, `character/Chell` | `PlayerCharacter` | Il giocatore li controlla in almeno un gioco (`playableIn`). |
| `platform/PlayStation_5` | `CurrentGenerationConsole` | Nei dati c'è solo la generazione (9): la classe è definita come console di generazione ≥ 9. |
| `character/Ganondorf` | `ReturningCharacter` | Ucciso in Twilight Princess e in Tears of the Kingdom; ricompare in giochi usciti dopo la sua morte. |
| `Grand_Theft_Auto_San_Andreas`, `The_Legend_of_Zelda_Breath_of_the_Wild` | `ReturnAfterDeathGame` | Catalina, uccisa in GTA III, ricompare in San Andreas; Ganondorf ricompare in Breath of the Wild. |
| `Halo_Combat_Evolved` | `StillPlayable`, `MustPlayGame`, `GOTYWinner` | Il remake Campaign Evolved è su PS5; Metacritic 97; D.I.C.E. 2002. |
| `Far_Cry_2`, `Far_Cry_6` | `SequelByDifferentStudio`, `EngineChangeSequel` (FC2), `ExternalEngineGame` (FC6) | FC2 passa da Crytek/CryEngine a Ubisoft Montreal/Dunia; FC6 è di Ubisoft Toronto con il motore di Montreal. |
| `Cyberpunk_2077`, `The_Walking_Dead` | `Adaptation` | Sono tratti da un gioco da tavolo e da un fumetto (`basedOn`). |
| `person/Hidetaka_Miyazaki` | `GameDirector`, `StudioHead` | Le definizioni `∃directorOf.VideoGame` e `∃heads.Company`. |
| `Mass_Effect`, `Fallout_4` | `FirstPartyGame` | Editore controllato da un costruttore di console (Xbox Game Studios e Bethesda Softworks → Microsoft): `∃publishedBy.(PlatformHolder ⊔ ∃subsidiaryOf.PlatformHolder)`. |
| `Mass_Effect`, `Fallout_4`, `Fallout_New_Vegas`, `Minecraft` | `FirstPartyOnRivalConsole` (regole `PublisherGroup`, `ParentGroup`, `ConsoleMaker`) | Il gioco è del gruppo di un costruttore di console ed è uscito sulla console di un altro (Microsoft → PlayStation, Nintendo Switch). Halo 4, Breath of the Wild e Mass Effect 2 no. |
| `Fallout_New_Vegas` | `FirstPartyGame`, `ExternalEngineGame` | Bethesda Softworks → ZeniMax → Microsoft (solo perché oggi è così: limite del tempo); motore Gamebryo di un'altra azienda. |
| `company/Obsidian_Entertainment`, `company/AdHoc_Studio` | `FoundedByVeterans` | I fondatori lavoravano per uno sviluppatore (Black Isle, Telltale). |
| `Grand_Theft_Auto_III` | `StillPlayable`, `LateEntry`, `ExternalEngineGame` | La Definitive Edition è uscita su PS5; è il terzo capitolo; usa RenderWare di Criterion. |
| `The_Witcher` | `Adaptation` | È tratto dalla saga di Sapkowski. |
| `character/Leonardo_da_Vinci` | `HistoricalCharacter` | Interpreta una persona reale. |
| `character/GLaDOS` | `RogueAI`, `RecurringCharacter` | È un'IA antagonista, presente in Portal e Portal 2. |
| `franchise/Halo`, `franchise/Fallout` | `FranchiseWithStudioChange`, `TransmediaFranchise` | Halo 4 è di 343 Industries dopo Bungie, Fallout 3 di Bethesda dopo Black Isle; da entrambe è nata una serie TV. |
| `Grand_Theft_Auto` | `VideoGame` | Il tipo non è asserito; deriva da dominio e range delle sue proprietà. |
| `Assassins_Creed_II` | `HistoricalGame` | Ha personaggi che interpretano persone reali: una specie di "genere" dedotto. |
| `Portal_2`, `Halo_Infinite`, `Mass_Effect_2` | `SciFiGame` | Personaggi sintetici (GLaDOS, Wheatley) o alieni (Arbiter, Atriox, Garrus, Liara). |
| `person/Hidetaka_Miyazaki`, `person/Shigeru_Miyamoto` | `ProlificDirector` | Almeno tre giochi diretti (`≥3 directorOf.VideoGame`). |
| `company/Bungie`, `company/Rockstar_North` | `ProlificDeveloper` | Almeno cinque giochi sviluppati. |
| `company/Halo_Studios`, `company/Nintendo_EPD` | `FirstPartyStudio` | Sono un costruttore di console o una sua controllata (`PlatformHolder ⊔ ∃subsidiaryOf.PlatformHolder`); BioWare e Capcom no. |
| `Portal_2`, `Minecraft`, `Dispatch` | `SelfPublishedGame` | Sviluppatore ed editore sono la stessa azienda (regola `SelfPublished`). |
| `franchise/Super_Mario`, `franchise/The_Legend_of_Zelda` | `FranchiseWithStudioChange` | Per Mario il cambio è sempre tra divisioni Nintendo; per Zelda ci sono anche passaggi esterni, gli episodi di Flagship (Capcom). |
| `Grand_Theft_Auto_V`, `Dark_Souls`, `The_Legend_of_Zelda_Ocarina_of_Time` | `Pegi18Game`, `Pegi16Game`, `Pegi12Game` (e `Pegi3Game`, `Pegi7Game`) | La fascia di età dal solo valore di `pegiRating`, senza bisogno di uccisioni nella trama. |
| `Grand_Theft_Auto_III`, `Halo_Combat_Evolved`, `The_Legend_of_Zelda_Ocarina_of_Time` | `ClassicGame`, `ClassicStillPlayable` | Usciti prima del 2005 (intervallo di date) e giocabili oggi su una console attuale (catena sul remaster). |
| `Grand_Theft_Auto_IV`, `Fallout_4` | `EngineChangeSequel` | GTA IV passa da RenderWare a RAGE; Fallout 4 da Gamebryo a Creation Engine. |

## Test

Apri un file di `test/` e avvia HermiT. Per i cinque errori Protégé segnala l'ontologia inconsistente e offre **Explain inconsistent ontology**.

| File | Atteso |
|---|---|
| `errore_disgiunzione.ttl` | inconsistente: una piattaforma è sia console sia PC |
| `errore_funzionale.ttl` | inconsistente: Portal 2 ha due punteggi Metacritic |
| `errore_cardinalita.ttl` | inconsistente: Breath of the Wild è "su al più una piattaforma", ma è uscito su Wii U e Switch |
| `errore_chiave.ttl` | inconsistente: due giochi hanno lo stesso identificativo Wikidata ma sono dichiarati diversi |
| `errore_proprieta_disgiunte.ttl` | inconsistente: Ocarina of Time 3D è remaster di Ocarina of Time e anche suo prequel, ma `remasterOf` e `prequelOf` sono disgiunte |
| `deduzione_sameas.ttl` | consistente: HermiT deduce che "NX" è la Nintendo Switch |

## Screenshot per la relazione

Salvali in `relazione/figure/` con questi nomi; appena il file esiste, il riquadro segnaposto nel PDF viene sostituito dall'immagine. Le stesse istruzioni sono scritte dentro i riquadri della relazione.

Prima di tutto: File > Open > `protege/videogiochi.ttl`, poi Reasoner > HermiT > Start reasoner e attendi la fine. Se dopo una modifica i colori gialli non compaiono, Reasoner > Synchronize reasoner.

1. **`gerarchia_inferita.png`.** Tab Entities > Classes. Cambia il menu sopra l'albero da *Asserted* a *Inferred*, espandi `Character`, `Company` e `Franchise`, ritaglia il solo pannello dell'albero.
2. **`spiegazione_gwyn.png`.** Tab Entities > Individuals, cerca *Gwyn* e seleziona *Gwyn, Lord of Sunlight*. Nel pannello Description, sotto Types, la riga gialla `DeceasedCharacter` è dedotta: clicca il punto interrogativo accanto e fotografa la finestra della spiegazione.
3. **`individuo_fallout_new_vegas.png`.** Tab Individuals, cerca *New Vegas*, selezionalo e fotografa il pannello Description: in giallo devono esserci `FirstPartyGame`, `FirstPartyOnRivalConsole`, `ExternalEngineGame` e `SequelByDifferentStudio`.
4. **`swrl_rules.png`.** Window > Tabs > SWRLTab. Allarga la colonna *Rule* e fotografa la tabella delle regole. Se è vuota, controlla in Active ontology > Ontology imports che `regole` sia importata.
5. **`inconsistenza.png`.** File > Open > `protege/test/errore_cardinalita.ttl` (in una nuova finestra se lo chiede), Reasoner > HermiT > Start reasoner. Dall'avviso di ontologia inconsistente scegli *Explain inconsistent ontology* e fotografa gli assiomi in conflitto.

Altre schermate che fanno bella figura dal vivo, ma non servono alla relazione: DL Query (Window > Tabs > DL Query) con `SequelByDifferentStudio and EngineChangeSequel` e *Instances* spuntato; la spiegazione di `character/Cortana` come `RogueAI`.

Nessun plugin aggiuntivo è necessario.
