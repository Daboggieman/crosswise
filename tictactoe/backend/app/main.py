import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.errors import install_error_handlers
from app.api.routes_games import router as games_router
from app.api.routes_pages import router as pages_router
from app.config import get_settings

logging.basicConfig(level=logging.INFO)


def create_app() -> FastAPI:
    app = FastAPI(title="Crosswise Tic Tac Toe")
    settings = get_settings()

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    install_error_handlers(app)
    app.include_router(games_router, prefix="/api/v1")
    app.mount(
        "/static",
        StaticFiles(directory=Path(settings.frontend_dir) / "static"),
        name="static",
    )
    app.include_router(pages_router)

    @app.get("/api/v1/health")
    async def health():
        return {"status": "ok"}

    return app


app = create_app()