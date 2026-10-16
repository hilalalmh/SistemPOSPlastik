import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.database import engine
from app.core.exceptions import AppError

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger("pos")

app = FastAPI(
    title="Sistem POS Toko Plastik",
    version="1.0.0",
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": exc.code, "message": exc.message, "details": exc.details}},
    )


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError):
    details = [{"loc": err.get("loc"), "message": err.get("msg")} for err in exc.errors()]
    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Data yang dikirim tidak valid.",
                "details": details,
            }
        },
    )


@app.get("/api/health", tags=["health"])
def health():
    return {"status": "ok", "version": app.version}


@app.get("/api/health/ready", tags=["health"])
def health_ready():
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return {"status": "ready", "database": "ok"}
    except Exception:  # noqa: BLE001
        return JSONResponse(status_code=503, content={"status": "not_ready", "database": "error"})


app.include_router(api_router, prefix="/api/v1")
