FROM fedora:32

ENV RUBYOPT="-KU -E utf-8:utf-8"

RUN dnf install -y rubygem-rails \
    ruby-devel \
    zlib-devel \
    make \
	python3-devel \
    python3-pip \
    m4 \
	@development-tools \
    fedora-packager \
    rpmdevtools \
    patchelf

RUN dnf remove -y python3-pyroute2

RUN gem install ronn-ng

RUN rpmdev-setuptree

WORKDIR /opt/kathara/scripts/Linux-Rpm
