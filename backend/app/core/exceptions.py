from fastapi import Request
from fastapi.responses import JSONResponse


class RAGLabError(Exception):
    def __init__(self, message: str, status_code: int = 400, detail: dict | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.detail = detail or {}


async def raglab_exception_handler(_: Request, exc: RAGLabError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.message, "detail": exc.detail},
    )

