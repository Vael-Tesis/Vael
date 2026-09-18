"""Punto de entrada de la aplicación FastAPI de VAEL."""
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.routers import auth, candidatos, entrevista, evaluaciones, publico, vacantes


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Ciclo de vida de la aplicación — punto de extensión para inicializar y liberar recursos."""
    yield


app = FastAPI(
    title="VAEL",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(vacantes.router)
app.include_router(candidatos.router)
app.include_router(evaluaciones.router)
app.include_router(entrevista.router)
app.include_router(publico.router)


@app.get("/health", tags=["health"])
async def health() -> dict[str, str]:
    """Endpoint de salud — verifica que el servicio está arriba."""
    return {"status": "ok"}
