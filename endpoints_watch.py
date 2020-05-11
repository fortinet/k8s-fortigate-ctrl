# Copyright 2020 Fortinet(c)
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Uses watch to print the stream of events from list namespaces and list pods.
The script will wait for 10 events related to namespaces to occur within
the `timeout_seconds` threshold and then move on to wait for another 10 events
related to pods to occur within the `timeout_seconds` threshold..metadata.resource_version
"""

from kubernetes import client, config, watch
import json
import os
from pprint import pprint

def main():
    # Configs can be set in Configuration class directly or using helper
    # utility. If no argument provided, the config will be loaded from
    # default location.
    config.load_kube_config()
    print("PID : %s" % (os.getpid()))

    v1 = client.CoreV1Api()
    count = 500
    w = watch.Watch()
    endpoints = v1.list_endpoints_for_all_namespaces(watch=False)
    endp_resversion = endpoints.metadata.resource_version
    print (endp_resversion)
    for event in w.stream(v1.list_endpoints_for_all_namespaces,  field_selector="metadata.namespace!=kube-system", resource_version=endp_resversion,timeout_seconds=10, pretty='true'):
        pprint(event)
        print("Event: %s %s %s" % (event['type'], event['object'].metadata.name, event['object'].metadata.annotations ))
        count -= 1
        if not count:
            w.stop()
    print("Finished endpoints stream.")
##
    for event in w.stream(v1.list_service_for_all_namespaces, label_selector="app", timeout_seconds=100):
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
