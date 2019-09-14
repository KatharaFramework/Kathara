FROM kathara/base

RUN apt update
RUN apt upgrade -y
RUN DEBIAN_FRONTEND=noninteractive apt install -y \
	quagga \
	quagga-core

RUN apt clean