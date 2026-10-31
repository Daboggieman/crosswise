from pathlib import Path
from fastapi import APIRouter, HTTPException
from app.config import get_settings
from fastapi.responses import FileResponse

router = APIRouter(tags=["pages"])

def _frontend_dir() -> Path:
    return Path(get_settings().frontend_dir)


@router.get("/play")
def play_page() -> FileResponse:
    play_file = _frontend_dir() / "play.html"

    if not play_file.is_file():
        raise HTTPException(
            status_code=404,
            detail="frontend not built",
        )

    return FileResponse(
        play_file,
        media_type="text/html",
    )