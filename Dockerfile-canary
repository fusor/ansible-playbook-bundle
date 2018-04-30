FROM centos:7

RUN yum -y install epel-release centos-release-openshift-origin \
 && yum -y install python-virtualenv git sudo origin-clients wget \
 && yum clean all

RUN virtualenv --no-setuptools /opt/apb
RUN source /opt/apb/bin/activate && wget https://bootstrap.pypa.io/get-pip.py
RUN source /opt/apb/bin/activate && python get-pip.py

RUN git clone https://github.com/ansibleplaybookbundle/ansible-playbook-bundle
RUN source /opt/apb/bin/activate \
 && cd ansible-playbook-bundle \
 && pip install -r src/requirements.txt \
 && python setup.py install
RUN echo -ne "#!/bin/bash\nsource /opt/apb/bin/activate\napb \$@" > /usr/local/bin/apb-wrapper
RUN chmod +x /usr/local/bin/apb-wrapper

RUN echo "ALL ALL=NOPASSWD: ALL" > /etc/sudoers.d/usermod
RUN chmod 666 /etc/passwd
COPY apb-wrapper /usr/local/bin/apb-wrapper
RUN chmod +x /usr/local/bin/apb-wrapper

WORKDIR /mnt

ENTRYPOINT ["apb-wrapper"]
CMD ["-h"]

LABEL RUN docker run --privileged --rm -v \${PWD}:/mnt -v \$HOME/.kube:/.kube -v /var/run/docker.sock:/var/run/docker.sock -u \${SUDO_UID} \${IMAGE}
