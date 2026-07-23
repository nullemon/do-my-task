"""Local web app for webscan.

Run it, open the printed URL in your browser, fill in the form, hit Scan.
The browser is just the UI — the actual requests are made by THIS local
process (so it can set Host / spoof headers and isn't blocked by CORS).

    python3 -m webscan.server           # then open http://127.0.0.1:8765

Bind stays on localhost by default so the tool isn't exposed to your network.
"""

from __future__ import annotations

import argparse
import json
import os
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from . import ai, bypass
from .bypass import BypassConfig
from .engine import ScanConfig, scan

_STATIC_DIR = os.path.join(os.path.dirname(__file__), "webui")

_CONTENT_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".css": "text/css; charset=utf-8",
}


class Handler(BaseHTTPRequestHandler):
    server_version = "webscan/1.0"

    def log_message(self, fmt, *args):  # keep the console quiet
        pass

    # --- static files -----------------------------------------------------
    def do_GET(self):
        path = self.path.split("?", 1)[0]
        if path in ("/", "/index.html"):
            return self._send_static("index.html")
        if path in ("/app.js", "/styles.css"):
            return self._send_static(path.lstrip("/"))
        self.send_error(404, "Not found")

    def _send_static(self, name):
        fp = os.path.join(_STATIC_DIR, name)
        if not os.path.isfile(fp):
            return self.send_error(404, "Not found")
        with open(fp, "rb") as fh:
            data = fh.read()
        ext = os.path.splitext(name)[1]
        self.send_response(200)
        self.send_header("Content-Type", _CONTENT_TYPES.get(ext, "application/octet-stream"))
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    # --- POST routing -----------------------------------------------------
    def do_POST(self):
        route = self.path.split("?", 1)[0]
        payload = self._read_json()
        if payload is None:
            return  # error already sent
        if route == "/api/scan":
            return self._stream(scan(self._config_from_payload(payload)))
        if route == "/api/bypass":
            return self._stream(bypass.run(self._bypass_config_from_payload(payload)))
        if route == "/api/analyze":
            return self._analyze(payload)
        self.send_error(404, "Not found")

    def _read_json(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
            return json.loads(self.rfile.read(length) or b"{}")
        except (ValueError, json.JSONDecodeError):
            self.send_error(400, "Bad JSON")
            return None

    def _stream(self, events):
        """Stream an event generator as newline-delimited JSON."""
        self.send_response(200)
        self.send_header("Content-Type", "application/x-ndjson")
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Accel-Buffering", "no")
        self.end_headers()
        try:
            for event in events:
                self.wfile.write((json.dumps(event) + "\n").encode("utf-8"))
                self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError):
            pass  # browser navigated away / cancelled
        except Exception as e:  # surface engine errors to the UI
            try:
                self.wfile.write((json.dumps({"type": "fatal", "error": str(e)}) + "\n")
                                 .encode("utf-8"))
                self.wfile.flush()
            except OSError:
                pass

    def _analyze(self, payload):
        """Run the optional AI analysis; return a single JSON object."""
        baseline = payload.get("baseline") or {}
        bypasses = payload.get("bypasses") or []
        api_key = payload.get("api_key") or None
        try:
            result = ai.analyze(baseline, bypasses, api_key=api_key)
            body = json.dumps({"ok": True, "analysis": result}).encode("utf-8")
            status = 200
        except ai.AIUnavailable as e:
            body = json.dumps({"ok": False, "error": str(e),
                               "needs_setup": True}).encode("utf-8")
            status = 200
        except Exception as e:
            body = json.dumps({"ok": False, "error": str(e)}).encode("utf-8")
            status = 200
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    @staticmethod
    def _config_from_payload(p: dict) -> ScanConfig:
        targets = p.get("targets") or []
        if isinstance(targets, str):
            targets = [t for t in targets.replace(",", "\n").splitlines() if t.strip()]
        custom = p.get("custom_paths") or []
        if isinstance(custom, str):
            custom = [c for c in custom.splitlines() if c.strip()]
        headers = p.get("extra_headers") or {}
        if isinstance(headers, str):
            headers = _parse_header_lines(headers)
        return ScanConfig(
            targets=targets,
            base_path=p.get("base_path") or "/",
            wordlist=p.get("wordlist") or "common",
            custom_paths=custom,
            concurrency=int(p.get("concurrency") or 20),
            timeout=float(p.get("timeout") or 8.0),
            method=(p.get("method") or "GET").upper(),
            follow_redirects=bool(p.get("follow_redirects")),
            verify_tls=bool(p.get("verify_tls", True)),
            delay=float(p.get("delay") or 0.0),
            user_agent=p.get("user_agent") or ScanConfig.__dataclass_fields__["user_agent"].default,
            host_header=p.get("host_header") or "",
            spoof_ip=p.get("spoof_ip") or "",
            extra_headers=headers,
        )

    @staticmethod
    def _bypass_config_from_payload(p: dict) -> BypassConfig:
        headers = p.get("extra_headers") or {}
        if isinstance(headers, str):
            headers = _parse_header_lines(headers)
        return BypassConfig(
            target_url=(p.get("target_url") or "").strip(),
            spoof_ip=(p.get("spoof_ip") or "127.0.0.1").strip(),
            host_header=(p.get("host_header") or "").strip(),
            extra_headers=headers,
            concurrency=int(p.get("concurrency") or 20),
            timeout=float(p.get("timeout") or 8.0),
            verify_tls=bool(p.get("verify_tls", True)),
            user_agent=p.get("user_agent")
            or BypassConfig.__dataclass_fields__["user_agent"].default,
        )


def _parse_header_lines(text: str) -> dict:
    out = {}
    for line in text.splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            if k.strip():
                out[k.strip()] = v.strip()
    return out


def serve(host="127.0.0.1", port=8765, open_browser=True):
    httpd = ThreadingHTTPServer((host, port), Handler)
    url = f"http://{host}:{port}"
    print(f"\n  webscan running at  {url}")
    print("  (scans run from THIS machine — for sites you own/are authorized to test)")
    print("  press Ctrl+C to stop\n")
    if open_browser:
        threading.Timer(0.6, lambda: webbrowser.open(url)).start()
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n  stopped.")
    finally:
        httpd.server_close()


def main(argv=None):
    ap = argparse.ArgumentParser(prog="webscan.server", description="webscan web UI")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--no-browser", action="store_true")
    args = ap.parse_args(argv)
    serve(args.host, args.port, open_browser=not args.no_browser)


if __name__ == "__main__":
    main()
