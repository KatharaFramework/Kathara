Name:           kathara
Version:	    __VERSION__
Release:        __PACKAGE_VERSION__%{?dist}
Summary:	    Lightweight network emulation tool
Group: 		    Applications/Emulators
License:	    GPLv3
URL:		    https://www.kathara.org/
Source:		    %{name}-%{version}.tar.gz
BuildRequires:	python3
BuildRequires:	python3-pip
BuildArch:		x86_64

%description
Lightweight network emulation system based on Docker containers.

It can be really helpful in showing interactive demos/lessons,
testing production networks in a sandbox environment, or developing
new network protocols.

%global debug_package %{nil}

%prep
%autosetup
python3 -m pip install -r src/requirements.txt
python3 -m pip install nuitka
python3 -m pip install pytest

%build
python3 -m pytest
cd src && python3 -m nuitka --plugin-enable=pylint-warnings --plugin-enable=multiprocessing --follow-imports --standalone --include-plugin-directory=Kathara kathara.py

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
- (Docker) Add possibility to share the same collision domains between different users
- (Docker) Add possibility to connect to a remote Docker daemon instead of local one (only on UNIX systems)
- (Docker) Checks on external interfaces are now always executed, even if the collision domain already exists
- (Kubernetes) Fix ltest, which never terminated due to a bug in "copy_files"
- Hidden files in a machine folder (like .htaccess) are now correctly copied into the container
- Commands are now accepted only if they are entirely lowercase
- Minor fixes (better lab integrity checks, better file I/O checks)
