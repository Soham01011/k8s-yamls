
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

## Backups

### This is a quick backup and setup, I wont recommend doing backup process for the large databases.

With the current setup that we made you can create a few records in the db to verify that the backup we created has worked.

So lets start with auotmated backups, for this we will use the built in cronjob resource of the kubernets.

Here is the YAML file for it : 
```yaml
# cronjob-pg-bkp.yaml

apiVersion: v1
kind: PersistentVolume
metadata:
  name: pg-backup-pv
  labels:
    type: local
spec:
  storageClassName: manual
  capacity:
    storage: 1Gi
  accessModes:
    - ReadWriteOnce
  hostPath:
    path: /mnt/pg-bkp
---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: app-backup-pvc
  namespace: pg-db
spec:
  storageClassName: manual
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 1Gi
  selector:
    matchLabels:
      type: local
---
apiVersion: batch/v1
kind: CronJob
metadata:
  name: app-db-backup
  namespace: pg-db
spec:
  schedule: "*/2 * * * *"  
  jobTemplate:
    spec:
      template:
        spec:
          restartPolicy: OnFailure
          containers:
            - name: pg-backup
              image: postgres:18
              env:
                - name: PGHOST
                  value: "cluster-example-initdb-rw.pg-db.svc"  
                - name: PGUSER
                  valueFrom:
                    secretKeyRef:
                      name: app-secret
                      key: username
                - name: PGPASSWORD
                  valueFrom:
                    secretKeyRef:
                      name: app-secret
                      key: password
                - name: PGDATABASE
                  value: "app"
              command:
                - /bin/bash
                - -c
                - |
                  set -e
                  echo "Starting pg_dump at $(date)"
                  mkdir -p /backup
                  pg_dump -Fc -f /backup/appdb-$(date +%Y%m%d-%H%M).dump
                  echo "Backup completed at $(date)"
                  find /backup -type f -mtime +7 -delete
              volumeMounts:
                - name: backup-volume
                  mountPath: /backup
          volumes:
            - name: backup-volume
              persistentVolumeClaim:
                claimName: app-backup-pvc
```

This yaml has all of it to create the backup with the pg.dump() command and save the dump to local path storage at /mnt/pg-bkp folder path. This cornjob runns every 2 mins you can change it as per your requirements to backup everyday at any giving time period.

So then apply this given yaml with : 
``` bash
kubectl apply -f cronjob-pg-bkp.yaml
```

Check the cronjob are there and jobs are running by 
``` bash
kubectl get cj 
kubectl get jobs
```

Once the jobs pods are completed thus the dump files are created at the give folder path. Thus we have successfully set the auotmated backup process.

Now we need to mount the dump file into another database. For this we need another postgres pod since the pod of the postgres cluster have the read only permission.

So to create a postgres pod real quick run this command : 
``` bash
 kubectl run pg-restore \
  -n pg-db \
  --image=postgres:18 \
  --restart=Never \
  -- sleep infinity
```

This will create a postgres pod for a temporary purpose of the backup, once the conatiner spins up now we can scp the locally saved dump fiel into the ephimeral storage of the pod : 

```bash
kubectl cp /mnt/pg-bkp/appdb-20251101-0714.dump -n pg-db pg-restore:/tmp/appdb.dum
```

Next exec into the temporary pod of the postgres and run the command to dump the db into the new cluster : 
``` bash
kubectl exec -it -n pg-db pg-restore -- bash
```

Now form the test pod check the connection with new pg database where you want to load the backup files : 

```bash
PGPASSWORD='password' psql -U app -h cluster-example-initdb-rw.pg-db.svc.cluster.local -d app -c '\conninfo
```

If the connection is good then we are good to go for backup 

``` bash
PGPASSWORD='password' pg_restore -U app -h cluster-example-initdb-rw.pg-db.svc.cluster.local -d app -Fc /tmp/appdb.dump
```

And that's it with this we have successfully backed up out pg data to a new database.

---

### FOR MORE EXEPRIMENTATION VISIT THE CNPG DOCS webiste 