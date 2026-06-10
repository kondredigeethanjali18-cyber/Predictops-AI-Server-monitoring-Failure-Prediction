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
@router.get("/all-servers")
def all_servers():

    metrics = list(
        metrics_collection.find()
        .sort("_id", -1)
        .limit(1000)
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