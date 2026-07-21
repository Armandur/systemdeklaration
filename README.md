# Systemdeklaration

Webbverktyg som genererar utskriftsfärdiga systemdeklarationer för bridge
enligt Sveriges Bridgeförbunds formulär. Man fyller i sina konventioner i ett
webbformulär, ser en live-förhandsvisning och laddar ner en PDF.

PDF:en är en **dubbelsidig, stående A4** med ett 2x2-rutnät av A6-paneler.
Arket innehåller **två identiska exemplar** av deklarationen (ett per rad) så
att alla fyra A6-rutor nyttjas. Efter utskrift skär man ett vertikalt och ett
horisontellt snitt = fyra A6-blad = **två kompletta deklarationer**, var och en
ett dubbelsidigt A6-kort att laminera och spiralbinda.

## De fyra panelerna

| Kort | Framsida | Baksida |
|------|----------|---------|
| Kort 1 | Omslag (namn, grundsystem, prickar) | Öppningsbud (budtabell) |
| Kort 2 | Konventioner + försvarsbud | Utspel, vändor, markeringar |

## Köra lokalt

```sh
uv venv --python 3.12
uv pip install -r requirements.txt
.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8008
```

Öppna sedan http://ubuntu-ai:8008/

WeasyPrint kräver systembibliotek (Pango/Cairo/gdk-pixbuf) - finns redan på
VM:en. På ren Ubuntu: `apt install libpango-1.0-0 libpangocairo-1.0-0
libgdk-pixbuf-2.0-0`.

## Utskrift och imposition

- Skriv ut **dubbelsidigt** i stående A4.
- Panelernas placering på baksidan styrs av kryssrutorna under "Utskrift":
  - **Byt vänster/höger på baksidan** (default på) - för långsidesvändning,
    vanligast i kontorsskrivare.
  - **Rotera baksidan 180°** - för kortsidesvändning.
  - Testa fysiskt: håll det utskrivna arket mot ljus, baksidorna ska ligga
    rakt bakom framsidorna. Justera annars kryssrutorna.
- **Korta kort 1 (mm)** ritar en röd streckad skärlinje så att första kortet
  blir några mm kortare - gör det lättare att öppna det bundna häftet.
- Färgsymboler skrivs som ♣ ♦ ♥ ♠ eller kortkommandon `/c /d /h /s` i
  textfälten; röda färger (ruter/hjärter) färgas röda automatiskt.

## Stack

FastAPI + Jinja2 + WeasyPrint, vanilla JS + Pico CSS. SQLite lagrar sparade
deklarationer som JSON. Se `CLAUDE.md` för filstruktur och designbeslut.
