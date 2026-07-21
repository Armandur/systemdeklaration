# ROADMAP

## Klart (MVP)

- Webbformulär med hela SBF-skelettet, live-förhandsvisning.
- WeasyPrint-PDF: dubbelsidig liggande A4, fyra A6-paneler, skärmarkeringar.
- Spara/ladda/ta bort deklarationer (SQLite).
- Pappas fyra fynd åtgärdade (se CLAUDE.md).
- Färgsymboler med kortkommandon (/c /d /h /s) och röd/svart-färgning.
- 3-vägs tema (auto/ljust/mörkt).

## Kvar / idéer

- **Fysiskt vändningstest** av duplex-impositionen (long- vs short-edge) -
  kräver riktig skrivare. Default `back_swap` kan behöva bytas.
- Finjustera A6-tätheten mot en riktig utskrift (fontstorlek, radhöjd) -
  förhandsvisning på skärm är inte 1:1 med papper.
- CSRF-skydd på POST (verktyget är enanvändar-lokalt idag).
- Ev. duplicera en deklaration som utgångspunkt för nästa par.
- Ev. flera formulärvarianter (SBF har olika blankettверсioner).
- Deployment som Docker-container på TERVO2 om det ska bli permanent.

## Referens

Källmaterial i `/mnt/vmworkspace/systemdeklaration/`:
DeklarationElisabeth02.docx/.pdf, skiss.jpg (pappas markeringar), SBF-logo.
