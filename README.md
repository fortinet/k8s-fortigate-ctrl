# k8s-ctrl-fortigate
K8S controller for fortigate in python
THIS IS ALPHA DEMO CODE ! 
no support, no help for now you have been warned 
It is functionnal.

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
spec:
  type: LoadBalancer
  # may try nodeport type to see if works better for K8S connector
  ports:
  - port: 80
  selector:
    app: azure-vote2-front
```

The controller will use or create the necessary custom ressources fortigate and lb-fgts.



Annotation or config-map on the controllers for the FGT ip.

# usage
# Tips
To have a nice monitoring of kubectl states

````shell script
watch -c "kubectl get pods,lb-fgt,svc -o wide|ccze -A"
````
