import http.server
import json
import os
from dotenv import load_dotenv

load_dotenv()

PORT = 8888

class DynamicSOCServerHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory="web_demo", **kwargs)

    def do_GET(self):
        if self.path.startswith("/api/config"):
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Cache-Control", "no-store, no-cache, must-revalidate")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()

            provider = os.getenv("LLM_PROVIDER", "google").upper()
            model_name = os.getenv("LLM_MODEL_NAME", "gemini-2.5-flash")
            
            config_data = {
                "provider": provider,
                "model_name": model_name,
                "display_name": f"{provider} ({model_name})"
            }

            self.wfile.write(json.dumps(config_data).encode("utf-8"))
        else:
            super().do_GET()

class ReusableThreadingHTTPServer(http.server.ThreadingHTTPServer):
    allow_reuse_address = True

def run():
    server_address = ('', PORT)
    httpd = ReusableThreadingHTTPServer(server_address, DynamicSOCServerHandler)
    print(f"🚀 VinBank AI SOC Console Server running at http://localhost:{PORT}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping server...")
        httpd.server_close()

if __name__ == '__main__':
    run()
