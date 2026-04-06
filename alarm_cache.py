"""
Alarm Cache (In-Memory State)

Purpose:
- Keep track of active root alarms
- Used for correlation (NO DB calls in hot path)

Stores:
- Power Issues
- LOS-OCH alarms
"""

import threading


class AlarmCache:
    def __init__(self):
        self._lock = threading.Lock()

        # Root alarms only
        self.active_power_issues = {}   # alarm_id → alarm dict
        self.active_los_alarms = {}     # alarm_id → alarm dict

    # ============================================================
    # LOAD (used only at startup)
    # ============================================================

    def load_power_issues(self, alarms):
        """Load existing Power Issues from DB into cache."""
        with self._lock:
            self.active_power_issues = {
                a["alarm_id"]: a for a in alarms
            }

    def load_los_alarms(self, alarms):
        """Load existing LOS alarms from DB into cache."""
        with self._lock:
            self.active_los_alarms = {
                a["alarm_id"]: a for a in alarms
            }

    # ============================================================
    # READ (used in hot path)
    # ============================================================

    def get_power_issues(self):
        """Return current active Power Issues."""
        with self._lock:
            return list(self.active_power_issues.values())

    def get_los_alarms(self):
        """Return current active LOS alarms."""
        with self._lock:
            return list(self.active_los_alarms.values())

    # ============================================================
    # WRITE (on alarm lifecycle updates)
    # ============================================================

    def add_or_update(self, alarm):
        """
        Add or update alarm in cache.
        Only stores ROOT alarms (not children).
        """

        alarm_id = alarm["alarm_id"]
        name = alarm.get("alarm_name")
        severity = alarm.get("severity")

        with self._lock:

            # -------------------------
            # Power Issue (ROOT)
            # -------------------------
            if (
                name == "Power Issue"
                and alarm.get("object_type") == "PHYSICALCONNECTION"
            ):
                self.active_power_issues[alarm_id] = alarm

            # -------------------------
            # LOS-OCH (ROOT)
            # -------------------------
            if (
                name == "Loss of signal - OCH"
                and severity in ("CRITICAL", "MAJOR")
            ):
                self.active_los_alarms[alarm_id] = alarm

    def remove(self, alarm_id):
        """Remove alarm from all caches (on CLEAR)."""
        with self._lock:
            self.active_power_issues.pop(alarm_id, None)
            self.active_los_alarms.pop(alarm_id, None)