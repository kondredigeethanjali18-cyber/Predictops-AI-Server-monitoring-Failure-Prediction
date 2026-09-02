from fastapi import FastAPI, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import logging

from Backend.routes.health import router as health_router
from Backend.routes.prediction import router as prediction_router
from Backend.routes.dashboard import router as dashboard_router
from Backend.routes.metrics import router as metrics_router
from Backend.routes.dashboard_api import router as dashboard_api_router
from Backend.routes.insights import router as insights_router
from Backend.routes.auth import router as auth_router, get_current_user_page, get_current_user_api

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="PredictOps AI Server Monitoring"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers with exception handling
try:
    app.include_router(dashboard_api_router)
except Exception as e:
    logger.error(f"Failed to include dashboard_api_router: {e}")

try:
    app.include_router(auth_router)
except Exception as e:
    logger.error(f"Failed to include auth_router: {e}")


class NoConditionalStaticFiles(StaticFiles):
    def file_response(
        self,
        full_path,
        stat_result,
        scope,
        status_code=200,
    ):
        try:
            response = FileResponse(full_path, status_code=status_code, stat_result=stat_result)
            return response
        except Exception as e:
            logger.error(f"Error serving static file {full_path}: {e}")
            return FileResponse("", status_code=404)

try:
    app.include_router(insights_router, dependencies=[Depends(get_current_user_api)])
except Exception as e:
    logger.error(f"Failed to include insights_router: {e}")

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

try:
    app.mount(
        "/static",
        NoConditionalStaticFiles(directory=str(BASE_DIR / "static")),
        name="static"
    )
except Exception as e:
    logger.error(f"Failed to mount static files: {e}")

@app.middleware("http")
async def add_no_cache_headers(request: Request, call_next):
    try:
        response = await call_next(request)
        # Prevent browser back-button bfcache from serving protected pages after logout
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response
    except Exception as e:
        logger.error(f"Middleware error for {request.url.path}: {e}")
        return JSONResponse(status_code=500, content={"detail": "Internal server error"})

try:
    templates = Jinja2Templates(
        directory=str(BASE_DIR / "templates")
    )
except Exception as e:
    logger.error(f"Failed to initialize Jinja2Templates: {e}")
    templates = None

def asset_version(path: str) -> str:
    try:
        asset_path = BASE_DIR / "static" / path
        return str(int(asset_path.stat().st_mtime))
    except OSError as e:
        logger.warning(f"Asset version error for {path}: {e}")
        return "1"
    except Exception as e:
        logger.error(f"Unexpected error in asset_version: {e}")
        return "1"

if templates:
    templates.env.globals["asset_version"] = asset_version

# Include remaining routers with exception handling
try:
    app.include_router(health_router)
except Exception as e:
    logger.error(f"Failed to include health_router: {e}")

try:
    app.include_router(prediction_router, dependencies=[Depends(get_current_user_api)])
except Exception as e:
    logger.error(f"Failed to include prediction_router: {e}")

try:
    app.include_router(dashboard_router, dependencies=[Depends(get_current_user_api)])
except Exception as e:
    logger.error(f"Failed to include dashboard_router: {e}")

try:
    app.include_router(metrics_router, dependencies=[Depends(get_current_user_api)])
except Exception as e:
    logger.error(f"Failed to include metrics_router: {e}")

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception at {request.url.path}: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "An unexpected error occurred"}
    )

