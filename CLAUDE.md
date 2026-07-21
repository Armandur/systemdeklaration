# CLAUDE.md - Systemdeklaration

Generator för bridge-systemdeklarationer (SBF-formulär). Webbformulär ->
live-förhandsvisning -> utskriftsfärdig PDF (dubbelsidig liggande A4 med fyra
A6-paneler, skärs till två dubbelsidiga A6-kort för laminering/spiralbindning).

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
      sample.json        # Elisabeth/Johan-exempel (referens från task-256)

## Centrala designbeslut

- **Fast skelett, redigerbara värden.** SBF-formuläret är standardiserat -
  raderna (1♣...4-nivå, försvarssektioner osv.) är fasta i `config.py`; bara
  cellvärdena varierar per par. Ingen generisk tabellbyggare.
- **En källa för panel-HTML.** `panels/_macros.html` + `print.css` används av
  BÅDE webbförhandsvisningen och WeasyPrint-PDF:en, så de aldrig divergerar.
- **Imposition parameteriseras, härleds inte.** Vilken baksidespanel som
  hamnar bakom vilken framsida beror på skrivarens duplex-vändning. `sheet.html`
  tar `back_swap`/`back_rotate`/`trim_first_mm`/`cut_marks`; default long-edge
  (swap=on). Verifieras fysiskt av användaren, inte analytiskt.
- **Färgfärgning:** `config.render_suits()` wrappar ♣♠ svart, ♦♥ rött. Filter
  `suits`/`bud`/`bud_suit` i `render.py` (och `bud` i `pages.py`).

## Pappas fyra fynd (från task-256, alla åtgärdade)

1. 4-nivå-Spärr renderas som 3-nivå-raden (enradig, `bud`-token `4CDHS`).
2. "Mot 3♣♦" och "Mot 3♥♠" på samma rad (`tr.merged` i `_macros.html`).
3. Borttaget vitt utrymme - budtabellen fyller panelhöjden (`height:100%`).
4. Kort 1 några mm kortare - röd streckad `trim-guide` i `sheet.html`.

## Vanliga ändringar

- Ny rad/sektion i formuläret: lägg till i `config.py` (skelett) + fältet i
  `index.html` (med `data-path`) + rendering i `panels/_macros.html`.
- Justera A6-täthet: `static/print.css` (fontstorlekar i pt, panelmått i mm).

## Köra

`.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port <ledig>` (se `svc port`).
Registrera i portalen. Browser-verifiera med shot vid mobil + desktop.
