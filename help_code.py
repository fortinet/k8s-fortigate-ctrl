# quick/dirty helping/getting the json values
from kubernetes import client, config, watch
import json
import os
from pprint import pprint
from recursive_json import extract_values

def main():
    # Configs can be set in Configuration class directly or using helper
    # utility. If no argument provided, the config will be loaded from
    # default location.
    data={
          "http_method":"GET",
          "results":[
            {
              "virtual_server_name":"K8S_default:azure-vote2-front",
              "virtual_server_ip":"0.0.0.0",
              "virtual_server_port":90,
              "list":[
                {
                  "real_server_ip":"10.40.0.27",
                  "real_server_port":80,
                  "mode":"active",
                  "status":"up",
                  "monitor_events":0,
                  "active_sessions":1,
                  "RTT":"<1",
                  "bytes_processed":2992
                },
                {
                  "real_server_ip":"10.40.0.52",
                  "real_server_port":80,
                  "mode":"active",
                  "status":"up",
                  "monitor_events":0,
                  "active_sessions":0,
                  "RTT":"<1",
                  "bytes_processed":0
                }
              ]
            }
          ],
          "vdom":"root",
          "path":"firewall",
          "name":"load-balance",
          "status":"success",
          "serial":"FGTAZRCZLHS4OSBF",
          "version":"v6.2.0",
          "build":866
        }
    searched_data=extract_values(data, 'vdom')
    print("DATA SORTED %s" % searched_data )

    config.load_kube_config()

    v1 = client.CoreV1Api()
    for service in v1.list_service_for_all_namespaces(label_selector="app").items:
        print('### service ####')
        pprint(service.metadata.annotations)
    count = 500
    w = watch.Watch()
    endpoints = v1.list_endpoints_for_all_namespaces(watch=False)
    endp_resversion = endpoints.metadata.resource_version
    print ("####   Endpoints all namespace ")
    for event in w.stream(v1.list_endpoints_for_all_namespaces,  field_selector="metadata.namespace!=kube-system",
                          resource_version=endp_resversion,timeout_seconds=50, pretty='true'):
        pprint(event)
        count -= 1
        if not count:
            w.stop()

    print ("####  Services all namespace ")
    count=300
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
