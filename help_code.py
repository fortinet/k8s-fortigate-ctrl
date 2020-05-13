# quick/dirty helping/getting the json values
from kubernetes import client, config, watch
import json
import os
from pprint import pprint


def main():
    # Configs can be set in Configuration class directly or using helper
    # utility. If no argument provided, the config will be loaded from

    config.load_kube_config()

    v1 = client.CoreV1Api()
    crds = client.CustomObjectsApi()
    LBDOMAIN = "fortigates.fortinet.com"
    lb_fgt_co = crds.get_namespaced_custom_object(LBDOMAIN, "v1", "bad", "lb-fgts",
                                                  "ugly")
    for service in v1.list_service_for_all_namespaces(label_selector="app").items:
        print('### service ####')
        pprint(service.metadata.annotations)
    count = 500
    w = watch.Watch()
    endpoints = v1.list_endpoints_for_all_namespaces(watch=False)
    endp_resversion = endpoints.metadata.resource_version
    print ("####   Endpoints all namespace ")
    for event in w.stream(v1.list_endpoints_for_all_namespaces,  field_selector="metadata.namespace!=kube-system",
                          resource_version=endp_resversion, timeout_seconds=50, pretty='true'):
        pprint(event)
        count -= 1
        if not count:
            w.stop()

    print ("####  Services all namespace ")
    count = 300
    for event in w.stream(v1.list_service_for_all_namespaces, label_selector="app", timeout_seconds=50):
        pprint(event)
        print("Event: %s %s %s" % (
            event['type'],
            event['object'].kind,
            json.loads(event['object'].metadata.annotations['kubectl.kubernetes.io/last-applied-configuration'])['metadata'])
        )
        count -= 1
        if not count:
            w.stop()
    print("Finished pod stream.")


if __name__ == '__main__':
    main()
