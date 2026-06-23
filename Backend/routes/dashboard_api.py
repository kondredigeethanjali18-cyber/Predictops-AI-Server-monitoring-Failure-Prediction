from fastapi import APIRouter
from starlette.concurrency import run_in_threadpool
from Backend.database.mongodb import predictions_collection

router = APIRouter()


def calculate_dashboard_metrics(predictions):
    total = len(predictions)
    healthy = 0
    warning = 0
    critical = 0

    for p in predictions:
        cpu = p.get("cpu_usage_percent", 0)
        memory = p.get("memory_usage_percent", 0)

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
        "critical": critical,
    }


@router.get("/dashboard-summary")
def dashboard_summary():
    """Synchronous dashboard summary endpoint."""
    predictions = list(predictions_collection.find())
    return calculate_dashboard_metrics(predictions)


@router.get("/dashboard-summary-async")
async def dashboard_summary_async():
    """Asynchronous dashboard summary endpoint using a thread pool."""

    def fetch_predictions():
        return list(predictions_collection.find())

    predictions = await run_in_threadpool(fetch_predictions)
    return calculate_dashboard_metrics(predictions)