"""Static file server, shaping API, and stroke-save endpoint for the jayasree demo.

Bound to 0.0.0.0 (not just localhost) so a tablet on the same Wi-Fi can open
tools/stroke-recorder.html against this machine and, via
`/api/save-strokes/<code>`, save recorded strokes straight into this repo's
`stroke-data.<code>.raw.json` - no downloading a file on the tablet and
copying it back by hand.
"""

from __future__ import annotations

import errno
import json
import socket
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse

#: How many ports past the requested one to try before giving up - covers
#: "left yesterday's `make demo` running" and "something else is on 8000"
#: without searching forever if the whole range happens to be occupied.
_MAX_PORT_ATTEMPTS = 20

_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT / "python" / "src"))

from jayasree import shape_word  # noqa: E402
from jayasree.languages import LANGUAGES, data_paths, language_by_code  # noqa: E402

FONT_PATH = _REPO_ROOT / "python" / "tests" / "fixtures" / "Manjari-Regular.ttf"

#: Recording strokes over Wi-Fi (tools/stroke-recorder.js's "Save to
#: server", see docs/languages/hi/labeling-worklist.md's "Using the stroke
#: recorder") is the whole point of binding this server to 0.0.0.0 rather
#: than just localhost - a tablet on the same network can trace strokes and
#: have them land directly in this repo's stroke-data.<code>.raw.json, no
#: download/AirDrop/copy round-trip. One process-wide lock since
#: ThreadingHTTPServer serves concurrent requests on separate threads and
#: two overlapping writes to the same file would otherwise race.
_SAVE_LOCK = threading.Lock()
#: Hard cap on a single save's request body - generous for even a large,
#: fully-recorded language's stroke-data.raw.json (Malayalam's is ~1.5MB),
#: just a sanity bound against something going wrong on the client end.
_MAX_SAVE_BODY = 32 * 1024 * 1024

_CONTENT_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".js": "application/javascript",
    ".css": "text/css",
    ".json": "application/json",
    ".svg": "image/svg+xml",
    ".gif": "image/gif",
}


class DemoHandler(BaseHTTPRequestHandler):
    """HTTP request handler for static files and the /api/shape/ endpoint."""

    def do_GET(self) -> None:
        """Handle GET requests, routing to static or shape handler."""
        parsed = urlparse(self.path)
        if parsed.path.startswith("/api/shape/"):
            self._handle_shape(unquote(parsed.path[len("/api/shape/") :]))
            return
        self._serve_static(parsed.path)

    def do_POST(self) -> None:
        """Handle POST requests - only /api/save-strokes/<code> exists today."""
        parsed = urlparse(self.path)
        if parsed.path.startswith("/api/save-strokes/"):
            self._handle_save_strokes(unquote(parsed.path[len("/api/save-strokes/") :]))
            return
        self.send_error(404)

    def _handle_save_strokes(self, code: str) -> None:
        """Write a full stroke library to `code`'s stroke-data.raw.json on disk.

        Body is the same `{clusterStr: {strokes: [...]}, ...}` object
        tools/stroke-recorder.js's Export already builds - this endpoint
        just writes it to disk instead of triggering a browser download, so
        strokes recorded from a tablet land directly in this repo on the
        machine running this server. Overwrites the whole file (matching
        how the recorder always exports its complete merged session, not a
        diff), written atomically (temp file + rename) so a crash or a
        second overlapping request can't corrupt the committed file.
        """
        try:
            lang = language_by_code(code)
        except ValueError as exc:
            self._send_json(404, {"error": str(exc)})
            return

        length = int(self.headers.get("Content-Length", 0))
        if length <= 0 or length > _MAX_SAVE_BODY:
            self._send_json(400, {"error": f"invalid Content-Length: {length}"})
            return
        raw = self.rfile.read(length)

        try:
            strokes = json.loads(raw)
        except json.JSONDecodeError as exc:
            self._send_json(400, {"error": f"invalid JSON: {exc}"})
            return
        if not isinstance(strokes, dict):
            self._send_json(400, {"error": "expected a JSON object of clusterStr -> {strokes}"})
            return

        out_path = data_paths(lang).stroke_data_raw
        text = json.dumps(strokes, ensure_ascii=False, indent=2)
        with _SAVE_LOCK:
            tmp_path = out_path.with_suffix(out_path.suffix + ".tmp")
            tmp_path.write_text(text, encoding="utf-8")
            tmp_path.replace(out_path)

        self._send_json(
            200,
            {
                "saved": True,
                "path": str(out_path.relative_to(_REPO_ROOT)),
                "clusters": len(strokes),
            },
        )

    def _send_json(self, status: int, payload: dict) -> None:
        """Write a JSON response with the given status code."""
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(body)

    def _serve_static(self, path: str) -> None:
        """Serve a file from the repo root, rejecting path-traversal attempts."""
        rel = path.lstrip("/") or "index.html"
        # Mirror GitHub Pages' directory-index behavior for the demo URL.
        if rel == "demo" or rel == "demo/":
            rel = "demo/index.html"
        file_path = (_REPO_ROOT / rel).resolve()

        # Don't serve anything outside the repo root.
        if _REPO_ROOT not in file_path.parents and file_path != _REPO_ROOT:
            self.send_error(403)
            return
        if not file_path.is_file():
            self.send_error(404)
            return

        self.send_response(200)
        self.send_header(
            "Content-Type",
            _CONTENT_TYPES.get(file_path.suffix, "application/octet-stream"),
        )
        self.end_headers()
        self.wfile.write(file_path.read_bytes())

    def _handle_shape(self, word: str) -> None:
        """Shape *word* with HarfBuzz and return StrokeTrace JSON."""
        try:
            trace = shape_word(word, FONT_PATH)
            self._send_json(200, trace)
        except ValueError as exc:
            self._send_json(400, {"error": str(exc)})

    def log_message(self, format: str, *args: object) -> None:
        """Suppress default access-log output."""


