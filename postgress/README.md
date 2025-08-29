
# PG Operator and Cluster Docs

A walkthrough to how to setup a pg Cluster in the k8s cluster. While making this doc it being made in k3s.

Currently my setup is : 
- k3s SNO setup
- Istio side car 




## Deployment

I have followed the official CNPG docs for deployment and testing : 
[CloudNativePG](https://cloudnative-pg.io/documentation/1.27/)

---

### So lets start with the deployment and setup

The operator can be installed like any other resource in Kubernetes, through a YAML manifest applied via `kubectl`.

You can install the latest operator manifest for this minor release as follows:

```bash
kubectl apply --server-side -f \
  https://raw.githubusercontent.com/cloudnative-pg/cloudnative-pg/release-1.27/releases/cnpg-1.27.0.yaml

```

This manifest file will install the te required CRD's for the postgress cluster and its operator, also after that it will spin up the operator pod in `cnpg-system` namespace. Make sure it comes in running state once pod is Initialized. 

Once this is set now you can simply spin the postgress clusters with a very small yaml like this : 

```yaml
# example-pg-cluster.yaml 
apiVersion: postgresql.cnpg.io/v1
kind: Cluster
metadata:
  name: cluster-example
spec:
  instances: 3

  storage:
    size: 1Gi
```

Then apply this yaml by : 
``` bash
kubectl -f apply mple-pg-cluster.yaml
```

This will create the 3 pods in the defualt namespace with Primary and Secondary pods of the cluster.
So now lets understand how this will work in depth : 


### 🔑 Connection Endpoints CNPG Creates

For a cluster named `cluster-example` in namespace `default` :

1. **Primary Service** (for read-write queries):

   ```
   cluster-example-rw.<namespace>.svc.cluster.local
   ```

2. **Replica Service** (for read-only queries, load-balanced across replicas):

   ```
   cluster-example-ro.<namespace>.svc.cluster.local
   ```

3. **Any-node Service** (connects randomly to any instance):

   ```
   cluster-example.<namespace>.svc.cluster.local
   ```

---

### 🛠️ Example Connection String

If you set `POSTGRES_USER=postgres` and `POSTGRES_DB=postgres` (defaults unless overridden in the `Cluster` spec), and assuming your CNPG created a secret called `cluster-example-superuser` with the password:

```
postgresql://postgres:<password>@cluster-example-rw.taskify.svc.cluster.local:5432/postgres
```

---

👉 To confirm the password:

```bash
kubectl get secret cluster-example-superuser -n taskify -o jsonpath='{.data.password}' | base64 -d
```

---

This will also create the username and password automatically by the operator itself and will deploy it too. But then lets say you want to create your own username and password then you can do bootstraped start where in you can specify configuration for postgress db to laod with. 

Below here is an example to set your own username and password:

k8s secret: 

```yaml
# postgress username and password
data:
  username: YXBw           # based 64 encoded
  password: cGFzc3dvcmQ=   # based 64 encoded
kind: Secret
metadata:
  name: app-secret
type: kubernetes.io/basic-auth
```

Once this secret is added then you can apply the cluster file which will use the same secret to create username and password.

```yaml
apiVersion: postgresql.cnpg.io/v1
kind: Cluster
metadata:
  name: cluster-example-initdb
spec:
  instances: 3

  bootstrap:
    initdb:
      database: app
      owner: app
      secret:
        name: app-secret

  storage:
    size: 1Gi
```

Apply this yaml and your cluster with the credentiasl will be created.

Here below is a sample architecture
![Logo](https://cloudnative-pg.io/documentation/1.27/images/architecture-in-k8s.png)

---

### FOR MORE EXEPRIMENTATION VISIT THE CNPG DOCS webiste 