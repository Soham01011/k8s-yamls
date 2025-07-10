import kopf
from kubernetes import client, config

# Use in-cluster config when running in Kubernetes
config.load_incluster_config()
# config.load_kube_config()  # Uncomment for local testing

@kopf.on.create('soham.dev', 'v1', 'myapps')
def create_myapp(spec, name, namespace, **kwargs):
    app_image = spec.get('appImage', 'sohamdalvi1011/random-num:v1')
    mongo_image = spec.get('mongoImage', 'mongo:6')
    app_pvc_size = spec.get('appPVCSize', '1Gi')
    mongo_pvc_size = spec.get('mongoPVCSize', '1Gi')
    app_replicas = spec.get('appReplicas', 1)
    mongo_replicas = spec.get('mongoReplicas', 1)

    core = client.CoreV1Api()
    apps = client.AppsV1Api()

    # 1. PVC for App
    core.create_namespaced_persistent_volume_claim(namespace, client.V1PersistentVolumeClaim(
        metadata=client.V1ObjectMeta(name=f'{name}-app-pvc'),
        spec=client.V1PersistentVolumeClaimSpec(
            access_modes=["ReadWriteOnce"],
            resources=client.V1ResourceRequirements(
                requests={"storage": app_pvc_size}
            )
        )
    ))

    # 2. PVC for MongoDB
    core.create_namespaced_persistent_volume_claim(namespace, client.V1PersistentVolumeClaim(
        metadata=client.V1ObjectMeta(name=f'{name}-mongo-pvc'),
        spec=client.V1PersistentVolumeClaimSpec(
            access_modes=["ReadWriteOnce"],
            resources=client.V1ResourceRequirements(
                requests={"storage": mongo_pvc_size}
            )
        )
    ))

    # 3. MongoDB Deployment
    apps.create_namespaced_deployment(namespace, client.V1Deployment(
        metadata=client.V1ObjectMeta(name=f'{name}-mongodb'),
        spec=client.V1DeploymentSpec(
            replicas=mongo_replicas,
            selector={"matchLabels": {"app": f'{name}-mongodb'}},
            template=client.V1PodTemplateSpec(
                metadata=client.V1ObjectMeta(labels={"app": f'{name}-mongodb'}),
                spec=client.V1PodSpec(
                    containers=[client.V1Container(
                        name="mongodb",
                        image=mongo_image,
                        ports=[client.V1ContainerPort(container_port=27017)],
                        volume_mounts=[client.V1VolumeMount(
                            name="mongo-storage",
                            mount_path="/data/db"
                        )]
                    )],
                    volumes=[client.V1Volume(
                        name="mongo-storage",
                        persistent_volume_claim=client.V1PersistentVolumeClaimVolumeSource(
                            claim_name=f'{name}-mongo-pvc'
                        )
                    )]
                )
            )
        )
    ))

    # 4. MongoDB Service
    core.create_namespaced_service(namespace, client.V1Service(
        metadata=client.V1ObjectMeta(name=f'{name}-mongodb'),
        spec=client.V1ServiceSpec(
            selector={"app": f'{name}-mongodb'},
            ports=[client.V1ServicePort(port=27017, target_port=27017)],
            type="ClusterIP"
        )
    ))

    # 5. App Deployment
    apps.create_namespaced_deployment(namespace, client.V1Deployment(
        metadata=client.V1ObjectMeta(name=f'{name}-app'),
        spec=client.V1DeploymentSpec(
            replicas=app_replicas,
            selector={"matchLabels": {"app": f'{name}-app'}},
            template=client.V1PodTemplateSpec(
                metadata=client.V1ObjectMeta(labels={"app": f'{name}-app'}),
                spec=client.V1PodSpec(
                    containers=[client.V1Container(
                        name="random-num",
                        image=app_image,
                        ports=[client.V1ContainerPort(container_port=3000)],
                        env=[client.V1EnvVar(
                            name="MONGO_URL",
                            value=f"mongodb://{name}-mongodb:27017"
                        )],
                        volume_mounts=[client.V1VolumeMount(
                            name="app-storage",
                            mount_path="/app/data"
                        )]
                    )],
                    volumes=[client.V1Volume(
                        name="app-storage",
                        persistent_volume_claim=client.V1PersistentVolumeClaimVolumeSource(
                            claim_name=f'{name}-app-pvc'
                        )
                    )]
                )
            )
        )
    ))

    # 6. App Service
    core.create_namespaced_service(namespace, client.V1Service(
        metadata=client.V1ObjectMeta(name=f'{name}-svc'),
        spec=client.V1ServiceSpec(
            selector={"app": f'{name}-app'},
            ports=[client.V1ServicePort(port=80, target_port=3000)],
            type="ClusterIP"
        )
    ))

    return {"message": f"MyApp '{name}' successfully deployed with app + MongoDB."}
