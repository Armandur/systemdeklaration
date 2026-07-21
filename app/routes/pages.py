"""HTML-sidor."""
import json

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from markupsafe import Markup

from .. import config

router = APIRouter()
templates = Jinja2Templates(directory=str(config.BASE_DIR / "templates"))
templates.env.filters["bud"] = lambda t: Markup(config.render_bud(t))


@router.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "empty": json.dumps(config.empty_declaration(), ensure_ascii=False),
            "opening_rows": config.OPENING_ROWS,
            "forsvarsbud_fields": config.FORSVARSBUD_FIELDS,
        },
    )
