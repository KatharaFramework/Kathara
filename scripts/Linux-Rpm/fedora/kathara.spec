Name:           kathara
Version:	__VERSION__
Release:        1%{?dist}
Summary:	Network emulation tool.
Group: 		Applications/Emulators
License:	GPLv3
URL:		https://www.kathara.org/
Source:		%{name}-%{version}.tar.gz
BuildRequires:	bash-completion

%description
Network emulation tool.
It is an implementation of the notorious Netkit using Python.  
Ten times faster than Netkit and more than 100 times lighter, the framework has the performances to run in production.

%prep
%autosetup
python3 -m pip install -r requirements.txt
python3 -m pip install nuitka


%build
python3 -m nuitka --show-progress --plugin-enable=pylint-warnings --follow-imports --standalone --include-plugin-directory=Resources kathara.py


%install
rm -rf $RPM_BUILD_ROOT
cp -r $(CURDIR)/kathara.dist/* %{buildroot}/usr/lib/kathara/
chmod 400 $(CURDIR)/debian/kathara/usr/lib/kathara/*.so*
chmod 755 $(CURDIR)/debian/kathara/usr/lib/kathara/kathara


%files
%license add-license-file-here
%doc add-docs-here

%changelog
*  __DATE__ Mariano Scazzariello <******@gmail.com> - __VERSION__-__PACKAGE_VERSION__
- Minor fixes
