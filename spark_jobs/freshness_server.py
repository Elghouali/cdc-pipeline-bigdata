"""Expose only the Gold driver's last completed refresh timestamp."""

import json
import math
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path != "/timestamp":
            self.send_error(404)
            return
        try:
            timestamp = float(Path("/var/lib/cdc-runtime/gold-refresh").read_text())
            if not math.isfinite(timestamp) or not 0 < timestamp <= time.time():
                timestamp = 0.0
        except (OSError, ValueError):
            timestamp = 0.0
        body = json.dumps({"timestamp": timestamp}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, _format, *_args):
        return


if __name__ == "__main__":
    ThreadingHTTPServer(("0.0.0.0", 8091), Handler).serve_forever()
