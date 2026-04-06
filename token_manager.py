"""
Token Manager

Handles:
- Getting access token
- Refreshing token
- Revoking token
- Storing token securely on disk
"""

import json
import time
import base64
import requests
from pathlib import Path
from requests.auth import HTTPBasicAuth


class TokenManager:
    def __init__(
        self,
        auth_url,
        revoke_url,
        client_id,
        client_secret,
        token_file,
        refresh_before=300,
        verify_ssl=False,
    ):
        self.auth_url = auth_url
        self.revoke_url = revoke_url
        self.client_id = client_id
        self.client_secret = client_secret

        self.token_file = Path(token_file)
        self.token_file.parent.mkdir(parents=True, exist_ok=True)

        self.refresh_before = refresh_before
        self.verify_ssl = verify_ssl

    # ============================================================
    # INTERNAL HELPERS
    # ============================================================

    def _now(self):
        return int(time.time())

    def _load_tokens(self):
        if not self.token_file.exists():
            return None
        return json.loads(self.token_file.read_text())

    def _save_tokens(self, data):
        if "access_token" not in data:
            raise RuntimeError("Invalid token response")

        tmp = self.token_file.with_suffix(".tmp")
        tmp.write_text(json.dumps(data))
        tmp.chmod(0o600)
        tmp.replace(self.token_file)

    def _decode_exp(self, token):
        try:
            payload = token.split(".")[1]
            payload += "=" * (-len(payload) % 4)
            decoded = base64.urlsafe_b64decode(payload)
            return json.loads(decoded).get("exp")
        except Exception:
            return None

    # ============================================================
    # TOKEN OPERATIONS
    # ============================================================

    def _get_token(self):
        print("🔐 Getting new token...")

        r = requests.post(
            self.auth_url,
            auth=HTTPBasicAuth(self.client_id, self.client_secret),
            json={"grant_type": "client_credentials"},
            verify=self.verify_ssl,
        )

        r.raise_for_status()
        self._save_tokens(r.json())

    def _refresh_token(self):
        tokens = self._load_tokens()
        if not tokens or "refresh_token" not in tokens:
            return False

        print("🔁 Refreshing token...")

        r = requests.post(
            self.auth_url,
            auth=HTTPBasicAuth(self.client_id, self.client_secret),
            json={
                "grant_type": "refresh_token",
                "refresh_token": tokens["refresh_token"],
            },
            verify=self.verify_ssl,
        )

        if r.status_code != 200:
            return False

        self._save_tokens(r.json())
        return True

    def ensure_token(self):
        tokens = self._load_tokens()

        if not tokens:
            self._get_token()
            return

        exp = self._decode_exp(tokens.get("access_token"))

        if not exp or (exp - self._now()) < self.refresh_before:
            if not self._refresh_token():
                self._get_token()

    def get_access_token(self):
        self.ensure_token()
        return self._load_tokens()["access_token"]

    # ============================================================
    # CLEANUP
    # ============================================================

    def revoke(self):
        tokens = self._load_tokens()
        if not tokens:
            return

        print("🛑 Revoking token...")

        requests.post(
            self.revoke_url,
            auth=HTTPBasicAuth(self.client_id, self.client_secret),
            data={"token": tokens["access_token"]},
            verify=self.verify_ssl,
        )

        self.token_file.unlink(missing_ok=True)
        print("✅ Token revoked")