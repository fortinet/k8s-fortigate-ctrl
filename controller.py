#K8S controller to have a load balancer on a fortigate
# use and manipulate CRD for fortigates load balancer fortigates.
# Use 1 controller per Fortigate the controller can create multiple LB per FGT.

import logging
import json
import yaml
from kubernetes import client, config, watch
import os
from pprint import pprint
from fortiosapi import FortiOSAPI

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

def fgt_logcheck():
    try:
        ret = fgt.get('firewall', 'vip', vdom=vdom) #TODO get vdom from CRD
    except e:
        pass

def update_lb_for_service(operation,object):
    #port to listen on
    #app-label must be json with the changes to make
    # check the crd is there and good
    if operation == "ADDED" or operation == "MODIFIED":
        metadata=object.metadata
        print("adding service :%s" % metadata.name)
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
        data["name"] = "K8S_"+metadata.name
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
        ## TODO find vdom in crd
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
        data["name"] = "K8S_"+metadata.name
        data["policyid"] = "4"+annotations['metadata']['annotations']["lb-fgts.fortigates.fortinet.com/port"]
        ##TODO be carefull with hardcoded policyid
        data["extport"]= annotations['metadata']['annotations']["lb-fgts.fortigates.fortinet.com/port"]
        data['dstaddr']= [{"name": "K8S_"+metadata.name}]

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


if __name__ == "__main__":
    print(os.uname().nodename)
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

    if 'KUBERNETES_PORT' in os.environ:
        config.load_incluster_config()
        definition = '/tmp/fortigates-crd.yml'
    else:
        config.load_kube_config()
        definition = 'fortigates-crd.yml'
    configuration = client.Configuration()
    configuration.assert_hostname = False
    api_client = client.api_client.ApiClient(configuration=configuration)
    v1crd = client.ApiextensionsV1beta1Api(api_client)
    current_crds = [x['spec']['names']['kind'].lower() for x in v1crd.list_custom_resource_definition().to_dict()['items']]
    pprint(current_crds)
    if 'fortigate' not in current_crds:
        print("You must apply Fortigates CRD definition first")
        exit(2) # linked to https://github.com/kubernetes-client/python/issues/376
        ##TODO remove when bug is fixed
        data=open(definition)
        body = yaml.safe_load(data)
        v1crd.create_custom_resource_definition(body) # TODO check why this fails but apply works

    crds = client.CustomObjectsApi(api_client)
    fortigates_crd = crds.list_cluster_custom_object(DOMAIN,"v1","fortigates")['items']
    fgt_names = [x['metadata']['name'] for x in fortigates_crd ]
    # update/create the crd of the Fortigate we do control
    #if add on infos is already there we keep it
    for fgt_crd in fortigates_crd:
        pprint(fgt_crd)
        metadata = fgt_crd.get("metadata")
        name = metadata.get("name")
        namespace = metadata.get("namespace")
        ## TODO check and ensure unicity of the controller name etc.. we rely on good crd data here
        if fgt_crd['metadata']['name'] == os.getenv('FGT_NAME'):
            fgt_crd['spec']['controller'] = os.uname().nodename
            print("in the initial setup for fgt-az: %s" % fgt_crd['metadata']['name'])
            fgt_crd['spec']['user'] = FGT_USER
            fgt_crd['spec']['fgt-ip'] = FGT_IP
            vdom = fgt_crd['spec'].get("vdom")
            if not vdom:
                vdom="root"
                fgt_crd['spec']["vdom"]=vdom
            print(" FGT URL : %s:%s@%s"%(FGT_USER,FGT_PASSWD,FGT_IP))
            fgt.login(FGT_IP , FGT_USER, password=FGT_PASSWD, verify=False)
            try:
                fgt_crd['spec']['fgt-publicip']=fgt.license()['results']['fortiguard']['fortigate_wan_ip']
            except KeyError:
                print("could not find the FGT public-ip which might be linked to license issue")
                pass
            except e:
                print("ERROR trying to check license")
                pass
            crds.replace_namespaced_custom_object(DOMAIN, "v1", namespace, "fortigates", name, fgt_crd)
            fgt_crd['status']={ 'status': "connected" }
            ##this only update the status even when the spec is changed need both
            crds.replace_namespaced_custom_object_status(DOMAIN, "v1", namespace, "fortigates", name, fgt_crd )
            # make the list/specs available globally
            crtled_fgt_crd=fgt_crd
    ##resource_versions are used to watch streams of change and not re run from beggining
    fgts_resource_version = fgt_crd['metadata']['resourceVersion']
    lb_fgts_resource_version = 0
    endpoints_resource_version = 0
    services_resource_version = 0
    # Global list of applications for which we manage LB
    list_of_applications =[]
    timeout=2 #make it small for dev TODO increase in prod
    count=15
    print("")
    print('_____________________________')

