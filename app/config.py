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
             "oppning": "", "svar": ""} for b in OPENING_ROWS
        ],
        "slamkonventioner": "",
        "ovriga_konventioner": "",
        "forsvarsbud": {k: "" for k, _ in FORSVARSBUD_FIELDS} | {"ovriga": ""},
        "utspel": {"mot_farg": "", "mot_nt": ""},
        "vandor": {"genom_spelforaren": "", "i_partnerns_farg": ""},
        "markeringar": {"styrka": "", "langd": "", "ovriga": ""},
        "display": {"four_color": False},
    }


def render_suits(text: str) -> str:
    """Wrappa färgsymboler i span med per-färg-klass. Escapar övrig text."""
    from markupsafe import escape
    out = []
    for ch in text or "":
        cls = SUIT_CLASS.get(ch)
        if cls:
            out.append(f'<span class="{cls}">{ch}︎</span>')
        else:
            out.append(str(escape(ch)))
    return "".join(out).replace("\n", "<br>")


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
