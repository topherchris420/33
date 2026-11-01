"""Serve the repository root for local laboratory development: python tools/serve_lab.py [port]

Then open http://localhost:8000/lab/ . Responses carry Cache-Control: no-store so edits
show up immediately. This is a static file server only; it serves files and nothing else.
"""

import functools
import http.server
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class NoStoreHandler(http.server.SimpleHTTPRequestHandler):
    extensions_map = {**http.server.SimpleHTTPRequestHandler.extensions_map,
                      ".mjs": "text/javascript", ".js": "text/javascript", ".woff2": "font/woff2"}

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def log_message(self, *args):
        pass


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    port = int(argv[0]) if argv else 8000
    handler = functools.partial(NoStoreHandler, directory=str(ROOT))
    with http.server.ThreadingHTTPServer(("127.0.0.1", port), handler) as server:
        print(f"Serving {ROOT} at http://localhost:{port}/lab/")
        server.serve_forever()


if __name__ == "__main__":
    main()
