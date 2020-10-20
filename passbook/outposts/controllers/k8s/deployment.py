"""Kubernetes Deployment Reconciler"""
from typing import TYPE_CHECKING, Dict

from kubernetes.client import (
    AppsV1Api,
    V1Container,
    V1ContainerPort,
    V1Deployment,
    V1DeploymentSpec,
    V1EnvVar,
    V1EnvVarSource,
    V1LabelSelector,
    V1ObjectMeta,
    V1PodSpec,
    V1PodTemplateSpec,
    V1SecretKeySelector,
)

from passbook import __version__
from passbook.outposts.controllers.k8s.base import (
    KubernetesObjectReconciler,
    NeedsUpdate,
)
from passbook.outposts.models import Outpost

if TYPE_CHECKING:
    from passbook.outposts.controllers.kubernetes import KubernetesController


class DeploymentReconciler(KubernetesObjectReconciler[V1Deployment]):
    """Kubernetes Deployment Reconciler"""

    image_base = "beryju/passbook"

    outpost: Outpost

    def __init__(self, controller: "KubernetesController") -> None:
        super().__init__(controller)
        self.api = AppsV1Api()
        self.outpost = self.controller.outpost

    @property
    def name(self) -> str:
        return f"passbook-outpost-{self.controller.outpost.uuid.hex}"

    def reconcile(self, current: V1Deployment, reference: V1Deployment):
        if current.spec.replicas != reference.spec.replicas:
            raise NeedsUpdate()
        if (
            current.spec.template.spec.containers[0].image
            != reference.spec.template.spec.containers[0].image
        ):
            raise NeedsUpdate()

    def get_pod_meta(self) -> Dict[str, str]:
        """Get common object metadata"""
        return {
            "app.kubernetes.io/name": "passbook-outpost",
            "app.kubernetes.io/managed-by": "passbook.beryju.org",
            "passbook.beryju.org/outpost-uuid": self.controller.outpost.uuid.hex,
        }

    def get_reference_object(self) -> V1Deployment:
        """Get deployment object for outpost"""
        # Generate V1ContainerPort objects
        container_ports = []
        for port_name, port in self.controller.deployment_ports.items():
            container_ports.append(V1ContainerPort(container_port=port, name=port_name))
        meta = self.get_object_meta(name=self.name)
        secret_name = f"passbook-outpost-{self.controller.outpost.uuid.hex}-api"
        return V1Deployment(
            metadata=meta,
            spec=V1DeploymentSpec(
                replicas=self.outpost.config.kubernetes_replicas,
                selector=V1LabelSelector(match_labels=self.get_pod_meta()),
                template=V1PodTemplateSpec(
                    metadata=V1ObjectMeta(labels=self.get_pod_meta()),
                    spec=V1PodSpec(
                        containers=[
                            V1Container(
                                name=str(self.outpost.type),
                                image=f"{self.image_base}-{self.outpost.type}:{__version__}",
                                ports=container_ports,
                                env=[
                                    V1EnvVar(
                                        name="PASSBOOK_HOST",
                                        value_from=V1EnvVarSource(
                                            secret_key_ref=V1SecretKeySelector(
                                                name=secret_name,
                                                key="passbook_host",
                                            )
                                        ),
                                    ),
                                    V1EnvVar(
                                        name="PASSBOOK_TOKEN",
                                        value_from=V1EnvVarSource(
                                            secret_key_ref=V1SecretKeySelector(
                                                name=secret_name,
                                                key="token",
                                            )
                                        ),
                                    ),
                                    V1EnvVar(
                                        name="PASSBOOK_INSECURE",
                                        value_from=V1EnvVarSource(
                                            secret_key_ref=V1SecretKeySelector(
                                                name=secret_name,
                                                key="passbook_host_insecure",
                                            )
                                        ),
                                    ),
                                ],
                            )
                        ]
                    ),
                ),
            ),
        )

    def create(self, reference: V1Deployment):
        return self.api.create_namespaced_deployment(self.namespace, reference)

    def delete(self, reference: V1Deployment):
        return self.api.delete_namespaced_deployment(
            reference.metadata.name, self.namespace
        )

    def retrieve(self) -> V1Deployment:
        return self.api.read_namespaced_deployment(self.name, self.namespace)

    def update(self, current: V1Deployment, reference: V1Deployment):
        return self.api.patch_namespaced_deployment(
            current.metadata.name, self.namespace, reference
        )