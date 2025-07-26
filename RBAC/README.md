

## 📘 Guide: Grant a User (`Bhidu`) Read-Only Access to the `default` Namespace in Kubernetes Using the CSR API

This guide walks through generating a client certificate and configuring `kubectl` for user-level access.

---

### 🔧 Step 1: Generate a Private Key and CSR (Certificate Signing Request)

```bash
openssl genrsa -out bhidu.key 2048
openssl req -new -key bhidu.key -out bhidu.csr -subj "/CN=Bhidu/O=appusers"
```

**Explanation:**

- `bhidu.key` is Bhidu’s private key.

- `bhidu.csr` is a certificate request where:
  
  - `CN=Bhidu` is the Common Name (Kubernetes treats it as the **username**).
  
  - `O=appusers` is the Organization (used for RBAC group binding if needed).

---

### 📤 Step 2: Encode the CSR in Base64 (Required by Kubernetes CSR object)

```bash
cat bhidu.csr | base64 | tr -d '\n' > bhidu.csr.b64
```

> We’re preparing the CSR to embed in a Kubernetes YAML. The `tr -d '\n'` removes line breaks — very important for valid YAML formatting.

---

### 📄 Step 3: Create a Kubernetes CSR Manifest

Create a file named `bhidu-csr.yaml`:

```yaml
apiVersion: certificates.k8s.io/v1
kind: CertificateSigningRequest
metadata:
  name: bhidu-csr
spec:
  request: <PASTE_BASE64_ENCODED_CSR_HERE>
  signerName: kubernetes.io/kube-apiserver-client
  usages:
    - client auth
```

Replace `<PASTE_BASE64_ENCODED_CSR_HERE>` with the content of `bhidu.csr.b64`.

Apply it:

```bash
kubectl apply -f bhidu-csr.yaml
```

---

### ✅ Step 4: Approve the CSR

```bash
kubectl certificate approve bhidu-csr
```

> This mimics a cluster admin's approval for the user to receive a certificate.

---

### 📥 Step 5: Retrieve the Signed Certificate

```bash
kubectl get csr bhidu-csr -o jsonpath='{.status.certificate}' | base64 -d > bhidu.crt
```

> The server-signed certificate is now saved as `bhidu.crt`.

---

### 🌐 Step 6: Set Up Bhidu’s `kubeconfig` (Client Credentials + Cluster Info)

First, extract cluster details dynamically:

```bash
CLUSTER_NAME=$(kubectl config view --minify -o jsonpath='{.clusters[0].name}')
CLUSTER_SERVER=$(kubectl config view --minify -o jsonpath='{.clusters[0].cluster.server}')
CA_CERT=$(kubectl config view --raw --minify -o jsonpath='{.clusters[0].cluster.certificate-authority-data}')
```

Now save the CA certificate locally:

```bash
echo "$CA_CERT" | base64 -d > ca.crt
```

Then configure the kubeconfig:

```bash
kubectl config set-cluster "$CLUSTER_NAME" \
  --server="$CLUSTER_SERVER" \
  --certificate-authority=ca.crt \
  --embed-certs=true \
  --kubeconfig=bhidu.kubeconfig

kubectl config set-credentials Bhidu \
  --client-certificate=bhidu.crt \
  --client-key=bhidu.key \
  --embed-certs=true \
  --kubeconfig=bhidu.kubeconfig

kubectl config set-context bhidu-context \
  --cluster="$CLUSTER_NAME" \
  --user=Bhidu \
  --namespace=default \
  --kubeconfig=bhidu.kubeconfig

kubectl config use-context bhidu-context --kubeconfig=bhidu.kubeconfig
```

---

### 🔐 Step 7: Create an RBAC Role and RoleBinding for Bhidu

Create a file `bhidu-role.yaml`:

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  namespace: default
  name: bhidu-pod-reader
rules:
  - apiGroups: [""]
    resources: ["pods"]
    verbs: ["get", "list", "watch"]

---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: bhidu-binding
  namespace: default
subjects:
  - kind: User
    name: Bhidu
    apiGroup: rbac.authorization.k8s.io
roleRef:
  kind: Role
  name: bhidu-pod-reader
  apiGroup: rbac.authorization.k8s.io
```

Apply it:

```bash
kubectl apply -f bhidu-role.yaml
```

> This grants user `Bhidu` read-only access to pods in the `default` namespace.

---

### 🧪 Step 8: Test Access as Bhidu

```bash
kubectl get pods --kubeconfig=bhidu.kubeconfig
```

You should now see pods in the `default` namespace — but only **read-only**, no create/update/delete rights.

---

## 🎯 Summary

| Component          | Purpose                                     |
| ------------------ | ------------------------------------------- |
| OpenSSL            | Generates key and CSR                       |
| Kubernetes CSR API | Requests and approves a client certificate  |
| kubeconfig         | Allows Bhidu to authenticate to the cluster |
| RBAC Role/Binding  | Restricts Bhidu’s permissions               |

---

Would you like this exported into a Markdown or PDF format for internal documentation? I can generate that next.
