FROM fortinetsolutioncse/k8s-fgt-base
LABEL maintainer="Nicolas Thomas <nthomas@fortinet.com>" provider="community"
ARG FGTCA_BUILD
ENV DEBIAN_FRONTEND=noninteractive
ENV FGTCA none
ENV FGT_SECRET none
ENV FGT_URL none
##to pass access to FGT as user@X.X.X.X
ADD controller.py /tmp
ADD fortigates-crd.yml /tmp

ENTRYPOINT  ["python3", "-u", "/tmp/controller.py"]
