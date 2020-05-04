FROM fortinetsolutioncse/k8s-fgt-base
LABEL maintainer="Nicolas Thomas <nthomas@fortinet.com>" provider="community"

ADD controller.py /tmp
ADD fortigates-crd.yml /tmp

ENTRYPOINT  ["python", "-u", "/tmp/controller.py"]
