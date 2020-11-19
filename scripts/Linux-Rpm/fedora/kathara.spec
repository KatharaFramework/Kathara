Name:           kathara
Version:	    __VERSION__
Release:        1%{?dist}
Summary:	    Network emulation tool.
Group: 		    Applications/Emulators
License:	    GPLv3
URL:		    https://www.kathara.org/
Source:		    %{name}-%{version}.tar.gz
BuildRequires:	bash-completion

%description
Network emulation tool.
It is an implementation of the notorious Netkit using Python.  
Ten times faster than Netkit and more than 100 times lighter, the framework has the performances to run in production.

%global debug_package %{nil}

%prep
%autosetup
python3 -m pip install -r requirements.txt
python3 -m pip install nuitka

%build
python3 -m nuitka --show-progress --plugin-enable=pylint-warnings --follow-imports --standalone --include-plugin-directory=Resources kathara.py

%install
rm -rf %{buildroot}
rm -f %{_builddir}/%{buildsubdir}/kathara.dist/libbz2.so.1.0
rm -f %{_builddir}/%{buildsubdir}/kathara.dist/libexpat.so.1
rm -f %{_builddir}/%{buildsubdir}/kathara.dist/libtinfo.so.6
rm -f %{_builddir}/%{buildsubdir}/kathara.dist/libz.so.1
rm -f %{_builddir}/%{buildsubdir}/kathara.dist/libtinfo.so.5
rm -f %{_builddir}/%{buildsubdir}/kathara.dist/libcrypto.so.1.1
install -d %{buildroot}%{_libdir}/kathara
install -p -m 400 %{_builddir}/%{buildsubdir}/kathara.dist/*.so* %{buildroot}%{_libdir}/kathara/
install -p -m 755 %{_builddir}/%{buildsubdir}/kathara.dist/kathara %{buildroot}%{_libdir}/kathara/
install -d -m 755 %{buildroot}%{_mandir}
cp -r %{_builddir}/%{buildsubdir}/manpages/* %{buildroot}%{_mandir}/
install -d -m 755 %{buildroot}%{_sysconfdir}/bash_completion.d/
install -p -m 644 %{_builddir}/%{buildsubdir}/kathara.bash-completion %{buildroot}%{_sysconfdir}/bash_completion.d/

%files
%{_libdir}/*
%{_mandir}/*
%{_sysconfdir}/bash_completion.d/kathara.bash-completion

%post
if [ $(getent group docker) ]; then
    chown root:docker %{_libdir}/kathara/kathara
fi
chmod g+s %{_libdir}/kathara/kathara
ln -sf %{_libdir}/kathara/kathara %{_bindir}/kathara

%preun
%{_libdir}/kathara/kathara wipe -f -a 2> /dev/null || true

%changelog
*  __DATE__ Mariano Scazzariello <******@gmail.com> - __VERSION__-__PACKAGE_VERSION__
- Minor fixes
