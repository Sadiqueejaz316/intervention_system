from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.auth.router import router as auth_router
from app.core.config import settings
from app.core.database import SessionLocal
from app.core.errors import AppError
from app.domain.current import get_domain_adapter
from app.routers import assignments, domain, notifications, tickets, workers
from app.schemas.common import ErrorResponse, HealthResponse

app = FastAPI(
    title=settings.APP_NAME,
    version="0.1.0",
    description=(
        "Generic issue reporting and intervention system. "
        "Domain-specific behaviour lives behind the domain adapter."
    ),
    responses={422: {"model": ErrorResponse}},
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(AppError)
def handle_app_error(request: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


@app.exception_handler(RequestValidationError)
def handle_validation_error(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    """Flatten FastAPI's list of errors into the single-string contract."""
    messages = [
        f"{'.'.join(str(part) for part in error['loc'][1:])}: {error['msg']}".lstrip(": ")
        for error in exc.errors()
    ]

    return JSONResponse(status_code=422, content={"detail": "; ".join(messages)})


app.include_router(auth_router)
app.include_router(tickets.router)
app.include_router(assignments.router)
app.include_router(workers.router)
app.include_router(notifications.router)
app.include_router(domain.router)


@app.get("/health", response_model=HealthResponse, tags=["Health"])
def health_check() -> HealthResponse:
    database_status = "connected"

    try:
        with SessionLocal() as session:
            session.execute(text("SELECT 1"))
    except Exception:
        database_status = "unavailable"

    return HealthResponse(
        status="ok" if database_status == "connected" else "degraded",
        database=database_status,
        domain=get_domain_adapter().domain_name,
    )
