# Handoff: ontologia Protégé

Branch `feat/protege-ontology`, cartella `protege/`. Tutto (schema, regole, dati, test, appendici della relazione) si rigenera con gli script; i comandi sono nel README.

## Stato
- 89 classi (53 definite), 49 object property, 5 datatype property, 20 regole SWRL, 95 giochi.
- `check_reasoning.py` (HermiT via owlready2, circa 3 minuti): tutti i controlli superati, compresi i 5 test di errore in `test/`.
- Relazione: 14 pagine, corpo fino a pagina 7, compila senza errori né warning. I numeri (classi, regole, controlli) sono scritti dagli script in `relazione/numeri.tex` e `controlli.tex`.
- `DEDUZIONI.md`: 16 sezioni con le deduzioni non banali, con fatti, assiomi e regole.

## Da fare a mano
1. **Controllo in Protégé.** Aprire `protege/videogiochi.ttl`, Reasoner > HermiT > Start reasoner: l'ontologia deve risultare consistente, e SWRLTab deve mostrare le 20 regole. Il tempo in Protégé non è stato misurato.
2. **Screenshot.** `relazione/figure/` è vuota: i 5 riquadri segnaposto della relazione contengono le istruzioni, ripetute nel README (`gerarchia_inferita`, `spiegazione_gwyn`, `individuo_fallout_new_vegas`, `swrl_rules`, `inconsistenza`). Con i PNG presenti, i riquadri spariscono da soli.
3. **Differenze con Wikidata.** `fetch_wikidata.py` ne elenca 66 non riviste.

## Limiti noti
- `research_agent.py` non è mai stato lanciato con un LLM vero (nessuna chiave API): i fatti di trama vengono da ricerche su Wikipedia e Wikidata con citazione verificata.
- Mondo aperto: non si deduce "non giocabile", "ultima console", "esterno e non di gruppo".
- Fallout: New Vegas risulta seguito interno al gruppo e Bungie first-party solo perché oggi appartengono a Microsoft e Sony (limite del tempo).
- `playable` e la natura dei personaggi valgono per tutta la serie (Zelda).
- Dati solo per i personaggi più noti: Mass Effect è fantascienza grazie a Garrus, Liara, Tali e Saren; Benezia non è stata aggiunta per mancanza di una fonte.
- La verifica con HermiT da riga di comando (OWL API) sui file reali non è stata fatta.
