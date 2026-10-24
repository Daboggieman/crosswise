from fastapi import FastAPI, Request
import logging as lg
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from app.services.game_service import GameValidationError, GameNotFoundError, GameConflictError


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(RequestValidationError)
    async def handle_request_validation_error(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={
                "code": "validation_error",
                "message":"request validation failed",
                "details": exc.errors(),
            }
        )

    @app.exception_handler(GameValidationError)
    async def handle_game_validation_error(
        request: Request, exc: GameValidationError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={
                "code": "validation_error",
                "message": str(exc),
                "details": None,
                },
            )
    
    @app.exception_handler(GameNotFoundError)
    async def handle_game_not_found_error(
        request: Request, exc: GameNotFoundError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=404,
            content={
                "code": "game_not_found",
                "message": "Game not found",      
            }
        )

    @app.exception_handler(GameConflictError)
    async def handle_game_conflict_error(
        request: Request, exc: GameConflictError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=409,
            content={
                "code":"conflict",
                "message": str(exc),
                "details": None
            }
        )
    @app.exception_handler(Exception)
    async def handle_unexpected_error(
        request: Request, exc: Exception
    ) -> JSONResponse:
        lg.error(
            "Unhandled exception on %s %s",
            request.method,
            request.url.path,
            exc_info=exc,
        )
        return JSONResponse(
            status_code=500,
            content={
                "code": "internal_error",
                "message": "Internal server error.",
                "details": None,
            },
        )