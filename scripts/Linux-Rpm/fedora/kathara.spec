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


%build
python3 -m nuitka --show-progress --plugin-enable=pylint-warnings --follow-imports --standalone --include-plugin-directory=Resources kathara.py


%install
rm -rf $RPM_BUILD_ROOT
%make_install


%files
%license add-license-file-here
%doc add-docs-here



%changelog
* Thu Nov 19 10:46:02 UTC 2020 root
