import json
import yaml
from kubernetes import client, config, watch
import os
from pprint import pprint
import fortiosapi


DOMAIN = "fortinet.com"


def review_fortigate(crds, obj):
    metadata = obj.get("metadata")
    if not metadata:
        print("No metadata in object, skipping: %s" % json.dumps(obj, indent=1))
        return
    name = metadata.get("name")
    namespace = metadata.get("namespace")
    pprint(obj)
    obj["spec"]["review"] = True

    print("Updating: %s" % name)
    crds.replace_namespaced_custom_object(DOMAIN, "v1", namespace, "fortigates", name, obj)


if __name__ == "__main__":
    pprint(os.uname().nodename)
    if 'KUBERNETES_PORT' in os.environ:
        config.load_incluster_config()
        definition = '/tmp/fortigates-crd.yml'
    else:
        config.load_kube_config()
        definition = 'fortigates-crd.yml'
    configuration = client.Configuration()
    configuration.assert_hostname = False
    api_client = client.api_client.ApiClient(configuration=configuration)
    v1 = client.ApiextensionsV1beta1Api(api_client)
    current_crds = [x['spec']['names']['kind'].lower() for x in v1.list_custom_resource_definition().to_dict()['items']]
    if 'fortigate' not in current_crds:
        print("Creating fortigates definition")
        with open(definition) as data:
            body = yaml.safe_load(data)
        v1.create_custom_resource_definition(body) # TODO check why this fails but apply works
    crds = client.CustomObjectsApi(api_client)
    pprint(crds.list_cluster_custom_object(DOMAIN,"v1","fortigates"))
    print("Waiting for Fortigates to come up...")
    resource_version = ''
    while True:
        stream = watch.Watch().stream(crds.list_cluster_custom_object, DOMAIN, "v1", "fortigates", resource_version=resource_version)
        print ("loop")
        for event in stream:
            obj = event["object"]
            operation = event['type']
            spec = obj.get("spec")
            if not spec:
                continue
            metadata = obj.get("metadata")
            resource_version = metadata['resourceVersion']
            name = metadata['name']
            print("Handling %s on %s" % (operation, name))
            done = spec.get("review", False)
            if done:
                continue
            review_fortigate(crds, obj)
