+++
title = 'Microservices'
weight = 5
+++

<!--
Copyright (c) 2024, 2025, Oracle and/or its affiliates.
Licensed under the Universal Permissive License v1.0 as shown at http://oss.oracle.com/licenses/upl.

spell-checker: ignore opentofu ocid oraclecloud   ollama crds ADBDB finalizers mxbai 
-->

The {{< full_app_ref >}} was specifically designed to run on infrastructure supporting microservices architecture, including [Kubernetes](https://kubernetes.io/).

## Oracle Kubernetes Engine

The following example shows running the {{< short_app_ref >}} in [Oracle Kubernetes Engine](https://docs.oracle.com/en-us/iaas/Content/ContEng/Concepts/contengoverview.htm) (**OKE**).  The Infrastructure as Code (**IaC**) provided in the source [opentofu](https://github.com/oracle-samples/ai-explorer/tree/main/opentofu) directory was used to provision the infrastructure in Oracle Cloud Infrastructure (**OCI**).

![OCI OKE](../images/infra_oci.png)

The command to connect to the **OKE** cluster will be output as part of the **IaC**.

### Images

You will need to build the {{< short_app_ref >}} container images and stage them in a container registry, such as the [OCI Container Registry](https://docs.oracle.com/en-us/iaas/Content/Registry/Concepts/registryoverview.htm) (**OCIR**).

1. Build the {{< short_app_ref >}} images:

    From the code source `src/` directory:
    ```bash
    podman build --arch amd64 -f client/Dockerfile -t ai-explorer-client:latest .

    podman build --arch amd64 -f server/Dockerfile -t ai-explorer-server:latest .
    ```

1. Log into your container registry:

    More information on authenticating to **OCIR** can be found [here](https://docs.oracle.com/en-us/iaas/Content/Registry/Tasks/registrypushingimagesusingthedockercli.htm).

    ```bash
    podman login <registry-domain>
    ```

    Example:
    ```bash
    podman login iad.ocir.io
    ```

    You will be prompted for a username and token password.

1. Push the {{< short_app_ref >}} images:

    More information on pushing images to **OCIR** can be found [here](https://docs.oracle.com/en-us/iaas/Content/Registry/Tasks/registrypushingimagesusingthedockercli.htm).

    Example (the values for `<server_repository>` and `<server_repository>` are provided from the **IaC**):
    ```bash
    podman tag ai-explorer-client:latest <client_repository>:latest
    podman push <client_repository>:latest

    podman tag ai-explorer-server:latest <server_repository>:latest
    podman push <server_repository>:latest
    ```

### Ingress

To access the {{< short_app_ref >}} GUI and API Server, you can either use a port-forward or an Ingress service.  For demonstration purposes, the [OCI Native Ingress Controller](https://docs.oracle.com/en-us/iaas/Content/ContEng/Tasks/contengsettingupnativeingresscontroller.htm), which was enabled on the **OKE** cluster as part of the **IaC**, will be used to for public Ingress access.

The [Flexible LoadBalancer](https://docs.oracle.com/en-us/iaas/Content/NetworkLoadBalancer/overview.htm) was provisioned using the **IaC**. This example will create the Listeners and Backends to expose port 80 for the {{< short_app_ref >}} GUI and port 8000 for the {{< short_app_ref >}} API Server on the existing LoadBalancer.  

It is _HIGHLY_ recommended to protect these ports with [Network Security Groups](https://docs.oracle.com/en-us/iaas/Content/Network/Concepts/networksecuritygroups.htm) (**NSGs**).

The service manifest has five values that should be supplied:

- `<lb_compartment_ocid>` - OCID of the LoadBalancer Compartment
- `<lb_subnet_ocid>` - OCID of the Subnet for the LoadBalancer
- `<lb_ocid>` - OCID of the LoadBalancer provisioned by IaC
- `<lb_nsg_ocid>` - **NSG** OCID's to protect the LB ports
- `<lb_reserved_ip_ocid>` - A reserved IP address for the Loadbalancer

These will be output as part of the **IaC** but can be removed from the code if not reserving an IP or protecting the Load Balancer.

1. Create a `native_ingress.yaml`:
    ```yaml
    apiVersion: v1
    kind: Namespace
    metadata:
      name: hologram
    ---
    apiVersion: "ingress.oraclecloud.com/v1beta1"
    kind: IngressClassParameters
    metadata:
      name: native-ic-params
      namespace: ai-explorer
    spec:
      compartmentId: <compartment_ocid>
      subnetId: <lb_subnet_ocid>
      loadBalancerName: "ai-explorer-lb"
      reservedPublicAddressId: <lb_reserved_ip_ocid>
      isPrivate: false
      maxBandwidthMbps: 1250
      minBandwidthMbps: 10
    ---
    apiVersion: networking.k8s.io/v1
    kind: IngressClass
    metadata:
      name: native-ic
      namespace: hologram
      annotations:
        ingressclass.kubernetes.io/is-default-class: "true"
        oci-native-ingress.oraclecloud.com/network-security-group-ids: <lb_nsg_ocid>
        oci-native-ingress.oraclecloud.com/id: <lb_ocid>
        oci-native-ingress.oraclecloud.com/delete-protection-enabled: "true"
    spec:
      controller: oci.oraclecloud.com/native-ingress-controller
      parameters:
        scope: Namespace
        namespace: hologram
        apiGroup: ingress.oraclecloud.com
        kind: IngressClassParameters
        name: native-ic-params
    ```

### The {{< short_app_ref >}}

The {{< short_app_ref >}} can be deployed using the [Helm](https://helm.sh/) chart provided with the source:
[{{< short_app_ref >}} Helm Chart](https://github.com/oracle-samples/ai-explorer/tree/main/helm).  A list of all values can be found in [values_summary.md](https://github.com/oracle-samples/ai-explorer/tree/main/helm/values_summary.md).

If you deployed a GPU node pool as part of the **IaC**, you can deploy Ollama and enable a Large Language and Embedding Model out-of-the-box.

1. Create the `ai-explorer` namespace:
    
    ```bash
    kubectl create namespace ai-explorer
    ```

1. Create a secret to hold the API Key:

    ```bash
    kubectl create secret generic api-key \
      --from-literal=apiKey=$(openssl rand -hex 32) \
      --namespace=ai-explorer
    ```

1. Create a secret to hold the Database Authentication:

    The command has two values that should be supplied:

    - `<adb_password>` - Password for the ADB ADMIN User
    - `<adb_service>` - The Service Name (i.e. ADBDB_TP)

    ```bash
    kubectl create secret generic db-authn \
      --from-literal=username='ADMIN' \
      --from-literal=password='<adb_password>' \
      --from-literal=service='<adb_service>' \
      --namespace=ai-explorer
    ```

    These will be output as part of the **IaC**.

    {{< icon "star" >}} While the example shows the ADMIN user, it is advisable to [create a new non-privileged database user](../client/configuration/db_config/#database-user).


1. Create the `values.yaml` file for the Helm Chart:

    The `values.yaml` has five values that should be supplied:

    - `<lb_reserved_ip>` - A reserved IP address for the Loadbalancer
    - `<adb_ocid>` - Autonomous Database OCID
    - `<client_repository>` - Full path to the repository for the {{< short_app_ref >}} Image 
    - `<server_repository>` - Full path to the repository for the API Server Image

    These will be output as part of the **IaC**.

    {{< icon "star" >}} If using the **IaC** for **OCI**, it is not required to specify an ImagePullSecret as the cluster nodes are configured with the [Image Credential Provider for OKE](https://github.com/oracle-devrel/oke-credential-provider-for-ocir).

    ```yaml
    global:
      api:
        secretName: "api-key"

    # -- API Server configuration
    server:
      enabled: true
      image:
        repository: <server_repository>
        tag: "latest"

      ingress:
        enabled: true
        className: native-ic
        annotations:
          nginx.ingress.kubernetes.io/upstream-vhost: "<lb_reserved_ip>"
          oci-native-ingress.oraclecloud.com/http-listener-port: "8000"
          oci-native-ingress.oraclecloud.com/protocol: TCP

      service:
        http:
          type: "NodePort"

      # -- Oracle Autonomous Database Configuration
      adb:
        enabled: true
        ocid: "<adb_ocid>"
        mtlsWallet: ""
        authN:
          secretName: "db-authn"

    client:
      enabled: true
      image:
        repository: <client_repository>
        tag: "latest"

      ingress:
        enabled: true
        className: native-ic
        annotations:
          nginx.ingress.kubernetes.io/upstream-vhost: "<lb_reserved_ip>"
          oci-native-ingress.oraclecloud.com/http-listener-port: "80"
          oci-native-ingress.oraclecloud.com/protocol: TCP

      service:
        http:
          type: "NodePort"

      features:
        disableTestbed: "false"
        disableApi: "false"
        disableTools: "false"
        disableDbCfg: "true"
        disableModelCfg: "false"
        disableOciCfg: "true"
        disableSettings: "true"

    ollama:
      enabled: true
      models:
        - llama3.1
        - mxbai-embed-large
      resources:
        limits:
          nvidia.com/gpu: 1
    ```

1. Deploy the Helm Chart:

    From the `helm/` directory:

    ```bash
    helm upgrade \
      --install ai-explorer . \
      --namespace ai-explorer \
      -f values.yaml
    ```

### Cleanup

To remove the {{< short_app_ref >}} from the OKE Cluster:

1. Uninstall the Helm Chart:

    ```bash
    helm uninstall ai-explorer -n ai-explorer
    ```

1. Delete the `ai-explorer` namespace:

    ```bash
    kubectl delete namespace ai-explorer
    ```