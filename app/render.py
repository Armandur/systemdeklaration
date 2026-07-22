"""Rendering: Jinja-miljö, färgfilter och WeasyPrint-PDF/förhandsvisning."""
import base64
from functools import lru_cache

from jinja2 import Environment, FileSystemLoader, select_autoescape
from markupsafe import Markup

from . import config

_env = Environment(
    loader=FileSystemLoader(str(config.BASE_DIR / "templates")),
    autoescape=select_autoescape(["html"]),
)
def _suit_only(s: str) -> Markup:
    glyph = config.SUIT_GLYPH.get(s, s)
    cls = config.SUIT_CLASS.get(glyph, "")
    return Markup(f'<span class="{cls}">{glyph}︎</span>')


_env.filters["suits"] = lambda t: Markup(config.render_suits(t))
_env.filters["bud"] = lambda t: Markup(config.render_bud(t))
_env.filters["bud_suit"] = _suit_only
_env.filters["stacked"] = lambda t: Markup(config.render_stacked(t))


@lru_cache(maxsize=1)
def _logo_data_uri() -> str:
    raw = (config.BASE_DIR / "static" / "sbf-logo.png").read_bytes()
    return "data:image/png;base64," + base64.b64encode(raw).decode()


def _resolve_logo(d: dict) -> str | None:
    """Avgör vilken logotyp-bild (om någon) som ska visas på omslaget,
    styrt av display.logo: 'sbf' (default) | 'none' | 'custom'."""
    disp = d.get("display", {}) or {}
    mode = disp.get("logo", "sbf")
    if mode == "none":
        return None
    if mode == "custom":
        return disp.get("logo_data") or None
    return _logo_data_uri()


def _print_css() -> Markup:
    # Ej cachad: läses fritt från disk så CSS-ändringar syns direkt utan
    # serveromstart (filen är liten). Logon nedan är fortsatt cachad.
    # Markup så CSS:en INTE HTML-escapas när den injiceras i <style> (annars
    # bryts font-family: "DejaVu Sans" av autoescaping -> serif-fallback).
    css = (config.BASE_DIR / "static" / "print.css").read_text(encoding="utf-8")
    return Markup(css)


_PANEL_NAMES = ("cover", "opening", "defense", "leads")


def _panel_scale(d: dict, name: str) -> float:
    """--font-scale för en given panel (cover/opening/defense/leads).
    Manuellt läge (display.font_mode == 'manual'): samma globala skala
    (display.font_scale) för alla paneler. Annars (auto): per-panel-skala
    ur display.font_scales - en dict som klientens autofit i
    förhandsvisnings-iframen fyller (se app.js). Saknas värde -> 1
    (ingen skalning), så tomma/äldre deklarationer beter sig som förut."""
    disp = d.get("display", {}) or {}
    mode = disp.get("font_mode", "auto")
    if mode == "manual":
        val = disp.get("font_scale", 1.0)
    else:
        val = (disp.get("font_scales") or {}).get(name, 1.0)
    try:
        return float(val) if val not in (None, "") else 1.0
    except (TypeError, ValueError):
        return 1.0


def _panel_scales(d: dict) -> dict:
    return {name: _panel_scale(d, name) for name in _PANEL_NAMES}


# ---- Server-sidig autofit (TASK-327) --------------------------------------
# Klientens autofit (app.js) styr live-previewen (snabbt DOM-mätt estimat).
# Här mäter vi i stället EXAKT med WeasyPrint självt, och används bara för
# PDF/exakt-PDF (render_sheet_html) - se filkommentar vid anropsstället.

_MEASURE_MACRO_CALLS = {
    "cover": "p.panel_cover(d, logo_src, scale)",
    "opening": "p.panel_opening(d, scale, row_fill)",
    "defense": "p.panel_defense(d, scale)",
    "leads": "p.panel_leads(d, scale)",
}


def _find_panel_box(box):
    """Djup-först-sök i WeasyPrints boxträd efter den box vars element har
    CSS-klassen 'panel' (dvs panelens root-div, border-box)."""
    el = getattr(box, "element", None)
    if el is not None and "panel" in (el.get("class", "") or "").split():
        return box
    for child in getattr(box, "children", []) or []:
        found = _find_panel_box(child)
        if found is not None:
            return found
    return None


