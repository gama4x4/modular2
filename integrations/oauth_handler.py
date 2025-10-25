import threading
import webbrowser
import http.server
import socketserver
from urllib.parse import urlparse, parse_qs

class CombinedOAuthHandler:
    def __init__(self, redirect_uri="http://localhost:8123"):
        self.redirect_uri = redirect_uri
        self.code = None
        self.httpd = None
        self.thread = None

    def start_oauth_server(self):
        class OAuthRedirectHandler(http.server.SimpleHTTPRequestHandler):
            def do_GET(inner_self):
                parsed = urlparse(inner_self.path)
                params = parse_qs(parsed.query)
                self.code = params.get("code", [None])[0]
                inner_self.send_response(200)
                inner_self.send_header("Content-type", "text/html")
                inner_self.end_headers()
                inner_self.wfile.write(b"<h2>Autorizacao recebida. Pode fechar essa aba.</h2>")
                if self.httpd:
                    threading.Thread(target=self.httpd.shutdown).start()

        self.httpd = socketserver.TCPServer(("localhost", 8123), OAuthRedirectHandler)
        self.thread = threading.Thread(target=self.httpd.serve_forever)
        self.thread.start()

    def open_browser_for_auth(self, client_id, auth_url, state=None):
        url = f"{auth_url}?response_type=code&client_id={client_id}&redirect_uri={self.redirect_uri}"
        if state:
            url += f"&state={state}"
        webbrowser.open(url)

    def wait_for_code(self, timeout=60):
        self.thread.join(timeout=timeout)
        return self.code
