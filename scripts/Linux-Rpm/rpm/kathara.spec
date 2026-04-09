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
python3.13 -m venv %{_builddir}/venv
%{_builddir}/venv/bin/pip install --upgrade pip
%{_builddir}/venv/bin/pip install -r src/requirements.txt
%{_builddir}/venv/bin/pip install pyinstaller
%{_builddir}/venv/bin/pip install pytest

%build
%{_builddir}/venv/bin/python -m pytest
cd src && %{_builddir}/venv/bin/pyinstaller --distpath=./kathara.dist --workpath=./kathara.build kathara.spec

%install
rm -rf %{buildroot}
install -d %{buildroot}%{_libdir}/kathara
cp -r %{_builddir}/%{buildsubdir}/src/kathara.dist/kathara/_internal %{buildroot}%{_libdir}/kathara/_internal
find %{buildroot}%{_libdir}/kathara/_internal -type f -exec chmod 644 {} \;
install -p -m 2755 -g 962 %{_builddir}/%{buildsubdir}/src/kathara.dist/kathara/kathara %{buildroot}%{_libdir}/kathara/
install -d -m 755 %{buildroot}%{_bindir}
ln -sf %{_libdir}/kathara/kathara %{buildroot}%{_bindir}/kathara
install -d -m 755 %{buildroot}%{_mandir}
cp -r %{_builddir}/%{buildsubdir}/manpages/* %{buildroot}%{_mandir}/
install -d -m 755 %{buildroot}%{_sysconfdir}/bash_completion.d/
install -p -m 644 %{_builddir}/%{buildsubdir}/kathara.bash-completion %{buildroot}%{_sysconfdir}/bash_completion.d/

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
%{_libdir}/kathara/kathara wipe -f -a &> /dev/null || true

%changelog
*  __DATE__ Kathara Team <******@kathara.org> - __VERSION__-__PACKAGE_VERSION__
- Add possibility to keep collision domains when undeploying a network scenario
- Fix tmux DeprecatedError
- Minor fixes