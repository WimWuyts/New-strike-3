# Afgiftemap voor bronbestanden

Tijdelijke doorgeefluik voor bron-pdf's die verwerkt moeten worden.

## Waarom deze map bestaat

`sources/` staat in `.gitignore`, zodat bronbestanden niet per ongeluk in
versiebeheer belanden. Dat is de gewenste standaard. Maar om een pdf éénmalig
door de extractie te halen op een machine die het bestand niet kan bereiken,
moet hij wél even mee. Deze map is die uitzondering, bewust zichtbaar en
bewust tijdelijk.

## Werkwijze

1. Maak een **aparte branch**, bijvoorbeeld `bron-dropoff`. Zet bronbestanden
   nooit op een werkbranch: dan blijven ze voorgoed in de projectgeschiedenis.
2. Kopieer de pdf in deze map.
3. Commit en push die branch.
4. Laat weten dat het bestand er staat.

Na de extractie:

5. De OCR-uitvoer komt in `data/extracted/` en wordt op de werkbranch gezet.
6. De branch met de pdf wordt verwijderd. Het bestand zit dan in geen enkele
   bewaarde geschiedenis meer.

## Wat hier niet hoort

- Geen bestanden op een werkbranch of op de standaardbranch.
- Geen volledige boeken; alleen de unit die op dat moment verwerkt wordt.
- Niets dat na de extractie nog moet blijven staan.

De map zelf blijft leeg in versiebeheer: alleen dit bestand hoort hier
permanent thuis.
