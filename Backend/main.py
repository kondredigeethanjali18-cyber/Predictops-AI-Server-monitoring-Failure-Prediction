from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from Backend.routes.health import router as health_router
from Backend.routes.prediction import router as prediction_router
from Backend.routes.dashboard import router as dashboard_router
from Backend.routes.metrics import router as metrics_router

app = FastAPI(
    title="PredictOps AI Server Monitoring"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5500",
        "http://localhost:5500"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(health_router)
app.include_router(prediction_router)
app.include_router(dashboard_router)
app.include_router(metrics_router)

@app.get("/")
def root():
    return {
        "message": "PredictOps API Running"
    }