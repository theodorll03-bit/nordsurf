"""Liten statisk testserver for nettlesertestene (S3, 16.10.2026): som http.server, men med HTTP Range
(206 Partial Content) slik GitHub Pages har - PMTiles-kartet (docs/geo/*.pmtiles) leses med
range requests og virker ikke mot en server som alltid svarer 200 med hele fila.

Bruk: srv, port = testserver.serve(DOCS); ...; srv.shutdown()"""
import http.server
import os
import re
import socket
import threading
from functools import partial

RANGE_RE = re.compile(r"bytes=(\d*)-(\d*)$")


class RangeHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def send_head(self):
        rng = self.headers.get("Range")
        path = self.translate_path(self.path)
        if not rng or os.path.isdir(path) or not os.path.isfile(path):
            return super().send_head()
        m = RANGE_RE.match(rng.strip())
        size = os.path.getsize(path)
        if not m:
            return super().send_head()
        a, b = m.group(1), m.group(2)
        if a == "":
            start, end = max(0, size - int(b)), size - 1
        else:
            start, end = int(a), (min(int(b), size - 1) if b else size - 1)
        if start >= size or start > end:
            self.send_response(416)
            self.send_header("Content-Range", f"bytes */{size}")
            self.end_headers()
            return None
        f = open(path, "rb")
        f.seek(start)
        self.send_response(206)
        self.send_header("Content-Type", self.guess_type(path))
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
        self.send_header("Content-Length", str(end - start + 1))
        self.send_header("ETag", f'"{int(os.path.getmtime(path))}-{size}"')
        self.end_headers()
        self._remaining = end - start + 1
        return f

    def copyfile(self, source, outputfile):
        n = getattr(self, "_remaining", None)
        if n is None:
            return super().copyfile(source, outputfile)
        self._remaining = None
        while n > 0:
            buf = source.read(min(65536, n))
            if not buf:
                break
            outputfile.write(buf)
            n -= len(buf)


def serve(directory):
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", port), partial(RangeHandler, directory=str(directory)))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, port

# WebGL i headless Chromium (MapLibre): programvare-GPU via SwiftShader. Uten disse flaggene kan nyere
# Chromium nekte WebGL i headless, og kartet blir tomt (S3, 16.10.2026).
WEBGL_ARGS = ["--use-gl=angle", "--use-angle=swiftshader", "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist"]
