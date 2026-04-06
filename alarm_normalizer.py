"""
Alarm Normalizer

Purpose:
- Convert raw NSP event → clean alarm dict
- Apply filtering decision
- Use cache for correlation (NO DB calls)
"""

from datetime import datetime, timezone
import pytz

from severity_mapper import map_severity
from object_parser import parse_affected_object
from alarm_filters import should_drop_alarm


LOCAL_TZ = pytz.timezone("Asia/Dhaka")


# ============================================================
# TIME HELPERS
# ============================================================

def utc_ms_to_local_iso(ts):
    """Convert epoch ms → local ISO time"""
    if not ts:
        return None

    if isinstance(ts, dict):
        ts = ts.get("value") or ts.get("milliseconds") or ts.get("seconds", 0) * 1000

    if isinstance(ts, str) and ts.isdigit():
        ts = int(ts)

    try:
        utc_dt = datetime.fromtimestamp(ts / 1000, tz=timezone.utc)
        return utc_dt.astimezone(LOCAL_TZ).isoformat()
    except Exception:
        return None


def epoch_ms_to_utc(ts):
    """Convert epoch ms → UTC ISO"""
    if not ts:
        return None

    if isinstance(ts, dict):
        ts = ts.get("value") or ts.get("milliseconds") or ts.get("seconds", 0) * 1000

    if isinstance(ts, str) and ts.isdigit():
        ts = int(ts)

    try:
        return datetime.utcfromtimestamp(ts / 1000).isoformat() + "Z"
    except Exception:
        return None


# ============================================================
# MAIN NORMALIZER
# ============================================================

def normalize_alarm(event, alarm_cache):

    # ----------------------------------------------------
    # Extract NSP notification
    # ----------------------------------------------------
    notif = event.get("data", {}).get("ietf-restconf:notification", {})

    alarm = None
    event_type = None

    for k, v in notif.items():
        if k.startswith("nsp-fault:"):
            event_type = k.replace("nsp-fault:", "")
            alarm = v
            break

    if not alarm:
        return None

    # ----------------------------------------------------
    # Extract core fields
    # ----------------------------------------------------
    alarm_name = alarm.get("alarmName")
    severity_raw = alarm.get("severity")

    normalized = {
        "event_type": event_type,
        "event_time": notif.get("eventTime"),

        "alarm_id": alarm.get("objectId"),
        "alarm_name": alarm_name,

        "specific_problem": alarm.get("specificProblem"),
        "probable_cause": alarm.get("probableCause"),

        "ne_name": alarm.get("neName"),
        "ne_id": alarm.get("neId"),
        "source": alarm.get("sourceType"),

        "severity_raw": severity_raw,
        "severity": map_severity(severity_raw, alarm.get("specificProblem")),

        "affected_object": alarm.get("affectedObject"),
        "affected_object_name": alarm.get("affectedObjectName"),
        "object_type": alarm.get("affectedObjectType"),
        "object_details": parse_affected_object(alarm.get("affectedObject")),

        "first_detected": utc_ms_to_local_iso(alarm.get("firstTimeDetected")),
        "last_detected": utc_ms_to_local_iso(alarm.get("lastTimeDetected")),

        "acknowledged": alarm.get("acknowledged", False),
        "service_affecting": alarm.get("serviceAffecting"),
        "implicitly_cleared": alarm.get("implicitlyCleared", False),
    }

    # ----------------------------------------------------
    # Get cache context
    # ----------------------------------------------------
    active_power = alarm_cache.get_power_issues()
    active_los = alarm_cache.get_los_alarms()

    # ----------------------------------------------------
    # FILTER DECISION
    # ----------------------------------------------------
    if should_drop_alarm(
        alarm_name=normalized["alarm_name"],
        specific_problem=normalized["specific_problem"],
        probable_cause=normalized["probable_cause"],
        ne_name=normalized["ne_name"],
        ne_id=normalized["ne_id"],
        source=normalized["source"],
        object_type=normalized["object_type"],
        severity=normalized["severity"],
        affected_object_name=normalized["affected_object_name"],
        first_detected=epoch_ms_to_utc(alarm.get("firstTimeDetected")),
        active_power_issues=active_power,
        active_los_alarms=active_los,
    ):
        return None

    return normalized