def _bind_first_free_port(preferred_port: int) -> tuple[ThreadingHTTPServer, int]:
    """Bind to `preferred_port`, or the next free one if it's already in use.

    A previous `make demo` you forgot to Ctrl+C, or anything else already
    listening on 8000, would otherwise just crash this with a raw
    `OSError: [Errno 98] Address already in use` traceback - annoying when
    all you actually want is *a* working server, not that exact port
    (nothing else in this project hardcodes 8000; the URLs printed below
    always reflect whatever port is actually bound).

    Parameters
    ----------
    preferred_port : int
        The port to try first (from argv, or the 8000 default).

    Returns
    -------
    tuple[ThreadingHTTPServer, int]
        The bound server and the port it actually landed on.
    """
    for port in range(preferred_port, preferred_port + _MAX_PORT_ATTEMPTS):
        try:
            return ThreadingHTTPServer(("0.0.0.0", port), DemoHandler), port
        except OSError as exc:
            if exc.errno != errno.EADDRINUSE:
                raise
            print(f"Port {port} is already in use, trying {port + 1}...", file=sys.stderr)
    raise SystemExit(
        f"Ports {preferred_port}-{preferred_port + _MAX_PORT_ATTEMPTS - 1} are all in use - "
        f"pass a different starting port: python demo/serve.py <port>"
    )


def _detect_lan_ip() -> str:
    """Return this machine's outbound-facing IP, not just its hostname's.

    `socket.gethostbyname(socket.gethostname())` resolves via /etc/hosts
    first - on Debian/Ubuntu (WSL included), that maps the hostname to
    127.0.1.1, a loopback address useless to any other device on the
    network. Opening a UDP "connection" (no packet actually sent - UDP has
    no handshake) to a public address and reading back the local endpoint
    the OS picked is the standard way to ask "which of my interfaces would
    traffic actually leave from," without depending on hostname/hosts-file
    configuration at all.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as probe:
        try:
            probe.connect(("8.8.8.8", 80))
            return probe.getsockname()[0]
        except OSError:
            return "127.0.0.1"


if __name__ == "__main__":
    requested_port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    server, port = _bind_first_free_port(requested_port)
    local_ip = _detect_lan_ip()
    print(f"jayasree demo running at http://127.0.0.1:{port}/demo/")
    print("On your tablet (same Wi-Fi), one link per registered language")
    print(
        "(?lang=<code> tells the recorder which glyph-data*.json to fetch"
        " automatically - see tools/stroke-recorder.js's applyLangParam):"
    )
    for lang in sorted(LANGUAGES.values(), key=lambda spec: spec.name):
        print(
            f"  {lang.name}: http://{local_ip}:{port}/tools/stroke-recorder.html?lang={lang.code}"
        )
    print("Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
