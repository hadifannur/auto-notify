import os
import threading
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
import requests
from urllib.parse import urlparse, parse_qs
from dotenv import load_dotenv
import re

load_dotenv()

APP_ID = os.getenv("APP_ID")
APP_SECRET = os.getenv("APP_SECRET")
REDIRECT_URI = "http://localhost:8000/"

# Use Lark International endpoints
TOKEN_URL = "https://open.larksuite.com/open-apis/authen/v1/access_token"
AUTH_URL = (
    f"https://open.larksuite.com/open-apis/authen/v1/index?app_id={APP_ID}"
    f"&redirect_uri={REDIRECT_URI}"
    f"&response_type=code"
    f"&state=state"
)

token_result = {}

def fetch_user_access_token(auth_code, redirect_uri):
    headers = {"Content-Type": "application/json"}
    data = {
        "app_id": APP_ID,
        "app_secret": APP_SECRET,
        "grant_type": "authorization_code",
        "code": auth_code,
        "redirect_uri": redirect_uri
    }
    response = requests.post(TOKEN_URL, json=data, headers=headers)
    response.raise_for_status()
    return response.json()

def update_env_user_access_token(new_token, env_path=".env"):
    with open(env_path, "r", encoding="utf-8") as f:
        content = f.read()
    if re.search(r"^USER_ACCESS_TOKEN=.+", content, re.MULTILINE):
        content = re.sub(r"^USER_ACCESS_TOKEN=.+", f"USER_ACCESS_TOKEN={new_token}", content, flags=re.MULTILINE)
    else:
        if not content.endswith("\n"): content += "\n"
        content += f"USER_ACCESS_TOKEN={new_token}\n"
    with open(env_path, "w", encoding="utf-8") as f:
        f.write(content)

class OAuthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)
        if "code" in params:
            code = params["code"][0]
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(b"<h1>Authorization successful! You can close this window.</h1>")
            # Exchange code for token
            try:
                result = fetch_user_access_token(code, REDIRECT_URI)
                global token_result
                token_result = result
            except Exception as e:
                print(f"Error exchanging code: {e}")
        else:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b"<h1>Authorization code not found.</h1>")

def run_server():
    server = HTTPServer(('localhost', 8000), OAuthHandler)
    print("Listening on http://localhost:8000 ...")
    server.handle_request()  # handle one request then exit

if __name__ == "__main__":
    print("Opening browser for Lark OAuth login...")
    threading.Thread(target=run_server, daemon=True).start()
    webbrowser.open(AUTH_URL)
    # Wait for the token to be set
    import time
    for _ in range(120):  # wait up to 120 seconds
        if token_result:
            break
        time.sleep(1)
    if token_result:
        user_token = token_result.get("data", {}).get("access_token") or token_result.get("access_token")
        print("\n--- User Access Token ---")
        print(user_token)
        update_env_user_access_token(user_token, os.path.join(os.path.dirname(__file__), ".env"))
        print("USER_ACCESS_TOKEN updated in .env")
    else:
        print("Timeout waiting for authorization code.")
