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
    cls = "suit-red" if glyph in config.RED_SUITS else "suit-black"
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


# Kortordning: kort 1 = omslag (fram) + öppningsbud (bak),
# kort 2 = försvar (fram) + utspel/markeringar (bak).
def render_sheet_html(d: dict, imposition: dict | None = None) -> str:
    imp = {"back_swap": True, "back_rotate": False, "trim_first_mm": 4,
           "cut_marks": True}
    if imposition:
        imp.update(imposition)
    tmpl = _env.get_template("sheet.html")
    return tmpl.render(d=d, imp=imp, logo_src=_logo_data_uri(),
                       print_css=_print_css())


def render_preview_html(d: dict) -> str:
    """Fristående HTML som visar alla fyra paneler (för webb-iframe)."""
    tmpl = _env.get_template("preview.html")
    return tmpl.render(d=d, logo_src=_logo_data_uri(), print_css=_print_css())


def render_pdf(d: dict, imposition: dict | None = None) -> bytes:
    from weasyprint import HTML
    html = render_sheet_html(d, imposition)
    return HTML(string=html, base_url=str(config.BASE_DIR)).write_pdf()