v1 = client.CoreV1Api()
while True:
        ##will need to be carefull on the order of checks to be sure
        DOMAIN="fortigates.fortinet.com"
        ## Watch and react to change on loadbalancerfortigate CRD (= changes to LB configs)
        stream = watch.Watch().stream(crds.list_cluster_custom_object, DOMAIN, "v1", "lb-fgts",
                                      resource_version= lb_fgts_resource_version, timeout_seconds=timeout)
        count = 15
        for event in stream:
            operation = event['type']
            obj = event["object"]
            metadata = obj.get("metadata")
            print("Handling %s on %s" % (operation, name))
            pprint(obj)
            # update the version # to not process old events
            count -= 1
            if not count:
                watch.stop()
            if metadata:
                lb_fgts_resource_version = metadata['resourceVersion']
            else:
                # assume that the stream is having issue and resync to the last good version
                if operation == "ERROR":
                    lb_fgts_resource_version= crds.list_cluster_custom_object( DOMAIN, "v1", "lb-fgts")['metadata']['resourceVersion']
        print("end processing LB FGTs events %s" % lb_fgts_resource_version)

        ## Watch and react to change on fortigates CRD (= changes to FGT config)
        stream = watch.Watch().stream(crds.list_cluster_custom_object, "fortinet.com", "v1", "fortigates",
                                      resource_version=fgts_resource_version, timeout_seconds=timeout)
        count=15
        for event in stream:
            pprint(event)
            operation = event['type']
            obj = event["object"]
            metadata = obj.get("metadata")
            if metadata:
                if metadata['name'] == fgt_crd['metadata']['name']:
                    print("Handling %s on %s" % (operation, name))
                    pprint(obj)
                    update_fgt(operation, obj, fgt_crd)
                # update the version # to not process old events
                fgts_resource_version = metadata['resourceVersion']
            else:
                # assume that the stream is having issue and resync to the last good version getting ERROR too old msg
                if operation == "ERROR":
                    fgts_resource_version = crds.list_cluster_custom_object("fortinet.com", "v1", "fortigates")['metadata']['resourceVersion']
            count -= 1
            if not count:
                watch.stop()
        print("end processing FGTs events %s" % fgts_resource_version)



        count = 50
        w = watch.Watch()
        # tried with  field_selector="metadata.namespace!=kube-system" but end in error in API
        for event in w.stream(v1.list_endpoints_for_all_namespaces,
                              resource_version=endpoints_resource_version,timeout_seconds=timeout):
            object=event.get("object")
            if object.metadata.namespace != "kube-system":
                print("Event: %s %s / %s" % (event['type'], object.metadata.name, object.metadata.namespace ))
            count -= 1
            endpoints_resource_version=object.metadata.resource_version
            if not count:
                w.stop()
        print("Finished endpoints stream: %s" % endpoints_resource_version)
    ##
        for event in w.stream(v1.list_service_for_all_namespaces, resource_version=services_resource_version ,
                              label_selector="app", timeout_seconds=timeout):
            object = event.get("object")
            annotations= json.loads(object.metadata.annotations['kubectl.kubernetes.io/last-applied-configuration'])
            print("Event: %s %s %s" % (
                event['type'],
                object.kind,
                annotations['metadata'])
            )
            if "lb-fgts.fortigates.fortinet.com/port" in annotations['metadata']['annotations']:
                ## if this annotation is on then we create/update a loadbalancer on fortigate
                #can add "fortigates.fortinet.com/name: myfgt" annotation if multiple FGT
                update_lb_for_service(event['type'],object)
            services_resource_version=object.metadata.resource_version
            count -= 1
            if not count:
                w.stop()
        print("Finished service stream rev: %s" % services_resource_version )

