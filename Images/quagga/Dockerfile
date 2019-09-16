FROM kathara/base

RUN apt update
RUN apt upgrade -y

RUN wget http://snapshot.debian.org/archive/debian/20161019T045440Z/pool/main/q/quagga/quagga_1.0.20160315-3_amd64.deb

RUN dpkg -i quagga_1.0.20160315-3_amd64.deb || true

RUN DEBIAN_FRONTEND=noninteractive apt install -y \
	cron \
	logrotate

RUN dpkg -i quagga_1.0.20160315-3_amd64.deb

RUN apt-mark hold quagga

RUN rm quagga_1.0.20160315-3_amd64.deb

RUN apt clean

RUN ln /etc/init.d/quagga /etc/init.d/zebra
RUN ln -s /etc/quagga /etc/zebra