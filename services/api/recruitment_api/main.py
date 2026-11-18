import logging
from typing import Literal
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from starlette.exceptions import HTTPException as StarletteHTTPException

from .admin import router as admin_router
from .catalogue import router as catalogue_router
from .database import DatabaseConfigurationError, engine
from .ingestion.routes import router as ingestion_router

logger = logging.getLogger("uvicorn.error")


class HealthResponse(BaseModel):
    status: Literal["ok"]


app = FastAPI(title="Recruitment Waala API", version="0.0.0", docs_url=None, redoc_url=None)


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok")


@app.get("/ready")
def readiness():
    try:
        with engine().connect() as connection:
            connection.execute(text("SELECT 1 FROM publication LIMIT 0"))
    except (SQLAlchemyError, RuntimeError):
        raise HTTPException(503, "Catalogue database unavailable.") from None
    return {"status": "ready"}


@app.middleware("http")
async def request_log(request: Request, call_next):
    request_id = uuid4().hex
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    route = getattr(request.scope.get("route"), "path", "unmatched")
    logger.info("%s %s %s %s", request_id, request.method, route, response.status_code)
    return response


def problem(request: Request, status: int, detail: str, headers=None):
    return JSONResponse(
        {"status": status, "detail": detail, "request_id": request.state.request_id},
        status_code=status,
        headers=headers,
    )


@app.exception_handler(RequestValidationError)
async def validation_error(request: Request, exc: RequestValidationError):
    return problem(request, 422, "Invalid request parameters or body.")


@app.exception_handler(StarletteHTTPException)
async def http_error(request: Request, exc: StarletteHTTPException):
    return problem(request, exc.status_code, str(exc.detail), exc.headers)


@app.exception_handler(DatabaseConfigurationError)
@app.exception_handler(SQLAlchemyError)
async def database_error(request: Request, exc: SQLAlchemyError | DatabaseConfigurationError):
    return problem(request, 503, "Catalogue database unavailable.")


app.include_router(catalogue_router)
app.include_router(admin_router)

app.include_router(ingestion_router)
