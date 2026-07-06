from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from saas.core.config import get_settings
from saas.db.postgres import SessionLocal
from saas.routers import auth, jobs, legacy, storage, system, users
from saas.services.plans import ensure_default_plans


def create_app() -> FastAPI:
    settings = get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        try:
            db = SessionLocal()
            ensure_default_plans(db)
        except Exception:
            # Migrations may not have run yet. Registration will fail clearly until DB is ready.
            pass
        finally:
            try:
                db.close()
            except Exception:
                pass
        yield

    app = FastAPI(title=settings.app_name, lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    if settings.static_dir.is_dir():
        app.mount("/static", StaticFiles(directory=settings.static_dir), name="static")
    if settings.assets_dir.is_dir():
        app.mount("/assets", StaticFiles(directory=settings.assets_dir), name="assets")

    app.include_router(auth.router)
    app.include_router(users.router)
    app.include_router(jobs.router)
    app.include_router(system.router)
    app.include_router(storage.router)
    app.include_router(legacy.router)

    def static_file(name: str, media_type: str) -> FileResponse:
        path = settings.static_dir / name
        if not path.is_file():
            raise HTTPException(status_code=404, detail=f"{name} not found")
        return FileResponse(path, media_type=media_type)

    @app.get("/")
    def index():
        return static_file("index.html", "text/html")

    @app.get("/health")
    def health():
        return {"ok": True}

    @app.get("/manifest.webmanifest", include_in_schema=False)
    def manifest():
        return static_file("manifest.webmanifest", "application/manifest+json")

    @app.get("/sw.js", include_in_schema=False)
    def service_worker():
        return static_file("sw.js", "application/javascript")

    @app.get("/favicon.ico", include_in_schema=False)
    def favicon():
        return static_file("pwa-192.png", "image/png")

    @app.get("/{full_path:path}", include_in_schema=False)
    def spa_fallback(full_path: str):
        if full_path.startswith(("api/", "static/", "assets/")):
            raise HTTPException(status_code=404, detail="Not found")
        return static_file("index.html", "text/html")

    return app


app = create_app()
