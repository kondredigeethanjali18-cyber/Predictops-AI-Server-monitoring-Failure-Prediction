from fastapi import APIRouter
from Backend.database.mongodb import predictions_collection

router = APIRouter()

@router.get("/latest-prediction")
def latest_prediction():

    result = predictions_collection.find_one(
        sort=[("timestamp", -1)]
    )

    print("DEBUG RESULT:")
    print(result)

    if result:
        result["_id"] = str(result["_id"])
        return result

    return {
        "message": "No predictions found"
    }

@router.get("/all-server-predictions")
def all_server_predictions():

    predictions = list(
        predictions_collection.find()
        .sort("timestamp", -1)
        .limit(1000)
    )

    servers = {}

    for prediction in predictions:

        server_name = prediction.get(
            "server_name",
            "Unknown"
        )

        if server_name not in servers:

            prediction["_id"] = str(
                prediction["_id"]
            )

            servers[server_name] = prediction

    return list(servers.values())