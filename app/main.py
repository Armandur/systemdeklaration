"""FastAPI-app: systemdeklarationsgenerator för bridge."""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from . import config, database
from .csrf import CSRFMiddleware
from .routes import api, pages


@asynccontextmanager
async def lifespan(app: FastAPI):
    database.init_db()
    yield


app = FastAPI(title="Systemdeklaration", lifespan=lifespan)
app.add_middleware(CSRFMiddleware)
app.mount("/static", StaticFiles(directory=str(config.BASE_DIR / "static")), name="static")
app.include_router(pages.router)
app.include_router(api.router)
