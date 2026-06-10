from fastapi import APIRouter
from Backend.database.mongodb import predictions_collection

router = APIRouter()

@router.get("/dashboard-summary")
def dashboard_summary():

    predictions = list(
        predictions_collection.find()
    )

    total = len(predictions)

    healthy = 0
    warning = 0
    critical = 0

    for p in predictions:

        cpu = p.get(
            "cpu_usage_percent",
            0
        )

        memory = p.get(
            "memory_usage_percent",
            0
        )

        if cpu > 90 or memory > 90:
            critical += 1

        elif cpu > 70 or memory > 80:
            warning += 1

        else:
            healthy += 1

    return {
        "total": total,
        "healthy": healthy,
        "warning": warning,
        "critical": critical
    }