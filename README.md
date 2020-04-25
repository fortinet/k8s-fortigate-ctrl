# k8s-ctrl-fortigate
K8S controller for fortigate in python

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
    service.beta.kubernetes.io/fortigate-load-balancer: "true"
    lb.fortigate.fortinet.com/name: "myfgt"
    lb.fortigate.fortinet.com/policy: {type: ctrl|fmg|manual, }
    lb.fortigate.fortinet.com/externalip: X.X.X.X
    lb.fortigate.fortinet.com/application-profile: "true"
    lb.fortigate.fortinet.com/https-cert: ??  ## TODO figure what we can do here to ref or load a cert
```


# usage

