"""
NSP Kafka Alarm Consumer - Main Entry Point

Flow:
1. Authenticate (TokenManager)
2. Create NSP Subscription (Kafka topic)
3. Start auto-renew thread
4. Load active alarms into cache (from DB)
5. Start Kafka consumer loop
6. On shutdown → cleanup (delete subscription + revoke token)
"""

import threading
import signal
import sys
import atexit
import requests
import os
from pathlib import Path

# Core modules
from alarm_cache import AlarmCache
from alarm_lifecycle import get_active_power_issues, get_active_los_alarms
from configuration import AUTH_URL, REVOKE_URL, USERNAME, PASSWORD
from token_manager import TokenManager
from create_kafka_subscription import create_subscription
from renew_subscription import renew_subscription
from delete_subscription import delete_subscription
from kafka_consumer import start_kafka_consumer


# ============================================================
# GLOBAL STATE (shared across threads)
# ============================================================
stop_event = threading.Event()
subscription_id = None
token_mgr = None
cleanup_done = False


# ============================================================
# TOKEN FILE (portable, no hardcoding)
# ============================================================
BASE_DIR = Path(__file__).resolve().parent
TOKEN_FILE = Path(os.getenv("TOKEN_FILE", BASE_DIR / "token.json"))


# ============================================================
# CLEANUP (runs on shutdown)
# ============================================================
def cleanup():
    """Safely release all NSP resources."""
    global cleanup_done

    if cleanup_done:
        return

    cleanup_done = True
    print("\n🧹 Cleaning up resources...")
    stop_event.set()

    # Delete NSP subscription
    if subscription_id and token_mgr:
        try:
            delete_subscription(token_mgr, subscription_id)
            print("✅ Subscription deleted")
        except Exception as e:
            print("⚠️ Subscription cleanup failed:", e)

    # Revoke token
    if token_mgr:
        try:
            token_mgr.revoke()
        except Exception as e:
            print("⚠️ Token revoke failed:", e)


# ============================================================
# SIGNAL HANDLING (CTRL+C / system kill)
# ============================================================
def shutdown_handler(sig, frame):
    print(f"\n🛑 Shutdown signal received ({sig})")
    cleanup()
    sys.exit(0)


signal.signal(signal.SIGINT, shutdown_handler)
signal.signal(signal.SIGTERM, shutdown_handler)

# Always run cleanup (even on crash)
atexit.register(cleanup)


# ============================================================
# AUTO-RENEW THREAD
# Keeps NSP subscription alive
# ============================================================
def auto_renew_subscription(token_mgr, subscription_id, stop_event, interval=1800):
    while not stop_event.is_set():

        # Wait OR exit if stopping
        if stop_event.wait(interval):
            return

        try:
            renew_subscription(token_mgr, subscription_id)
            print("🔁 Subscription renewed")

        except requests.HTTPError as e:
            if stop_event.is_set():
                return

            if e.response and e.response.status_code == 401:
                print("🔐 Token expired → refreshing")
                token_mgr.ensure_token()
            else:
                print("❌ Renewal failed:", e)

        except Exception as e:
            if stop_event.is_set():
                return
            print("❌ Unexpected renewal error:", e)


# ============================================================
# MAIN APPLICATION
# ============================================================
if __name__ == "__main__":

    print("🚀 Starting NSP Alarm Consumer")
    print(f"🔐 Token file: {TOKEN_FILE}")

    try:
        # ----------------------------------------------------
        # 1. AUTHENTICATION
        # ----------------------------------------------------
        token_mgr = TokenManager(
            auth_url=AUTH_URL,
            revoke_url=REVOKE_URL,
            client_id=USERNAME,
            client_secret=PASSWORD,
            token_file=str(TOKEN_FILE),
            verify_ssl=False,
        )

        # ----------------------------------------------------
        # 2. CREATE SUBSCRIPTION (Kafka topic)
        # ----------------------------------------------------
        subscription_id, topic_id = create_subscription(token_mgr)
        print(f"📡 Kafka topic: {topic_id}")

        # ----------------------------------------------------
        # 3. START AUTO-RENEW THREAD
        # ----------------------------------------------------
        threading.Thread(
            target=auto_renew_subscription,
            args=(token_mgr, subscription_id, stop_event),
            daemon=True,
            name="subscription-renew-thread",
        ).start()

        # ----------------------------------------------------
        # 4. INITIALIZE CACHE (from DB)
        # ----------------------------------------------------
        alarm_cache = AlarmCache()

        print("📥 Loading active alarms into cache...")
        alarm_cache.load_power_issues(get_active_power_issues())
        alarm_cache.load_los_alarms(get_active_los_alarms())
        print("✅ Cache ready")

        # ----------------------------------------------------
        # 5. START KAFKA CONSUMER LOOP
        # ----------------------------------------------------
        start_kafka_consumer(topic_id, stop_event, alarm_cache)

    except Exception as e:
        print("❌ Fatal error:", e)
        cleanup()
        sys.exit(1)