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

    try:
        pipeline = [
            {"$match": {"server_name": {"$ne": None}}},
            {"$sort": {"_id": -1}},
            {"$group": {
                "_id": "$server_name",
                "doc": {"$first": "$$ROOT"}
            }},
            {"$replaceRoot": {"newRoot": "$doc"}},
            {"$sort": {"server_name": 1}}
        ]
        results = list(col.aggregate(pipeline))
        for r in results:
            if "_id" in r:
                r["_id"] = str(r["_id"])
            if "timestamp" in r and hasattr(r["timestamp"], "isoformat"):
                r["timestamp"] = r["timestamp"].isoformat()
        return results
    except Exception:
        metrics = list(col.find().sort("_id", -1).limit(500))
        servers = {}
        for metric in metrics:
            server_name = metric.get("server_name")
            if server_name and server_name not in servers:
                metric["_id"] = str(metric["_id"])
                if "timestamp" in metric and hasattr(metric["timestamp"], "isoformat"):
                    metric["timestamp"] = metric["timestamp"].isoformat()
                servers[server_name] = metric
        return list(servers.values())