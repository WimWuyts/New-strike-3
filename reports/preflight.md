# Preflight-rapport — New Ace 3 / New Strike 3

**Datum:** 2026-08-12
**Fase:** Read-only preflight (sectie 3 van de masterprompt)
**Status:** ⛔ Geblokkeerd — wacht op beslissingen. Geen projectsetup, geen contentproductie uitgevoerd.

---

## 1. Gevonden bronbestanden

De projectmap `/home/user/New-strike-3` was **volledig leeg** (git-repo zonder commits, geen `sources/`).
De bronbestanden staan **niet lokaal**, maar in Google Drive van `wuw.sjb@gmail.com`.

### New Ace 3 — map `1zP8mzxRSU6vO6O4lvYCRYfK64Ipjc9IC`

| Unit | Bestand | Grootte | Drive file ID |
|---|---|---|---|
| 1 | Digiboek - New Ace 3 UNIT 1.pdf | 49,6 MB | `1qKM_5fa-UAU4aszPyScMzwBEJaVMymKH` |
| 2 | Digiboek - New Ace 3 UNIT 2.pdf | 49,5 MB | `1juxe0zJGY4E7LLLyImR097jn7gFiC4MG` |
| 3 | Digiboek - New Ace 3 UNIT 3.pdf | 26,8 MB | `1vH2OIO2gapYaQU-xGnQsqTZMITfd_pl5` |
| 4 | Digiboek - New Ace 3 UNIT 4.pdf | 41,2 MB | `1ggBk1bMP-Xk8sehDxmhxSYZe_dMISceI` |
| 5 | Digiboek - New Ace 3 UNIT 5.pdf | 26,8 MB | `11fsWi9X02EK4RdFta8rqhsir8UCx5yT4` |
| 6 | Digiboek - New Ace 3 UNIT 6.pdf | 53,6 MB | `1-2PKrXTDNqC6I7sL1cI0jTQ1xuVUAjjS` |
| 7 | Digiboek - New Ace 3 UNIT 7.pdf | 25,4 MB | `1XColbXNRW2sFR5IouD-5wIADV73_PP4e` |
| 8 | Digiboek - New Ace 3 UNIT 8.pdf | 43,6 MB | `1ENOPACO1qfdRVP_4ZFPSGQgfn_jp40uQ` |

**Subtotaal: 8 units, ± 316 MB.**

### New Strike 3 (2024) — map `1wBdhGP8kiN7YIvaPyD0rtG8j7d-yg_db`

| Unit | Bestand | Grootte | Drive file ID |
|---|---|---|---|
| 1 | Digiboek - New Strike 3 UNIT 1.pdf | 29,3 MB | `1nQzYuesywQVY90mFfMs5xzOwzL3-jc4w` |
| 2 | Digiboek - New Strike 3 UNIT 2.pdf | 38,1 MB | `1GsjH3Y-yOFZufkTzKm3UTDv0onv6D2Sl` |
| 3 | Digiboek - New Strike 3 UNIT 3.pdf | 18,2 MB | `1ST1y-JI8nMUvYSif7QCQqJgB0xyTo3b_` |
| 4 | Digiboek - New Strike 3 UNIT 4.pdf | 28,4 MB | `1mUe4DPVnKzvWPd6N6AnS2w2sYLw_X6eo` |
| 5 | Digiboek - New Strike 3 UNIT 5.pdf | 35,5 MB | `1a3SbSJS2V9y37HBk_W4TqxN8gCtLxDR1` |
| 6 | Digiboek - New Strike 3 UNIT 6.pdf | 50,5 MB | `1uRItWfwIoqi7wNiaDFYcyS0WwLDMTEAV` |
| 7 | Digiboek - New Strike 3 UNIT 7.pdf | 34,7 MB | `1LhnXjlhGpx3ggZIzCLUCFBuSHEgWPjXt` |

