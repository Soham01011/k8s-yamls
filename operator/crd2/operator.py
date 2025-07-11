import kopf
import kubernetes.client
from kubernetes.client import ApiClient
import yaml

@kopf.on.startup()
def configure(settings: kopf.OperatorSettings, **_):
    settings.persistence.finalizer = 'randomnumbergenerator.operators.sohamdalvi1011.io/finalizer'
    settings.watching.server_timeout = 60
    settings.watching.client_timeout = 60

@kopf.on.create('operators.sohamdalvi1011.io', 'v1', 'randomnumbergenerators')
def create_fn(spec, name, namespace, logger, **kwargs):
    # Create MongoDB resources if enabled
    if spec.get('mongodb', {}).get('enabled', True):
        create_mongodb_resources(spec, name, namespace, logger)
    
    # Create Random Number App resources
    create_app_resources(spec, name, namespace, logger)
    
    return {'message': 'Resources created successfully'}

def create_mongodb_resources(spec, name, namespace, logger):
    mongodb_spec = spec.get('mongodb', {})
    mongo_service_name = f"{name}-mongodb"
    
    # MongoDB PVC
    mongo_pvc = {
        'apiVersion': 'v1',
        'kind': 'PersistentVolumeClaim',
        'metadata': {
            'name': f'{name}-mongodb-pvc',
            'namespace': namespace,
            'labels': {'app': 'mongodb', 'instance': name}
        },
        'spec': {
            'accessModes': ['ReadWriteOnce'],
            'resources': {
                'requests': {
                    'storage': mongodb_spec.get('pvc', {}).get('size', '256Mi')
                }
            }
        }
    }
    
    # MongoDB Deployment
    mongo_deployment = {
        'apiVersion': 'apps/v1',
        'kind': 'Deployment',
        'metadata': {
            'name': mongo_service_name,
            'namespace': namespace,
            'labels': {'app': 'mongodb', 'instance': name}
        },
        'spec': {
            'replicas': mongodb_spec.get('replicaCount', 1),
            'selector': {
                'matchLabels': {'app': 'mongodb', 'instance': name}
            },
            'template': {
                'metadata': {
                    'labels': {'app': 'mongodb', 'instance': name}
                },
                'spec': {
                    'containers': [{
                        'name': 'mongodb',
                        'image': mongodb_spec.get('image', 'mongo:latest'),
                        'ports': [{'containerPort': mongodb_spec.get('port', 27017)}],
                        'volumeMounts': [{
                            'name': 'mongodb-data',
                            'mountPath': '/data/db'
                        }],
                        'resources': mongodb_spec.get('resources', {})
                    }],
                    'volumes': [{
                        'name': 'mongodb-data',
                        'persistentVolumeClaim': {
                            'claimName': f'{name}-mongodb-pvc'
                        }
                    }]
                }
            }
        }
    }
    
    # MongoDB Service
    mongo_service = {
        'apiVersion': 'v1',
        'kind': 'Service',
        'metadata': {
            'name': mongo_service_name,
            'namespace': namespace,
            'labels': {'app': 'mongodb', 'instance': name}
        },
        'spec': {
            'ports': [{
                'port': mongodb_spec.get('service', {}).get('port', 27017),
                'targetPort': mongodb_spec.get('port', 27017)
            }],
            'selector': {'app': 'mongodb', 'instance': name},
            'type': mongodb_spec.get('service', {}).get('type', 'ClusterIP')
        }
    }
    
    api = kubernetes.client.CoreV1Api()
    apps_api = kubernetes.client.AppsV1Api()
    
    # Create MongoDB resources
    kopf.adopt(mongo_pvc)
    kopf.adopt(mongo_deployment)
    kopf.adopt(mongo_service)
    
    api.create_namespaced_persistent_volume_claim(namespace, mongo_pvc)
    apps_api.create_namespaced_deployment(namespace, mongo_deployment)
    api.create_namespaced_service(namespace, mongo_service)
    logger.info(f"MongoDB resources created with service name: {mongo_service_name}")

