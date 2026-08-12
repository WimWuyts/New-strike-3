# Antwoordsleutels

Oplossingen bij de oefeningen uit de handboeken, per thema één bestand
`<theme_id>.json` volgens `schemas/answer_key.json`.

## Dit is uitgeversinhoud

Alles hier is **broninhoud**, geen origineel werk. Het bestaat alleen onder de
bevestiging in `docs/rights-confirmation.md`, met `use_scope:
own_lesson_groups`: projectiemateriaal voor de eigen lesgroepen van de
leerkracht.

Drie regels die de code afdwingt:

1. `teacher_only` moet `true` zijn — het schema weigert de rest.
2. `provenance` is altijd `source_core`.
3. `use_scope` in het bestand moet overeenkomen met `rights.use_scope` in
   `config/project.yaml`, anders weigert de bouwstap.

## Waarom deze map wél in versiebeheer staat

`sources/` staat in `.gitignore`, deze map niet. Dat is een bewuste afweging:
de sleutels zijn met de hand samengesteld en niet opnieuw te genereren, dus
verliezen we ze zodra een werkomgeving wegvalt. Ze staan in een **private**
repository van de leerkracht zelf.

Wordt deze repository ooit openbaar gemaakt of met anderen gedeeld, dan moet
deze map er eerst uit — inclusief uit de geschiedenis. Dat valt buiten de
bevestigde `use_scope`.

## Wat de webomgeving hiermee doet

Niets. `src/web/content.ts` leest uitsluitend `data/content/` en
`data/catalog/`. Deze map ligt daar bewust buiten, zodat leerlingmateriaal er
technisch niet bij kan — niet door een fout, niet door een latere wijziging.

## Bouwen

```
make answers THEME=ace3-u1
```

Levert `dist/pptx/<boek>/<thema>-answers.pptx`: één antwoord per klik, met de
bronpagina in beeld en didactische aantekeningen in de speaker notes.

## Herroepen

Zet `rights.allow_source_answer_keys` op `false` en verwijder deze map. Geen
enkel ander onderdeel van het project hangt ervan af.