**Subtotaal: 7 van de 8 units aangeleverd, ± 235 MB.** Unit 8 bestaat maar ontbreekt; zie hieronder.

**Totaal: 15 pdf's, ± 551 MB.** De mappen bevatten uitsluitend deze pdf's — geen audio, geen fonts, geen licentiebestanden.

### Ontbrekend

- ❌ `sources/grammar-reference/english-grammar-in-use.pdf` — niet in Drive, niet lokaal.
- ❌ `sources/licenses/RIGHTS_CONFIRMATION.md` — bestaat niet.
- ❌ `sources/audio/`, `sources/fonts/` — bestaan niet.
- ⚠️ **New Strike 3 UNIT 8** — bestaat wel (bevestigd door de gebruiker), maar is niet aangeleverd. Het boek telt dus acht units, waarvan er zeven verwerkt kunnen worden. Unit 8 wordt in de praktijk zelden bereikt en staat op lage prioriteit.

---

## 2. Technische staat van de bronnen

Twee representatieve bestanden zijn inhoudelijk gesondeerd via de Drive-connector.

| Kenmerk | New Ace 3 UNIT 1 | New Strike 3 UNIT 3 |
|---|---|---|
| Titel in document | `Digiboek - New Ace 3` | `Digiboek - New Strike 3 (2024)` |
| Waargenomen pagina's | 54 | 24 |
| Bruikbare tekstlaag | **Nee** | **Nee** |
| Enige extraheerbare tekst | watermerk `Wim Wuyts` | watermerk `Wim Wuyts` |
| OCR nodig | **Ja, volledig** | **Ja, volledig** |

**Conclusie:** beide boeken zijn **gerasterde paginascans met een gepersonaliseerd watermerk**. Er is geen tekstlaag, dus ook **geen font-, kleur- of bounding-box-metadata**.

### Gevolgen

1. **OCR is verplicht voor alle 15 pdf's**, niet alleen voor losse pagina's. Fase A stap 3 van de masterprompt ("OCR alleen voor pagina's zonder bruikbare tekstlaag") wordt in de praktijk 100 %.
2. **Fase A stap 2 is niet uitvoerbaar zoals beschreven.** Tekstblokken, leesvolgorde, fontinformatie en kleuren kunnen niet uit een tekstlaag komen; alles moet worden *afgeleid* uit beeldanalyse. Dat is haalbaar maar met lagere betrouwbaarheid en een grotere `manual-review-queue`.
3. **Het watermerk `Wim Wuyts` ligt over elke pagina.** Het verstoort OCR-nauwkeurigheid en zou zichtbaar meekomen in elke rasterreproductie in PowerPoint.
4. **De `page_faithful_portrait`-modus wordt fundamenteel duurder en zwakker**: zonder tekstlaag is "bewerkbare tekst" alleen te bereiken via OCR-resultaten, met OCR-fouten als gevolg.

---

## 3. Blockers

### ⛔ Blocker 1 — de bronbestanden kunnen deze omgeving niet bereiken

Dit is de zwaarste blocker.

- `drive.google.com` wordt **geweigerd door het egress-beleid** van deze remote omgeving (`403` op CONNECT, bevestigd in de proxy-status). Volgens het proxy-beleid mag dit niet omzeild worden.
- De Drive-connector kan bestandsinhoud alleen als base64-string teruggeven. Voor pdf's van 18–53 MB is dat niet werkbaar.
- Gevolg: **de pdf-bytes staan niet op schijf en kunnen hier niet op schijf komen.** Zonder de bytes is renderen, OCR, beeldanalyse, designtokenextractie en PPTX-reconstructie onmogelijk.

**Mogelijke oplossingen (keuze door jou):**

