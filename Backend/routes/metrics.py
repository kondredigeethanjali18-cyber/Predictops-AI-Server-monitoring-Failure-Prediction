from fastapi import APIRouter
from Backend.database.mongodb import get_metrics_collection

router = APIRouter()


@router.get("/latest-metrics")
def latest_metrics():
    col = get_metrics_collection()
    if col is None:
        return {"message": "Database not available"}

    metric = col.find_one(
        sort=[("_id", -1)]
    )

    if metric:
        metric["_id"] = str(metric["_id"])
        return metric

    return {
        "message": "No metrics found"
    }


@router.get("/all-servers")
def all_servers():
    col = get_metrics_collection()
    if col is None:
        return []

    metrics = list(
        col.find()
        .sort("_id", -1)
    )

    servers = {}

    for metric in metrics:
        server_name = metric.get(
            "server_name",
            "Unknown"
        )

        if server_name not in servers:
            metric["_id"] = str(
                metric["_id"]
            )
            servers[server_name] = metric

    return list(servers.values())