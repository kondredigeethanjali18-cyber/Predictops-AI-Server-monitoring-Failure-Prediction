from fastapi import APIRouter
from Backend.database.mongodb import predictions_collection

router = APIRouter()

@router.get("/latest-prediction")
def latest_prediction():

    result = predictions_collection.find_one(
        sort=[("timestamp", -1)]
    )

    if result:
        result["_id"] = str(result["_id"])
        return result

    return {"message": "No predictions found"}