def create_app_resources(spec, name, namespace, logger):
    app_spec = spec.get('app', {})
    mongo_service_name = f"{name}-mongodb"
    mongo_port = spec.get('mongodb', {}).get('service', {}).get('port', 27017)
    
    # App PVC
    app_pvc = {
        'apiVersion': 'v1',
        'kind': 'PersistentVolumeClaim',
        'metadata': {
            'name': f'{name}-app-pvc',
            'namespace': namespace,
            'labels': {'app': 'random-number', 'instance': name}
        },
        'spec': {
            'accessModes': ['ReadWriteOnce'],
            'resources': {
                'requests': {
                    'storage': app_spec.get('pvc', {}).get('size', '1Gi')
                }
            }
        }
    }
    
    # App Deployment with automatic MongoDB URI
    app_deployment = {
        'apiVersion': 'apps/v1',
        'kind': 'Deployment',
        'metadata': {
            'name': f'{name}-app',
            'namespace': namespace,
            'labels': {'app': 'random-number', 'instance': name}
        },
        'spec': {
            'replicas': app_spec.get('replicaCount', 1),
            'selector': {
                'matchLabels': {'app': 'random-number', 'instance': name}
            },
            'template': {
                'metadata': {
                    'labels': {'app': 'random-number', 'instance': name}
                },
                'spec': {
                    'containers': [{
                        'name': 'random-number',
                        'image': app_spec.get('image', 'sohamdalvi1011/random-num:v2'),
                        'ports': [{'containerPort': app_spec.get('port', 3000)}],
                        'volumeMounts': [{
                            'name': 'app-data',
                            'mountPath': '/data'
                        }],
                        'env': [
                            {
                                'name': 'MONGO_URI',
                                'value': f'mongodb://{mongo_service_name}:{mongo_port}/randomNumbers'
                            },
                            {
                                'name': 'LOG_LEVEL',
                                'value': app_spec.get('logLevel', 'info')
                            },
                            {
                                'name': 'LOG_DIR',
                                'value': '/data/logs'
                            }
                        ],
                        'resources': app_spec.get('resources', {}),
                        'readinessProbe': {
                            'httpGet': {
                                'path': '/health',
                                'port': app_spec.get('port', 3000)
                            },
                            'initialDelaySeconds': 10,
                            'periodSeconds': 5
                        },
                        'livenessProbe': {
                            'httpGet': {
                                'path': '/health',
                                'port': app_spec.get('port', 3000)
                            },
                            'initialDelaySeconds': 30,
                            'periodSeconds': 10
                        }
                    }],
                    'volumes': [{
                        'name': 'app-data',
                        'persistentVolumeClaim': {
                            'claimName': f'{name}-app-pvc'
                        }
                    }]
                }
            }
        }
    }
    
    # App Service
    service_spec = app_spec.get('service', {})
    app_service = {
        'apiVersion': 'v1',
        'kind': 'Service',
        'metadata': {
            'name': f'{name}-service',
            'namespace': namespace,
            'labels': {'app': 'random-number', 'instance': name}
        },
        'spec': {
            'ports': [{
                'port': service_spec.get('port', 3000),
                'targetPort': app_spec.get('port', 3000),
                'nodePort': service_spec.get('nodePort') if service_spec.get('type') == 'NodePort' else None
            }],
            'selector': {'app': 'random-number', 'instance': name},
            'type': service_spec.get('type', 'ClusterIP')
        }
    }
    
    api = kubernetes.client.CoreV1Api()
    apps_api = kubernetes.client.AppsV1Api()
    
    # Create App resources
    kopf.adopt(app_pvc)
    kopf.adopt(app_deployment)
    kopf.adopt(app_service)
    
    api.create_namespaced_persistent_volume_claim(namespace, app_pvc)
    apps_api.create_namespaced_deployment(namespace, app_deployment)
    api.create_namespaced_service(namespace, app_service)
    logger.info(f"App resources created with MongoDB URI: mongodb://{mongo_service_name}:{mongo_port}/randomNumbers")

@kopf.on.delete('operators.sohamdalvi1011.io', 'v1', 'randomnumbergenerators')
def delete_fn(name, namespace, logger, **kwargs):
    logger.info(f"Cleaning up resources for {name} in {namespace}")

@kopf.on.update('operators.sohamdalvi1011.io', 'v1', 'randomnumbergenerators')
def update_fn(spec, name, namespace, logger, **kwargs):
    logger.info(f"Updating {name} with new configuration")