from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.core.config import settings
from app.api.routes import scripts, executions, auth, health, websocket, admin, secrets
from app.db.session import engine
from app.db.base import Base


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    Base.metadata.create_all(bind=engine)
    yield
    # Shutdown
    pass


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router, prefix=settings.API_V1_STR, tags=["health"])
app.include_router(auth.router, prefix=f"{settings.API_V1_STR}/auth", tags=["auth"])
app.include_router(scripts.router, prefix=f"{settings.API_V1_STR}/scripts", tags=["scripts"])
app.include_router(executions.router, prefix=f"{settings.API_V1_STR}/executions", tags=["executions"])
app.include_router(admin.router, prefix=f"{settings.API_V1_STR}/admin", tags=["admin"])
app.include_router(secrets.router, prefix=f"{settings.API_V1_STR}/secrets", tags=["secrets"])
app.include_router(websocket.router, tags=["websocket"])

@app.get("/")
async def root():
    return {
        "message": "OpsCraft API",
        "version": settings.VERSION,
        "docs": f"{settings.API_V1_STR}/docs"
    }