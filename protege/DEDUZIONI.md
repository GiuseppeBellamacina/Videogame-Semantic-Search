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

## 3. La violenza realistica: uccisioni nella trama e PEGI

**Esempio.** *Far Cry 3* è `RealisticViolenceGame`; *Twilight Princess* è solo `ViolentStoryGame`.

**Nei dati.**
- *Far Cry 3*: un'uccisione (Jason Brody uccide Vaas Montenegro) e `pegiRating 18`;
- *Twilight Princess*: un'uccisione (Link uccide Ganondorf) e `pegiRating 12`.

**Assiomi.**
- `ViolentStoryGame ≡ VideoGame ⊓ ∃hasKilling.Killing`
- `RealisticViolenceGame ≡ ViolentStoryGame ⊓ ∃pegiRating.integer[≥ 16]`

**Perché non è banale.**
- La trama da sola non separa i due giochi: in entrambi qualcuno muore. Lo fa il PEGI, letto con i criteri ufficiali (dal 16 la violenza è realistica).
- Questa deduzione ha anche trovato un errore di Wikidata: *Assassin's Creed Origins* risultava "di fantasia" perché Wikidata gli dava PEGI 12, mentre è PEGI 18. È corretto in `fonti/correzioni.json`.

---
## 4. Mass Effect e Fallout 4: giochi di un costruttore di console

**Esempio.** *Fallout 4* e *Mass Effect* sono `FirstPartyGame` e anche `FirstPartyOnRivalConsole`: sono usciti su PlayStation, console di un altro costruttore.

**Nei dati.**
- *Fallout 4* è pubblicato da Bethesda Softworks.
- Bethesda Softworks è controllata da ZeniMax, ZeniMax da Xbox Game Studios, Xbox Game Studios da Microsoft (`subsidiaryOf`, transitiva).
- Microsoft costruisce la Xbox One (`manufacturedBy`), Sony la PlayStation 4; il gioco è disponibile su entrambe (`availableOn`).

**Assiomi.**
- `PlatformHolder ≡ Company ⊓ ∃manufacturerOf.ConsolePlatform`: Microsoft lo diventa perché costruisce console
- `FirstPartyGame ≡ VideoGame ⊓ ∃publishedBy.(PlatformHolder ⊔ ∃subsidiaryOf.PlatformHolder)`: l'editore è un costruttore di console o ne è controllato, a qualunque livello
- regole `PublisherGroup` e `ParentGroup`: `publishedByGroup` parte dall'editore e sale una controllante alla volta (Bethesda Softworks, ZeniMax, Xbox Game Studios, Microsoft)
- regola `ConsoleMaker`: `availableOn(?g, ?p) ∧ ConsolePlatform(?p) ∧ manufacturedBy(?p, ?m) → onConsoleOf(?g, ?m)`
- regola `FirstPartyOnRivalConsole`: `publishedByGroup(?g, ?h) ∧ PlatformHolder(?h) ∧ onConsoleOf(?g, ?m) ∧ differentFrom(?h, ?m)`: il costruttore del gruppo è diverso da quello della console

**Perché non è banale.** Una classe definita su un'altra (`PlatformHolder`), un'unione dentro un'esistenziale e una proprietà transitiva: `FirstPartyGame` è solo OWL. La versione con console rivale confronta due aziende, quindi serve una regola, e le regole di gruppo salgono la catena un passo alla volta: dentro SWRL HermiT non vede la transitività di `subsidiaryOf`, e con una sola regola Fallout 4 (tre livelli) falliva, Mass Effect (uno) no. Non risultano rivali *Halo 4*, *Breath of the Wild* e *Mass Effect 2*. È anche un limite istruttivo: nel 2015 ZeniMax non era di Microsoft (lo è dal 2021), ma OWL non rappresenta il tempo.

---

## 5. Obsidian è fondata da veterani

**Esempio.** Obsidian Entertainment è `FoundedByVeterans`.

**Nei dati.**
- *New Vegas* è sviluppato da Obsidian, fondata da Feargus Urquhart e altri, ex dipendenti di Black Isle Studios (`formerEmployeeOf`).
- Black Isle ha sviluppato *Fallout 2* (`Developer`).

**Assioma.**
- `FoundedByVeterans ≡ Company ⊓ ∃foundedBy.(∃formerEmployeeOf.Developer)`, con `Developer` a sua volta definita

**Perché non è banale.** Collega tre individui (studio, persona, vecchio studio) e una classe a sua volta definita. Lo stesso schema riconosce AdHoc Studio (Dispatch), fondata da ex Telltale.

