"""JSON-API och rendering-endpoints."""
from fastapi import APIRouter, Body, HTTPException
from fastapi.responses import HTMLResponse, Response

from .. import database, render

router = APIRouter(prefix="/api")


@router.get("/declarations")
def list_declarations():
    return database.list_declarations()


@router.get("/declarations/{dec_id}")
def get_declaration(dec_id: int):
    d = database.get_declaration(dec_id)
    if not d:
        raise HTTPException(404, "Deklaration saknas")
    return d


@router.post("/declarations")
def create_declaration(body: dict = Body(...)):
    name = (body.get("name") or "Namnlös").strip()
    payload = body.get("payload") or {}
    dec_id = database.create_declaration(name, payload)
    return {"id": dec_id}


@router.put("/declarations/{dec_id}")
def update_declaration(dec_id: int, body: dict = Body(...)):
    if not database.get_declaration(dec_id):
        raise HTTPException(404, "Deklaration saknas")
    name = (body.get("name") or "Namnlös").strip()
    payload = body.get("payload") or {}
    database.update_declaration(dec_id, name, payload)
    return {"ok": True}


@router.delete("/declarations/{dec_id}")
def delete_declaration(dec_id: int):
    database.delete_declaration(dec_id)
    return {"ok": True}


@router.post("/preview", response_class=HTMLResponse)
def preview(body: dict = Body(...)):
    payload = body.get("payload") or {}
    return render.render_preview_html(payload)


@router.post("/pdf-preview", response_class=HTMLResponse)
def pdf_preview(body: dict = Body(...)):
    """Rastrerad, exakt bild av de faktiska utskriftssidorna."""
    import base64
    payload = body.get("payload") or {}
    imposition = body.get("imposition") or None
    payload2 = body.get("payload2") or None
    pages = render.render_pdf_page_pngs(payload, imposition, payload2)
    labels = ["Framsida", "Baksida"]
    imgs = "".join(
        f'<figure><img src="data:image/png;base64,{base64.b64encode(p).decode()}">'
        f'<figcaption>{labels[i] if i < len(labels) else "Sida %d" % (i+1)}</figcaption></figure>'
        for i, p in enumerate(pages)
    )
    return (
        "<!DOCTYPE html><html><head><meta charset='utf-8'><style>"
        "body{margin:0;background:#e9e9ef;padding:12px;font:12px system-ui,sans-serif}"
        ".g{display:flex;flex-wrap:wrap;gap:12px;justify-content:center}"
        "figure{margin:0;text-align:center}"
        "img{max-width:100%;box-shadow:0 1px 6px rgba(0,0,0,.3);background:#fff}"
        "figcaption{color:#555;margin-top:4px}"
        "</style></head><body><div class='g'>" + imgs + "</div></body></html>"
    )


@router.post("/pdf")
def pdf(body: dict = Body(...)):
    payload = body.get("payload") or {}
    imposition = body.get("imposition") or None
    payload2 = body.get("payload2") or None
    name = (body.get("name") or "systemdeklaration").strip() or "systemdeklaration"
    pdf_bytes = render.render_pdf(payload, imposition, payload2)
    safe = "".join(c for c in name if c.isalnum() or c in " -_").strip() or "systemdeklaration"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{safe}.pdf"'},
    )
