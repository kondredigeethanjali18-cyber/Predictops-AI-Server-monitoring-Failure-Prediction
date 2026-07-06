from fastapi import APIRouter
from Backend.database.mongodb import get_predictions_collection

router = APIRouter()


def clean_confidence(conf_val):
    try:
        c = float(conf_val)
        if c > 100:
            c = c / 100.0
        return round(c, 2)
    except Exception:
        return conf_val


@router.get("/latest-prediction")
def latest_prediction():
    col = get_predictions_collection()
    if col is None:
        return {"message": "Database not available"}

    result = col.find_one(
        sort=[("_id", -1)]
    )

    if result:
        result["_id"] = str(result["_id"])
        if "confidence" in result:
            result["confidence"] = clean_confidence(result["confidence"])
        if "timestamp" in result and hasattr(result["timestamp"], "isoformat"):
            result["timestamp"] = result["timestamp"].isoformat()
        return result

    return {
        "message": "No predictions found"
    }


@router.get("/all-server-predictions")
def all_server_predictions():
    col = get_predictions_collection()
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
        predictions = list(col.aggregate(pipeline))
        for p in predictions:
            if "_id" in p:
                p["_id"] = str(p["_id"])
            if "confidence" in p:
                p["confidence"] = clean_confidence(p["confidence"])
            if "timestamp" in p and hasattr(p["timestamp"], "isoformat"):
                p["timestamp"] = p["timestamp"].isoformat()
        return predictions
    except Exception:
        predictions = list(
            col.find()
            .sort("_id", -1)
            .limit(500)
        )
        servers = {}
        for prediction in predictions:
            server_name = prediction.get("server_name")
            if server_name and server_name not in servers:
                prediction["_id"] = str(prediction["_id"])
                if "confidence" in prediction:
                    prediction["confidence"] = clean_confidence(prediction["confidence"])
                if "timestamp" in prediction and hasattr(prediction["timestamp"], "isoformat"):
                    prediction["timestamp"] = prediction["timestamp"].isoformat()
                servers[server_name] = prediction
        return list(servers.values())