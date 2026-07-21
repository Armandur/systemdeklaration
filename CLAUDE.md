# CLAUDE.md - Systemdeklaration

Generator för bridge-systemdeklarationer (SBF-formulär). Webbformulär ->
live-förhandsvisning -> utskriftsfärdig PDF (dubbelsidig stående A4, 2x2-rutnät
av A6-paneler = två exemplar per ark, skärs till A6-kort för laminering).

## Stack

- Backend: Python 3.12 + FastAPI (uvicorn), venv via `uv`.
- PDF: WeasyPrint (HTML/CSS -> PDF). Kräver Pango/Cairo (finns på VM:en).
- Templates: Jinja2. Frontend: vanilla JS (ES-moduler) + Pico CSS + tokens.css.
- Databas: SQLite (rå `sqlite3`), en tabell `declarations` (JSON-payload).

## Filstruktur

    app/
      main.py            # FastAPI-app, lifespan, router-registrering
      config.py          # fast SBF-skelett, färgglyfer, empty_declaration()
      database.py        # sqlite: declarations (id, name, payload JSON, ts)
      render.py          # Jinja-miljö + filter, WeasyPrint-PDF/preview
      routes/
        pages.py         # GET / (formuläret)
        api.py           # CRUD + /api/preview (HTML) + /api/pdf
      templates/
        index.html       # formulär + live-preview + PDF-knapp
        sheet.html       # WeasyPrint: A4-imposition av fyra paneler
        preview.html     # fristående HTML för webb-iframe (samma paneler)
        panels/_macros.html  # de fyra A6-panelerna (delas preview<->PDF)
      static/
        print.css        # panel-/A6-stil, delas av preview och PDF
        app.css, app.js, utils.js, tokens.css, pico.min.css, sbf-logo.png
    data/
      sample.json        # fiktivt exempel (Anna/Bertil) för demo och tester

## Centrala designbeslut

- **Fast skelett, redigerbara värden.** SBF-formuläret är standardiserat -
  raderna (1♣...4-nivå, försvarssektioner osv.) är fasta i `config.py`; bara
  cellvärdena varierar per par. Ingen generisk tabellbyggare.
- **En källa för panel-HTML.** `panels/_macros.html` + `print.css` används av
  BÅDE webbförhandsvisningen och WeasyPrint-PDF:en, så de aldrig divergerar.
- **A4 stående, 2x2, två exemplar.** Slutresultatet är A6, så arket är stående
  A4 med fyra A6-paneler (`@page A4 portrait; margin 5.5mm 5mm` i print.css;
  panel 100x143mm). En rad = ett exemplar (kort 1 vänster, kort 2 höger); båda
  raderna är samma deklaration så alla fyra A6-rutor nyttjas. `render._build_slots()`
  bygger fram-/bak-slotlistorna.
- **Imposition parameteriseras, härleds inte.** Vilken baksidespanel som
  hamnar bakom vilken framsida beror på skrivarens duplex-vändning. `_build_slots`
  tar `back_swap`/`back_rotate`/`trim_first_mm`/`cut_marks`; default long-edge
  (swap=on, byter kolumn inom raden). Verifieras fysiskt av användaren.
- **Färgfärgning:** `config.render_suits()` wrappar varje färg i en per-färg-klass
  (`suit-c/d/h/s`). Filter `suits`/`bud`/`bud_suit` i `render.py` (och `bud` i
  `pages.py`). print.css ger tvåfärg som default; klassen `.fourcolor` på behållaren
  (styrd av `payload.display.four_color`) slår om till fyrfärgslek (♣ grön, ♦ blå,
  ♥ röd, ♠ svart). Sätts via kryssrutan i palettraden, sparas per deklaration.

## Pappas fyra fynd (från task-256, alla åtgärdade)

1. 4-nivå-Spärr renderas som 3-nivå-raden (enradig, `bud`-token `4CDHS`).
2. "Mot 3♣♦"/"Mot 3♥♠" - var på samma rad ett tag för att spara plats, men
   ligger nu på var sin rad igen (platsen vanns via 2x2/A6-omläggningen).
3. Borttaget vitt utrymme - budtabellen fyller panelhöjden (`height:100%`).
4. Kort 1 några mm kortare - röd streckad `trim-guide` på kort 1:s båda faces
   (omslag + öppningsbud) i `sheet.html`.

## Vanliga ändringar

- Ny rad/sektion i formuläret: lägg till i `config.py` (skelett) + fältet i
  `index.html` (med `data-path`) + rendering i `panels/_macros.html`.
- Justera A6-täthet: `static/print.css` (fontstorlekar i pt, panelmått i mm).

## Köra

`.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port <ledig>` (se `svc port`).
Registrera i portalen. Browser-verifiera med shot vid mobil + desktop.
