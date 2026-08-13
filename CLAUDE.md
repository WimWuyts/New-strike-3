# CLAUDE.md — blijvende projectregels

Leermiddelenproject rond **New Ace 3** en **New Strike 3**. Dit bestand bevat
alleen regels die altijd gelden. Procedures staan in `docs/`, beslissingen in
`reports/decisions.md`, instellingen in `config/project.yaml`.

## Harde regels

1. **Wijzig nooit iets in `sources/`.** Read-only, en niet in versiebeheer.
2. **Vermeng de twee boeken nooit.** Elk item draagt `book_id`, `theme_id`,
   `source_page_refs` en `provenance`.
3. **Alle uitleg, teksten, voorbeelden, distractoren en feedback zijn origineel.**
   Geen overname uit de bron of uit English Grammar in Use.
4. **Geen paginagetrouwe reproductie** zolang `rights.confirmed: false` in
   `config/project.yaml`. Geen bronbeelden, geen rasterachtergronden in slides.
5. **Bronwoorden blijven intact** in `source_core`; nieuwe woorden in
   `extension`. Elke afwijking van de bron gaat naar de changelog, nooit stil.
6. **Geen placeholders**, lorem ipsum, lege answer keys of TODO's in output.
   Elke vraag moet aantoonbaar beantwoordbaar zijn uit de stimulus.
7. **Geen secrets in het project.** Alleen environment variables.
8. **Idempotent werken.** Een onderbroken run is veilig hervatbaar via
   `state/progress.json` en `state/content-hashes.json`.
9. **Engels** voor alle leerlingtekst: opdrachten, instructies, hints en
   feedback. Variant: `en-GB`. Nederlands blijft alleen in leerkrachtmateriaal
   over het handboek, zoals de antwoordsleutel.

## Scope van de oefeningen

`topic_scope`: exact **25 activiteiten** per grammaticaonderwerp en per
woordenschatset. Niet per afzonderlijk woord. Verdeling over 5 stages van elk
5 activiteiten, oplopend van receptief naar productief. De quota per type staan
in `config/project.yaml` onder `exercises.quotas` en worden afgedwongen door
`scripts/validate.py`.

Eén activiteit = één afgeronde interactieve opdracht met eigen leerdoel,
instructie, stimulus, feedbacklogica en 3–8 betekenisvolle antwoordmomenten.
Splits nooit kunstmatig om aan 25 te komen.

## Commando's

Alles loopt via `make`. Elk commando is veilig opnieuw uit te voeren.

```
make setup                          # venv + node deps + systeemcheck
make preflight                      # inventariseer sources/, schrijf rapporten
make extract BOOK=ace3              # render + OCR naar data/extracted/
make catalog                        # curriculumkaart + scope-berekening
make pilot BOOK=ace3 THEME=ace3-u1
make validate THEME=ace3-u1         # schema's + quota + antwoordbaarheid
make web THEME=ace3-u1
make pptx BOOK=ace3 THEME=ace3-u1
make render-pptx BOOK=ace3 THEME=ace3-u1
make batch BOOK=ace3
make release
```

## Naamgeving

- Thema-ID: `<book_id>-u<nummer>` — `ace3-u1`, `strike3-u7`.
- Grammaticaonderwerp: `<theme_id>-gr-<slug>`.
- Woordenschatset: `<theme_id>-vocab-<slug>`.
- Activiteit: `<target_id>-act-<01..25>`.
- Reading/listening: `<theme_id>-read-<n>`, `<theme_id>-listen-<n>`.

## QA-eisen voor publicatie naar `dist/`

Een artefact gaat pas naar `dist/` als **alle** controles groen zijn:

- JSON-schema geldig;
- exact 25 activiteiten per scope-eenheid, unieke ID's;
- alle quota gehaald, geen interactiepatroon vaker dan 3×;
- elke vraag beantwoordbaar, elke `canonical_answer` niet-leeg;
- reading/listening: elke inhoudsvraag heeft een `evidence_ref`;
- leerling- en leerkrachtoutput correct gescheiden, geen antwoorden in
  alt-tekst, bestandsnamen of leerlinglagen;
- PPTX rendert zonder overflow, overlap of fontsubstitutie;
- axe-core zonder violations, toetsenbordnavigatie werkt;
- opgenomen in `dist/release-manifest.json` met hash en QA-status.

## Wat deze omgeving niet kan

De bron-pdf's zijn **gerasterde scans met een gepersonaliseerd watermerk** en
hebben **geen tekstlaag**. Alle tekst komt uit OCR; fonts en kleuren worden
afgeleid uit beeldanalyse, niet uit pdf-metadata. Behandel OCR-output altijd
als onzeker: alles onder `extraction.ocr_min_confidence` gaat naar
`reports/manual-review-queue.md` in plaats van naar de content.
