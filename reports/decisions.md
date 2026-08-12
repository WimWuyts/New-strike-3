# Beslissingslogboek

Elke beslissing die de pipeline bindt. Bij wijziging: pas ook
`config/project.yaml` aan en noteer de datum.

---

## 2026-08-12 — Intake na preflight

### D1. Bronaanlevering — *lokaal draaien*

**Beslist door gebruiker.** De remote sessie kan `drive.google.com` niet
bereiken (egress-beleid, 403 op CONNECT) en de Drive-connector levert inhoud
alleen als base64 in het gesprek, wat voor pdf's van 18–53 MB onwerkbaar is.

**Gevolg:** dit project wordt lokaal gedraaid met de pdf's in
`sources/books/ace3/` en `sources/books/strike3/`. De remote sessie levert de
volledige projectomgeving, pipeline en scripts op; extractie en
contentproductie gebeuren op de machine van de gebruiker.

### D2. Rechten en PowerPointmodus — *alleen origineel materiaal*

**Beslist door gebruiker.** `rights.status: original_only`.

**Gevolg:**
- PowerPoint uitsluitend in `hybrid_classroom_16x9`, opgebouwd uit eigen
  designtokens en eigen vormen.
- `page_faithful_portrait` blijft uit.
- Geen bronbeelden in `assets/original/`, geen rasterachtergronden uit de bron.
- Inventariseren, curriculumkaart en originele companion materials mogen wel.

Deze keuze is bindend zolang `sources/licenses/RIGHTS_CONFIRMATION.md`
ontbreekt. Komt die bevestiging er later, dan is dit herzienbaar zonder dat
bestaand werk vervalt.

### D3. Scope van de 25 oefeningen — *topic_scope*

**Beslist door gebruiker.** 25 activiteiten per grammaticaonderwerp en per
woordenschatset, niet per afzonderlijk woord.

**Onderbouwing:** `lexeme_scope` zou op ± 42 000 activiteiten uitkomen. Dat is
onverenigbaar met de projectregel dat semantische leerinhoud item voor item
inhoudelijk gecontroleerd wordt, en zou onvermijdelijk tot sjabloonherhaling
leiden.

**Gevolg:** de lexemen van een woordenschatset worden over de 25 activiteiten
van die set verdeeld, zodat elk woord meermaals en in wisselende
interactievormen terugkomt. Verwachte omvang: ± 1 875 activiteiten.

### D4. Doelgroep — *per boek gedifferentieerd*

**Beslist door gebruiker.**

| Boek | Doelgroep | CEFR-richtniveau |
|---|---|---|
| New Ace 3 | 3e jaar, doorstroomfinaliteit | A2+ tot B1 |
| New Strike 3 | 3e jaar, dubbele of arbeidsmarktfinaliteit | A2 |

**Gevolg:** tekstlengte, zinscomplexiteit, woordenschatselectie en
opdrachtsturing verschillen per boek. Dit wordt afgedwongen in de
niveaucontrole van `scripts/validate.py`.

---

## Standaardwaarden, toegepast bij gebrek aan expliciete keuze

Conform sectie 3 van de masterprompt vastgelegd zonder aparte vraag.

| # | Onderwerp | Toegepaste standaard |
|---|---|---|
| S1 | Readings per thema | 2, elk met kern- en uitdagingsvariant |
| S2 | Listenings per thema | 2, elk met kern- en uitdagingsvariant |
| S3 | Audio | Alleen scripts en SSML; browser-spraaksynthese als fallback. Geen TTS-provider geconfigureerd, dus audio krijgt status `not_built` — nooit `voltooid`. |
| S4 | Leerling- en leerkrachtversie | Beide, voor web en voor PPTX |
| S5 | Pilootthema | New Ace 3 UNIT 1 (`ace3-u1`), met `ace3-u4` als terugvaloptie |
| S6 | Engelse variant | `en-GB`, te herbevestigen zodra OCR de bron leesbaar maakt |
| S7 | Interfacetaal | Nederlands |

---

## Technische vaststellingen uit de preflight

| # | Vaststelling | Gevolg |
|---|---|---|
| T1 | Geen tekstlaag in beide boeken | OCR verplicht voor 100 % van de paginas |
| T2 | Gepersonaliseerd watermerk `Wim Wuyts` op elke pagina | Watermerkfilter in de OCR-pijplijn; extra reden om rasterreproductie te vermijden |
| T3 | Geen font-, kleur- of bounding-box-metadata beschikbaar | Designtokens worden afgeleid uit beeldanalyse, met lagere zekerheid en een grotere manual review queue |
| T4 | English Grammar in Use niet aanwezig | Fase D gaat door zonder deze private referentielaag. Geen invloed op leerlingmateriaal, want overname was sowieso verboden |
| T5 | New Strike 3 UNIT 8 niet aangeleverd | Openstaande vraag: telt het boek 7 units of ontbreekt er een? |
| T6 | Toolchain volledig installeerbaar | Python 3.11, Node 22, LibreOffice 24.2 aanwezig; pymupdf, tesseract, poppler, ffmpeg en pptxgenjs installeerbaar |

---

## Openstaande punten

| # | Vraag | Blokkeert |
|---|---|---|
| O1 | Bestaat New Strike 3 UNIT 8? | Volledigheid van de curriculumkaart voor strike3 |
| O2 | Klopt `en-GB` als variant? | Spellingnormalisatie in de antwoordcontrole |
| O3 | Is `ace3-u1` een volwaardige unit of een instapunit? | Definitieve pilootkeuze; wordt beantwoord door Fase A |
