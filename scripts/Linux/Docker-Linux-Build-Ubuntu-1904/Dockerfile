FROM ubuntu:19.04

RUN apt update \
	&& DEBIAN_FRONTEND=noninteractive apt upgrade -y \
	&& apt install -y \
		apt-utils \
		debhelper \
		python3 \
		python3-dev \
		python3-pip \
		libxml2-dev \
		zlib1g-dev \
		build-essential \
		lintian \
		devscripts \
		git \
		ruby-full

RUN python3 -m pip install nuitka

RUN gem install nokogiri mustache kramdown rubocop sinatra rack rake test-unit

COPY dput.cf /root/.dput.cf

WORKDIR /opt

RUN git clone https://github.com/apjanke/ronn-ng.git
ENV PATH="/opt/ronn-ng/bin:${PATH}"
ENV RUBYOPT="-KU -E utf-8:utf-8"

WORKDIR /opt/kathara/scripts/Linux
