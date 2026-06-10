from fastapi import APIRouter
from Backend.database.mongodb import predictions_collection

router = APIRouter()

@router.get("/all-predictions")
def all_predictions():

    predictions = list(
        predictions_collection.find().sort(
            "timestamp",
            -1
        )
    )

    for p in predictions:

        p["_id"] = str(p["_id"])

    return predictions



@router.get("/latest-prediction")
def latest_prediction():

    result = predictions_collection.find_one(
        sort=[("timestamp", -1)]
    )

    print(result)

    if result:
        result["_id"] = str(result["_id"])
        return result

    return {"message": "No predictions found"}