async def auto_telemetry_generator():
    """Generates continuous live telemetry for all 22 servers in the background."""
    import asyncio
    import random
    from datetime import datetime, timezone
    from data.servers import SERVERS
    from Backend.database.mongodb import get_metrics_collection
    from Backend.services.prediction_service import predict_metric

    logger.info(f"Auto Telemetry Generator active for fleet of {len(SERVERS)} servers.")

    while True:
        try:
            col = get_metrics_collection()
            # Select 3-4 servers to be active anomaly incidents in this 20s cycle
            incident_servers = {"SRV003", "SRV007", "SRV015", "SRV022"}

            for server in SERVERS:
                sname = server["server_name"]

                if sname in incident_servers:
                    # Active Anomaly Telemetry
                    cpu_usage = round(random.uniform(91.5, 98.4), 1)
                    memory_percent = round(random.uniform(86.0, 96.5), 1)
                    disk_usage = round(random.uniform(84.0, 93.5), 1)
                    latency = round(random.uniform(360.0, 680.0), 1)
                    active_procs = random.randint(344, 356)
                else:
                    # Healthy Baseline Telemetry
                    cpu_usage = round(random.uniform(22.0, 64.0), 1)
                    memory_percent = round(random.uniform(28.0, 68.0), 1)
                    disk_usage = round(random.uniform(25.0, 65.0), 1)
                    latency = round(random.uniform(35.0, 85.0), 1)
                    active_procs = random.randint(335, 345)

                metrics = {
                    "server_id": server["server_id"],
                    "server_name": sname,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "cpu_usage_percent": cpu_usage,
                    "memory_usage_percent": memory_percent,
                    "memory_used_mb": round((memory_percent / 100.0) * 16000.0, 2),
                    "disk_usage_percent": disk_usage,
                    "network_sent_mb": round(random.uniform(70, 160), 2),
                    "network_received_mb": round(random.uniform(70, 160), 2),
                    "request_latency_ms": latency,
                    "active_processes": active_procs
                }

                if col is not None:
                    try:
                        col.insert_one(dict(metrics))
                        predict_metric(metrics)
                    except Exception as ins_err:
                        logger.error(f"Auto telemetry insertion error: {ins_err}")

            await asyncio.sleep(8)
        except Exception as loop_err:
            logger.error(f"Auto telemetry loop error: {loop_err}")
            await asyncio.sleep(8)


@app.on_event("startup")
async def on_startup():
    import asyncio
    from Backend.routes.auth import clear_all_sessions
    try:
        clear_all_sessions()
        logger.info("Application started: All prior user sessions have been cleared. Fresh login required.")
    except Exception as e:
        logger.error(f"Error resetting sessions on startup: {e}")

    # Launch real-time telemetry generator in background
    asyncio.create_task(auto_telemetry_generator())

@app.get("/")
def landing(request: Request):
    token = request.cookies.get("session_token")
    from Backend.routes.auth import get_session
    username = get_session(token) if token else None
    if not username:
        return RedirectResponse(url="/login", status_code=302)
    try:
        if not templates:
            return JSONResponse(status_code=500, content={"detail": "Templates not initialized"})
        return templates.TemplateResponse(
            request=request,
            name="landing.html",
            context={"user": username}
        )
    except Exception as e:
        logger.error(f"Error rendering landing page: {e}")
        return JSONResponse(status_code=500, content={"detail": "Failed to render landing page"})

@app.get("/dashboard")
def dashboard(request: Request, user: str = Depends(get_current_user_page)):
    try:
        if not templates:
            return JSONResponse(status_code=500, content={"detail": "Templates not initialized"})
        return templates.TemplateResponse(
            request=request,
            name="dashboard.html",
            context={"user": user}
        )
    except Exception as e:
        logger.error(f"Error rendering dashboard page: {e}")
        return JSONResponse(status_code=500, content={"detail": "Failed to render dashboard page"})

@app.get("/servers")
def servers(request: Request, user: str = Depends(get_current_user_page)):
    return templates.TemplateResponse(
        request=request,
        name="servers.html",
        context={"user": user}
    )

@app.get("/predictions")
def predictions(request: Request, user: str = Depends(get_current_user_page)):
    return templates.TemplateResponse(
        request=request,
        name="predictions.html",
        context={"user": user}
    )

@app.get("/alerts")
def alerts(request: Request, user: str = Depends(get_current_user_page)):
    return templates.TemplateResponse(
        request=request,
        name="alerts.html",
        context={"user": user}
    )

@app.get("/insights")
def insights(request: Request, user: str = Depends(get_current_user_page)):
    return templates.TemplateResponse(
        request=request,
        name="insights.html",
        context={"user": user}
    )

@app.get("/analytics")
def analytics(request: Request, user: str = Depends(get_current_user_page)):
    return templates.TemplateResponse(
        request=request,
        name="analytics.html",
        context={"user": user}
    )

@app.get("/trends")
def trends():
    return RedirectResponse(url="/analytics", status_code=302)

@app.get("/favicon.ico")
def favicon() -> RedirectResponse:
    return RedirectResponse(url="/static/favicon.ico")