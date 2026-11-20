# L'ontologia in Protégé

Questa cartella contiene l'ontologia dei videogiochi così come si apre in Protégé: lo schema generato da uno script, un dataset dimostrativo curato a mano, le regole SWRL e i test di inconsistenza. Il sito web e la pipeline in `ontology/` qui non servono.

## File

| File | Contenuto |
|---|---|
| `videogames.ttl` | **Il file da aprire in Protégé.** Importa schema, dati demo e regole. |
| `generate_schema.py` | Genera lo schema e le regole SWRL a partire da tabelle dichiarative, usando solo rdflib come negli esempi del corso. **Non modificare a mano i `.ttl` generati.** |
| `schema_generated.ttl` | Lo schema (TBox): 105 classi (47 primitive, 58 definite), 27 object property, 14 datatype property, 4 catene, 6 blocchi di disgiunzione e una `hasKey`. Contiene solo elementi che hanno istanze. |
| `swrl_rules.ttl` | Le 6 regole SWRL, tutte DL-safe ed eseguite da HermiT. La soglia di punteggio è un intervallo di dati (`xsd:integer[> 94]`), come negli esempi del corso, non una built-in `swrlb:`. |
| `abox_demo.ttl` | I dati (ABox), curati a mano e verificati su Wikidata. Contengono 25 giochi di 7 serie (GTA, Zelda, Dark Souls, The Witcher, Mass Effect, Portal, Halo), le aziende con i loro gruppi (`subsidiaryOf`) e i costruttori delle console (`manufacturedBy`). |
| `inconsistencies/` | Un file per ogni test (vedi più sotto). |
| `catalog-v001.xml` | Indica a Protégé dove trovare i file locali corrispondenti agli `owl:imports`. |
| `check_reasoning.py` | Strumento extra, l'unico fuori dallo stile del corso. Lancia HermiT da Python con owlready2 e verifica 86 condizioni: consistenza, inferenze, regole e test. |
| `SCHEMA_DIFF.md`, `ANALISI.md` | Confronto con il vecchio schema scritto a mano e analisi dell'ontologia. |

## Comandi (dalla radice del repository)

```bash
uv run python protege/generate_schema.py           # rigenera schema e regole (--diff: confronto con il vecchio schema)
uv run --with owlready2==0.46 python protege/check_reasoning.py   # verifica tutto con HermiT
```

## Uso in Protégé

Protégé 5.6.9 si trova in `Protege-5.6.9-win/` (avvialo con `Protege.exe`). Contiene già Java e i plugin che servono: HermiT, SWRLTab, OntoGraf ed Explanation Workbench. Pellet non è necessario.

1. **Apri l'ontologia.** File > Open > `protege/videogames.ttl`. Nel tab *Active ontology*, alla voce *Imported ontologies*, compaiono schema, demo e regole. Se vuoi vedere solo lo schema, apri `schema_generated.ttl`.
2. **Avvia il reasoner.** Reasoner > HermiT, poi Reasoner > Start reasoner. Dopo ogni modifica usa Reasoner > Synchronize reasoner. L'ontologia è consistente e nessuna classe deve risultare insoddisfacibile (in rosso).
3. **Cosa guardare.**
   - *Entities > Classes*, vista "Inferred": `LateEntry` e `AcclaimedSequel` compaiono sotto `SequelGame`.
   - *Individuals*, `Mass_Effect`: in giallo i tipi dedotti `FirstPartyGame` e `FirstPartyOnRivalConsole`. Il "?" accanto a `FirstPartyGame` mostra la spiegazione, che passa per la catena `publishedBy ∘ subsidiaryOf`, l'inversa `manufacturerOf` e due classi definite.
   - `franchise/Halo` risulta `FranchiseWithStudioChange`; `franchise/Grand_Theft_Auto` risulta `LongRunningFranchise`.
   - `dev/Halo_Studios` è `subsidiaryOf` Microsoft per transitività.
   - `Grand_Theft_Auto` non ha tipo asserito, ma risulta `VideoGame` grazie a dominio e range.
   - Tab *DL Query*, per esempio `FirstPartyGame`, `SequelGame and HighlyRatedGame` o `sequelOf value Grand_Theft_Auto` (spunta "Instances").
4. **OntoGraf** (Window > Tabs > OntoGraf): seleziona `Grand_Theft_Auto_VI` ed espandi la serie.
5. **SWRL.** Le regole si vedono in Window > Tabs > SWRLTab. Le applica HermiT allo Start reasoner, senza bisogno di Drools. Nota: negli atomi delle regole HermiT vede solo relazioni asserite, non quelle dedotte da catene o transitività. Per questo la regola first-party ha due versioni (editore diretto ed editore controllato).
6. **Inconsistenze.** Apri un file di `inconsistencies/` e avvia HermiT. Protégé segnala l'ontologia inconsistente e propone **Explain inconsistent ontology**.
   - `inc1_disjoint.ttl`: una piattaforma è sia console sia PC (classi disgiunte).
   - `inc2_functional.ttl`: Portal 2 ha due `metacriticScore` (proprietà funzionale).
   - `inc3_cardinality.ttl`: Tears of the Kingdom è "su al più una piattaforma", ma è su Switch e Switch 2, dichiarate diverse.
   - `inc4_key.ttl`: due giochi hanno lo stesso `hasWikidataId` (`hasKey`) ma sono dichiarati diversi.
   - `inc3b_sameas.ttl` **non** è inconsistente. Splatoon 2 è collegato a "Nintendo Switch" e a "NX", il nome in codice della Switch, non dichiarati diversi. Il reasoner deduce NX `sameAs` Nintendo Switch, che è corretto. Il confronto con `inc3` mostra mondo aperto e assenza di Unique Name Assumption.

## Caricare, creare ed esportare in Protégé

- **Aprire:** File > Open. Per aggiungere un'altra ontologia: *Active ontology > Imported ontologies* > "+".
- **Salvare:** File > Save as… permette di scegliere il formato (Turtle, RDF/XML, OWL/XML…).
- **Solo lo schema:** Refactor > Copy/move/delete axioms… e scegli gli assiomi di classi e proprietà.
- **Le deduzioni:** File > Export inferred axioms as ontology…
- **Tutto in un file:** Refactor > Merge ontologies.

## Screenshot per la relazione

Salvali in `protege/relazione/figure/` con questi nomi. Finché mancano, la relazione mostra un riquadro segnaposto.

| File | Cosa |
|---|---|
| `gerarchia_inferita.png` | La gerarchia "Inferred" con `VideoGame` espansa (`SequelGame` > `LateEntry`, `AcclaimedSequel`). |
| `individuo_mass_effect.png` | `Mass_Effect` nel tab Individuals, con i tipi dedotti in giallo. |
| `spiegazione_firstparty.png` | La spiegazione ("?") di `Mass_Effect` come `FirstPartyGame`. |
| `ontograf_gta.png` | OntoGraf della serie GTA. |
| `swrl_rules.png` | Il tab SWRLTab con le regole. |
| `inconsistenza.png` | La finestra "Explain inconsistent ontology" di `inc3_cardinality.ttl`. |
