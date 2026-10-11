from fastapi import FastAPI, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from mahara_data.schemas.common import ApiError

# Machine-readable labels. Callers branch on these, never on the message.
_CODES = {
    400: "bad_request",
    401: "unauthenticated",
    403: "forbidden",
    404: "not_found",
    409: "conflict",
    422: "validation_error",
    503: "unavailable",
}


def _as_api_error(status_code: int, message: str, details: dict | None = None) -> JSONResponse:
    body = ApiError(code=_CODES.get(status_code, "error"), message=message, details=details)
    return JSONResponse(status_code=status_code, content=jsonable_encoder(body))


def install_error_handlers(app: FastAPI) -> None:
    """Every failure leaves WP5 in WP1's ApiError shape, so callers parse one format."""

    @app.exception_handler(StarletteHTTPException)
    async def http_error(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        return _as_api_error(exc.status_code, str(exc.detail))

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
        return _as_api_error(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "The payload does not match the contract",
            {"errors": jsonable_encoder(exc.errors())},
        )