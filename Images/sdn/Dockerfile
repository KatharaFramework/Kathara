FROM kathara/base

RUN apt update
RUN DEBIAN_FRONTEND=noninteractive apt upgrade -y
RUN DEBIAN_FRONTEND=noninteractive apt install -y \
	python-pip \
    openvswitch-common \
    openvswitch-switch \
    gcc \
    python-dev \
    libffi-dev \
    libssl-dev \
    libxml2-dev \
    libxslt1-dev \
    zlib1g-dev

RUN pip install --no-cache-dir ryu

RUN apt clean