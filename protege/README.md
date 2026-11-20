# Ontologia dei videogiochi per Protégé

## File

| File | Contenuto |
|---|---|
| `schema.ttl` | **Lo schema vuoto**: classi, proprietà e assiomi, nessun gioco. È generato da `generate_schema.py`. |
| `dati.ttl` | **Solo le asserzioni**: 95 giochi (11 serie e 6 titoli singoli), 28 nuove edizioni, classificazioni PEGI, personaggi, persone, aziende e piattaforme, verificati su Wikipedia e Wikidata. Non contiene nessuna conclusione. |
| `regole.ttl` | Le 11 regole SWRL, generate da `generate_schema.py`. |
| `videogiochi.ttl` | **Il file da aprire in Protégé**: importa schema, dati e regole. |
| `test/` | Quattro errori da far trovare a HermiT e un caso di `sameAs` corretto. |
| `generate_schema.py` | Genera `schema.ttl`, `regole.ttl` e `relazione/appendice.tex` a partire dalle stesse tabelle. |
| `check_reasoning.py` | Strumento extra: lancia HermiT da Python e controlla le 182 deduzioni attese. |
| `relazione/` | La relazione LaTeX; le appendici sono generate. |

```bash
uv run python protege/generate_schema.py
uv run --with owlready2==0.46 python protege/check_reasoning.py
```

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
   - dentro le regole SWRL, i valori ottenuti da catene o transitività. Per questo il gruppo di un editore è calcolato da due regole, un passo alla volta.

## Deduzioni da mostrare (dove cliccare)

Le classi si cercano nel tab *Classes*, sezione *Instances*; gli individui nel tab *Individuals*.

| Individuo o classe | Cosa compare in giallo | Perché |
|---|---|---|
| `character/Gwyn_Lord_of_Sunlight` | `DeceasedCharacter`, `DefeatedVillain` | È stato ucciso dal Prescelto: il dominio di `killedBy` lo fa morto, la regola lo rende cattivo sconfitto dall'eroe. |
| `character/Chosen_Undead` | `Killer` | Lo stesso fatto, letto dall'altra parte: il range di `killedBy`. |
| `character/Jason_Brody`, `character/Link` | `MultipleKiller` | Hanno ucciso almeno due personaggi (inversa `kills`, cardinalità ≥ 2). |
| `Far_Cry_3`, `The_Legend_of_Zelda_Twilight_Princess` | `ViolentStoryGame` | Due assassini, oppure uno che uccide più volte. |
| `Grand_Theft_Auto_IV` / `The_Legend_of_Zelda_Ocarina_of_Time` | `RealisticViolenceGame` / `FantasyViolenceGame` | Stessa violenza nella storia, la distingue il PEGI: ≥ 16 realistica, ≤ 12 di fantasia. |
| `character/Cortana` | `ArtificialIntelligence`, `DigitalMind`, `RogueAI` | Nei dati c'è solo `mindCopiedFrom` Catherine Halsey: il dominio la fa IA, e Halsey è umana. In Halo 5 è l'antagonista, quindi IA ribelle. |
| `Halo_Combat_Evolved` | `StillPlayable`, `MustPlayGame`, `GOTYWinner` | Il remake Campaign Evolved è su PS5; Metacritic 97; D.I.C.E. 2002. |
| `Far_Cry_2`, `Far_Cry_6` | `SequelByDifferentStudio`, `EngineChangeSequel` (FC2), `ExternalEngineGame` (FC6) | FC2 passa da Crytek/CryEngine a Ubisoft Montreal/Dunia; FC6 è di Ubisoft Toronto con il motore di Montreal. |
| `Cyberpunk_2077`, `The_Walking_Dead` | `Adaptation` | Sono tratti da un gioco da tavolo e da un fumetto (`basedOn`). |
| `Minecraft` | `FirstPartyOnRivalConsole` | Mojang → Xbox Game Studios → Microsoft, ed è uscito su PlayStation e Switch. |
| `person/Hidetaka_Miyazaki` | `GameDirector`, `StudioHead` | Il range di `directedBy` e il dominio di `heads`. |
| `Mass_Effect` | `FirstPartyGame`, `FirstPartyOnRivalConsole`, `RemasteredClassic` | Xbox Game Studios → Microsoft, costruttore della Xbox 360; il gioco è uscito anche su PS3; ha la Legendary Edition. |
| `Fallout_New_Vegas` | `VeteransReturn`, `FirstPartyOnRivalConsole`, `ExternalEngineGame` | Obsidian, fondata da ex Black Isle (che aveva fatto Fallout 2); Bethesda Softworks → ZeniMax → Microsoft; motore Gamebryo. |
| `company/Obsidian_Entertainment`, `company/AdHoc_Studio` | `FoundedByVeterans` | I fondatori lavoravano per uno sviluppatore (Black Isle, Telltale). |
| `Grand_Theft_Auto_III` | `StillPlayable`, `LateEntry`, `ExternalEngineGame` | La Definitive Edition è uscita su PS5; è il terzo capitolo; usa RenderWare di Criterion. |
| `The_Witcher` | `LiteraryAdaptation`, relazione `techLinkedTo Mass_Effect` | È tratto dalla saga di Sapkowski e usa il motore Aurora di BioWare. |
| `character/Leonardo_da_Vinci` | `HistoricalCharacter` | Interpreta una persona reale. |
| `character/GLaDOS` | `RogueAI`, `RecurringVillain` | È un'IA antagonista, presente in Portal e Portal 2. |
| `franchise/Halo`, `franchise/Fallout` | `FranchiseWithStudioChange`, `TransmediaFranchise` | Halo 4 è di 343 Industries dopo Bungie, Fallout 3 di Bethesda dopo Black Isle; da entrambe è nata una serie TV. |
| `Grand_Theft_Auto` | `VideoGame` | Il tipo non è asserito; deriva da dominio e range delle sue proprietà. |
| `Grand_Theft_Auto_IV`, `Fallout_4` | `EngineChangeSequel` | GTA IV passa da RenderWare a RAGE; Fallout 4 da Gamebryo a Creation Engine. |

## Test

Apri un file di `test/` e avvia HermiT. Per i quattro errori Protégé segnala l'ontologia inconsistente e offre **Explain inconsistent ontology**.

| File | Atteso |
|---|---|
| `errore_disgiunzione.ttl` | inconsistente: una piattaforma è sia console sia PC |
| `errore_funzionale.ttl` | inconsistente: Portal 2 ha due punteggi Metacritic |
| `errore_cardinalita.ttl` | inconsistente: Breath of the Wild è "su al più una piattaforma", ma è uscito su Wii U e Switch |
| `errore_chiave.ttl` | inconsistente: due giochi hanno lo stesso identificativo Wikidata ma sono dichiarati diversi |
| `deduzione_sameas.ttl` | consistente: HermiT deduce che "NX" è la Nintendo Switch |

## Screenshot per la relazione

Salvali in `relazione/figure/` con questi nomi:
- `gerarchia_inferita.png`: la vista "Inferred" delle classi;
- `spiegazione_gwyn.png`: la spiegazione di Gwyn come `DeceasedCharacter`;
- `individuo_fallout_new_vegas.png`: Fallout: New Vegas con i tipi dedotti in giallo;
- `swrl_rules.png`: il tab SWRLTab;
- `inconsistenza.png`: la spiegazione di `errore_cardinalita.ttl`.

Nessun plugin aggiuntivo è necessario.
