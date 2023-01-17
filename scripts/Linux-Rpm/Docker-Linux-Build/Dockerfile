FROM fedora:36

ENV RUBYOPT="-KU -E utf-8:utf-8"

RUN dnf install -y rubygem-rails \
    ruby-devel \
    zlib-devel \
    make \
    m4 \
    @development-tools \
    @rpm-development-tools \
    @c-development \
    fedora-packager \
    rpmdevtools \
    patchelf \
    pip \
    python3-devel

RUN gem install ronn-ng

RUN rpmdev-setuptree

WORKDIR /opt/kathara/scripts/Linux-Rpm