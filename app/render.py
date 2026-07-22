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
    tmpl = _env.get_template("sheet.html")
    return tmpl.render(d=d, imp=imp, front_slots=front, back_slots=back,
                       logo_src=_resolve_logo(d), print_css=_print_css(),
                       page_margin_mm=margin, content_w=content_w, content_h=content_h,
                       panel_w=panel_w, panel_h=panel_h, panel_scales=_panel_scales(d))


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
