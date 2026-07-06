import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from Backend.services.server_registry import SERVERS
from Backend.database.mongodb import get_metrics_collection
from Backend.services.prediction_service import predict_metric
from Backend.services.cache_service import CacheService

logger = logging.getLogger(__name__)

# Active chaos overrides: server_name -> {metric, value, remaining_ticks, injected_by}
ACTIVE_CHAOS_OVERRIDES: Dict[str, Dict[str, Any]] = {}


def inject_chaos_telemetry_spike(server_name: str, metric_type: str = "cpu", custom_value: Optional[float] = None, injected_by: str = "admin") -> Dict[str, Any]:
    """
    Injects an operational chaos anomaly spike on a specific server.
    Immediately generates telemetry record, triggers ML prediction, invalidates cache.
    """
    # Find server metadata
    target_server = next((s for s in SERVERS if s["server_name"].lower() == server_name.lower()), None)
    if not target_server:
        # Default fallback server descriptor
        target_server = {"server_id": f"srv-{server_name.lower()}", "server_name": server_name}

    sname = target_server["server_name"]
    now_utc = datetime.now(timezone.utc)

    # Base telemetry values for spike
    cpu = 45.0
    mem = 48.0
    disk = 42.0
    lat = 55.0
    procs = 340
    net_sent = 65.0
    net_recv = 65.0

    mtype = metric_type.lower().strip()
    if mtype == "cpu":
        cpu = custom_value if custom_value is not None else 97.8
        lat = 420.0
        procs = 355
    elif mtype in ["memory", "mem"]:
        mem = custom_value if custom_value is not None else 96.4
        lat = 380.0
    elif mtype == "disk":
        disk = custom_value if custom_value is not None else 94.5
        lat = 310.0
    elif mtype in ["latency", "lat"]:
        lat = custom_value if custom_value is not None else 640.0
        cpu = 88.0
    elif mtype == "network":
        net_sent = custom_value if custom_value is not None else 210.0
        net_recv = custom_value if custom_value is not None else 195.0
    else:
        # General severe anomaly
        cpu = 95.0
        mem = 92.0
        lat = 500.0

    metrics_doc = {
        "server_id": target_server["server_id"],
        "server_name": sname,
        "timestamp": now_utc.isoformat(),
        "cpu_usage_percent": round(cpu, 1),
        "memory_usage_percent": round(mem, 1),
        "memory_used_mb": round((mem / 100.0) * 16000.0, 2),
        "disk_usage_percent": round(disk, 1),
        "network_sent_mb": round(net_sent, 2),
        "network_received_mb": round(net_recv, 2),
        "request_latency_ms": round(lat, 1),
        "active_processes": procs,
        "chaos_injected": True,
        "injected_by": injected_by
    }

    # Persist to metrics collection
    col = get_metrics_collection()
    if col is not None:
        try:
            doc_to_save = dict(metrics_doc)
            col.insert_one(doc_to_save)
        except Exception as e:
            logger.error(f"Error persisting chaos telemetry for {sname}: {e}")

    metrics_doc.pop("_id", None)

    # Evaluate ML prediction immediately
    prediction_result = None
    try:
        prediction_result = predict_metric(metrics_doc)
        if isinstance(prediction_result, dict):
            prediction_result.pop("_id", None)
    except Exception as e:
        logger.error(f"Error predicting chaos telemetry for {sname}: {e}")

    # Register temporary override for the next 3 auto-generator cycles (30 seconds)
    ACTIVE_CHAOS_OVERRIDES[sname] = {
        "metric": mtype,
        "cpu": cpu,
        "mem": mem,
        "disk": disk,
        "lat": lat,
        "remaining_ticks": 3,
        "injected_by": injected_by
    }

    # Invalidate caches
    try:
        CacheService.invalidate_prefix("metrics:")
        CacheService.invalidate_prefix("predictions:")
        CacheService.invalidate_prefix("dashboard:")
        CacheService.invalidate_prefix("insights:")
    except Exception:
        pass

    logger.info(f"Chaos anomaly successfully injected onto {sname} by {injected_by} ({mtype}={custom_value or 'default'})")
    return {
        "success": True,
        "server_name": sname,
        "metric_type": mtype,
        "metrics": metrics_doc,
        "prediction": prediction_result
    }


def get_chaos_override_for_server(server_name: str) -> Optional[Dict[str, Any]]:
    """Checks if server has an active chaos anomaly override."""
    override = ACTIVE_CHAOS_OVERRIDES.get(server_name)
    if override:
        override["remaining_ticks"] -= 1
        if override["remaining_ticks"] <= 0:
            del ACTIVE_CHAOS_OVERRIDES[server_name]
        return override
    return None