---

## 6. Chi muore e ritorna: Ganondorf e Catalina

**Esempio.**
- Ganondorf è `ReturningCharacter`.
- *Breath of the Wild* è `ReturnAfterDeathGame`.
- *Grand Theft Auto: San Andreas* è `ReturnAfterDeathGame`.

**Nei dati.**
- Ganondorf è ucciso da Link in *Twilight Princess* (2006) e in *Tears of the Kingdom* (2023), ed è antagonista di *A Link Between Worlds* e *Breath of the Wild*.
- Catalina è uccisa da Claude in *GTA III* e compare in *San Andreas*.
- *San Andreas* è `prequelOf` *GTA III* (è ambientato nel 1992, *GTA III* nel 2001).
- I seguiti sono scritti solo verso il capitolo precedente.

**Assiomi e regole.**
- regole `ReleaseOrder` e `ReleaseOrderChain`: ricavano "uscito dopo" (`releasedAfter`) risalendo i seguiti un passo alla volta
- regola `ReturnAfterDeath`: `victim(?k, ?c) ∧ inGame(?k, ?g) ∧ appearsIn(?c, ?h) ∧ releasedAfter(?h, ?g) → ReturningCharacter(?c) ∧ ReturnAfterDeathGame(?h)`

**Perché non è banale.** Un personaggio morto non dovrebbe tornare in un gioco uscito dopo. Il reasoner trova i casi, ma non li spiega: per Catalina (*San Andreas* è un prequel) e per Ganondorf non c'è spiegazione tra i dati, e in un mondo aperto il reasoner non può concludere che sia una resurrezione o un'altra linea temporale: può solo segnalarlo. È un buon esempio di cosa OWL sa e non sa dire.

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

## 8. Dark Souls è un gioco d'autore

**Esempio.** *Dark Souls*, *Dark Souls III* ed *Elden Ring* sono `AuteurGame`.

**Nei dati.** Sono diretti da Hidetaka Miyazaki, che guida FromSoftware (`heads`).

**Assiomi.**
- `GameDirector ≡ Person ⊓ ∃directorOf.VideoGame`
- `StudioHead ≡ Person ⊓ ∃heads.Company`
- `AuteurGame ≡ VideoGame ⊓ ∃directedBy.StudioHead`

**Perché non è banale.** La classe del gioco dipende dal ruolo dedotto di una persona. *Dark Souls II*, diretto da altri, non entra.

---

## 9. Seguiti che cambiano studio o motore

**Esempi.**
- *Halo 4* (343 Industries dopo Bungie) e *Oracle of Seasons* (Flagship, studio di Capcom, dopo Nintendo) sono `SequelByDifferentStudio`.
- *Grand Theft Auto IV* (da RenderWare a RAGE) e *Far Cry 2* (da CryEngine a Dunia) sono `EngineChangeSequel`.
- *Mass Effect*, *The Witcher*, *Fallout 3* e *Far Cry 6* sono `ExternalEngineGame`: il motore è sviluppato da un'altra azienda.

**Regole.**
- `SequelByDifferentStudio`, `EngineChangeSequel`, `ExternalEngineGame` confrontano due individui con `differentFrom`, cosa che una classe OWL non può esprimere.

**Limite.**
- `ExternalEngineGame` non distingue le aziende dello stesso gruppo: *GTA V* usa RAGE, sviluppato da una divisione di Rockstar Games, e risulta "motore di un'altra azienda". Lo stesso vale per i seguiti passati a un'altra divisione dello stesso gruppo (le divisioni Nintendo, le sedi Ubisoft): servirebbe una negazione, che in un mondo aperto non si deduce.
- Il limite del tempo torna per le aziende passate di mano: oggi Obsidian e Bethesda sono entrambe di Microsoft, ma non lo erano quando uscì *Fallout: New Vegas*.

---

## 10. Serie che cambiano mano e serie diventate film o serie TV

**Esempi.**
- `FranchiseWithStudioChange`: Halo, Fallout, Far Cry, Assassin's Creed, Super Mario e Zelda.
- `TransmediaFranchise`: The Witcher, Fallout, Halo, Assassin's Creed, Far Cry, Mass Effect e Super Mario; GTA e Zelda no.

**Assiomi.**
- `FranchiseWithStudioChange ≡ Franchise ⊓ ∃includes.SequelByDifferentStudio`: la classe della serie nasce dalla classe di un suo gioco, che a sua volta nasce da una regola
- `TransmediaFranchise ≡ Franchise ⊓ ∃adaptedInto.(Film ⊔ TVSeries)`: un'unione dentro un'esistenziale

