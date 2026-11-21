# Deduzioni da mostrare

Ogni voce dice: che cosa conclude il reasoner, un esempio vero della nostra ontologia, i fatti scritti nei dati, l'assioma o la regola che lavora e perché non è banale. Nessuna delle conclusioni è scritta in `dati.ttl`: le aggiunge HermiT.

Per vederle in Protégé: apri `videogiochi.ttl`, Reasoner > HermiT > Start reasoner, poi cerca l'individuo nel tab *Individuals*. Le righe gialle sono dedotte; il "?" accanto mostra la spiegazione, cioè i fatti e gli assiomi da cui segue.

---

## 1. Da un fatto, due conclusioni: chi muore e chi uccide

**Esempio.** Gwyn, Lord of Sunlight è un `DeceasedCharacter`; il Prescelto (`Chosen_Undead`) è un `Killer`.

**Nei dati.** Un solo individuo, l'uccisione di *Dark Souls*:
```turtle
killing:Gwyn_Lord_of_Sunlight_by_Chosen_Undead_in_Dark_Souls a vg:Killing ;
    vg:victim character:Gwyn_Lord_of_Sunlight ; vg:killer character:Chosen_Undead ; vg:inGame vg:Dark_Souls .
```

**Assiomi.**
- `DeceasedCharacter ≡ Character ⊓ ∃victimIn.Killing`
- `Killer ≡ Character ⊓ ∃killerIn.Killing` (`victimIn` e `killerIn` sono le inverse di `victim` e `killer`)
- regola `KillingEvent`: `victim(?k, ?v) ∧ killer(?k, ?a) → killedBy(?v, ?a)`

**Perché non è banale.** L'uccisione è una relazione a tre (vittima, assassino, gioco), modellata con il pattern delle relazioni n-arie. Da quel solo nodo il reasoner ricava due tipi e la relazione diretta `killedBy`, che nessuno ha scritto.

---

## 2. Cortana è un'intelligenza artificiale, e diventa ribelle

**Esempio.** Cortana è `Synthetic` e `RogueAI`, come GLaDOS.

**Nei dati.** Due fatti soltanto: Cortana è stata costruita dalla dottoressa Halsey (`builtBy`) ed è l'antagonista di *Halo 5* (`antagonistOf`). Non c'è scritto che sia un'IA.

**Assiomi.**
- `Synthetic ≡ Character ⊓ ∃builtBy.⊤`: chi è stato costruito da qualcuno è sintetico
- `Antagonist ≡ Character ⊓ ∃antagonistOf.VideoGame`
- `RogueAI ≡ Synthetic ⊓ Antagonist`

**Perché non è banale.** Sono tre passi su due fatti diversi. Cortana è anche protagonista di *Halo: Combat Evolved* e *Halo 4*: il reasoner non si confonde, perché i ruoli non si escludono. Lo stesso vale per GLaDOS e Wheatley (costruiti da Aperture Science, una `FictionalOrganization`) e per 343 Guilty Spark (costruito dai Precursori).

---

## 3. GTA e Zelda: stessa violenza nella storia, la distingue il PEGI

**Esempio.** *Far Cry 3* è `RealisticViolenceGame`; *Skyward Sword* è `FantasyViolenceGame`.

**Nei dati.**
- *Far Cry 3*: un'uccisione (Jason Brody uccide Vaas Montenegro) e `pegiRating 18`;
- *Skyward Sword*: un'uccisione (Link uccide Demise) e `pegiRating 12`.

**Assiomi.**
- `ViolentStoryGame ≡ VideoGame ⊓ ∃hasKilling.Killing`
- `RealisticViolenceGame ≡ ViolentStoryGame ⊓ ∃pegiRating.integer[≥ 16]`
- `FantasyViolenceGame ≡ ViolentStoryGame ⊓ ∃pegiRating.integer[≤ 12]`

