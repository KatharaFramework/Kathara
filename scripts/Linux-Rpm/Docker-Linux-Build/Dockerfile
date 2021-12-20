FROM fedora:32

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
    patchelf

RUN dnf install -y wget \
    openssl-devel \
    bzip2-devel \
    ncurses-devel \
    sqlite-devel \
    libffi-devel && \
 wget https://www.python.org/ftp/python/3.9.9/Python-3.9.9.tgz && \
 tar xfvz Python-3.9.9.tgz && cd Python-3.9.9 && \
 ./configure --enable-optimizations && \
 make -j8 && \
 make install && \
 dnf remove -y wget && \
 cd .. && rm -Rf Python3.9.9*

RUN gem install ronn-ng

RUN rpmdev-setuptree

WORKDIR /opt/kathara/scripts/Linux-Rpm