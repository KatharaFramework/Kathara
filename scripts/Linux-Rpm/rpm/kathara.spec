Name:           kathara
Version:	    __VERSION__
Release:        __PACKAGE_VERSION__%{?dist}
Summary:	    Lightweight network emulation tool
Group: 		    Applications/Emulators
License:	    GPLv3
URL:		    https://www.kathara.org/
Source:		    %{name}-%{version}.tar.gz

%description
A lightweight container-based network emulation tool.

It can be really helpful in showing interactive demos/lessons,
testing production networks in a sandbox environment, or developing
new network protocols.

%global debug_package %{nil}

%prep
%autosetup
python3.11 -m venv %{_builddir}/venv
%{_builddir}/venv/bin/pip install --upgrade pip
%{_builddir}/venv/bin/pip install -r src/requirements.txt
%{_builddir}/venv/bin/pip install nuitka
%{_builddir}/venv/bin/pip install pytest

%build
%{_builddir}/venv/bin/python -m pytest
cd src && %{_builddir}/venv/bin/python -m nuitka --lto=yes --plugin-enable=pylint-warnings --plugin-enable=multiprocessing --follow-imports --standalone --include-plugin-directory=Kathara --output-filename=kathara kathara.py

%install
mv %{_builddir}/%{buildsubdir}/src/kathara.dist %{_builddir}/%{buildsubdir}/kathara.dist
rm -rf %{buildroot}
rm -f %{_builddir}/%{buildsubdir}/kathara.dist/libbz2.so.1.0
rm -f %{_builddir}/%{buildsubdir}/kathara.dist/libexpat.so.1
rm -f %{_builddir}/%{buildsubdir}/kathara.dist/libtinfo.so.6
rm -f %{_builddir}/%{buildsubdir}/kathara.dist/libz.so.1
rm -f %{_builddir}/%{buildsubdir}/kathara.dist/libtinfo.so.5
rm -f %{_builddir}/%{buildsubdir}/kathara.dist/libcrypto.so.1.1
install -d %{buildroot}%{_libdir}/kathara
install -p -m 644 %{_builddir}/%{buildsubdir}/kathara.dist/*.so* %{buildroot}%{_libdir}/kathara/
install -p -m 755 %{_builddir}/%{buildsubdir}/kathara.dist/kathara %{buildroot}%{_libdir}/kathara/
install -d -m 755 %{buildroot}%{_libdir}/kathara/certifi
cp -r %{_builddir}/%{buildsubdir}/kathara.dist/certifi/* %{buildroot}%{_libdir}/kathara/certifi/
install -d -m 755 %{buildroot}%{_libdir}/kathara/pyuv
cp -r %{_builddir}/%{buildsubdir}/kathara.dist/pyuv/* %{buildroot}%{_libdir}/kathara/pyuv/
install -d -m 755 %{buildroot}%{_mandir}
cp -r %{_builddir}/%{buildsubdir}/manpages/* %{buildroot}%{_mandir}/
install -d -m 755 %{buildroot}%{_sysconfdir}/bash_completion.d/
install -p -m 644 %{_builddir}/%{buildsubdir}/kathara.bash-completion %{buildroot}%{_sysconfdir}/bash_completion.d/
mkdir %{buildroot}%{_bindir}
ln -sf %{_libdir}/kathara/kathara %{buildroot}%{_bindir}/kathara

%files
%{_libdir}/kathara/*
%{_mandir}/*
%{_sysconfdir}/bash_completion.d/kathara.bash-completion
%{_bindir}/kathara

%post
if [ $(getent group docker) ]; then
    chown root:docker %{_libdir}/kathara/kathara
fi
chmod g+s %{_libdir}/kathara/kathara

%preun
%{_libdir}/kathara/kathara wipe -f -a 2> /dev/null || true

%changelog
*  __DATE__ Kathara Team <******@kathara.org> - __VERSION__-__PACKAGE_VERSION__
- Add the possibility to mount additional volumes on devices using the "volume" metadata
- Allow to run a single device in privileged mode using the "privileged" metadata
- Add the possibility to specify custom entrypoint and arguments for a device using the "entrypoint" and "args" metadata
- Allow specifying per-network-scenario "kathara.conf" configuration file
- (Python API) Add "retrieve_files" method to copy files from devices to the host
- Minor fixes