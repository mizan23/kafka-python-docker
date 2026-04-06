#!/usr/bin/env python3

import psycopg2
import os
import time
import argparse
from tabulate import tabulate


# ============================================================
# DATABASE CONFIG (SMART)
# ============================================================

def get_db_config():
    return {
        "host": os.getenv("DB_HOST") or "localhost",
        "port": int(os.getenv("DB_PORT", 5432)),
        "dbname": os.getenv("DB_NAME", "nsp"),
        "user": os.getenv("DB_USER", "nsp_user"),
        "password": os.getenv("DB_PASSWORD", "nsp_pass"),
    }


def get_conn():
    config = get_db_config()
    try:
        return psycopg2.connect(**config)
    except Exception as e:
        print("❌ DB connection failed:", e)

        print("\n💡 Fix options:")
        print("1. Run inside container:")
        print("   docker exec -it nsp-alarm-consumer python alarm_cli.py")
        print("\n2. Or expose DB port and run:")
        print("   export DB_HOST=localhost")

        raise


# ============================================================
# FETCH DATA
# ============================================================

def fetch_alarms(limit=20, ne=None, severity=None):
    query = """
    SELECT 
        alarm->>'alarm_name',
        alarm->>'ne_name',
        alarm->>'severity',
        alarm->>'affected_object_name',
        created_at
    FROM active_alarms
    """

    conditions = []
    params = []

    if ne:
        conditions.append("alarm->>'ne_name' = %s")
        params.append(ne)

    if severity:
        conditions.append("alarm->>'severity' = %s")
        params.append(severity)

    if conditions:
        query += " WHERE " + " AND ".join(conditions)

    query += " ORDER BY created_at DESC LIMIT %s"
    params.append(limit)

    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(query, params)
            return cur.fetchall()
    finally:
        conn.close()


# ============================================================
# DISPLAY
# ============================================================

def display_table(rows):
    headers = ["Alarm", "NE", "Severity", "Object", "Created"]
    print(tabulate(rows, headers=headers, tablefmt="fancy_grid"))


# ============================================================
# MAIN
# ============================================================

def main():
    parser = argparse.ArgumentParser(description="NSP Alarm CLI Viewer")

    parser.add_argument("--limit", type=int, default=20, help="Number of alarms")
    parser.add_argument("--ne", help="Filter by NE name")
    parser.add_argument("--severity", help="Filter by severity")
    parser.add_argument("--watch", type=int, help="Auto refresh every N seconds")

    args = parser.parse_args()

    def run_once():
        rows = fetch_alarms(args.limit, args.ne, args.severity)
        os.system("clear")
        print("📡 NSP Alarm Viewer\n")
        display_table(rows)

    if args.watch:
        while True:
            run_once()
            time.sleep(args.watch)
    else:
        run_once()


if __name__ == "__main__":
    main()