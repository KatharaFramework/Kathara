FROM kathara/quagga:10
RUN mkdir -p /var/run/netns

ADD ./requirements.txt /
#######################Kathara################################

RUN apt-key adv --keyserver keyserver.ubuntu.com --recv-keys 21805A48E6CBBA6B991ABE76646193862B759810
COPY kathara.list /etc/apt/sources.list.d
RUN apt update
RUN apt install python3-pip xterm kathara -y
RUN python3 -m pip install -r requirements.txt

####################DIND###################################
# Install Docker from Docker Inc. repositories.
RUN curl -sSL https://get.docker.com/ | sh

ADD ./katharanp /var/lib/docker/plugins/7e2438b0d2dc2316a820469416abe782f87e1e4009d4606a47255f2a45db833e/

# Install the magic wrapper.
ADD ./wrapdocker /usr/local/bin/wrapdocker
RUN chmod +x /usr/local/bin/wrapdocker

# Define additional metadata for our image.
VOLUME /var/lib/docker
CMD ["wrapdocker"]



