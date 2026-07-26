from fastapi import APIRouter
from Backend.database.mongodb import get_predictions_collection, get_metrics_collection

router = APIRouter()


@router.get("/ai-insights")
def ai_insights():
    p_col = get_predictions_collection()
    m_col = get_metrics_collection()

    if p_col is None:
        return {}

    data = list(p_col.find().sort("timestamp", -1))
    if not data:
        return {}

    # Get latest entry per server
    latest_by_server = {}
    for p in data:
        sname = p.get("server_name", "Unknown")
        if sname not in latest_by_server:
            latest_by_server[sname] = p

    unique_servers = list(latest_by_server.values())

    highest_cpu = max(
        unique_servers,
        key=lambda x: float(x.get("cpu_usage_percent", 0))
    )

    highest_memory = max(
        unique_servers,
        key=lambda x: float(x.get("memory_usage_percent", 0))
    )

    anomalies = [x for x in unique_servers if x.get("prediction") == "ANOMALY"]
    if anomalies:
        highest_risk = max(
            anomalies,
            key=lambda x: float(x.get("confidence", 0))
        )
    else:
        highest_risk = max(
            unique_servers,
            key=lambda x: float(x.get("confidence", 0))
        )

    # Risk score calculation
    anomaly_ratio = len(anomalies) / max(1, len(unique_servers))
    avg_cpu = sum(float(x.get("cpu_usage_percent", 0)) for x in unique_servers) / max(1, len(unique_servers))
    avg_mem = sum(float(x.get("memory_usage_percent", 0)) for x in unique_servers) / max(1, len(unique_servers))

    if anomalies:
        risk_score = min(98.5, max(75.0, round(float(highest_risk.get("confidence", 91.2)), 1)))
    else:
        risk_score = round(max(15.0, (avg_cpu + avg_mem) / 4.0), 1)

    top_conf = round(float(highest_risk.get("confidence", 95.0)), 1)
    if top_conf > 100:
        top_conf = round(top_conf / 100.0, 1)

    # Dynamic recommendation & action plan
    top_name = highest_risk.get("server_name", "Unknown")
    top_causes = highest_risk.get("possible_causes", [])

    if anomalies:
        causes_str = ", ".join(top_causes) if top_causes else "Severe resource saturation"
        recommendation = (
            f"Active incident detected on {top_name} with {top_conf}% confidence. "
            f"Primary trigger: {causes_str}. Automated traffic throttling and worker thread rebalancing are strongly recommended."
        )
        actions = [
            f"Isolate traffic routing to {top_name} to prevent cluster cascading",
            f"Inspect thread contention & reclaim memory buffers on {highest_memory.get('server_name', top_name)}",
            f"Review process allocation for high-CPU workloads on {highest_cpu.get('server_name', top_name)}",
            "Trigger automated horizontal container scale-out if stress persists > 5 minutes"
        ]
    else:
        recommendation = (
            f"All {len(unique_servers)} monitored nodes are operating comfortably within baseline parameters. "
            "Continuous heuristic telemetry monitoring active with zero anomalies detected."
        )
        actions = [
            "Maintain standard periodic node health polling",
            "Run routine cache garbage collection during low-traffic windows",
            "Verify backup database replica synchronization",
            "Keep automated AI mitigation triggers on active standby"
        ]

    return {
        "top_risk": top_name,
        "top_risk_confidence": top_conf,
        "top_risk_causes": top_causes,
        "highest_cpu": highest_cpu.get("server_name", "Unknown"),
        "highest_cpu_val": round(float(highest_cpu.get("cpu_usage_percent", 0)), 1),
        "highest_memory": highest_memory.get("server_name", "Unknown"),
        "highest_memory_val": round(float(highest_memory.get("memory_usage_percent", 0)), 1),
        "risk_score": f"{risk_score}%",
        "prediction_confidence": f"{top_conf}%",
        "total_anomalies": len(anomalies),
        "total_servers": len(unique_servers),
        "recommendation": recommendation,
        "actions": actions
    }