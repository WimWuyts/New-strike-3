# Rechtenbevestiging

Vastgelegd op 2026-08-12. Dit bestand is de poort die
`config/project.yaml` controleert voordat er iets met broninhoud gebeurt.

## Wie en wat

De gebruiker is leerkracht Engels en beschikt over persoonlijke
licentiekopieën van de digiboeken **New Ace 3** en **New Strike 3**. De
bestanden dragen een gepersonaliseerd watermerk op elke pagina, wat bevestigt
dat het om een aan die persoon gebonden licentie gaat.

## Wat hiermee bevestigd is

De leerkracht bevestigt dat de oplossingen bij de oefeningen uit het handboek
verwerkt mogen worden tot **projectiemateriaal voor de eigen lesgroepen**.

`use_scope: own_lesson_groups`.

Dat is bewust smal. Het dekt: de leerkracht projecteert de correctie in de
eigen klas, bij leerlingen die met datzelfde handboek werken.

Het dekt **niet**: verspreiding binnen de vakgroep of de school, doorgeven aan
collega's, plaatsing op een leerplatform dat verder reikt dan de eigen
lesgroepen, of publicatie in welke vorm dan ook. Wil je een van die dingen,
werk dit bestand dan eerst bij en verzet `use_scope`.

## Wat hiermee niet bevestigd is

Deze bevestiging gaat **uitsluitend over antwoordsleutels**. Ze zegt niets over
pagina- of beeldreproductie, en die blijven geblokkeerd:

| Instelling | Stand | Betekenis |
|---|---|---|
| `allow_source_answer_keys` | `true` | Oplossingen bij de boekoefeningen mogen verwerkt worden |
| `answer_keys_teacher_only` | `true` | Uitsluitend in leerkrachtmateriaal, nooit in leerlingoutput |
| `allow_page_faithful_reproduction` | `false` | Geen paginagetrouwe nabouw van het handboek |
| `allow_source_image_reuse` | `false` | Geen bronbeelden overnemen |
| `allow_raster_slide_backgrounds` | `false` | Geen scans als slideachtergrond |

Die drie laatste staan los. Ze bewegen niet mee met de bevestiging hierboven,
en de code dwingt dat af: `assert_may_reproduce_pages()` kijkt naar de
specifieke vlag, niet naar `confirmed`.

## Hoe dit in de bouw doorwerkt

- Antwoordsleutels leven in `data/answers/`, gescheiden van `data/content/`.
  De webbuild leest alleen `data/content/`, dus leerlingmateriaal kan er
  technisch niet bij.
- Het correctiedeck krijgt het achterschrift "Leerkrachtmateriaal — eigen
  lesgroepen" op elke slide.
- Elk artefact met broninhoud draagt `provenance: source_core` en
  `rights_status: licensed_confirmed`, zodat in
  `dist/release-manifest.json` zichtbaar blijft welke bestanden onder deze
  bevestiging vallen.
- Alle overige materialen — woordenschatbanken, grammaticamodules, readings,
  listenings, de 25 activiteiten — blijven volledig origineel. Daar verandert
  deze bevestiging niets aan.

## Herroepen

Zet `rights.allow_source_answer_keys` op `false` en verwijder `data/answers/`.
De rest van het project blijft dan gewoon werken: er is geen enkel onderdeel
dat van de antwoordsleutels afhangt.