def _measure_panel_h_mm(kind: str, d: dict, scale: float, panel_w_mm: float,
                         logo_src: str | None, row_fill: float = 0.0) -> float:
    """Rendera EN panels innehåll fristående (fast bredd, height:auto,
    overflow:visible på en gigantisk sida) och mät dess faktiska
    border-box-höjd i mm via WeasyPrint. Detta är den bevisade mättekniken
    (se TASK-327-uppdraget) - exakt, inget estimat. ~200-250ms per anrop."""
    from weasyprint import HTML
    call = _MEASURE_MACRO_CALLS[kind]
    tmpl_src = (
        "<!DOCTYPE html><html><head><meta charset='utf-8'><style>{{ css }}\n"
        "@page{size:%.3fmm 2000mm;margin:0}html,body{margin:0}\n"
        ".measure .panel{width:%.3fmm;height:auto;overflow:visible}\n"
        "</style></head><body class='measure'>"
        "{%% import 'panels/_macros.html' as p %%}"
        "{{ " + call + " }}</body></html>"
    ) % (panel_w_mm, panel_w_mm)
    html = _env.from_string(tmpl_src).render(
        css=_print_css(), d=d, scale=scale, row_fill=row_fill, logo_src=logo_src,
    )
    doc = HTML(string=html, base_url=str(config.BASE_DIR)).render()
    panel_box = _find_panel_box(doc.pages[0]._page_box)
    # OBS: WeasyPrints Box.height är content-box-höjd (padding/border
    # exkluderat) - INTE border-box, trots att padding sitter "inuti"
    # box-sizing:border-box konceptuellt. panel_h_mm (målvärdet vi jämför
    # mot) är CSS-höjden på .panel, som ÄR border-box. Måste alltså lägga
    # tillbaka padding+border här för att få en höjd som är jämförbar med
    # panel_h_mm - annars blir varje panel felaktigt "för kort" med precis
    # paddingens belopp (8mm vid --pad:4mm), vilket för Fas 2 (radutfyllnad)
    # ger en alldeles för stor utfyllnad och panelen svämmar över och
    # spiller en rad till en extra sida (upptäckt empiriskt vid verifiering).
    px_h = (panel_box.height + panel_box.padding_top + panel_box.padding_bottom
            + panel_box.border_top_width + panel_box.border_bottom_width)
    return px_h / 96 * 25.4


# Säkerhetsmarginal (mm) mot panel_h vid alla höjdjämförelser nedan. Utan
# den landar Fas 2 (radutfyllnad) exakt på gränsen där WeasyPrints paginering
# knäcker: tabeller fragmenteras över sidbrytning oavsett .panel { overflow:
# hidden } (overflow klipper bara VISUELLT vid rendering, det hindrar inte
# WeasyPrints layout-fragmentering av en tabell som "precis" inte får plats).
# Upptäckt empiriskt: en isolerad mätning exakt lika med panel_h gav ändå en
# extra tredje sida med sista raden bortklippt till en spilld sida - en
# marginal krävs för att stanna på säker sida av den gränsen.
_AUTOFIT_SAFETY_MM = 1.0


def _autofit_panel(kind: str, d: dict, panel_w_mm: float, panel_h_mm: float,
                    logo_src: str | None) -> tuple[float, float]:
    """Fas 1 (alla paneler): mät naturlig höjd vid scale=1.0. Får den plats
    (<= panel_h_mm minus säkerhetsmarginal) - klart, ingen binärsökning
    behövs (vanligast, sparar tid). Svämmar den över - binärsök största
    skala i [0.6, 1.0] som får plats. INGEN tillväxt >1.0 (skulle spräcka
    fasta kolumnbredder - utanför scope).
    Fas 2 (bara 'opening'): finns vertikalt tomrum kvar vid vald skala,
    fördela det som extra rad-padding (--row-fill) så tabellen fyller
    panelen. En verifieringsmätning med utfyllnaden tillämpad korrigerar
    ner den om den skulle knappa in marginalen.
    Returnerar (scale, row_fill_mm) - row_fill alltid 0.0 för icke-opening."""
    target_h = panel_h_mm - _AUTOFIT_SAFETY_MM
    h1 = _measure_panel_h_mm(kind, d, 1.0, panel_w_mm, logo_src)
    if h1 <= target_h:
        scale, h_final = 1.0, h1
    else:
        lo, hi = 0.6, 1.0
        scale, h_final = lo, None
        for _ in range(7):  # upplösning ~0.4/128 ≈ 0.003
            mid = (lo + hi) / 2
            h = _measure_panel_h_mm(kind, d, mid, panel_w_mm, logo_src)
            if h <= target_h:
                scale, h_final = mid, h
                lo = mid
            else:
                hi = mid
        if h_final is None:
            # Även golvskalan 0.6 svämmar över - extremfall utanför scope,
            # acceptera golvet ändå (bättre än att krascha).
            scale = lo
            h_final = _measure_panel_h_mm(kind, d, scale, panel_w_mm, logo_src)
        scale = int(scale * 1000) / 1000  # avrunda nedåt - behåll säker marginal

    if kind != "opening":
        return scale, 0.0

    n_rows = len(d.get("oppningsbud") or []) or 1
    slack = target_h - h_final
    if slack <= 2.0:
        return scale, 0.0
    row_fill = slack / (2 * n_rows)
    # Verifiera: mät om med utfyllnaden pålagd och krymp proportionellt om
    # den (pga avrundningar/kantfall) ändå skulle svämma över.
    h_check = _measure_panel_h_mm(kind, d, scale, panel_w_mm, logo_src, row_fill)
    overflow = h_check - target_h
    if overflow > 0.05:
        total_added = max(0.0, row_fill * 2 * n_rows - overflow)
        row_fill = total_added / (2 * n_rows)
    return scale, round(row_fill, 3)