**Perché non è banale.**
- La trama da sola non separa i due giochi: in entrambi qualcuno muore. Lo fa il PEGI, letto con i criteri ufficiali (dal 16 la violenza è realistica, fino al 12 è contro personaggi di fantasia).
- Il risultato divide i 43 giochi violenti in 38 realistici (GTA, Assassin's Creed, Far Cry, Halo, The Witcher…) e 5 di fantasia (tutti Zelda).
- Questa deduzione ha anche trovato un errore di Wikidata: *Assassin's Creed Origins* risultava "di fantasia" perché Wikidata gli dava PEGI 12, mentre è PEGI 18. È corretto in `fonti/correzioni.json`.

---

## 4. Mass Effect e Fallout 4: giochi Microsoft usciti su console Sony

**Esempio.** *Fallout 4* è `FirstPartyGame` e `FirstPartyOnRivalConsole`.

**Nei dati.**
- *Fallout 4* è pubblicato da Bethesda Softworks ed è uscito su PS4 e Xbox One.
- Bethesda Softworks è controllata da ZeniMax, ZeniMax da Xbox Game Studios, Xbox Game Studios da Microsoft (`subsidiaryOf`).
- Microsoft costruisce la Xbox One, Sony la PS4 (`manufacturedBy`).

**Assiomi e regole.**
- `PlatformHolder ≡ Company ⊓ ∃manufacturerOf.ConsolePlatform`: Microsoft lo diventa perché costruisce console
- regole `PublisherGroup` e `ParentGroup`: risalgono il gruppo dell'editore un passo alla volta (`publishedByGroup`)
- `FirstPartyGame ≡ VideoGame ⊓ ∃publishedByGroup.PlatformHolder`
- regola `FirstPartyOnRivalConsole`: un gioco del gruppo di un costruttore, uscito su una console di un altro costruttore

**Perché non è banale.** Sono quattro passaggi di proprietà, una classe definita da un ruolo dedotto e un confronto tra due aziende (`differentFrom`). È anche un limite istruttivo: nel 2015 ZeniMax non era di Microsoft (lo è dal 2021), ma OWL non rappresenta il tempo.

---

## 5. Fallout: New Vegas, fatto da veterani della serie

**Esempio.** *Fallout: New Vegas* è `VeteransReturn`; Obsidian Entertainment è `FoundedByVeterans`.

**Nei dati.**
- *New Vegas* è sviluppato da Obsidian, fondata da Feargus Urquhart e altri, ex dipendenti di Black Isle Studios (`formerEmployeeOf`).
- Black Isle ha sviluppato *Fallout 2*.
- Entrambi i giochi appartengono alla serie Fallout.

**Assiomi e regole.**
- `FoundedByVeterans ≡ Company ⊓ ∃foundedBy.(∃formerEmployeeOf.Developer)`, con `Developer` a sua volta definita
- regola `VeteransReturn`: lo studio del gioco è fondato da chi lavorava per lo sviluppatore di un altro gioco della stessa serie

**Perché non è banale.** Collega cinque individui (gioco, studio, persona, vecchio studio, vecchio gioco) e una serie. Lo stesso schema riconosce AdHoc Studio (Dispatch), fondata da ex Telltale.

---

## 6. Ganondorf muore e ritorna; Catalina ritorna perché è un prequel

**Esempio.**
- Ganondorf è `KilledMoreThanOnce` e `ReturningCharacter`.
- *Breath of the Wild* è `ReturnAfterDeathGame`.
- *Grand Theft Auto: San Andreas* è `ReturnAfterDeathGame` e `PrequelReturn`.

**Nei dati.**
- Ganondorf è ucciso da Link in *Twilight Princess* (2006) e in *Tears of the Kingdom* (2023), ed è antagonista di *A Link Between Worlds* e *Breath of the Wild*.
- Catalina è uccisa da Claude in *GTA III* e compare in *San Andreas*.
- *San Andreas* è `prequelOf` *GTA III* (è ambientato nel 1992, *GTA III* nel 2001).
- I seguiti sono scritti solo verso il capitolo precedente.

**Assiomi e regole.**
- `KilledMoreThanOnce ≡ DeceasedCharacter ⊓ ≥2 victimIn.Killing` (le uccisioni sono dichiarate tutte diverse)
- regole `ReleaseOrder` e `ReleaseOrderChain`: ricavano "uscito dopo" (`releasedAfter`) risalendo i seguiti un passo alla volta
- regola `ReturnAfterDeath`: `victim(?k, ?c) ∧ inGame(?k, ?g) ∧ appearsIn(?c, ?h) ∧ releasedAfter(?h, ?g) → ReturningCharacter(?c) ∧ ReturnAfterDeathGame(?h)`
- `PrequelReturn ≡ ReturnAfterDeathGame ⊓ PrequelGame`

**Perché non è banale.** Un personaggio morto non dovrebbe tornare in un gioco uscito dopo. Il reasoner trova i casi e ne spiega uno: Catalina torna in un prequel. Per Ganondorf non c'è spiegazione tra i dati, e in un mondo aperto il reasoner non può concludere che sia una resurrezione o un'altra linea temporale: può solo segnalarlo. È un buon esempio di cosa OWL sa e non sa dire.

---

## 7. GTA III e Halo: Combat Evolved si giocano ancora oggi

**Esempio.** *Grand Theft Auto III* (2001, PS2) e *Halo: Combat Evolved* (2001, Xbox) sono `StillPlayable`. La PS5 è `CurrentGenerationConsole`.

**Nei dati.**
- *GTA III* è uscito su PS2; la sua *Definitive Edition* (`remasterOf`) è uscita su PS5.
- Il remake *Halo: Campaign Evolved* è uscito su PS5.
- Della PS5 c'è solo `generation 9`.

**Assiomi.**
- catena `hasRemaster ∘ availableOn ⊑ playableOn`: un gioco è giocabile dove è uscita una sua nuova edizione
- `CurrentGenerationConsole ≡ ConsolePlatform ⊓ ∃generation.integer[≥ 9]`
- `StillPlayable ≡ VideoGame ⊓ ∃playableOn.CurrentGenerationConsole`

**Perché non è banale.**
- Combina una property chain, una restrizione su un valore numerico e una classe definita su un'altra classe definita.
- Halo CE, gioco Microsoft, risulta giocabile su una console Sony.
- "Console attuale" non si può dedurre come "l'ultima uscita" (servirebbe una negazione): la soglia sulla generazione rende esplicita questa scelta.

---

## 8. The Witcher è tecnologicamente legato a Mass Effect

**Esempio.** *The Witcher* `techLinkedTo` *Mass Effect*.

**Nei dati.**
- *The Witcher* è fatto con l'Aurora Engine, sviluppato da BioWare.
- BioWare ha sviluppato *Mass Effect*.

**Assioma.** Catena `madeWith ∘ engineDevelopedBy ∘ developerOf ⊑ techLinkedTo`.

**Perché non è banale.** Due giochi di studi e serie diverse risultano collegati attraverso un motore e un'inversa: tre archi diventano uno.

---

## 9. Giochi dell'anno "per consenso"

**Esempio.** *The Witcher 3*, *Breath of the Wild*, *Elden Ring*, *Portal 2*, *Mass Effect 2* sono `ConsensusGOTY` (10 giochi in tutto).

**Nei dati.**
- *The Witcher 3* ha vinto il premio Gioco dell'anno ai Golden Joystick, a The Game Awards e ai Game Developers Choice Awards.
- I premi sono dichiarati tutti diversi (`owl:AllDifferent`).

**Assiomi.**
- `GOTYWinner ≡ VideoGame ⊓ ∃wonAward.Award`
- `ConsensusGOTY ≡ GOTYWinner ⊓ ≥2 wonAward.Award`

**Perché non è banale.** Senza `AllDifferent` la cardinalità non scatterebbe: OWL non assume che nomi diversi indichino premi diversi (niente Unique Name Assumption). Ogni premio è stato verificato sulla tabella dei vincitori di Wikipedia; due erano sbagliati e sono corretti in `fonti/correzioni.json` (Breath of the Wild non ha vinto il Golden Joystick, Ocarina of Time non ha vinto il Grand Award dei Japan Game Awards).

---

## 10. Dark Souls è un gioco d'autore

**Esempio.** *Dark Souls*, *Dark Souls III* ed *Elden Ring* sono `AuteurGame`.

**Nei dati.** Sono diretti da Hidetaka Miyazaki, che guida FromSoftware (`heads`).

**Assiomi.**
- `GameDirector ≡ Person ⊓ ∃directorOf.VideoGame`
- `StudioHead ≡ Person ⊓ ∃heads.Company`
- `AuteurGame ≡ VideoGame ⊓ ∃directedBy.StudioHead`

**Perché non è banale.** La classe del gioco dipende dal ruolo dedotto di una persona. *Dark Souls II*, diretto da altri, non entra.

---

## 11. Seguiti che cambiano studio o motore

**Esempi.**
- *Halo 4* (343 Industries dopo Bungie) e *Oracle of Seasons* (Flagship, studio di Capcom, dopo Nintendo) sono `SequelByDifferentStudio`.
- *Grand Theft Auto IV* (da RenderWare a RAGE) e *Far Cry 2* (da CryEngine a Dunia) sono `EngineChangeSequel`.
- *Far Cry 6* è `ExternalEngineGame`: Ubisoft Toronto usa Dunia 2, sviluppato da Ubisoft Montreal.

**Regole.** `SequelByDifferentStudio`, `EngineChangeSequel`, `ExternalEngineGame` confrontano due individui con `differentFrom`, cosa che una classe OWL non può esprimere.

**Perché non è banale.** Il caso di Far Cry 6 è sottile: per l'ontologia due sedi della stessa azienda sono studi diversi, e il reasoner lo fa notare.

---

## 12. Serie che cambiano mano e serie diventate film o serie TV

**Esempi.**
- Halo, Fallout, Far Cry e Assassin's Creed sono `FranchiseWithStudioChange`.
- The Witcher, Fallout, Halo, Super Mario sono `TransmediaFranchise`; GTA e Zelda no.

**Assiomi.**
- `FranchiseWithStudioChange ≡ Franchise ⊓ ∃includes.SequelByDifferentStudio`: la classe della serie nasce dalla classe di un suo gioco, che a sua volta nasce da una regola
- `TransmediaFranchise ≡ Franchise ⊓ ∃adaptedInto.(Film ⊔ TVSeries)`: un'unione dentro un'esistenziale

---

## 13. Personaggi storici e cattivi sconfitti

**Esempi.**
- Leonardo da Vinci e Cesare Borgia sono `HistoricalCharacter`.
- Cesare Borgia è anche `DefeatedVillain`: antagonista ucciso da Ezio, protagonista dello stesso gioco.

**Assiomi e regole.**
- `HistoricalCharacter ≡ Character ⊓ ∃portrays.Person`
- regola `DefeatedVillain`: `antagonistOf(?v, ?g) ∧ protagonistOf(?h, ?g) ∧ killedBy(?v, ?h) → DefeatedVillain(?v)`, con `killedBy` a sua volta ricavata dalla regola `KillingEvent`

**Perché non è banale.** Una regola lavora sul risultato di un'altra regola.

---

## 14. Gli errori che il reasoner trova, e un'uguaglianza che deduce

I file in `test/` aggiungono pochi fatti e fanno scattare un assioma preciso.

| File | Fatto aggiunto | Assioma | Esito |
|---|---|---|---|
| `errore_disgiunzione` | Steam Deck è console e PC | `ConsolePlatform` e `PCPlatform` disgiunte | inconsistente |
| `errore_funzionale` | Portal 2 ha Metacritic 90 oltre a 95 | `metacriticScore` funzionale | inconsistente |
| `errore_cardinalita` | Breath of the Wild "su al più una piattaforma" | cardinalità massima, Wii U e Switch dichiarate diverse | inconsistente |
| `errore_chiave` | un secondo gioco con l'ID Wikidata di GTA V, dichiarato diverso | `VideoGame hasKey (hasWikidataId)` | inconsistente |
| `deduzione_sameas` | Splatoon 2 "su al più una piattaforma", ma su Switch e su "NX" | stessa cardinalità, senza `differentFrom` | consistente: NX **è** la Switch |

L'ultimo è il più interessante: lo stesso assioma che nel caso di Breath of the Wild produce un errore, qui produce una deduzione corretta (NX era il nome in codice della Switch). Mostra insieme il mondo aperto e l'assenza della Unique Name Assumption.
