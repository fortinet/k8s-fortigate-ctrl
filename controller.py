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
K8S controller to have a load balancer on a fortigate
 use and manipulate CRD for fortigates load balancer fortigates.
 Use 1 controller per Fortigate the controller can create multiple LB per FGT.
"""

import logging
import json
import yaml
from kubernetes import client, config, watch
import os
from pprint import pprint
from fortiosapi import FortiOSAPI
import signal
import sys

def signal_handler(sig, frame):
    # catch the stop condition to release the fgt session
    print('You pressed Ctrl+C! disconnecting firewall before exit')
    fgt.logout()
    sys.exit(3)
signal.signal(signal.SIGINT, signal_handler)
# must stop with ctrl+c rerun does SIGKILL and can't handle that

formatter = logging.Formatter(
    '%(asctime)s %(name)-12s %(levelname)-8s %(message)s')
logger = logging.getLogger('fortiosapi')
hdlr = logging.FileHandler('testfortiosapi.log')
hdlr.setFormatter(formatter)
logger.addHandler(hdlr)
logger.setLevel(logging.DEBUG)

fgt = FortiOSAPI()
crtled_fgt_crd = ""
fgt.debug("on")
DOMAIN = "fortinet.com"
list_of_applications=[]
SERVICES_RESOURCE_VERSION = 0
LB_FGTS_RESOURCES_VERSION = 0
VDOM= "root"
################################
def monitor_lb_co_status():
    ## use get monitor to update the status of all lb linked to this controlled fgt
    fgt_co_status = crds.get_cluster_custom_object_status(DOMAIN, "v1", "fortigates", os.getenv('FGT_NAME'))
    LBS_INERROR=0 # must assigned here so not local to func
    try:
        fgt_lbs=fgt.monitor('firewall', 'load-balance',
                    mkey='select', vdom='root', parameters='count=999')
    except:
        # if pb this means we can not connect to FGT
        # update status
        # get the new version of the object before changing status (or err)
        if monitored_lbs['status'] == 'success':
            fgt_co_status['status'] = {'status': "connected"}
            LBS_INERROR = 0
        else:
            fgt_co_status['status'] = {'status': "error"}
            LBS_INERROR=1
        crds.replace_cluster_custom_object_status(DOMAIN, "v1", "fortigates", os.getenv('FGT_NAME'), fgt_co_status)
        # make the list/specs available globally
    for lb_co in crds.list_cluster_custom_object(LBDOMAIN, "v1", "lb-fgts")['items']:
        # must check on every lbs linked to this fgt or leave them
        fgt_lb_results=fgt_lbs['results']
        metadata=lb_co['metadata']
        if lb_co['spec']['fgt'] == os.getenv('FGT_NAME'):
            print ("handle %s with LBS ERROR= %s" % (lb_co['spec']['fgt'],LBS_INERROR))
            if LBS_INERROR == 0:
                for vlb in fgt_lb_results:
                    if vlb['virtual_server_name'] == "K8S_"+metadata['namespace']+":"+metadata['name']:
                        realserver_number=len(vlb['list'])
                        realserver_ups=0
                        for realserv in vlb['list']:
                            if realserv['status'] == "up":
                                realserver_ups += 1
                        # update status with #servup/#servconf
                        lb_co['status']['status'] = str(realserver_ups)+"/"+str(realserver_number)
                    else:
                        try:
                            lb_co['status']['status'] = "no config"
                        except KeyError:
                            # if Keyerror then status is empty
                            lb_co['status'] = {'status': "no config"}
            else:
                #this means fgt is not reachable
                try:
                    lb_co['status']['status'] = "error"
                except KeyError:
                    # if Keyerror then status is empty
                    lb_co['status'] = {'status': "error"}
        crds.replace_namespaced_custom_object_status(LBDOMAIN, "v1", metadata['namespace'], "lb-fgts",
                                                         metadata['name'],
                                                         lb_co)


def initialize_fortigate(fgt_co):
    # initialize the setup based on what is available at start to avoid repeat of old events.
    ###Intialize based on discovered setup first to avoid re-runing failed events on streams
    #print(os.uname().nodename)
    # Setup the associated FGT with this controller (1 controller 1 FGT n LBs)
    FGT_URL=os.getenv('FGT_URL')
    # Initialize fgt connection
    FGT_IP = FGT_URL.split("@")[1]
    try:
        user_passwd = FGT_URL.split("@")[0]
    except KeyError:
        pass
    try:
        FGT_USER = user_passwd.split(":")[0]
        FGT_PASSWD = user_passwd.split(":")[1]
    except KeyError:
        # TODO Allow to pass a API KEY instead.
        pass
    metadata = fgt_co.get("metadata")
    name = metadata.get("name")
    print("in the initial setup for fgt-az: %s" % fgt_co['metadata']['name'])
    fgt_co['spec']['user'] = FGT_USER
    fgt_co['spec']['fgt-ip'] = FGT_IP
    if not fgt_co['spec']['vdom']:
        fgt_co['spec']['vdom']="root"
    VDOM=fgt_co['spec']['vdom']
    LOGINERR=0
    try:
        fgt.login(FGT_IP , FGT_USER, password=FGT_PASSWD, verify=False)
    except:
        LOGINERR=1

    try:
        fgt_co['spec']['fgt-publicip']=fgt.license()['results']['fortiguard']['fortigate_wan_ip']
    except KeyError:
        print("could not find the FGT public-ip which might be linked to license issue")
        pass
    except:
        print("ERROR trying to check license")
        pass
    fgt_co_status = crds.replace_cluster_custom_object(DOMAIN, "v1", "fortigates", name, fgt_co)
    # get the new version of the object before changing status (or err)
    if LOGINERR == 0:
        if fgt.monitor('system', 'vdom-resource', mkey='select', vdom=fgt_co['spec']['vdom'])['status'] == 'success':
            fgt_co_status['status']={ 'status': "connected" }
        else:
            fgt_co_status['status'] = {'status': "not managed"}
    else:
        fgt_co_status['status'] = {'status': "login error"}
    crds.replace_cluster_custom_object_status(DOMAIN, "v1", "fortigates", name, fgt_co_status )
    # make the list/specs available globally
    crtled_fgt_co=fgt_co_status

def initialize_lb_for_service(lb_fgt,extport):
    #port to listen on
    #app-label must be json with the changes to make
    # check the crd is there and good
    metadata=lb_fgt['metadata']
    print("adding service :%s" % metadata['name'])
    if metadata['name'] not in list_of_applications:
        list_of_applications.append(metadata['name'])
        pprint(list_of_applications)
    #create fgt loadbalancer name k8_≤app-name> http only for now (will be in CRD or annotations)
    data = {
        "type": "server-load-balance",
        "ldb-method": "least-rtt",
        "extintf": "port1",
        "server-type": "http",
# TODO add monitor            "monitor": [{"name": "http"}],
    }
    data["name"] = "K8S_"+metadata['namespace']+":"+metadata['name']
    data["extport"]= extport
    print("label of obj: %s"%metadata)
    for endpoint in v1.list_namespaced_endpoints(metadata['namespace'],label_selector="app="+metadata['name']).items:
        print("### ENDPOINT ###")
        realserver_id=1
        realservers=[]
        for subset in endpoint.subsets:
            for address in subset.addresses:
                for port in subset.ports:
#                        print("id: %s ip: %s port: %s " %(realserver_id,address.ip,port.port))
                    realservers.append({"id": realserver_id, "ip": address.ip, "port": port.port, "status": "active"})
                    realserver_id += 1
    data["realservers"]=realservers
    ## TODO find vdom, wanport and lanport in crd
    UPDATED = 0
    try:
        ret = fgt.set('firewall', 'vip', vdom="root", data=data)
        if ret['status'] != 'success':
            UPDATED = 1
    except:
        UPDATED = 1
    # create the policy to allow getting in
    # TODO check if id is available or find another one create the virtual server LB policy (need its id)
    ## fgt.get('firewall', 'policy', vdom="root", mkey=403)
    data = {
        'action': "accept",
        'srcintf': [{"name": "port1"}],
        'dstintf': [{"name": "port2"}],
        'srcaddr': [{"name": "all"}],
        'schedule': "always",
        'service': [{"name": "HTTP"}],
        'logtraffic': "all",
        'inspection-mode': "proxy"
    }
    data["name"] = "K8S_"+metadata['namespace']+":"+metadata['name']
    data["policyid"] = "8"+extport
    #convention policyId is 8 (K8S) concat with the port number which must be unique per FGT
    ##TODO be carefull with hardcoded policyid
    data["extport"]= extport
    data['dstaddr']= [{"name": "K8S_"+metadata['namespace']+":"+metadata['name']}]
    if UPDATED == 0:
        ret2 = fgt.set('firewall', 'policy', vdom="root", data=data)
        if ret2['status'] == 'success' and ret['status'] == 'success':
            UPDATED=0
        else:
            UPDATED=1
    lb_fgt_co['spec']['fgt-port'] = extport
    lb_fgt_co['spec']['fgt'] = os.getenv('FGT_NAME')
    lb_fgt_co_status = crds.replace_namespaced_custom_object(LBDOMAIN, "v1", metadata['namespace'],
                                                                    "lb-fgts", metadata['name'], lb_fgt_co)
    pprint(lb_fgt_co_status)
    if UPDATED == 0:
        lb_fgt_co_status['status'] = {'status': "configured"}
    else:
        lb_fgt_co_status['status'] = {'status': "error"}
    #TODO update the service itself in K8S
    crds.replace_namespaced_custom_object_status(LBDOMAIN, "v1", metadata['namespace'], "lb-fgts", metadata['name'],
                                                 lb_fgt_co_status)


def fgt_logcheck():
    try:
        ret = fgt.get('firewall', 'vip', vdom=vdom) #TODO get vdom from CRD
    except e:
        pass

def update_lb_for_service(operation,object):
##TODO replace redundant
    #port to listen on
    #app-label must be json with the changes to make
    # check the crd is there and good
    if operation == "ADDED" or operation == "MODIFIED":
        metadata=object.metadata
        print("adding service :%s" % metadata.name)
        pprint(object)
        if metadata.name not in list_of_applications:
            list_of_applications.append(metadata.name)
        #create fgt loadbalancer name k8_≤app-name> http only for now (will be in CRD or annotations)
        data = {
            "type": "server-load-balance",
            "ldb-method": "least-rtt",
            "extintf": "port1",
            "server-type": "http",
# TODO add monitor            "monitor": [{"name": "http"}],
        }
        data["name"] = "K8S_"+metadata.namespace+":"+metadata.name
        annotations = json.loads(object.metadata.annotations['kubectl.kubernetes.io/last-applied-configuration'])
        data["extport"]= annotations['metadata']['annotations']["lb-fgts.fortigates.fortinet.com/port"]
        print("label of obj: %s"%metadata.labels)
        for endpoint in v1.list_namespaced_endpoints(metadata.namespace,label_selector="app="+metadata.name).items:
            print("### ENDPOINT ###")
            realserver_id=1
            realservers=[]
            for subset in endpoint.subsets:
                for address in subset.addresses:
                    for port in subset.ports:
#                        print("id: %s ip: %s port: %s " %(realserver_id,address.ip,port.port))
                        realservers.append({"id": realserver_id, "ip": address.ip, "port": port.port, "status": "active"})
                        realserver_id += 1
        data["realservers"]=realservers
        ## TODO find vdom, wanport and lanport in crd
        ret = fgt.set('firewall', 'vip', vdom="root", data=data)
        pprint(ret)
        # create the policy to allow getting in
        # TODO check if id is available or find another one create the virtual server LB policy (need its id)
        ## fgt.get('firewall', 'policy', vdom="root", mkey=403)
        data = {
            'action': "accept",
            'srcintf': [{"name": "port1"}],
            'dstintf': [{"name": "port2"}],
            'srcaddr': [{"name": "all"}],
            'schedule': "always",
            'service': [{"name": "HTTP"}],
            'logtraffic': "all",
            'inspection-mode': "proxy"
        }
        data["name"] = "K8S_"+metadata.namespace+":"+metadata.name
        data["policyid"] = "8"+annotations['metadata']['annotations']["lb-fgts.fortigates.fortinet.com/port"]
        ##TODO be carefull with hardcoded policyid
        data["extport"]= annotations['metadata']['annotations']["lb-fgts.fortigates.fortinet.com/port"]
        data['dstaddr']= [{"name": "K8S_"+metadata.namespace+":"+metadata.name}]

        ret2 = fgt.set('firewall', 'policy', vdom="root", data=data)
        pprint(ret2)



def update_fgt(operation, obj, crd):
    ##OPERATION: enum { ADDED, DELETED; MODIFIED }
    # DELETE must also delete all related load-balancers (warning service with annotations ! try to fail them)
    # ADDED should create if not existing and login works.
    # UPDATE the FGT config vs. the crd and report in crd

    print("### update FGT oper: %s ###" % operation)
    pprint(obj)
    pprint(crd)
# def review_fortigate(crds, obj):
#     metadata = obj.get("metadata")
#     if not metadata:
#         print("No metadata in object, skipping: %s" % json.dumps(obj, indent=1))
#         return
#     name = metadata.get("name")
#     namespace = metadata.get("namespace")
#     pprint(obj)
#     obj["spec"]["review"] = True
#
#     print("Updating: %s" % name)
#     crds.replace_namespaced_custom_object(DOMAIN, "v1", namespace, "fortigates", name, obj)
def delete_lb_co(obj):
    # First delete the policy on FGT
    POLID= "8"+str(obj['spec']['fgt-port'])
    ret=fgt.delete('firewall',"policy",vdom=VDOM,mkey=POLID)
    print("## DELETE POLICY ##")
    pprint(ret)
    ##TODO remove vip on FGT change status info on lb-fgt custom object(function ?)


def update_endp_for_service(object):
    metadata=object.metadata
    data={}
    app_name=object.metadata.labels['app']
    if app_name:
        data["name"] = "K8S_" + metadata.namespace + ":" + app_name
    try:
        ret=fgt.get('firewall', 'vip', vdom="root", mkey=data["name"])
    except:
        print("Can not get %s VIP infos" % data["name"])
    print("---------  Update endps")
    if ret['status'] == 'success':
        # the FGT LB can be found
        realserver_id = 1
        realservers = []
        for subset in object.subsets:
            for address in subset.addresses:
                for port in subset.ports:
                    realservers.append(
                        {"id": realserver_id, "ip": address.ip, "port": port.port, "status": "active"})
                    realserver_id += 1
                    # API doc says limited to 4 but test show 20ish works

        data["realservers"] = realservers
        ## API accept to put only certain value no need to check the others which can be changed when CRD changes
        UPDATED = 0
        try:
            ret = fgt.put('firewall', 'vip', vdom="root", mkey=data["name"], data=data)
            if ret['status'] != 'success':
                UPDATED = 1
        except:
            UPDATED = 1
        if UPDATED == 0:
            return True
        else:
            #TODO change the status to error
            return False


if __name__ == "__main__":

    if 'KUBERNETES_PORT' in os.environ:
        config.load_incluster_config()
        definition = '/tmp/fortigates-crd.yml'
    else:
        config.load_kube_config()
        definition = 'fortigates-crd.yml'
    configuration = client.Configuration()
    configuration.assert_hostname = False
    api_client = client.api_client.ApiClient(configuration=configuration)
    #handler for CRDs
    v1crd = client.ApiextensionsV1beta1Api(api_client)
    # handler for namespace/service/endpoints
    v1 = client.CoreV1Api()

    current_crds = [x['spec']['names']['kind'].lower() for x in v1crd.list_custom_resource_definition().to_dict()['items']]
    if 'fortigate' not in current_crds:
        print("You must apply Fortigates CRD definition first")
        exit(2) # linked to https://github.com/kubernetes-client/python/issues/376
        ##TODO remove when bug is fixed
        data=open(definition)
        body = yaml.safe_load(data)
        v1crd.create_custom_resource_definition(body) # TODO check why this fails but apply works

    crds = client.CustomObjectsApi(api_client)
    ## get or create the custom object (Cluster) for the FGT
    try:
        fgt_co = crds.get_cluster_custom_object(DOMAIN,"v1","fortigates",os.getenv('FGT_NAME'))
    except client.rest.ApiException:
        print("CREATE a NEW FGT object")
        # if no previous custom object  then create a generic
        body = {"apiVersion": "fortinet.com/v1", "kind": "Fortigate",
                "spec": {"vdom": "root"}, "scope": "Cluster" , "wanintf": "port1"}
        body['metadata']={"name": os.getenv('FGT_NAME') }
        body['spec']['fgt-name']=os.getenv('FGT_NAME') ##TODO refactor this is redondant
        crds.create_cluster_custom_object(DOMAIN,"v1","fortigates",body)
        fgt_co = crds.get_cluster_custom_object(DOMAIN,"v1","fortigates",os.getenv('FGT_NAME'))
    initialize_fortigate(fgt_co)
    FGTS_RESOURCE_VERSION=fgt_co['metadata']['resourceVersion']
    LBDOMAIN="fortigates.fortinet.com"
    ## Look for annotations in services and update/create lb-fgt custom objets if needed
    SERVICES_RESOURCE_VERSION=v1.list_service_for_all_namespaces(label_selector="app").metadata.resource_version
    for service in v1.list_service_for_all_namespaces(label_selector="app").items:
        if "lb-fgts.fortigates.fortinet.com/port" in service.metadata.annotations:
            ## if this annotation is on then we create/update a loadbalancer on fortigate
            # can add "fortigates.fortinet.com/name: myfgt" annotation if multiple FGT
            metadata=service.metadata
            try:
                lb_fgt_co=crds.get_namespaced_custom_object(LBDOMAIN,"v1",metadata.namespace,"lb-fgts", metadata.name)
            except:
                print("CREATE a NEW LB-FGT object")
                # if no previous custom object  then create a generic
                body = {"apiVersion": "fortigates.fortinet.com/v1", "kind": "LoadBalancer",
                        "spec": {"fgt-port": "00"}}
                body['metadata'] = { "name": metadata.name }
                body['spec']['fgt-name'] = os.getenv('FGT_NAME')
                crds.create_namespaced_custom_object(LBDOMAIN, "v1",metadata.namespace, "lb-fgts", body)
                lb_fgt_co=crds.get_namespaced_custom_object(LBDOMAIN,"v1",metadata.namespace,"lb-fgts", metadata.name)
            initialize_lb_for_service(lb_fgt_co,metadata.annotations["lb-fgts.fortigates.fortinet.com/port"])
            # set the resource pointer to the current version
    LB_FGTS_RESOURCES_VERSION = crds.list_cluster_custom_object(LBDOMAIN, "v1", "lb-fgts")['metadata']['resourceVersion']

    endpoints_resource_version = 0

    # Global list of applications for which we manage LB

    timeout=2 #make it small for dev TODO increase in prod
    count=15
    print("")
    print('_____________________________')


while True:
        ##update LB and FGT status if can get LB monitoring infos
        monitor_lb_co_status()
        ## Watch and react to change on loadbalancerfortigate CRD (= changes to LB configs)
        stream = watch.Watch().stream(crds.list_cluster_custom_object, LBDOMAIN, "v1", "lb-fgts",
                                      resource_version= LB_FGTS_RESOURCES_VERSION, timeout_seconds=timeout)
        count = 15
        for event in stream:
            operation = event['type']
            obj = event["object"]
            metadata = obj.get("metadata")
            if operation == "ADDED":
                pass
                # just adding a lb-fgt def do nothing you must have a service set up with annotations
            elif operation == "MODIFIED":
                # must check if service is active before changing
                pass #modified_lb_for_service()
            elif operation == "DELETED":
                delete_lb_co(obj)
            elif operation == "ERROR":
                # this is usually due to a bad resource version pointer
                LB_FGTS_RESOURCES_VERSION = crds.list_cluster_custom_object(DOMAIN, "v1", "lb-fgts")['metadata'][
                    'resourceVersion']
            else:
                # should not arrive here
                raise ValueError

            if metadata:
                # Covers ERROR case with empty metadata
                print("Handling %s on %s" % (operation, metadata['name']))
                LB_FGTS_RESOURCES_VERSION = metadata['resourceVersion']
            count -= 1
            if not count:
                watch.stop()

        print("end processing LB FGTs events %s" % LB_FGTS_RESOURCES_VERSION)

        ## Watch and react to change on fortigates CRD (= changes to FGT config)
        stream = watch.Watch().stream(crds.list_cluster_custom_object, "fortinet.com", "v1", "fortigates",
                                      resource_version=FGTS_RESOURCE_VERSION, timeout_seconds=timeout)
        count=15
        for event in stream:
            operation = event['type']
            obj = event["object"]
            metadata = obj.get("metadata")
            if metadata:
                if metadata['name'] == fgt_co['metadata']['name']:
                    print("Handling %s on %s" % (operation, metadata['name']))
                    pprint(obj)
                    update_fgt(operation, obj, fgt_co)
                # update the version # to not process old events
                FGTS_RESOURCE_VERSION = metadata['resourceVersion']
            else:
                # assume that the stream is having issue and resync to the last good version getting ERROR too old msg
                if operation == "ERROR":
                    FGTS_RESOURCE_VERSION = crds.list_cluster_custom_object("fortinet.com", "v1", "fortigates")['metadata']['resourceVersion']
            count -= 1
            if not count:
                watch.stop()
        print("end processing FGTs events %s" % FGTS_RESOURCE_VERSION)


##ENDPOINTS WATCH
        count = 15
        w = watch.Watch()
        # tried with  field_selector="metadata.namespace!=kube-system" but end in error in API
        for event in w.stream(v1.list_endpoints_for_all_namespaces,
                              resource_version=endpoints_resource_version,timeout_seconds=timeout):
            object=event.get("object")
            operation = event['type']
            if operation == "ERROR":
                endpoints_resource_version = v1.list_endpoints_for_all_namespaces().metadata.resource_version
                # just adding a lb-fgt def do nothing you must have a service set up with annotations
            if object.metadata.namespace != "kube-system" and object.metadata.labels:
                print("in endp handler with list app %s" % list_of_applications)
                pprint(object.metadata.labels)
                if object.metadata.labels['app'] in list_of_applications:
                    if operation != "ERROR":
                        update_endp_for_service(object)
                        # force monitor check to reflect faster the changes
                        monitor_lb_co_status()
                    print("Endp event: %s %s / %s" % (event['type'], object.metadata.name, object.metadata.namespace ))
            ## should get the max # in the list dict and +1 len of dict can result in colisions
            # for finding the id in realserver struct
            #actually the endpoint update object resend the full list of endp so being brutal
            endpoints_resource_version=object.metadata.resource_version
            count -= 1
            if not count:
                w.stop()
        print("Finished endpoints stream: %s" % endpoints_resource_version)

        count = 15
        for event in w.stream(v1.list_service_for_all_namespaces, resource_version=SERVICES_RESOURCE_VERSION ,
                              label_selector="app", timeout_seconds=timeout):

            object = event.get("object")
            print("Event: %s %s %s" % (
                event['type'],
                object.kind,
                object.metadata)
                  )
            annotations= json.loads(object.metadata.annotations['kubectl.kubernetes.io/last-applied-configuration'])

            if "lb-fgts.fortigates.fortinet.com/port" in annotations['metadata']['annotations']:
                ## if this annotation is on then we create/update a loadbalancer on fortigate
                #can add "fortigates.fortinet.com/name: myfgt" annotation if multiple FGT
                update_lb_for_service(event['type'],object)
            SERVICES_RESOURCE_VERSION=object.metadata.resource_version
            count -= 1
            if not count:
                w.stop()
        print("Finished service stream rev: %s" % SERVICES_RESOURCE_VERSION )