| Optie | Werkwijze | Opmerking |
|---|---|---|
| A | Draai Claude Code **lokaal** op je eigen machine met de pdf's in `sources/books/` | Wat de masterprompt oorspronkelijk veronderstelt. Meest wrijvingsloos. |
| B | Zet de pdf's in de GitHub-repo (Git LFS aangeraden) | ± 551 MB in versiebeheer; auteursrechtelijk bezwaarlijk voor gewatermerkt materiaal. |
| C | Laat een beheerder `drive.google.com` toelaten in het egress-beleid | Vereist rechten op de omgevingsconfiguratie. |

### ⛔ Blocker 2 — geen tekstlaag

Zie sectie 2. Vraagt een expliciete bijstelling van de aanpak in Fase A en Fase H, plus een OCR-kwaliteitsdrempel.

### ⛔ Blocker 3 — rechtenstatus niet bevestigd

`RIGHTS_CONFIRMATION.md` ontbreekt. Het gepersonaliseerde watermerk wijst op een **persoonlijke licentiekopie van commercieel uitgeversmateriaal**.

Volgens de eigen regels in sectie 2 van de masterprompt geldt dan: inventariseren en **originele** companion materials maken mag, maar **bijna identieke pagina- of beeldreproductie niet**. Concreet geblokkeerd tot bevestiging:

- `page_faithful_portrait`-PPTX;
- de hybride rasterachtergrond in PowerPoint;
- overname van bronbeelden in `assets/original/`.

Niet geblokkeerd: curriculumkaart, woordenschatbanken, originele readings/listenings, grammaticamodules, de 25-oefenreeksen, de HTML-omgeving en `hybrid_classroom_16x9`-decks met eigen designtokens.

### ⚠️ Blocker 4 — definitie van "25 per item" niet beslist

Zie sectie 5. Blokkerend volgens sectie 3 van de masterprompt.

### ⚠️ Aandachtspunt — English Grammar in Use ontbreekt

Niet aanwezig. Fase D kan volledig doorgaan zonder deze referentie; de didactische volgorde en foutgevoelige punten worden dan onderbouwd zonder die private referentielaag. Dit heeft **geen** invloed op het leerlingmateriaal, want daaruit mocht sowieso niets worden overgenomen.

---

## 4. Beschikbare toolchain

Geverifieerd in deze omgeving.

| Tool | Status |
|---|---|
| Python | ✅ 3.11.15 |
| uv / pip | ✅ 0.8.17 / 24.0 |
| Node / npm / pnpm | ✅ 22.22.2 / 10.9.7 / 10.33.0 |
| LibreOffice (headless) | ✅ 24.2.7.2 |
| make, git | ✅ 4.3 / 2.43.0 |
| CPU / RAM / vrije schijf | 4 cores / 15 GB / 30 GB |

**Ontbrekend maar installeerbaar** (PyPI, npm en het Ubuntu-archief zijn bereikbaar):

- via pip: `pymupdf` (1.28.2 beschikbaar), `pdfplumber`, `pypdf`, `Pillow`, `lxml`, `jsonschema`, `python-pptx`, `numpy`, `pytesseract`
- via apt: `poppler-utils`, `tesseract-ocr` (5.3.4) + `tesseract-ocr-eng`/`-nld`, `ffmpeg`
- via npm: `pptxgenjs` (4.0.1), Vite, Playwright, axe-core

Er is dus **geen toolblocker**. De volledige beoogde stack is opzetbaar zodra de bronbestanden bereikbaar zijn.

---

## 5. Schaalberekening voor "25 oefeningen per item"

**Harde basis:** 15 verwerkbare thema's (8 New Ace 3 + 7 van de 8 New Strike 3), uitgaande van één unit = één thema. New Strike 3 unit 8 bestaat wel maar is niet aangeleverd en telt hier dus niet mee; komt die pdf er later bij, dan schuiven de aantallen met één eenheid op.

**Geschatte basis (nog niet uit de bron afgeleid — vereist OCR):** onderstaande aantallen per thema zijn een gemotiveerde schatting voor een Vlaams derdejaars-EFL-handboek en **moeten na Fase A vervangen worden door echte tellingen**.

