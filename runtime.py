from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs

hostName = "192.168.1.107"
serverPort = 10001

class MyServer(BaseHTTPRequestHandler):
    def do_GET(self):
        print(self.path)
        query = parse_qs(urlparse(self.path).query)
        print(query)
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(bytes("good connection", "utf-8"))


if __name__ == "__main__":
    webServer = HTTPServer((hostName, 10001), MyServer)
    print("Server started with ip http://{0}:{1}".format(hostName, serverPort))

    try:
        webServer.serve_forever()
    except KeyboardInterrupt:
        pass

    webServer.server_close()
    print("Server stopped")

