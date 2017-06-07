%if 0%{?fedora} || 0%{?rhel}
%global use_python3 0
%global use_python2 1
%global pythonbin %{__python2}
%global python_sitelib %{python2_sitelib}
%else
%else
%global use_python3 0
%global use_python2 1
%if 0%{?__python2:1}
%global pythonbin %{__python2}
%global python_sitelib %{python2_sitelib}
%else
%global pythonbin %{__python}
%global python_sitelib %{python_sitelib}
%endif
%endif
%{!?python_sitelib: %define python_sitelib %(%{pythonbin} -c "from distutils.sysconfig import get_python_lib; print get_python_lib()")}

%if 0%{?copr}
%define build_timestamp .%(date +"%Y%m%d%H%M%%S")
%else
%define build_timestamp %{nil}
%endif

Name: apb
Version: 0.1.1
Release: 1%{build_timestamp}%{?dist}
Summary: Ansible Playbook Bundle (APB) is a lightweight application definition (meta-container).

Group: Development/Tools
License: GPLv2
URL: https://github.com/openshift/ansible-service-broker
Source0: %{name}-%{version}.tar.gz

BuildArch: noarch
%if 0%{?use_python3}
BuildRequires: python3-devel
BuildRequires: python3-setuptools
BuildRequires: python3-pip
Requires: python3-PyYAML >= 3.10
Requires: python3-PyYAML < 4
%else
BuildRequires: python-devel
BuildRequires: python-setuptools
BuildRequires: python-pip
Requires: PyYAML >= 3.10
Requires: PyYAML < 4
%endif
Requires: docker
Requires: python-docker >= 2.1.0
Requires: python-docker < 3.0.0
Requires: python-jinja2 >= 2.7.2
Requires: python-requests2 >= 2.10.0

%description
Ansible Playbook Bundle (APB) is a lightweight application definition (meta-containers). APB
has the following features:

%prep
%setup -q -n %{name}-%{version}

%build
%{pythonbin} setup.py build

%install
rm -rf $RPM_BUILD_ROOT
%{pythonbin} setup.py install -O1 --skip-build --root $RPM_BUILD_ROOT
install -d -m 755 $RPM_BUILD_ROOT/%{_mandir}/man1/
cp docs/apb.1 $RPM_BUILD_ROOT/%{_mandir}/man1/apb.1

%clean
rm -rf $RPM_BUILD_ROOT


%files
%{_bindir}/apb
%dir %{python_sitelib}/apb
%{python_sitelib}/apb/*
%{python_sitelib}/apb-*.egg-info
%{_mandir}/man1/apb.1*

%changelog
