# Developmeeent documentation / choice reuse

can be dev with microk8s, mnikube etc.. and 1 VM with Fortigate on the side, ideally on the network using a nic on Dockerd bridge for dev.
## Decisions

1 controller per fortigate allowing to use secret for the API access.
Controller name controlled by hostname or declaratif (avoid duplicate)
If crd for a FGT delete controller must kill itself.

Multiple LB per FGT, might need LB type HTTP, HTTPS, TCP... won't work for https.. 
Need a CRD per LB !!

##types CRD
you must use :
```shell script
 kubectl apply -f fortigates-crd.yml --force
```
For type to be LoadBalancer

## TTD
