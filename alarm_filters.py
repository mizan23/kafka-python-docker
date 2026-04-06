"""
Alarm Filtering & Correlation Engine

Return:
- True  → DROP alarm
- False → KEEP alarm

Logic Layers:
1. Always allow critical root alarms
2. Suppress child alarms (Power / LOS)
3. Drop known noise (login, threshold, etc.)
"""

from datetime import datetime, timedelta


# ============================================================
# HELPERS
# ============================================================

def _parse_time(ts):
    """Convert ISO string → datetime."""
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))


def _extract_ops_span(name):
    """
    Extract OPS span (e.g., OPS-3-7 from string)
    """
    if not name:
        return None

    for part in name.split("/"):
        if part.startswith("OPS-"):
            return "-".join(part.split("-")[:3])

    return None


# ============================================================
# RULE SETS
# ============================================================

# --- POWER ---
POWER_CHILD_ALARMS = {
    "Power Adjustment Required",
    "Power Adjustment Failure",
}
POWER_TIME_WINDOW = timedelta(minutes=10)


# --- LOS ---
LOS_ROOT_ALARMS = {
    "Loss of signal - OCH",
}
LOS_CHILD_ALARMS = {
    "Transport Failure",
    "OPS Protection Loss of Redundancy",
}
LOS_TIME_WINDOW = timedelta(seconds=30)


# ============================================================
# MAIN FILTER FUNCTION
# ============================================================

def should_drop_alarm(
    *,
    alarm_name,
    specific_problem,
    probable_cause,
    ne_name,
    ne_id,
    source,
    object_type,
    severity,
    affected_object_name=None,
    first_detected=None,
    active_power_issues=None,
    active_los_alarms=None,
):
    """
    Core decision engine.
    """

    # ============================================================
    # 1. ALWAYS KEEP ROOT POWER ISSUE
    # ============================================================
    if alarm_name == "Power Issue" and object_type == "PHYSICALCONNECTION":
        return False

    # ============================================================
    # 2. POWER CHILD SUPPRESSION
    # ============================================================
    if (
        alarm_name in POWER_CHILD_ALARMS
        and object_type == "TP"
        and active_power_issues
        and affected_object_name
        and first_detected
    ):
        child_time = _parse_time(first_detected)
        child_span = _extract_ops_span(affected_object_name)

        for root in active_power_issues:
            if not root.get("first_detected") or not root.get("affected_object_name"):
                continue

            # Time correlation
            if abs(child_time - _parse_time(root["first_detected"])) > POWER_TIME_WINDOW:
                continue

            # Span match
            if child_span == _extract_ops_span(root["affected_object_name"]):
                return True  # DROP child

    # ============================================================
    # 3. LOS CHILD SUPPRESSION
    # ============================================================
    if (
        alarm_name in LOS_CHILD_ALARMS
        and active_los_alarms
        and first_detected
    ):
        child_time = _parse_time(first_detected)
        child_span = _extract_ops_span(affected_object_name)

        for root in active_los_alarms:

            if (
                root.get("alarm_name") not in LOS_ROOT_ALARMS
                or root.get("severity") != "CRITICAL"
                or not root.get("first_detected")
            ):
                continue

            root_time = _parse_time(root["first_detected"])

            if abs(child_time - root_time) > LOS_TIME_WINDOW:
                continue

            root_span = _extract_ops_span(root.get("affected_object_name"))

            if (
                (child_span and root_span and child_span == root_span)
                or ne_name == root.get("ne_name")
            ):
                return True  # DROP child

    # ============================================================
    # 4. NOISE FILTERING (STATIC RULES)
    # ============================================================
    if (
        # Login / Logout noise
        (isinstance(object_type, str) and "Login" in object_type)
        or (isinstance(probable_cause, str) and "Login" in probable_cause)

        # Threshold noise
        or ("Threshold" in str(object_type))

        # Known junk alarms
        or alarm_name in {
            "SR_RESTORED",
            "SR_MANUAL_SWITCH",
            "BASELINE",
            "Adjacency Not Found",
        }

        # Maintenance / system noise
        or probable_cause in {"OPR", "PWRSUSP", "MAINT2-ALLOWED-REMOTE"}

        # Low priority
        or severity in {"WARNING", "INFO"}
    ):
        return True

    # ============================================================
    # DEFAULT: KEEP
    # ============================================================
    return False