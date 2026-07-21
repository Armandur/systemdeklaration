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
    return Markup(f'<span class="{cls}">{glyph}</span>')


_env.filters["suits"] = lambda t: Markup(config.render_suits(t))
_env.filters["bud"] = lambda t: Markup(config.render_bud(t))
_env.filters["bud_suit"] = _suit_only


@lru_cache(maxsize=1)
def _logo_data_uri() -> str:
    raw = (config.BASE_DIR / "static" / "sbf-logo.png").read_bytes()
    return "data:image/png;base64," + base64.b64encode(raw).decode()


@lru_cache(maxsize=1)
def _print_css() -> str:
    return (config.BASE_DIR / "static" / "print.css").read_text(encoding="utf-8")


# Kort 1 = omslag (fram) + öppningsbud (bak). Kort 2 = försvar (fram) +
# utspel/markeringar (bak). Trim gäller kort 1 (omslag + öppningsbud).
# En A4 (stående, 2x2) rymmer TVÅ exemplar: en rad per exemplar, kort 1 i
# vänsterkolumnen, kort 2 i högerkolumnen. Baksidan speglas efter duplex-läge.
def _build_slots(imp: dict) -> tuple[list, list]:
    trim = imp["trim_first_mm"] if imp.get("trim_first_mm") else 0
    # Framsida, radvis: [kort1=omslag, kort2=försvar] x 2 exemplar.
    front = [
        {"kind": "cover", "trim": trim, "rot": False},
        {"kind": "defense", "trim": 0, "rot": False},
        {"kind": "cover", "trim": trim, "rot": False},
        {"kind": "defense", "trim": 0, "rot": False},
    ]
    # Baksidorna som ska ligga bakom: kort1->öppningsbud, kort2->utspel.
    if imp.get("back_swap", True):
        # Långsidesvändning speglar vänster/höger: byt kolumn inom varje rad.
        base = ["leads", "opening", "leads", "opening"]
    else:
        base = ["opening", "leads", "opening", "leads"]
    rot = bool(imp.get("back_rotate", False))
    back = [{"kind": k, "trim": trim if k == "opening" else 0, "rot": rot}
            for k in base]
    if rot:
        # Kortsidesvändning: hela baksidan roteras, vänd ordningen.
        back = list(reversed(back))
    return front, back


def render_sheet_html(d: dict, imposition: dict | None = None) -> str:
    imp = {"back_swap": True, "back_rotate": False, "trim_first_mm": 4,
           "cut_marks": True, "center_lines": True}
    if imposition:
        imp.update(imposition)
    front, back = _build_slots(imp)
    tmpl = _env.get_template("sheet.html")
    return tmpl.render(d=d, imp=imp, front_slots=front, back_slots=back,
                       logo_src=_logo_data_uri(), print_css=_print_css())


def render_preview_html(d: dict) -> str:
    """Fristående HTML som visar alla fyra paneler (för webb-iframe)."""
    tmpl = _env.get_template("preview.html")
    return tmpl.render(d=d, logo_src=_logo_data_uri(), print_css=_print_css())


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
