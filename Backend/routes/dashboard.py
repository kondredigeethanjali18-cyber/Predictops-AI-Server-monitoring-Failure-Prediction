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
        sort=[("timestamp", -1)]
    )

    if result:
        result["_id"] = str(result["_id"])
        if "confidence" in result:
            result["confidence"] = clean_confidence(result["confidence"])
        return result

    return {
        "message": "No predictions found"
    }


@router.get("/all-server-predictions")
def all_server_predictions():
    col = get_predictions_collection()
    if col is None:
        return []

    predictions = list(
        col.find()
        .sort("timestamp", -1)
    )

    servers = {}

    for prediction in predictions:
        server_name = prediction.get(
            "server_name",
            "Unknown"
        )

        if server_name not in servers:
            prediction["_id"] = str(prediction["_id"])
            if "confidence" in prediction:
                prediction["confidence"] = clean_confidence(prediction["confidence"])
            servers[server_name] = prediction

    return list(servers.values())