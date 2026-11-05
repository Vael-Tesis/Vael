"""Punto de entrada de la aplicación FastAPI de VAEL."""
import logging
import time
from collections.abc import AsyncGenerator, Awaitable, Callable
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.logs import configurar_logging
from app.routers import areas, auth, candidatos, entrevista, evaluaciones, metricas, plantillas, publico, tags, vacantes


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Ciclo de vida de la aplicación — punto de extensión para inicializar y liberar recursos."""
    yield


configurar_logging()
logger = logging.getLogger("vael.http")

# DEV-C-07: la documentación interactiva solo existe con DEBUG=true; en producción
# DEBUG=false la deshabilita (doc 09, checklist de producción).
app = FastAPI(
    title="VAEL",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)



@app.middleware("http")
async def registrar_peticion(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    """Registra cada petición en JSON con su ruta, estado, duración y tenant (DEV-C-08)."""
    inicio = time.perf_counter()
    status_code = 500
    try:
        respuesta = await call_next(request)
        status_code = respuesta.status_code
        return respuesta
    finally:
        ruta = getattr(request.scope.get("route"), "path", request.url.path)
        logger.info(
            "%s %s %s",
            request.method,
            ruta,
            status_code,
            extra={
                "operation": f"{request.method} {ruta}",
                "method": request.method,
                "path": ruta,
                "status_code": status_code,
                "duration_ms": round((time.perf_counter() - inicio) * 1000, 1),
                "tenant_id": getattr(request.state, "tenant_id", None),
            },
        )


app.include_router(auth.router)
app.include_router(areas.router)
app.include_router(vacantes.router)
app.include_router(candidatos.router)
app.include_router(evaluaciones.router)
app.include_router(entrevista.router)
app.include_router(metricas.router)
app.include_router(plantillas.router)
app.include_router(tags.router)
app.include_router(publico.router)


@app.get("/health", tags=["health"])
async def health() -> dict[str, str]:
    """Endpoint de salud — verifica que el servicio está arriba."""
    return {"status": "ok"}
