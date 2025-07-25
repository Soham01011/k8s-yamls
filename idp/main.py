from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from jose import jwt
from datetime import datetime, timedelta
import json
import os

app = FastAPI()

# Jinja2 templates for rendering HTML pages
templates = Jinja2Templates(directory="templates")


@app.get("/")
def root():
    return {"message": "Welcome to Soham's Custom IdP"}


@app.get("/.well-known/jwks.json")
def get_jwks():
    """Serve the public keys for JWT verification"""
    with open("keys/jwks.json", "r") as f:
        return JSONResponse(content=json.load(f))


@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    """Show the login page"""
    return templates.TemplateResponse("login.html", {"request": request})


@app.post("/login", response_class=HTMLResponse)
def login_submit(request: Request, username: str = Form(...), password: str = Form(...)):
    """Authenticate and issue a JWT"""
    # Hardcoded credentials
    if username != "admin" or password != "password":
        return HTMLResponse("<h3>Invalid credentials</h3>", status_code=401)

    # Load RSA private key
    with open("keys/private.pem", "r") as f:
        private_key = f.read()

    now = datetime.utcnow()
    payload = {
        "sub": username,
        "iss": "https://auth.192.168.1.247.nip.io",
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=30)).timestamp()),
    }

    headers = {"kid": "my-rsa-key"}
    token = jwt.encode(payload, private_key, algorithm="RS256", headers=headers)

    html = f"""
    <html><body>
    <h2>Login successful!</h2>
    <p><strong>Here is your token:</strong></p>
    <textarea rows="10" cols="90">{token}</textarea><br/><br/>
    <p>Use this token in your requests like this:</p>
    <pre><code>Authorization: Bearer &lt;paste-your-token-here&gt;</code></pre>
    </body></html>
    """
    return HTMLResponse(html)
