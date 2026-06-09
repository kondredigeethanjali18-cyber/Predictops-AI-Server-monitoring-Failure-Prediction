from fastapi import APIRouter
from Backend.database.mongodb import metrics_collection

router = APIRouter()

@router.get("/latest-metrics")
def latest_metrics():

    metric = metrics_collection.find_one(
        sort=[("_id", -1)]
    )

    if metric:
        metric["_id"] = str(metric["_id"])
        return metric

    return {
        "message": "No metrics found"
    }