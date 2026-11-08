"""Example-only loopback page transport; not a product or execution host."""

import json
import os
import secrets
import subprocess
from http.server import BaseHTTPRequestHandler, HTTPServer


def serve_application(app, root, assets):
    token = secrets.token_hex(32)

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def respond(self, status, body, mime="application/json"):
            body = body.encode()
            self.send_response(status)
            for key, value in {
                "Content-Type": mime,
                "Content-Length": str(len(body)),
                "Cache-Control": "no-store",
                "Referrer-Policy": "no-referrer",
                "X-Content-Type-Options": "nosniff",
                "Content-Security-Policy": "default-src 'self'; style-src 'unsafe-inline'; frame-ancestors 'none'",
            }.items():
                self.send_header(key, value)
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            if self.headers.get("Host") != self.server.authority:
                return self.respond(403, "{}")
            if self.path in ("/", "/app.js"):
                return self.respond(
                    200,
                    (
                        assets / ("index.html" if self.path == "/" else "app.js")
                    ).read_text(),
                    "text/html; charset=utf-8"
                    if self.path == "/"
                    else "text/javascript; charset=utf-8",
                )
            if (
                self.path != "/view"
                or self.headers.get("Authorization") != "Bearer " + token
            ):
                return self.respond(403, "{}")
            try:
                self.respond(200, json.dumps(app.view()))
            except (
                ValueError,
                OSError,
                RuntimeError,
                KeyError,
                TypeError,
                StopIteration,
                subprocess.SubprocessError,
            ) as error:
                self.respond(400, json.dumps({"error": str(error)}))

        def do_POST(self):
            if (
                self.headers.get("Host") != self.server.authority
                or self.path != "/action"
                or self.headers.get("Origin") != "http://" + self.server.authority
                or self.headers.get("Authorization") != "Bearer " + token
            ):
                return self.respond(403, "{}")
            try:
                size = int(self.headers.get("Content-Length", "0"))
                if not 0 < size <= 131072:
                    raise ValueError("Invalid request size")
                self.respond(
                    200, json.dumps(app.act(json.loads(self.rfile.read(size))))
                )
            except (
                ValueError,
                OSError,
                RuntimeError,
                KeyError,
                TypeError,
                StopIteration,
                subprocess.SubprocessError,
            ) as error:
                self.respond(400, json.dumps({"error": str(error)}))

    server = HTTPServer(("127.0.0.1", 0), Handler)
    server.authority = f"127.0.0.1:{server.server_port}"
    (root / "application-endpoint.json").write_text(
        json.dumps({"url": f"http://{server.authority}/#{token}"})
    )
    os.chmod(root / "application-endpoint.json", 0o600)
    try:
        server.serve_forever()
    finally:
        server.server_close()