| Grootheid | Laag | Midden | Hoog |
|---|---|---|---|
| Grammaticaonderwerpen per thema | 2 | 3 | 4 |
| Woordenschatsets per thema | 1 | 2 | 3 |
| Lexemen per thema | 80 | 110 | 150 |
| **Grammaticaonderwerpen totaal** | 30 | **45** | 60 |
| **Woordenschatsets totaal** | 15 | **30** | 45 |
| **Lexemen totaal** | 1 200 | **1 650** | 2 250 |

### Scenario `topic_scope` — 25 activiteiten per grammaticaonderwerp én per woordenschatset

| Grootheid | Laag | Midden | Hoog |
|---|---|---|---|
| Scope-eenheden | 45 | **75** | 105 |
| **Activiteiten** | 1 125 | **1 875** | 2 625 |
| Antwoordmomenten (3–8 per activiteit) | ± 6 200 | **± 10 300** | ± 14 400 |
| Omvang content-JSON | ± 3 MB | **± 6 MB** | ± 9 MB |
| Batchindeling | 15 batches van 1 thema | ± 125 activiteiten per batch | |

### Scenario `lexeme_scope` — 25 activiteiten per grammaticaonderwerp én per afzonderlijk woord

| Grootheid | Laag | Midden | Hoog |
|---|---|---|---|
| Scope-eenheden | 1 230 | **1 695** | 2 310 |
| **Activiteiten** | 30 750 | **42 375** | 57 750 |
| Antwoordmomenten | ± 169 000 | **± 233 000** | ± 318 000 |
| Omvang content-JSON | ± 90 MB | **± 125 MB** | ± 170 MB |
| Batchindeling | 1 thema = ± 2 800 activiteiten → moet onderverdeeld worden in subbatches van ± 10 lexemen | | |

Daarbovenop, in beide scenario's: pagina-renders op 200 dpi voor 15 units (± 600 pagina's) ≈ **0,9–1,2 GB** in `build/`, plus 30 PPTX-bestanden (leerling + leerkracht per thema).

### Beoordeling

`lexeme_scope` is **niet verenigbaar met de kwaliteitsregels van je eigen masterprompt**. Sectie 2 eist dat semantische leerinhoud *item voor item inhoudelijk gecontroleerd* wordt en verbiedt "massaproductie met oppervlakkige sjabloonvarianten". Bij 42 000 activiteiten is dat niet realiseerbaar, en 25 verschillende volwaardige activiteiten per afzonderlijk woord leidt onvermijdelijk tot sjabloonherhaling — precies wat sectie 2 uitsluit.

**Advies: `topic_scope`**, met de 15 tot 45 lexemen van een set verdeeld over de 25 activiteiten van die set. Elk woord komt dan meermaals en in wisselende interactievormen terug, zonder kwaliteitsverlies.

---

## 6. Voorgesteld pilootthema

**New Ace 3 — UNIT 1** (de standaard uit de masterprompt).

Argumenten: New Ace 3 is met 8 units het grootste boek; unit 1 is met 54 pagina's tegelijk de omvangrijkste gesondeerde unit en bevat vermoedelijk de volledige rubriekenset, wat de designtokens en masterlayouts meteen breed test.

**Voorbehoud:** in veel methodes is unit 1 atypisch (instap- of herhalingsmateriaal). Blijkt dat na OCR het geval, dan is **New Ace 3 UNIT 4** (41 MB, midden in het boek) de betere piloot. Dit wordt gemeld vóór Fase B.

---

## 7. Openstaande beslissingen

Zie de vragenlijst in de sessie. Blokkerend: 1 (bronaanlevering), 2 (rechten/fidelity), 3 (scope-definitie). Niet-blokkerend met standaardwaarden: doelgroep, aantal readings/listenings, audio-beleid, leerling-/leerkrachtversies.