**Perché è istruttivo.** Per Super Mario il "cambio di studio" è sempre tra divisioni Nintendo; per Zelda ci sono anche passaggi esterni, gli episodi di Flagship.

---

## 11. Personaggi storici e cattivi sconfitti

**Esempi.**
- Leonardo da Vinci e Cesare Borgia sono `HistoricalCharacter`.
- Cesare Borgia è anche `DefeatedVillain`: antagonista ucciso da Ezio, protagonista dello stesso gioco.

**Assiomi e regole.**
- `HistoricalCharacter ≡ Character ⊓ ∃portrays.Person`
- regola `DefeatedVillain`: `antagonistOf(?v, ?g) ∧ protagonistOf(?h, ?g) ∧ killedBy(?v, ?h) → DefeatedVillain(?v)`, con `killedBy` a sua volta ricavata dalla regola `KillingEvent`

**Perché non è banale.** Una regola lavora sul risultato di un'altra regola.

---

## 12. Il genere dai personaggi

**Esempi.**
- `HistoricalGame`: tutti i 14 *Assassin's Creed*.
- `SciFiGame`: quasi tutti gli *Halo*, i due *Portal* e i tre *Mass Effect*.

**Nei dati.** Il genere "storico" o "fantascientifico" non c'è: ci sono i personaggi che interpretano persone reali, i personaggi alieni, i personaggi costruiti da qualcuno.

**Assiomi.**
- `HistoricalGame ≡ VideoGame ⊓ ∃hasCharacter.HistoricalCharacter`
- `SciFiGame ≡ VideoGame ⊓ ∃hasCharacter.(Alien ⊔ Synthetic)`

**Perché non è banale.** Il genere si deduce da chi abita il gioco, in due passi (per `SciFiGame`: `builtBy` → `Synthetic`, poi `hasCharacter`, inversa di `appearsIn`, fino al gioco). Sono condizioni sufficienti, non necessarie: tra i personaggi dei tre *Mass Effect* ci sono Garrus (turian), Liara (asari) e Tali'Zorah (quarian), ciascuno con la fonte, e per questo sono di fantascienza; un gioco i cui alieni non sono nei dati non lo sarebbe, perché in un mondo aperto un dato mancante non è una smentita.

---

## 13. Registi e studi prolifici, studi first-party, giochi autopubblicati

**Esempi.**
- `ProlificDirector` (almeno tre giochi diretti): Miyazaki, Miyamoto, Aonuma, Casey Hudson.
- `ProlificDeveloper` (almeno cinque giochi): Bungie, Rockstar North, Ubisoft Montreal e le divisioni Nintendo.
- `FirstPartyStudio`: Halo Studios, Mojang, Nintendo EPD, Bethesda Game Studios. BioWare e Capcom no, pur avendo sviluppato giochi pubblicati da un costruttore di console.
- `SelfPublishedGame`: *Portal*, *Portal 2*, *Minecraft*, *Dispatch*.

**Assiomi e regole.**
- `ProlificDirector ≡ GameDirector ⊓ ≥3 directorOf.VideoGame` e `ProlificDeveloper ≡ Developer ⊓ ≥5 developerOf.VideoGame`: cardinalità qualificate su proprietà semplici, con i giochi dichiarati tutti diversi
- `FirstPartyStudio ≡ Developer ⊓ (PlatformHolder ⊔ ∃subsidiaryOf.PlatformHolder)`
- regola `SelfPublished`: `developedBy(?g, ?c) ∧ publishedBy(?g, ?c) → SelfPublishedGame(?g)`

**Perché non è banale.** `FirstPartyStudio` usa una proprietà transitiva e una classe (`PlatformHolder`) ricavata da un'altra relazione. Bungie ne fa parte solo perché oggi è di Sony (nel 2007 Microsoft la lasciò): il limite del tempo.

---

## 14. I classici che si giocano ancora: data, catena e classe dedotta insieme

**Esempio.** `Grand_Theft_Auto_III`, `Grand_Theft_Auto_San_Andreas`, `Grand_Theft_Auto_Vice_City`, `Halo_Combat_Evolved` e `The_Legend_of_Zelda_Ocarina_of_Time` sono `ClassicStillPlayable`.

**Nei dati.** Solo la data di uscita, le piattaforme e i remaster (per esempio GTA III 2001 per PS2; la Definitive Edition uscita su PS5, dichiarata `remasterOf` GTA III).

