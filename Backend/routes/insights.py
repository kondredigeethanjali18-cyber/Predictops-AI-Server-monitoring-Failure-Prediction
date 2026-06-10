from fastapi import APIRouter
from Backend.database.mongodb import predictions_collection

router = APIRouter()

@router.get("/ai-insights")
def ai_insights():

    data = list(
        predictions_collection.find()
    )

    if not data:

        return {}

    highest_cpu = max(
        data,
        key=lambda x:
        x.get(
            "cpu_usage_percent",
            0
        )
    )

    highest_memory = max(
        data,
        key=lambda x:
        x.get(
            "memory_usage_percent",
            0
        )
    )

    highest_risk = max(
        data,
        key=lambda x:
        x.get(
            "confidence",
            0
        )
    )

    return {

        "top_risk":
            highest_risk["server_name"],

        "highest_cpu":
            highest_cpu["server_name"],

        "highest_memory":
            highest_memory["server_name"]
    }