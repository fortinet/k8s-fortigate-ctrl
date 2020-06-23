# k8s-fortigate-ctrl

K8S controller for using fortigates as load balancers 
THIS IS ALPHA DEMO CODE ! 
It is functionnal.
Code provided as is (see License) PR are welcome

# Goals
- use loadbalancer annotation to implement LB in Fortigate
- in python thanks https://github.com/karmab/samplecontroller/
- and https://github.com/kubernetes-client/python especially examples
- use fortiospai
- Use one CRD per LB created
- Allow multiple fortigates
- create a loop watch endpoint changes -> change on FGT, once in while do a get.
- LB http for now, use endpoints as targets
- use annotation on services like:

```shell script
apiVersion: v1
kind: Service
metadata:
  name: azure-vote2-front
  labels:
    app: azure-vote2-front
  annotations:
    lb-fgts.fortigates.fortinet.com/port: "90"
    service.beta.kubernetes.io/azure-load-balancer-internal: "true"
    fortigates.fortinet.com/name: "fgt-az1"
spec:
  type: LoadBalancer
  # may try nodeport type to see if works better for K8S connector
  ports:
  - port: 80
  selector:
    app: azure-vote2-front
```

# get started

The controller will use or create the necessary custom ressources fortigate and lb-fgts.



Annotation or config-map on the controllers for the FGT ip.

# usage
# Tips
To have a nice monitoring of kubectl states

````shell script
watch -c "kubectl get pods,lb-fgt,svc -o wide|ccze -A"
````
