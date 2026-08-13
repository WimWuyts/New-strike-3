# Manual review queue

Alles wat niet met zekerheid uit de bron is af te leiden. Deze punten komen
**niet** ongecontroleerd in de content terecht.

Normaal vult `scripts/extract.py` deze lijst met OCR-blokken onder de
confidencedrempel. Voor `ace3-u1` is de bron niet door die pijplijn gegaan,
dus komen de punten hieronder uit de handmatige inventaris.

## New Ace 3 — Unit 1

### Onleesbaar op de scan

| Blz. | Punt | Gevolg |
|---|---|---|
| 25 | Tekstballonnen van *Brain camp* te klein om te lezen | Alleen het onderwerp is bekend, geen tekst |
| 10–16 | Tekstballonnen van de graphic novel niet overal scherp | Geen citaten overgenomen |
| 55 | Tekstballonnen in de ingesloten strip te klein | Alleen omringende tekst bekend |
| 61 | Laatste blok van de tijdlijn gelezen als "1970s", schrijfwijze niet scherp | Alleen relevant als de tijdlijn hergebruikt wordt |

Geen van deze vier blokkeert het werk: het gaat om bronteksten die we sowieso
niet overnemen. Ze staan hier omdat ze niet stilzwijgend mogen verdwijnen.

### Te bevestigen vóór het in `source_core` komt

| Blz. | Vraag | Waarom het uitmaakt |
|---|---|---|
| ~~46–49~~ | ~~**Het boek vermeldt nergens de woordsoort.**~~ **Afgehandeld:** woordsoorten komen in Engelse termen in de bank, met `part_of_speech_source: derived`. Zie D6 | — |
| 30 vs 46–49 | Schrijfwijzen verschillen tussen woordweb en woordenlijst, bv. `a guidance counsel(l)or` tegenover `a guidance counsellor (Br. E.) / counselor (Am. E.)` | Welke vorm is de bronvorm? De andere gaat naar de changelog |
| 29, 30 | Zestien woorden staan in het woordweb en de definitie-oefening **zonder vertaling** | Horen ze in `source_core`, of vallen ze buiten de bank? |
| 61 | `slavery`, `segregation`, `Jim Crow laws`, `separate but equal`, `civil rights movement`, `sit-ins`, `boycotts` staan in geen enkele woordenlijst | Eigen woordenschatset, of buiten scope? Het zijn inhoudelijke begrippen, geen taalleerdoel |
| 47 | Vertaling van `a high school` luidt "een middelbare school (vanaf 3de middelbaar)"; de tekst tussen haakjes staat in kleine druk | Nemen we de precisering mee in de bank? |

### Groeperingskeuzes die bevestiging vragen

| Blz. | Keuze | Alternatief |
|---|---|---|
| 17, 21, 32–33 | De drie tijdenkaders zijn samengevoegd tot één grammaticaonderwerp | Het boek toetst ze apart in Test yourself 4, 5 en 7. Splitsen geeft 75 activiteiten over één tijdenpaar |
| 47–48 | "How to describe school life" is gesplitst in plaatsen/mensen/voorwerpen en vakken | Het boek zet ze onder één kop: 54 woorden in één set |
| 39, 49 | Mr/Ms/Mrs/Miss is bij de e-mailconventies gezet | Het staat in het boek naast de genitief |
| 49 | "Good to know" is samengevoegd met het Amerikaanse schoolsysteem | Kan ook een eigen set zijn |

### Bewust niet overgenomen

| Blz. | Punt |
|---|---|
| 62 | Op de muur in Rockwells *The Problem We All Live With* staat racistische graffiti. Leesbaar, maar niet overgenomen. Als de unit dit schilderij inhoudelijk behandelt, hoort dat met didactische omkadering te gebeuren, niet als losse brontekst |
