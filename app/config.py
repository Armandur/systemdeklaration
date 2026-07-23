"""Konstanter, det fasta SBF-skelettet och hjälpfunktioner för färgglyfer."""
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
ROOT_DIR = BASE_DIR.parent
DATA_DIR = ROOT_DIR / "data"
DB_PATH = DATA_DIR / "systemdeklaration.db"

# Färgsymboler. Varje färg får en egen klass (suit-c/d/h/s); CSS avgör om
# tvåfärgs- eller fyrfärgspalett gäller (styrt av .fourcolor på behållaren).
SUIT_GLYPH = {"C": "♣", "D": "♦", "H": "♥", "S": "♠"}
SUIT_CLASS = {"♣": "suit-c", "♦": "suit-d", "♥": "suit-h", "♠": "suit-s"}
RED_SUITS = {"♦", "♥"}
BLACK_SUITS = {"♣", "♠"}

# Fast skelett: öppningsbudens etiketter (bud-token -> visning). Endast värden
# i cellerna varierar per par, inte vilka rader som finns.
OPENING_ROWS = ["1C", "1D", "1H", "1S", "1NT", "2C", "2D", "2H", "2S", "2NT",
                "3CDHS", "3NT", "4CDHS"]

FORSVARSBUD_FIELDS = [
    ("1NT", "1NT"),
    ("2NT", "2NT"),
    ("enkelt_overbud", "Enkelt överbud"),
    ("dubbelt_overbud", "Dubbelt överbud"),
    ("hoppinkliv", "Hoppinkliv"),
    ("mot_1nt", "Mot 1NT"),
    ("mot_stark_1c", "Mot stark 1♣"),
    ("mot_multi_2d", "Mot multi 2♦"),
    ("mot_svaga_2", "Mot svaga 2♦♥♠"),
    ("mot_3cd", "Mot 3♣♦"),
    ("mot_3hs", "Mot 3♥♠"),
]


DEFAULT_KORT = {"1C": "3", "1D": "3", "1H": "5", "1S": "5", "2D": "6",
                "2H": "6", "2S": "6", "3CDHS": "7"}


def empty_declaration() -> dict:
    """Tomt fast skelett - alla rader finns, värdena är blanka."""
    return {
        "meta": {"player1_name": "", "player1_number": "", "player2_name": "",
                 "player2_number": "", "grundsystem": "", "antal_prickar": "",
                 "special_forsvar": ""},
        "oppningsbud": [
            {"bud": b, "prickar": "", "ant_kort": DEFAULT_KORT.get(b, ""),
             "oppning": "", "svar": "", "merge_up": False} for b in OPENING_ROWS
        ],
        "slamkonventioner": "",
        "ovriga_konventioner": "",
        "forsvarsbud": {k: "" for k, _ in FORSVARSBUD_FIELDS} | {"ovriga": ""},
        "utspel": {"mot_farg": "", "mot_nt": ""},
        "vandor": {"genom_spelforaren": "", "i_partnerns_farg": ""},
        "markeringar": {"styrka": "", "langd": "", "ovriga": ""},
        "display": {"four_color": False, "logo": "sbf", "logo_data": "",
                    "font_mode": "auto", "font_scale": 1.0, "font_scales": {}},
    }


def render_suits(text: str) -> str:
    """Wrappa färgsymboler i span med per-färg-klass. Escapar övrig text.

    Stödjer en fejk-markdown för enkel formatering:
    - `**text**` -> `<b>text</b>` (fet, dubbel-asterisk växlar läge)
    - `*text*` -> `<i>text</i>` (kursiv, enkel asterisk växlar läge)
    - `_text_` -> `<u>text</u>` (understruken, `_` växlar läge)

    En ensam `*` utan matchande partner längre fram i strängen (t.ex.
    fotnotsmarkören i "... samt*") tolkas INTE som kursiv-start utan skrivs
    ut literalt - annars skulle resten av texten bli oavsiktligt kursiv.
    Oavslutade taggar vid strängslut stängs automatiskt.

    Backslash escapar nästa tecken: `\\*` -> literal `*`, `\\_` -> literal `_`,
    `\\\\` -> literal `\\` (och `\\` följt av en färgsymbol ger en ofärgad literal
    glyf). Så man kan skriva bokstavliga markup-tecken."""
    from markupsafe import escape
    out = []
    underline = False
    italic = False
    bold = False
    s = text or ""
    n = len(s)
    i = 0
    while i < n:
        ch = s[i]
        if ch == "\\" and i + 1 < n:
            out.append(str(escape(s[i + 1])))
            i += 2
            continue
        if ch == "*" and i + 1 < n and s[i + 1] == "*":
            out.append("</b>" if bold else "<b>")
            bold = not bold
            i += 2
            continue
        if ch == "*":
            if italic:
                out.append("</i>")
                italic = False
            elif "*" in s[i + 1:]:
                out.append("<i>")
                italic = True
            else:
                out.append(str(escape(ch)))
            i += 1
            continue
        if ch == "_":
            out.append("</u>" if underline else "<u>")
            underline = not underline
            i += 1
            continue
        cls = SUIT_CLASS.get(ch)
        if cls:
            out.append(f'<span class="{cls}">{ch}︎</span>')
        elif ch == "\n":
            out.append("<br>")
        else:
            out.append(str(escape(ch)))
        i += 1
    if underline:
        out.append("</u>")
    if italic:
        out.append("</i>")
    if bold:
        out.append("</b>")
    return "".join(out)


def render_stacked(text: str) -> str:
    """En bokstav per rad (upprättstående, staplad) - för smala kolumnrubriker.
    Mellanslag blir en tom rad (ordgap). Robustare än roterad text i WeasyPrint."""
    from markupsafe import escape
    chars = ["" if c == " " else str(escape(c)) for c in (text or "")]
    return "<br>".join(chars)


def render_bud(token: str) -> str:
    """Rendera ett bud-token (t.ex. '1C', '3CDHS') med färgade symboler."""
    i = 0
    while i < len(token) and (token[i].isdigit()):
        i += 1
    level, suits = token[:i], token[i:]
    if suits == "NT":
        return f'{level}NT'
    parts = [f'{level}']
    for s in suits:
        glyph = SUIT_GLYPH.get(s, s)
        cls = SUIT_CLASS.get(glyph, "")
        parts.append(f'<span class="{cls}">{glyph}︎</span>')
    return "".join(parts)


def opening_render(rows: list[dict]) -> list[dict]:
    """Annotera öppningsbudsraderna med rowspan-info för Öppningsbud/Svar
    (TASK-340). En START-rad (första raden i skelettet, alltid - ett
    merge_up på rad 0 ignoreras - eller en rad vars merge_up är falskt)
    får `_span` = 1 + antalet DIREKT följande rader med merge_up=True.
    Dessa följande rader markeras `_merged=True`: deras Öppningsbud/Svar-
    celler ska inte renderas alls (start-radens celler spänner ner till
    dem via rowspan). Bud/Prickar/Ant kort hålls separata per rad oavsett
    - bara de två sammanslagningsbara kolumnerna påverkas."""
    out = []
    n = len(rows)
    i = 0
    while i < n:
        span = 1
        j = i + 1
        while j < n and rows[j].get("merge_up"):
            span += 1
            j += 1
        out.append({**rows[i], "_span": span, "_merged": False})
        for k in range(i + 1, i + span):
            out.append({**rows[k], "_span": 1, "_merged": True})
        i += span
    return out
