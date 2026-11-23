# Handoff: ontologia Protégé

Branch `feat/protege-ontology`, cartella `protege/`. Tutto (schema, regole, dati, test, appendici della relazione) si rigenera con gli script; i comandi sono nel README.

## Stato
- 96 classi (60 definite), 49 object property, 5 datatype property, 20 regole SWRL, 95 giochi.
- `check_reasoning.py` (HermiT via owlready2): tutti i controlli superati, compresi i 6 test in `test/` (5 errori e 1 `sameAs` corretto). 287 controlli, circa 4 minuti in tutto (il ragionamento su `videogiochi.ttl` da solo circa 110 secondi). Serve il JRE di Protégé (`Protege-5.6.9/jre`) o `JAVA_EXE`.
- Relazione: 14 pagine, corpo fino a pagina 7, compila senza errori né warning, senza bibliografia. I numeri (classi, regole, controlli) sono scritti dagli script in `relazione/numeri.tex` e `controlli.tex`.
- `DEDUZIONI.md`: 19 sezioni con le deduzioni non banali, con fatti, assiomi e regole; l'ultima racconta una prova scartata (chiusura con nominali).
- Novità di questa revisione: le fasce di età `Pegi3Game`...`Pegi18Game` (restrizione `hasValue` sul PEGI), `ClassicGame` e `ClassicStillPlayable` (intervallo di date + catena sul remaster + classe dedotta), `remasterOf` e `prequelOf` disgiunte con il test `errore_proprieta_disgiunte`, bibliografia tolta, bug di `research_agent.py` sulle sezioni con sottosezioni corretto.

## Da fare a mano
1. **Controllo in Protégé.** Aprire `protege/videogiochi.ttl`, Reasoner > HermiT > Start reasoner: l'ontologia deve risultare consistente, e SWRLTab deve mostrare le 20 regole. Il tempo in Protégé non è stato misurato (con owlready2/HermiT circa 110 secondi).
2. **Screenshot.** `relazione/figure/` è vuota: i 5 riquadri segnaposto della relazione contengono le istruzioni, ripetute nel README (`gerarchia_inferita`, `spiegazione_gwyn`, `individuo_fallout_new_vegas`, `swrl_rules`, `inconsistenza`). Con i PNG presenti, i riquadri spariscono da soli.
3. **Differenze con Wikidata.** `fetch_wikidata.py` ne elenca 66 non riviste.
4. **Agente.** Ora è un agente LangChain (`create_agent`, `langchain>=1.5.2` in `pyproject.toml` al posto di deepagents, `uv.lock` aggiornato) con due strumenti (`find_game`, `read_plot`) e tre limiti: 5 chiamate al modello, `recursion_limit` 12 (predefinito 9.999), 6.000 token in uscita. La prima versione con deepagents non si fermava (Portal: 40 passi, 573.920 token, circa 5,8 centesimi, nessun risultato). Prove con `claude-haiku-5-5` (2 chiamate al modello a gioco): Portal 5.504 token in e 476 out (0,08 centesimi), Dark Souls 5.298/721, Far Cry 3 6.773/1.505 (0,14 centesimi). Far Cry 3: protagonisti, antagonisti e le 4 uccisioni uguali al dataset. Portal: Chell e GLaDOS, come nel dataset. Dark Souls: il modello ha scritto "Ashen One" (protagonista di Dark Souls III, non nel testo) con una citazione vera; ora `mentioned()` scarta i nomi che non compaiono nella pagina e `canonical()` riporta i nomi a quelli del dataset ("Gwyn" → "Gwyn, Lord of Sunlight"); per Dark Souls resta senza protagonista perché la pagina dice solo "the player character". Da fare: lanciarlo sugli altri giochi (stima 10-15 centesimi per tutti e 95): `uv run python protege/research_agent.py`, poi `--applica`.

## Limiti noti
- Dataset e agente: i fatti di trama del dataset sono stati raccolti con Claude Sonnet e Opus in sessioni con ricerca web e poi rivisti. `research_agent.py` è la versione ripetibile e a basso costo (Haiku 5.5), provata su tre giochi; `--applica` e `--nuovi` non sono mai stati lanciati. Corretto un bug: per Portal 2 e simili la lettura della trama restituiva 1 carattere perché la trama è in sottosezioni.
- Provenienza: nel dataset solo 15 personaggi su 330 hanno la fonte (URL e citazione); le 124 uccisioni in 43 giochi non l'hanno. Per averla su tutto servirebbe lanciare l'agente sui 95 giochi (circa 10 centesimi con Haiku 5.5 secondo la prova su Portal, trame più lunghe costano di più). Il controllo delle citazioni verifica che la frase esista nella pagina, non che dimostri il fatto.
- Mondo aperto: non si deduce "non giocabile", "ultima console", "esterno e non di gruppo", né "tutti i giochi di una serie sono X". Provata la chiusura con nominali (`includes only {…}` più `∀includes.FirstPartyGame`): corretta, ma HermiT passa da 110 a 580 secondi anche con una sola serie chiusa; scartata (DEDUZIONI.md, sezione 18).
- Fallout: New Vegas risulta seguito interno al gruppo e Bungie first-party solo perché oggi appartengono a Microsoft e Sony (limite del tempo).
- `playable` e la natura dei personaggi valgono per tutta la serie (Zelda).
- Dati solo per i personaggi più noti: Mass Effect è fantascienza grazie a Garrus, Liara, Tali e Saren; Benezia non è stata aggiunta per mancanza di una fonte.
- La verifica con HermiT da riga di comando (OWL API) sui file reali non è stata fatta.
- `dati.ttl` usa nodi anonimi (liste di `AllDifferent`): rigenerandolo, `git diff` mostra molte righe cambiate anche se i dati sono gli stessi.
