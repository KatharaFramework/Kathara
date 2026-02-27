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
cd src && %{_builddir}/venv/bin/pyinstaller \
    --name kathara \
    --strip \
    --console \
    --noconfirm \
    --hidden-import=Kathara \
    --hidden-import=Kathara.cli \
    --hidden-import=Kathara.cli.command \
    --hidden-import=Kathara.cli.command.CheckCommand \
    --hidden-import=Kathara.cli.command.ConnectCommand \
    --hidden-import=Kathara.cli.command.ExecCommand \
    --hidden-import=Kathara.cli.command.LcleanCommand \
    --hidden-import=Kathara.cli.command.LinfoCommand \
    --hidden-import=Kathara.cli.command.ListCommand \
    --hidden-import=Kathara.cli.command.LrestartCommand \
    --hidden-import=Kathara.cli.command.LstartCommand \
    --hidden-import=Kathara.cli.command.LconfigCommand \
    --hidden-import=Kathara.cli.command.SettingsCommand \
    --hidden-import=Kathara.cli.command.VcleanCommand \
    --hidden-import=Kathara.cli.command.VconfigCommand \
    --hidden-import=Kathara.cli.command.VstartCommand \
    --hidden-import=Kathara.cli.command.WipeCommand \
    --hidden-import=Kathara.cli.ui \
    --hidden-import=Kathara.cli.ui.setting \
    --hidden-import=Kathara.cli.ui.setting.DockerOptionsHandler \
    --hidden-import=Kathara.cli.ui.setting.KubernetesOptionsHandler \
    --hidden-import=Kathara.manager \
    --hidden-import=Kathara.manager.Kathara \
    --hidden-import=Kathara.manager.docker \
    --hidden-import=Kathara.manager.docker.DockerManager \
    --hidden-import=Kathara.manager.kubernetes \
    --hidden-import=Kathara.manager.kubernetes.KubernetesManager \
    --hidden-import=Kathara.setting \
    --hidden-import=Kathara.setting.addon \
    --hidden-import=Kathara.setting.addon.DockerSettingsAddon \
    --hidden-import=Kathara.setting.addon.KubernetesSettingsAddon \
    --additional-hooks-dir=. \
    --paths=. \
    kathara.py

%install
mv %{_builddir}/%{buildsubdir}/src/dist/kathara %{_builddir}/%{buildsubdir}/kathara.dist
rm -rf %{buildroot}
rm -f %{_builddir}/%{buildsubdir}/kathara.dist/libbz2.so.1.0
rm -f %{_builddir}/%{buildsubdir}/kathara.dist/libexpat.so.1
rm -f %{_builddir}/%{buildsubdir}/kathara.dist/libtinfo.so.6
rm -f %{_builddir}/%{buildsubdir}/kathara.dist/libz.so.1
rm -f %{_builddir}/%{buildsubdir}/kathara.dist/libtinfo.so.5
rm -f %{_builddir}/%{buildsubdir}/kathara.dist/libcrypto.so.1.1
install -d %{buildroot}%{_libdir}/kathara
cp -r %{_builddir}/%{buildsubdir}/kathara.dist/_internal %{buildroot}%{_libdir}/kathara/_internal
find %{buildroot}%{_libdir}/kathara/_internal -type f -exec chmod 644 {} \;
install -p -m 2755 -g 962 %{_builddir}/%{buildsubdir}/kathara.dist/kathara %{buildroot}%{_libdir}/kathara/
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
%{_libdir}/kathara/kathara wipe -f -a 2> /dev/null || true

%changelog
*  __DATE__ Kathara Team <******@kathara.org> - __VERSION__-__PACKAGE_VERSION__
- Add a configurable setting to manage volume mounting behavior
- Remove `--xterm` parameter from `vstart`/`lstart` commands
- Remove the `pyuv` dependency
- Add a timeout while checking for new releases on GitHub
- Add a timeout while checking for new versions of Docker images
- Minor fixes