**Assiomi.**
- `ClassicGame ≡ VideoGame ⊓ ∃releaseDate.dateTime[< 2005-01-01]`: restrizione su un intervallo di date
- `StillPlayable ≡ VideoGame ⊓ ∃playableOn.CurrentGenerationConsole`, con la catena `hasRemaster ∘ availableOn ⊑ playableOn`
- `ClassicStillPlayable ≡ ClassicGame ⊓ StillPlayable`

**Perché non è banale.** Tre meccanismi diversi lavorano insieme: un confronto tra date (con SWRL non si può: HermiT non supporta le funzioni sulle date, qui basta un intervallo di valori), una catena di proprietà (la piattaforma del remaster) e una soglia di generazione. Nessun dato dice "classico" né "giocabile oggi".

---

## 15. La fascia di età: PEGI 3, 7, 12, 16 e 18

**Esempio.** `Grand_Theft_Auto_V` e `Grand_Theft_Auto_VI` sono `Pegi18Game`; `Dark_Souls` è `Pegi16Game`; `The_Legend_of_Zelda_Ocarina_of_Time` è `Pegi12Game`; `The_Legend_of_Zelda_The_Wind_Waker` è `Pegi7Game`; `Super_Mario_Bros` è `Pegi3Game`.

**Nei dati.** Solo il valore, per esempio `vg:Grand_Theft_Auto_V vg:pegiRating 18`.

**Assiomi.** `Pegi18Game ≡ VideoGame ⊓ ∃pegiRating.{18}` (una restrizione `hasValue` su un dato), e le altre quattro uguali con 3, 7, 12 e 16.

**Perché serve.** `ViolentStoryGame` si ricava dalle uccisioni raccontate nella trama: GTA V e GTA VI non ne hanno nei dati, quindi non risultano violenti. La fascia di età è un'altra informazione, già nei dati, e non va forzata aggiungendo uccisioni.

---

## 16. Gli errori che il reasoner trova, e un'uguaglianza che deduce

I file in `test/` aggiungono pochi fatti e fanno scattare un assioma preciso.

| File | Fatto aggiunto | Assioma | Esito |
|---|---|---|---|
| `errore_disgiunzione` | Steam Deck è console e PC | `ConsolePlatform` e `PCPlatform` disgiunte | inconsistente |
| `errore_funzionale` | Portal 2 ha Metacritic 90 oltre a 95 | `metacriticScore` funzionale | inconsistente |
| `errore_cardinalita` | Breath of the Wild "su al più una piattaforma" | cardinalità massima, Wii U e Switch dichiarate diverse | inconsistente |
| `errore_chiave` | un secondo gioco con l'ID Wikidata di GTA V, dichiarato diverso | `VideoGame hasKey (hasWikidataId)` | inconsistente |
| `errore_proprieta_disgiunte` | Ocarina of Time 3D (remaster di Ocarina of Time) dichiarato anche prequel dello stesso gioco | `remasterOf` e `prequelOf` disgiunte | inconsistente |
| `deduzione_sameas` | Splatoon 2 "su al più una piattaforma", ma su Switch e su "NX" | stessa cardinalità, senza `differentFrom` | consistente: NX **è** la Switch |

L'ultimo è il più interessante: lo stesso assioma che nel caso di Breath of the Wild produce un errore, qui produce una deduzione corretta (NX era il nome in codice della Switch). Mostra insieme il mondo aperto e l'assenza della Unique Name Assumption.

---

## 17. Provato e scartato: "tutti i giochi della serie" con una chiusura

L'idea: `FirstPartyFranchise ≡ Franchise ⊓ ∃includes.VideoGame ⊓ ∀includes.FirstPartyGame`, con per ogni serie un'asserzione di chiusura `includes only {giochi della serie}` (un `owl:oneOf` con i giochi). Nel mondo aperto è l'unico modo per concludere "tutti": senza chiusura, un gioco non nominato potrebbe sempre esistere.

**Funzionava.** HermiT classificava Halo, Super Mario e Zelda come serie interamente first-party, e non GTA, Fallout o Mass Effect (le attese erano calcolate dal dataset in Python, e tutti i 298 controlli passavano).

**Non l'abbiamo tenuta.** Il ragionamento completo passa da circa 110 secondi a circa 580: lo stesso con la chiusura di tutte le serie, con quella di quattro o di una sola (Mass Effect, tre giochi: 575 secondi). Il costo non dipende da quanti giochi ci sono: basta un individuo con un universale su un insieme di nomi (nominali), insieme a inverse, cardinalità e chiavi. Un'ontologia che in Protégé richiede dieci minuti per ogni "Start reasoner" non si può mostrare dal vivo.