def _server_autofit(d: dict, panel_w_mm: float, panel_h_mm: float,
                     logo_src: str | None) -> tuple[dict, float]:
    """Per-panel-skalor för PDF/exakt-PDF. Manuellt läge (display.font_mode
    == 'manual'): display.font_scale för alla paneler, ingen mätning/
    utfyllnad (oförändrat beteende). Annars: server-sidig shrink-to-fit
    (Fas 1) + utfyllnad av öppningsbudstabellen (Fas 2)."""
    disp = d.get("display", {}) or {}
    if disp.get("font_mode", "auto") == "manual":
        try:
            manual = float(disp.get("font_scale", 1.0))
        except (TypeError, ValueError):
            manual = 1.0
        return {name: manual for name in _PANEL_NAMES}, 0.0

    scales = {}
    opening_row_fill = 0.0
    for name in _PANEL_NAMES:
        scale, row_fill = _autofit_panel(name, d, panel_w_mm, panel_h_mm, logo_src)
        scales[name] = scale
        if name == "opening":
            opening_row_fill = row_fill
    return scales, opening_row_fill


_OPPOSITE = {"left": "right", "right": "left", "top": "bottom", "bottom": "top"}
_MIRROR_LR = {"left": "right", "right": "left", "top": "top", "bottom": "bottom"}


def _opposite(edge: str) -> str:
    """Motsatt kant: left<->right, top<->bottom."""
    return _OPPOSITE[edge]


def _mirror_lr(edge: str) -> str:
    """Spegling vid duplex-vändning på långsidan: left<->right byts,
    top/bottom lämnas orört."""
    return _MIRROR_LR[edge]


# Kort 1 = omslag (fram) + öppningsbud (bak). Kort 2 = försvar (fram) +
# utspel/markeringar (bak). Trim gäller kort 1 eller kort 2 (styrs av
# imp["trim_card"], default 1: omslag + öppningsbud).
# En A4 (stående, 2x2) rymmer TVÅ exemplar: en rad per exemplar, kort 1 i
# vänsterkolumnen, kort 2 i högerkolumnen. Baksidan speglas efter duplex-läge.
def _build_slots(imp: dict) -> tuple[list, list]:
    trim = imp["trim_first_mm"] if imp.get("trim_first_mm") else 0
    edge = imp.get("binding_edge", "left")
    trim_card = imp.get("trim_card", 1)

    def _trim_for(kind: str) -> float:
        if trim_card == 2:
            return trim if kind in ("defense", "leads") else 0
        return trim if kind in ("cover", "opening") else 0

    # Gutter (bindningsmarginal) ligger på bindningskanten, trim på den
    # motsatta (öppnings-)kanten - på FRAMSIDAN direkt enligt valet.
    front_gutter = edge
    front_trim_side = _opposite(edge)
    # Framsida, radvis: [kort1=omslag, kort2=försvar] x 2 exemplar.
    front = [
        {"kind": "cover", "trim": _trim_for("cover"), "rot": False,
         "gutter": front_gutter, "trim_side": front_trim_side},
        {"kind": "defense", "trim": _trim_for("defense"), "rot": False,
         "gutter": front_gutter, "trim_side": front_trim_side},
        {"kind": "cover", "trim": _trim_for("cover"), "rot": False,
         "gutter": front_gutter, "trim_side": front_trim_side},
        {"kind": "defense", "trim": _trim_for("defense"), "rot": False,
         "gutter": front_gutter, "trim_side": front_trim_side},
    ]
    # Baksidorna som ska ligga bakom: kort1->öppningsbud, kort2->utspel.
    if imp.get("back_swap", True):
        # Långsidesvändning speglar vänster/höger: byt kolumn inom varje rad.
        base = ["leads", "opening", "leads", "opening"]
    else:
        base = ["opening", "leads", "opening", "leads"]
    rot = bool(imp.get("back_rotate", False))
    # Vid default duplex (long-edge, back_rotate=False) speglas baksidan i
    # vänster/höger (topp/botten bevaras), så samma fysiska kant motsvaras av
    # mirror_lr(edge) i back-slotens koordinatsystem.
    # Känd begränsning: om back_rotate (kortsidesvändning) används roteras
    # panelen 180° via CSS (.slot.rot180 .panel), vilket speglar layouten
    # ytterligare ett steg - gutter-/trim-sidan nedan stämmer då eventuellt
    # inte längre mot den fysiska bindningskanten och kan behöva justeras
    # separat. Utanför denna task.
    back_gutter = _mirror_lr(edge)
    back_trim_side = _mirror_lr(_opposite(edge))
    back = [{"kind": k, "trim": _trim_for(k), "rot": rot,
             "gutter": back_gutter, "trim_side": back_trim_side} for k in base]
    if rot:
        # Kortsidesvändning: hela baksidan roteras, vänd ordningen.
        back = list(reversed(back))
    return front, back


