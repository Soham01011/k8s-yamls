Absolutely, Soham. Let's rebuild the whole setup step-by-step—keeping it clean, secure, and Istio-ready.

---

## ✅ Step 1: Directory Structure

Here’s how we’ll organize the project:

```
custom-idp/
├── main.py
├── keys/
│   ├── private.pem
│   ├── public.pem
│   └── jwks.json
├── Dockerfile
├── requirements.txt
└── k8s/
    ├── deployment.yaml
    ├── service.yaml
    └── virtualservice.yaml
```

---

## 🔐 Step 2: Generate RSA Keys & JWKS

From `custom-idp/`:

```bash
mkdir keys
openssl genrsa -out keys/private.pem 2048
openssl rsa -in keys/private.pem -pubout -out keys/public.pem
```

Then use Python to generate the JWKS:

```python
# generate_jwks.py
from jwcrypto import jwk
import json

with open("keys/public.pem", "rb") as f:
    key = jwk.JWK.from_pem(f.read())
    key_obj = json.loads(key.export(private_key=False))
    key_obj["kid"] = "my-rsa-key"  # Static key ID
    with open("keys/jwks.json", "w") as out:
        json.dump({"keys": [key_obj]}, out)
```

Run it:

```bash
pip install jwcrypto
python generate_jwks.py
```

---

## ⚙️ Step 3: FastAPI App (`main.py`)

```python
from fastapi import FastAPI, Form
from fastapi.responses import JSONResponse
from jose import jwt
from datetime import datetime, timedelta
import json

app = FastAPI()

@app.get("/")
def read_root():
    return {"msg": "Custom IdP is running"}

@app.get("/.well-known/jwks.json")
def get_jwks():
    with open("keys/jwks.json") as f:
        return JSONResponse(content=json.load(f))

@app.post("/login")
def login(username: str = Form(...), password: str = Form(...)):
    # Basic hardcoded credentials
    if username != "admin" or password != "password":
        return JSONResponse(status_code=401, content={"error": "Invalid credentials"})

    with open("keys/private.pem") as f:
        private_key = f.read()

    payload = {
        "sub": username,
        "iss": "https://auth.192.168.1.247.nip.io",
        "iat": datetime.utcnow(),
        "exp": datetime.utcnow() + timedelta(minutes=30),
    }

    token = jwt.encode(payload, private_key, algorithm="RS256", headers={"kid": "my-rsa-key"})
    return {"access_token": token, "token_type": "bearer"}
```

---

## 📦 Step 4: `requirements.txt`

```txt
fastapi
uvicorn
python-jose
jwcrypto
```

---

## 🐳 Step 5: Dockerfile

```Dockerfile
FROM python:3.10-slim

WORKDIR /app
COPY . /app

RUN pip install --no-cache-dir -r requirements.txt

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "80"]
```

Build and push it:

```bash
docker build -t sohamdalvi1011/custom-idp:v1 .
docker push sohamdalvi1011/custom-idp:v1
```

---

## ☸️ Step 6: K8s Deployment (in `k8s/deployment.yaml`)

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: custom-idp
  namespace: default
spec:
  replicas: 1
  selector:
    matchLabels:
      app: custom-idp
  template:
    metadata:
      labels:
        app: custom-idp
    spec:
      containers:
      - name: custom-idp
        image: sohamdalvi1011/custom-idp:v1
        ports:
        - containerPort: 80
```

---

## ☸️ Step 7: Service & VirtualService

```yaml
# service.yaml
apiVersion: v1
kind: Service
metadata:
  name: custom-idp
  namespace: default
spec:
  selector:
    app: custom-idp
  ports:
  - port: 80
    targetPort: 80
```

```yaml
# virtualservice.yaml
apiVersion: networking.istio.io/v1beta1
kind: VirtualService
metadata:
  name: custom-idp
  namespace: default
spec:
  hosts:
  - "auth.192.168.1.247.nip.io"
  gateways:
  - istio-system/istio-ingressgateway
  http:
  - match:
    - uri:
        prefix: /
    route:
    - destination:
        host: custom-idp
        port:
          number: 80
```

---

## 🔐 Final Step: RequestAuthentication

```yaml
apiVersion: security.istio.io/v1
kind: RequestAuthentication
metadata:
  name: rng-auth
  namespace: default
spec:
  selector:
    matchLabels:
      app: rng-app
  jwtRules:
  - issuer: "https://auth.192.168.1.247.nip.io"
    jwksUri: "http://auth.192.168.1.247.nip.io/.well-known/jwks.json"
```

---

Let me know and I’ll package everything into a `.zip`, or help you roll it out step-by-step with your operator-driven cluster. Want me to regenerate the full folder structure for you too?
