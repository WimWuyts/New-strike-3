# New Ace 3 / New Strike 3 — leermiddelenomgeving

Pipeline en leeromgeving rond de handboeken **New Ace 3** en **New Strike 3**:
originele woordenschatbanken, grammaticamodules, readings, listenings,
oefenreeksen, een statische HTML-leeromgeving en klasklare PowerPoints.

> **Bronbestanden zitten niet in deze repo.** `sources/` staat in `.gitignore`.
> De pdf's zijn gewatermerkte persoonlijke licentiekopieën en horen niet in
> versiebeheer.

---

## 1. Bronbestanden klaarzetten

Plaats de pdf's exact zo:

```
sources/
  books/
    ace3/
      Digiboek - New Ace 3 UNIT 1.pdf
      ... t/m UNIT 8
    strike3/
      Digiboek - New Strike 3 UNIT 1.pdf
      ... t/m UNIT 7
      # UNIT 8 bestaat maar is niet aangeleverd. Zet je hem er later bij,
      # dan moet source_available voor strike3-u8 in config/project.yaml
      # op true.
  licenses/
    RIGHTS_CONFIRMATION.md     # optioneel, zie §6
```

## 2. Installatie

Vereist: Python 3.11+, Node 20+, en de systeemtools hieronder.

**Systeemtools** (Debian/Ubuntu):

```bash
sudo apt-get install -y poppler-utils tesseract-ocr tesseract-ocr-eng \
                        tesseract-ocr-nld ffmpeg libreoffice
```

macOS:

```bash
brew install poppler tesseract tesseract-lang ffmpeg
brew install --cask libreoffice
```

Daarna:

```bash
make setup
```

Dit maakt een projectlokale `.venv`, installeert de Python- en
Node-afhankelijkheden uit de lockfiles, en controleert of alle systeemtools
gevonden worden. `make setup` is veilig opnieuw uit te voeren.

## 3. Werkvolgorde

De fases hebben bewuste stopmomenten. Sla ze niet over.

```bash
make preflight                          # inventariseer sources/, technische staat
make extract BOOK=ace3                  # render paginas + OCR
make extract BOOK=strike3
make catalog                            # curriculumkaart + scope-berekening
```

**Quality Gate 1.** Lees `reports/curriculum-map.md` en
`reports/manual-review-queue.md`. Corrigeer wat fout is voordat je verder gaat.

```bash
make pilot BOOK=ace3 THEME=ace3-u1      # bouw één thema volledig
make validate THEME=ace3-u1
make web THEME=ace3-u1
make pptx BOOK=ace3 THEME=ace3-u1
make render-pptx BOOK=ace3 THEME=ace3-u1
```

**Quality Gate 2.** Lees `reports/pilot-review.md`. Pas na goedkeuring:

```bash
make batch BOOK=ace3
make batch BOOK=strike3
make release
```

Elk commando is idempotent: wat al gebouwd en ongewijzigd is, wordt
overgeslagen op basis van `state/content-hashes.json`. Forceer opnieuw bouwen
met `FORCE=1`.

## 4. Tests

```bash
make test        # Python: blueprintquota en validator, 39 tests
make test-web    # browser- en toegankelijkheidstests, 18 tests op desktop en mobiel
make lint        # TypeScript typecheck
```

`make test-web` bouwt eerst een synthetisch testthema (`scripts/make_test_fixture.py`),
daarna de webbuild, en draait dan Playwright met axe-core. Dat testthema is
testmateriaal, geen leerinhoud, en staat niet in versiebeheer.

`make render-pptx` heeft een werkende headless LibreOffice nodig. Controleer dat
met `soffice --headless --convert-to pdf <bestand>`; in sommige containers is
die conversie stuk, en dan faalt de visuele deck-QA terwijl de decks zelf prima
zijn.

## 5. Wat de pipeline oplevert

| Pad | Inhoud |
|---|---|
| `data/extracted/` | OCR-resultaat per pagina, met confidence en bounding boxes |
| `data/catalog/` | Curriculumkaart, themalijst, scope-berekening |
| `data/content/` | Woordenschat, grammatica, readings, listenings, activiteiten |
| `dist/web/` | Statische leeromgeving, werkt zonder netwerk |
| `dist/pptx/` | Leerling- en leerkrachtdecks per thema |
| `dist/printable/` | Printbare kerninhoud en answer keys |
| `reports/` | Rapporten en QA |

## 6. Rechten

De bron-pdf's dragen een gepersonaliseerd watermerk en zijn persoonlijke
licentiekopieën van commercieel uitgeversmateriaal.

Standaard staat het project op `rights.status: original_only`:

- ✅ inventariseren, curriculumkaart, volledig originele companion materials,
  PowerPoints met eigen designtokens (`hybrid_classroom_16x9`);
- ❌ paginagetrouwe reproductie, hergebruik van bronbeelden,
  rasterachtergronden uit de bron.

Wil je die laatste categorie inschakelen, dan moet
`sources/licenses/RIGHTS_CONFIRMATION.md` bestaan én
`rights.confirmed: true` in `config/project.yaml` staan. De pipeline
weigert anders elke paginagetrouwe build.

## 7. Belangrijk over de bronkwaliteit

De pdf's hebben **geen tekstlaag** — het zijn paginascans met een watermerk
over elke pagina. Gevolgen voor je verwachtingen:

- Alle tekst komt uit OCR en is dus foutgevoelig. Blokken onder de
  confidencedrempel gaan naar `reports/manual-review-queue.md` en komen
  **niet** ongecontroleerd in de content terecht.
- Fonts en kleuren worden afgeleid uit beeldanalyse, niet uit pdf-metadata.
  De designtokens zijn een benadering, geen exacte reconstructie.
- Reken op een handmatige correctieronde na `make catalog`. Dat is bewust:
  liever een expliciete reviewwachtrij dan stilzwijgend verzonnen inhoud.

## 8. Projectstructuur

```
config/project.yaml     centrale instellingen, bindend voor de pipeline
schemas/                JSON Schemas per entiteit
scripts/                Python-pipeline
src/web/                Vite + TypeScript leeromgeving
src/pptx/               PptxGenJS deckgenerator
tests/                  unit-, schema-, browser- en toegankelijkheidstests
state/                  voortgang en contenthashes, voor hervatbaarheid
reports/                rapporten en QA
```

Blijvende projectregels staan in `CLAUDE.md`, beslissingen in
`reports/decisions.md`.
