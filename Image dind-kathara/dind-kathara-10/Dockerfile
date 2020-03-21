FROM kathara/quagga:10
RUN mkdir -p /var/run/netns

ADD ./requirements.txt /
#######################Kathara################################

RUN apt-key adv --keyserver keyserver.ubuntu.com --recv-keys 21805A48E6CBBA6B991ABE76646193862B759810
COPY kathara.list /etc/apt/sources.list.d
RUN apt update
RUN apt install kathara -y
RUN python3 -m pip install -r requirements.txt

####################DIND###################################
# Install Docker from Docker Inc. repositories.
RUN curl -sSL https://get.docker.com/ | sh

ADD ./ef66521f2fe7ae92ed9c1868391f79631c28a63c2e6e7afbcfd4a8a6ba537680 /var/lib/docker/plugins/ef66521f2fe7ae92ed9c1868391f79631c28a63c2e6e7afbcfd4a8a6ba537680/

# Install the magic wrapper.
ADD ./wrapdocker /usr/local/bin/wrapdocker
RUN chmod +x /usr/local/bin/wrapdocker

# Define additional metadata for our image.
VOLUME /var/lib/docker
CMD ["wrapdocker"]



