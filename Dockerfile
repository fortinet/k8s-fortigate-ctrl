# Dockerfile for K8S fortigate controller
#  optionnal if in need to trust a CA for ssl inspection set the FGTCA_BUILD variable
# build cmd:
# on MacOS
#export FGTCA_BUILD=$(base64 Fortinet_CA_SSL.cer -b0)
# on Linux
#export FGTCA_BUILD=$(base64 Fortinet_CA_SSL.cer -w0)
#
# docker build --build-arg FGTCA_BUILD --pull -t fortinetsolutioncse/k8s-fgt-base -f Dockerfile.base .
# docker build --pull -t fortinetsolutioncse/k8s-fortigate-ctrl  .


FROM ubuntu:20.04
LABEL maintainer="Nicolas Thomas <nthomas@fortinet.com>" provider="Community"

RUN apt-get update
ARG FGTCA_BUILD
ENV DEBIAN_FRONTEND=noninteractive
ENV FGTCA none
ENV FGT_NAME none
# name that the K8S crd will use to identify this FGT
ENV FGT_URL none
# format user:password@<fortigate> the credentials to make Fortigate API calls

RUN apt-get install -y ca-certificates lsb-release  python3-pip sudo
RUN groupadd -r ubuntu && useradd  -g ubuntu -G adm,sudo ubuntu -m -p fortinet -s /bin/bash && \
    echo "ubuntu ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/99-nopasswd && chmod 640 /etc/sudoers.d/99-nopasswd

#build arg to allow ssl inspect during build must create a base64 env with the CA in it: export FGTCA=$(base64 Fortinet_CA_SSL.crt -w0)
RUN  (echo "${FGTCA_BUILD}"| base64 -d > /usr/local/share/ca-certificates/Fortinet_CA_SSL.crt; update-ca-certificates)
COPY docker-entrypoint.sh /usr/local/bin/
ENTRYPOINT [ "/usr/local/bin/docker-entrypoint.sh"]

RUN pip3 install kubernetes fortiosapi
RUN apt-get -y upgrade && apt-get clean
# remove the CA used during build and rely on ENV at runtime avoid allowing access in non wanted places
RUN rm -f /usr/local/share/ca-certificates/Fortinet_CA_SSL.crt && update-ca-certificates
##to pass access to FGT as user@X.X.X.X
ADD controller.py /tmp
ADD fortigates.fortinet.com.yml /tmp

ENTRYPOINT  ["python3", "-u", "/tmp/controller.py"]
