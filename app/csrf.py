"""CSRF-skydd via double-submit cookie (stateless, ingen serversession).

Alla svar sätter en läsbar cookie `csrftoken` om den saknas. Muterande
metoder mot `/api/declarations`-vägar kräver att headern `X-CSRF-Token`
matchar cookien - annars avvisas requesten. Läs-/beräkna-endpoints
(preview, pdf, pdf-preview) muterar ingen data och undantas.
"""
import secrets

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

COOKIE_NAME = "csrftoken"
HEADER_NAME = "x-csrf-token"
UNSAFE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
PROTECTED_PREFIX = "/api/declarations"


class CSRFMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        incoming_token = request.cookies.get(COOKIE_NAME)

        needs_check = (
            request.method in UNSAFE_METHODS
            and request.url.path.startswith(PROTECTED_PREFIX)
        )
        if needs_check:
            header_token = request.headers.get(HEADER_NAME)
            if not incoming_token or not header_token or not secrets.compare_digest(
                incoming_token, header_token
            ):
                return JSONResponse(
                    status_code=403,
                    content={"detail": "Ogiltig eller saknad CSRF-token"},
                )

        response = await call_next(request)

        if not incoming_token:
            response.set_cookie(
                COOKIE_NAME,
                secrets.token_urlsafe(32),
                httponly=False,  # JS måste kunna läsa den för att skicka som header
                samesite="lax",
                secure=False,  # sätt True bakom TLS
                path="/",
            )

        return response
