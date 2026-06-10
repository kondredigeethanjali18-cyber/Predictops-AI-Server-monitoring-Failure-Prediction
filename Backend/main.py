from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi import Request

from Backend.routes.health import router as health_router
from Backend.routes.prediction import router as prediction_router
from Backend.routes.dashboard import router as dashboard_router
from Backend.routes.metrics import router as metrics_router
from Backend.routes.dashboard_api import router as dashboard_api_router
from Backend.routes.insights import router as insights_router

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

app.mount(
    "/static",
    StaticFiles(directory="Backend/static"),
    name="static"
)

app.include_router(
    dashboard_api_router
)

app.include_router(
    insights_router
)

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

app.mount(
    "/static",
    StaticFiles(directory=str(BASE_DIR / "static")),
    name="static"
)

templates = Jinja2Templates(
    directory=str(BASE_DIR / "templates")
)
app.include_router(health_router)
app.include_router(prediction_router)
app.include_router(dashboard_router)
app.include_router(metrics_router)

@app.get("/")
def dashboard():
    return "Dashboard Route Working"

@app.get("/dashboard")
def dashboard(request: Request):

    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={}
    )

@app.get("/servers")
def servers(request: Request):

    return templates.TemplateResponse(
        request=request,
        name="servers.html",
        context={}
    )

@app.get("/predictions")
def predictions(request: Request):

    return templates.TemplateResponse(
        request=request,
        name="predictions.html",
        context={}
    )

@app.get("/alerts")
def alerts(request: Request):

    return templates.TemplateResponse(
        request=request,
        name="alerts.html",
        context={}
    )

@app.get("/insights")
def insights(request: Request):

    return templates.TemplateResponse(
        request=request,
        name="insights.html",
        context={}
    )

@app.get("/analytics")
def analytics(request: Request):

    return templates.TemplateResponse(
        request=request,
        name="analytics.html",
        context={}
    )