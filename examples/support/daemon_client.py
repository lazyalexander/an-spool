"""Bounded example client over the existing host protocol; owns no execution state."""

import json
import time
from pathlib import Path


class DaemonClient:
    def request(self, value, credential=None):
        # Credentials exist only in this call; original grants belong to the daemon.
        import socket

        payload = {"credential": credential, "request": value} if credential else value
        data = json.dumps(payload).encode() + b"\n"
        if len(data) > 131072:
            raise ValueError("Request too large")
        with socket.socket(socket.AF_UNIX) as sock:
            sock.settimeout(60)
            sock.connect(
                str(
                    Path(self.config["service"])
                    / ("tasks.sock" if credential else "control.sock")
                )
            )
            sock.sendall(data)
            response = b""
            while True:
                chunk = sock.recv(65536)
                if not chunk:
                    break
                response += chunk
                if len(response) > 4 * 1024 * 1024:
                    raise ValueError("Response too large")
        value = json.loads(response)
        if "error" in value:
            raise ValueError(value["error"])
        return value["result"]

    def execute_plan(self, plan):
        req = plan["request"]
        if "scope" not in plan:
            return self.request({**req, "approve": plan["native"]["approval_sha256"]})
        scope = {
            **plan["scope"],
            "expires_ms": int(time.time() * 1000)
            + (plan["request"].get("seconds", 60) + 120) * 1000,
        }
        grant_req = {"op": "grant", "scope": scope}
        preview = self.request(grant_req)
        credential = self.request({**grant_req, "approve": preview["approval_sha256"]})[
            "credential"
        ]
        try:
            authorized = self.request(req, credential)
            # The only permitted preview change is the newly issued task binding.
            before = plan["native"]["plan"].copy()
            after = authorized["plan"].copy()
            after.pop("task_authorization", None)
            if before != after:
                raise ValueError("Native execution changed after permission binding")
            return self.request(
                {**req, "approve": authorized["approval_sha256"]}, credential
            )
        except Exception:
            revoke = {"op": "revoke-grant", "id": credential["id"]}
            preview = self.request(revoke)
            self.request({**revoke, "approve": preview["approval_sha256"]})
            raise
