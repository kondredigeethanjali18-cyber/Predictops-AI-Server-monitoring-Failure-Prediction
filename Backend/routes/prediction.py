from fastapi import APIRouter, HTTPException
from pymongo.errors import PyMongoError
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


@router.get("/all-predictions")
def all_predictions():
    col = get_predictions_collection()
    if col is None:
        return []

    try:
        predictions = list(
            col.find().sort(
                "timestamp",
                -1
            )
        )
    except PyMongoError as exc:
        raise HTTPException(status_code=503, detail="Unable to fetch predictions from database") from exc

    for p in predictions:
        p["_id"] = str(p["_id"])
        if "confidence" in p:
            p["confidence"] = clean_confidence(p["confidence"])

    return predictions


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

    return {"message": "No predictions found"}