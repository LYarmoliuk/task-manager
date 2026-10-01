from http.server import BaseHTTPRequestHandler, HTTPServer
import sys


class FaultHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        if self.path != "/data":
            self.send_response(404)
            self.end_headers()
            return

        mode = sys.argv[1] if len(sys.argv) > 1 else "ok"

        if mode == "fail":
            self.send_response(503)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"error":"External service unavailable"}')
            return

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(b'{"message":"External service is available"}')

    def log_message(self, format: str, *args: object) -> None:
        print(format % args)


server = HTTPServer(("127.0.0.1", 9001), FaultHandler)

print("Fault server started on http://127.0.0.1:9001")
print(f"Mode: {sys.argv[1] if len(sys.argv) > 1 else 'ok'}")

server.serve_forever()