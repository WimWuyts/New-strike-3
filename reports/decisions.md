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

### D5. New Strike 3 telt acht units, unit 8 heeft lage prioriteit

**Bevestigd door gebruiker.** Het boek heeft een unit 8, maar de leerkracht
geraakt er in de praktijk bijna nooit. De pdf is niet aangeleverd.

**Gevolg:**
- `strike3.unit_count` staat op 8 en `strike3-u8` staat in de kaart, zodat het
  boek correct beschreven is;
- het thema draagt `source_available: false` en `priority: low`;
- preflight meldt het als "bekend maar niet aangeleverd" en blokkeert er niet
  op; extract, catalog en batch slaan het over zonder het als fout te tellen;
- zodra de pdf in `sources/books/strike3/` staat en `source_available` op
  `true` gaat, loopt het thema gewoon mee.

Omdat de unit zelden aan bod komt, komt hij hoe dan ook als laatste aan de
beurt. Er wordt geen werk aan besteed zolang de zeven andere units niet af
zijn.

---

## Standaardwaarden, toegepast bij gebrek aan expliciete keuze

Conform sectie 3 van de masterprompt vastgelegd zonder aparte vraag.

| # | Onderwerp | Toegepaste standaard |
|---|---|---|
| S1 | Readings per thema | 2, elk met kern- en uitdagingsvariant |
| S2 | Listenings per thema | 2, elk met kern- en uitdagingsvariant |
| S3 | Audio | Alleen scripts en SSML; browser-spraaksynthese als fallback. Geen TTS-provider geconfigureerd, dus audio krijgt status `not_built` — nooit `voltooid`. |
| S4 | Leerling- en leerkrachtversie | Beide, voor web en voor PPTX |
| S5 | Pilootthema | New Ace 3 UNIT 1 (`ace3-u1`) — bevestigd, zie O3 |
| S6 | Engelse variant | `en-GB` — bevestigd voor beide boeken, zie O2 |
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

Geen. Alle intakevragen zijn beantwoord.

### Opgelost

**O1 — Bestaat New Strike 3 UNIT 8?** Ja. De gebruiker bevestigt dat het boek
acht units telt, maar dat unit 8 in de praktijk zelden bereikt wordt.

De pdf is niet aangeleverd. `strike3` staat daarom op `unit_count: 8` met
`strike3-u8` in de kaart, gemarkeerd als `source_available: false` en
`priority: low`. Zie D5.

**O2 — Klopt `en-GB` als variant?** Ja, bevestigd voor **beide** boeken.
`project.english_variant_confirmed` staat op `true`. De antwoordcontrole
normaliseert dus naar Britse spelling; Amerikaanse varianten worden niet
stilzwijgend goedgekeurd, tenzij een activiteit ze expliciet in
`accepted_variants` opneemt.

**O3 — Is `ace3-u1` een volwaardige unit?** Ja, net als `strike3-u1`. De
piloot blijft dus `ace3-u1` en de terugvaloptie `ace3-u4` vervalt.
`pilot.confirmed` staat op `true`.

Dat `strike3-u1` ook volwaardig is, betekent dat het tweede boek op zijn
eigen unit 1 kan starten zodra de piloot goedgekeurd is. Er is geen
instapunit die overgeslagen of anders behandeld moet worden.