def render_sheet_html(d: dict, imposition: dict | None = None) -> str:
    imp = {"back_swap": True, "back_rotate": False, "trim_first_mm": 4,
           "trim_card": 1, "cut_marks": True, "center_lines": True,
           "binding_margin_mm": 0, "binding_edge": "left", "page_margin_mm": 5}
    if imposition:
        imp.update(imposition)
    front, back = _build_slots(imp)
    # Sidmarginalen styr paneldimensionerna direkt: vid margin=0 blir varje
    # panel äkta A6 (105x148.5mm) och 2x2 fyller hela A4 marginalfritt.
    margin = imp["page_margin_mm"]
    content_w = round(210 - 2 * margin, 3)
    content_h = round(297 - 2 * margin, 3)
    panel_w = round(content_w / 2, 3)
    panel_h = round(content_h / 2, 3)
    logo_src = _resolve_logo(d)
    # Server-autofit (TASK-327, alt a): körs bara här (PDF + exakt-PDF via
    # render_pdf_page_pngs, båda går genom render_sheet_html), INTE i
    # render_preview_html - live-previewen fortsätter använda klientens
    # snabba estimat (app.js).
    # center_lines (default på) ritar en --cut-w (0.12mm, print.css) bred
    # skärlinje-border på EN sida av varje panel (bredd- och höjdledd), vilket
    # äter en aning av panelens innehållsyta jämfört med den fristående
    # mätningen (som inte har den bordern). Utan denna justering upptäcktes
    # empiriskt att extremt långa textrader kunde radbryta en rad extra i
    # produktion jämfört med mätningen - synligt först vid stress-fall med
    # mycket text. Dra bort den från mätdimensionerna så mätningen matchar
    # produktionens faktiska tillgängliga yta.
    cut_w_mm = 0.12 if imp.get("center_lines") else 0.0
    fit_w = panel_w - cut_w_mm
    fit_h = panel_h - cut_w_mm
    panel_scales, opening_row_fill = _server_autofit(d, fit_w, fit_h, logo_src)
    tmpl = _env.get_template("sheet.html")
    return tmpl.render(d=d, imp=imp, front_slots=front, back_slots=back,
                       logo_src=logo_src, print_css=_print_css(),
                       page_margin_mm=margin, content_w=content_w, content_h=content_h,
                       panel_w=panel_w, panel_h=panel_h, panel_scales=panel_scales,
                       opening_row_fill=opening_row_fill)


def render_preview_html(d: dict) -> str:
    """Fristående HTML som visar alla fyra paneler (för webb-iframe)."""
    tmpl = _env.get_template("preview.html")
    return tmpl.render(d=d, logo_src=_resolve_logo(d), print_css=_print_css(),
                       panel_scales=_panel_scales(d))


def render_pdf(d: dict, imposition: dict | None = None) -> bytes:
    from weasyprint import HTML
    html = render_sheet_html(d, imposition)
    return HTML(string=html, base_url=str(config.BASE_DIR)).write_pdf()


def render_pdf_page_pngs(d: dict, imposition: dict | None = None,
                         dpi: int = 120) -> list[bytes]:
    """Rendera PDF:en och rastrera varje sida till PNG (via pdftoppm) så UI:t
    kan visa exakt vad som skrivs ut. WeasyPrint 69 saknar egen PNG-utmatning."""
    import os
    import subprocess
    import tempfile
    pdf = render_pdf(d, imposition)
    with tempfile.TemporaryDirectory() as tmp:
        pdf_path = os.path.join(tmp, "sheet.pdf")
        with open(pdf_path, "wb") as f:
            f.write(pdf)
        subprocess.run(
            ["pdftoppm", "-png", "-r", str(dpi), pdf_path, os.path.join(tmp, "page")],
            check=True, capture_output=True,
        )
        pages = sorted(p for p in os.listdir(tmp)
                       if p.startswith("page") and p.endswith(".png"))
        return [open(os.path.join(tmp, p), "rb").read() for p in pages]
