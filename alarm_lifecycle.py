"""
Alarm Lifecycle Manager

Handles:
- Insert/update active alarms
- Move cleared alarms to history
- Keep cache in sync with DB
"""

import os
import psycopg2
import json
from contextlib import contextmanager


# ============================================================
# DATABASE CONFIG
# ============================================================

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "nsp_alarm_db"),
    "port": int(os.getenv("DB_PORT", 5432)),
    "dbname": os.getenv("DB_NAME", "nsp"),
    "user": os.getenv("DB_USER", "nsp_user"),
    "password": os.getenv("DB_PASSWORD", "nsp_pass"),
}


@contextmanager
def get_conn():
    conn = psycopg2.connect(**DB_CONFIG)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# ============================================================
# SQL
# ============================================================

UPSERT_ACTIVE = """
INSERT INTO active_alarms (alarm_id, alarm)
VALUES (%s, %s::jsonb)
ON CONFLICT (alarm_id)
DO UPDATE SET alarm = EXCLUDED.alarm, last_updated = now();
"""

DELETE_ACTIVE = """
DELETE FROM active_alarms WHERE alarm_id = %s RETURNING alarm;
"""

INSERT_HISTORY = """
INSERT INTO alarm_history (alarm_id, alarm, cleared_at)
VALUES (%s, %s::jsonb, now());
"""


# ============================================================
# MAIN HANDLER
# ============================================================

def handle_alarm_lifecycle(alarm, alarm_cache):

    alarm_id = alarm.get("alarm_id")
    event_type = alarm.get("event_type")
    severity = alarm.get("severity")

    if not alarm_id or not event_type:
        return

    # Ignore delete events
    if event_type == "alarm-delete":
        return

    with get_conn() as conn, conn.cursor() as cur:

        # ----------------------------------------------------
        # CLEAR EVENT → move to history
        # ----------------------------------------------------
        if event_type == "alarm-change" and severity == "CLEAR":

            alarm_cache.remove(alarm_id)

            cur.execute(DELETE_ACTIVE, (alarm_id,))
            row = cur.fetchone()

            if row:
                cur.execute(
                    INSERT_HISTORY,
                    (alarm_id, json.dumps(row[0], default=str)),
                )
            return

        # ----------------------------------------------------
        # CREATE / UPDATE
        # ----------------------------------------------------
        if event_type not in ("alarm-create", "alarm-change"):
            return

        if not alarm.get("alarm_name") or not alarm.get("ne_name"):
            return

        cur.execute(
            UPSERT_ACTIVE,
            (alarm_id, json.dumps(alarm, default=str)),
        )

        alarm_cache.add_or_update(alarm)


# ============================================================
# STARTUP HELPERS (CACHE PRELOAD)
# ============================================================

def get_active_power_issues():
    sql = """
    SELECT alarm FROM active_alarms
    WHERE alarm->>'alarm_name' = 'Power Issue'
    """
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(sql)
        return [row[0] for row in cur.fetchall()]


def get_active_los_alarms():
    sql = """
    SELECT alarm FROM active_alarms
    WHERE alarm->>'alarm_name' = 'Loss of signal - OCH'
    """
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(sql)
        return [row[0] for row in cur.fetchall()]