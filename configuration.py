"""
Configuration Loader

Loads all environment variables and builds:
- NSP API URLs
- Kafka credentials
- Application settings

Source: .env file (via python-dotenv)
"""

import os
from dotenv import load_dotenv


# ============================================================
# LOAD ENV FILE
# ============================================================
load_dotenv()


# ============================================================
# HELPERS
# ============================================================

def require_env(name):
    """Raise error if required env variable is missing."""
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"❌ Missing required environment variable: {name}")
    return value


def get_bool(name, default=False):
    """Parse boolean env variable."""
    return os.getenv(name, str(default)).lower() in ("1", "true", "yes")


# ============================================================
# CORE CONFIG
# ============================================================

NSP_SERVER = os.getenv("NSP_SERVER", "192.168.42.7")

USERNAME = require_env("NSP_USERNAME")
PASSWORD = require_env("NSP_PASSWORD")

KAFKA_KEYSTORE_PASSWORD = require_env("KAFKA_KEYSTORE_PASSWORD")


# ============================================================
# URLS (auto-generated)
# ============================================================

BASE_URL = f"https://{NSP_SERVER}:8443"

AUTH_URL = f"{BASE_URL}/rest-gateway/rest/api/v1/auth/token"
SUBSCRIPTION_URL = f"{BASE_URL}/nbi-notification/api/v1/notifications/subscriptions"
REVOKE_URL = f"{BASE_URL}/rest-gateway/rest/api/v1/auth/revocation"


# ============================================================
# FLAGS
# ============================================================

VERIFY_SSL = get_bool("VERIFY_SSL", False)


# ============================================================
# DEBUG PRINT (optional)
# ============================================================

if get_bool("DEBUG_CONFIG", False):
    print("\n🔧 Loaded Configuration:")
    print(f"NSP_SERVER = {NSP_SERVER}")
    print(f"AUTH_URL = {AUTH_URL}")
    print(f"VERIFY_SSL = {VERIFY_SSL}")