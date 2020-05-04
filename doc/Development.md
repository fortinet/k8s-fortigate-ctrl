# Developmeeent documentation / choice reuse

can be dev with microk8s, mnikube etc.. and 1 VM with Fortigate on the side, ideally on the network using a nic on Dockerd bridge for dev.
## Decisions

1 controller per fortigate allowing to use secret for the API access.
Controller name controlled by hostname or declaratif (avoid duplicate)
If crd for a FGT delete controller must kill itself.

Multiple LB per FGT, might need LB type HTTP, HTTPS, TCP... won't work for https.. 
Need a CRD per LB !!


## TTD

## addons creating TAPs (Deamonset)
Should be available with :
Set traffic mirror rules to capture all traffic of TEST_DEVICE_IP_ADDRESS to MONITORING_COMPUTER_IP_ADDRESS. Add iptables rules to mirror upstream and downstream traffic.
```shell script
iptables -A PREROUTING -t mangle -i docker0 ! -d <TEST_DEVICE_IP_ADDRESS> -j TEE --gateway <MONITORING_WORKSTATION_IP_ADDRESS>
iptables -A POSTROUTING -t mangle -o docker0 ! -s <TEST_DEVICE_IP_ADDRESS> -j TEE --gateway <MONITORING_WORKSTATION_IP_ADDRESS>
```

Should be readable from a one-arm sniffer on the target.

## References
https://github.com/mkevac/goduplicator might worth a look too.
https://github.com/session-replay-tools to check
