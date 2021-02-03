FROM kathara/base:10

RUN apt update
RUN apt upgrade -y
RUN DEBIAN_FRONTEND=noninteractive apt install -y quagga

RUN apt clean

RUN mkdir /var/log/quagga
RUN chmod -R 777 /var/log/quagga
RUN ln -s /var/log/quagga /var/log/zebra
RUN ln -s /etc/quagga /etc/zebra

COPY zebra.conf /etc/quagga/zebra.conf
RUN chown quagga:quagga /etc/quagga/zebra.conf
RUN chmod 640 /etc/quagga/zebra.conf

COPY debian.conf /etc/quagga/debian.conf
RUN chown quagga:quagga /etc/quagga/debian.conf
RUN chmod 640 /etc/quagga/debian.conf

COPY quagga /etc/init.d/quagga
RUN chown root:root /etc/init.d/quagga
RUN chmod 0755 /etc/init.d/quagga