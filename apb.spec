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
Version: 1.2.3
Release: 1%{build_timestamp}%{?dist}
Summary: Ansible Playbook Bundle (APB) is a lightweight application definition (meta-container).

Group: Development/Tools
License: GPLv2
URL: https://github.com/openshift/ansible-service-broker
Source0: https://github.com/ansibleplaybookbundle/ansible-playbook-bundle/archive/%{name}-%{version}.tar.gz

BuildArch: noarch
%if 0%{?use_python3}
BuildRequires: python3-devel
BuildRequires: python3-setuptools
Requires: python3-PyYAML >= 3.10
Requires: python3-PyYAML < 4
Requires: python3-docker >= 2.1.0
Requires: python3-docker < 3.0.0
Requires: python-openshift >= 1:0.4.0
Requires: python3-jinja2 >= 2.7.2
Requires: python3-requests >= 2.6.0
%else
BuildRequires: python-devel
BuildRequires: python-setuptools
Requires: PyYAML >= 3.10
Requires: PyYAML < 4
Requires: python-docker >= 2.1.0
Requires: python-docker < 3.0.0
Requires: python-openshift >= 1:0.4.0
Requires: python-jinja2 >= 2.7.2
Requires: python-requests >= 2.6.0
%endif
Requires: docker

%description
Ansible Playbook Bundle (APB) is a lightweight application definition (meta-containers). APB
has the following features:

%package container-scripts
Summary: scripts required for running apb in a container
BuildArch: noarch
Requires: %{name}

%description container-scripts
containers scripts for apb

%prep
%setup -q -n %{name}-%{version}

%build
%{pythonbin} setup.py build

%install
rm -rf $RPM_BUILD_ROOT
%{pythonbin} setup.py install -O1 --skip-build --root %{buildroot}
install -d -m 755 %{buildroot}/%{_mandir}/man1/
cp docs/apb.1 %{buildroot}/%{_mandir}/man1/apb.1
install -d  %{buildroot}%{_bindir}
install -m 755 apb-wrapper %{buildroot}%{_bindir}/apb-wrapper

%clean
rm -rf $RPM_BUILD_ROOT

%files
%{_bindir}/apb
%dir %{python_sitelib}/apb
%{python_sitelib}/apb/*
%{python_sitelib}/apb-*.egg-info
%{_mandir}/man1/apb.1*

%files container-scripts
%{_bindir}/apb-wrapper

%changelog
* Wed Apr 25 2018 David Zager <david.j.zager@gmail.com> 1.2.3-1
-  Don't force the use of the containerised apb tools in Makefile commands, apb
  should be installed locally using one of the recommended approaches
  https://github.com/ansibleplaybookbundle/ansible-playbook-
  bundle/blob/master/docs/apb_cli.md#installing-the-apb-tool (#263)
  (m.nairn@gmail.com)
- Added fix if using pip newer than 9.0.3 (#266) (jwmatthews@gmail.com)
- Add example using oc new-app instead of apb push (#257) (dymurray@redhat.com)

* Thu Apr 19 2018 David Zager <david.j.zager@gmail.com> 1.2.2-1
- Bug 1569220 - Add developer documentation on using asb_dashboard_url (#264)
  (dymurray@redhat.com)
- Fix links to ASB (#262) (SaravanaStorageNetwork@users.noreply.github.com)

* Wed Apr 11 2018 David Zager <david.j.zager@gmail.com> 1.2.1-1
- Update developers.md to include parameter validation information (#260)
  (dymurray@redhat.com)
- Bump version (#255) (dzager@redhat.com)
- Add a command to refresh all the catalog data (#259) (rhallise@redhat.com)
- Bug 1554138 - Address potential issue where user is forbidden from broker
  namespace (#250) (dymurray@redhat.com)
- add instructions for custom error message (#248) (jkim@redhat.com)
- chore: Minor doc fixes + fix of an error message (#249) (roland@ro14nd.de)
- Add docs teaching APB authors how to consume proxy settings. (#247)
  (derekwhatley@gmail.com)
- Bug 1476330 - Add a check for 3.7 development endpoint (#246)
  (dymurray@redhat.com)
- Openshift doc changed, and routes are now on the network section
  (#239) (matzew@apache.org)

* Mon Mar 05 2018 David Zager <david.j.zager@gmail.com> 1.1.15-1
- Bug 1550017 - Add ability to remove locally pushed APBs (#240)
  (dymurray@redhat.com)

* Thu Mar 01 2018 Jason Montleon <jmontleo@redhat.com> 1.1.14-1
- Bug 1546843 - Delete images even if registry prefix doesn't match (#238)
  (dymurray@redhat.com)

* Tue Feb 27 2018 David Zager <david.j.zager@gmail.com> 1.1.13-1
- Bug 1546843 - Delete any old images that exist in the registry with apb push
  (#227) (dymurray@redhat.com)

* Mon Feb 26 2018 Jason Montleon <jmontleo@redhat.com> 1.1.12-1
- Make flake happy (#234) (ernelson@redhat.com)
- Add explicit error if user is system:admin (#233) (ernelson@redhat.com)
- Add docker port to setup-network script (#232) (ernelson@redhat.com)

* Mon Feb 26 2018 Jason Montleon <jmontleo@redhat.com>
- Make flake happy (#234) (ernelson@redhat.com)
- Add explicit error if user is system:admin (#233) (ernelson@redhat.com)
- Add docker port to setup-network script (#232) (ernelson@redhat.com)

* Mon Feb 26 2018 Jason Montleon <jmontleo@redhat.com> 1.1.10-1
- Add network setup script (#231) (ernelson@redhat.com)
- Fix Canary. pip install -U pip setuptools is failing (#229)
  (jmontleo@redhat.com)
- Bug 1548543 - Fix minishift SSL Error with latest/downstream (#230)
  (jmontleo@redhat.com)
- Fix doc for apb cli container (#228)
  (1840387+karmab@users.noreply.github.com)

* Tue Feb 13 2018 David Zager <david.j.zager@gmail.com> 1.1.9-1
- Bug 1537599 - Push when running apb test. (#226) (cchase@redhat.com)

* Wed Feb 07 2018 David Zager <david.j.zager@gmail.com> 1.1.8-1
- Remove alias rec (#224) (ernelson@redhat.com)
- Bug 1536687 - Prevent script from running as root (#225)
  (ernelson@redhat.com)

* Fri Feb 02 2018 David Zager <david.j.zager@gmail.com> 1.1.7-1
- Bug 1540487 - Fix apb remove URL suffix (#222) (dymurray@redhat.com)
- Bug 1541339 - Add action name to apb run pod (#221) (dymurray@redhat.com)
- Bug 1523252 - Prepend broker route with https if no schema supplied (#220)
  (dymurray@redhat.com)
- Use the host network namespace with containerized apb-tool (#217)
  (rhallise@redhat.com)
- Bug 1538969 - Add version subcommand to CLI options (#219)
  (dymurray@redhat.com)
- Add support for minishift to apb container (#211) (ernelson@redhat.com)
- Bug 1533318 - Use internal registry in apb run (#210)
  (david.j.zager@gmail.com)

* Tue Jan 23 2018 Jason Montleon <jmontleo@redhat.com> 1.1.6-1
- Bug 1537599 Update the pod_exec call to use kubernetes 4.0 client (#196)
  (cchase@redhat.com)
- Bug 1536963 Updates required to work with openshift 0.4.0 (#209)
  (jmontleo@redhat.com)
- Update apb_cli.md (ernelson@redhat.com)
- Bug 1536687 - Add minishift support (#207) (ernelson@redhat.com)
- Add instructions for testing APBs with docker run. (#208)
  (derekwhatley@gmail.com)

* Wed Jan 17 2018 David Zager <david.j.zager@gmail.com> 1.1.5-1
- Bug 1532972 - Replace needed subcommand argument (#202) (dymurray@redhat.com)

* Tue Jan 16 2018 David Zager <david.j.zager@gmail.com> 1.1.4-1
- Apb run bugfixes (#200) (david.j.zager@gmail.com)
- Update getting_started.md (#199) (josemigallas@gmail.com)
- Update apb_cli docs (#198) (dymurray@redhat.com)
- Remove all old references to apb push -o (#194) (dymurray@redhat.com)
- fixes two minor doc typos (#193) (mhrivnak@hrivnak.org)
- Don't append ansible-service-broker suffix without a check (#192)
  (dymurray@redhat.com)
- Generic tool improvements (#187) (dymurray@redhat.com)

* Mon Jan 08 2018 David Zager <david.j.zager@gmail.com> 1.1.3-1
- Update tito releasers (david.j.zager@gmail.com)
- Use the routing prefix for apb commands (#186) (rhallise@redhat.com)
- fix(doc): correct typos (#189) (dara.hayes@redhat.com)
- Locate the apb route, but avoid the etcd route (#185) (rhallise@redhat.com)
- Added downstream namespace check for getting broker route (#183)
  (dymurray@redhat.com)
- Document the pattern of creating OpenShift and Kubernetes apbs (#171)
  (rhallise@redhat.com)
- Add the ability to create most of a serviceinstance template (#158)
  (rhallise@redhat.com)

* Thu Dec 21 2017 Jason Montleon <jmontleo@redhat.com> 1.1.2-1
- APB Run Command (#178) (david.j.zager@gmail.com)
- Some basic error handling updates and more customization (#176)
  (dymurray@redhat.com)
- Fixes typos (#177) (mhrivnak@hrivnak.org)
- update apb to apb-tools (#175) (phil.brookes@gmail.com)
- Fixes #172 - Update docs for container rename (#173) (jmontleo@redhat.com)

* Mon Dec 04 2017 Jason Montleon <jmontleo@redhat.com> 1.1.1-1
- Fixed minor errors in getting_started.md (cchase@redhat.com)
- Fix example for apb remove. (cchase@redhat.com)
- Issue #169.  Fix relist error when using apb remove. (cchase@redhat.com)
- Add Makefile to apb init (#149) (phil.brookes@gmail.com)
- Update documentation (#165) (cchase@redhat.com)
- bump release (#162) (jmrodri@gmail.com)

* Tue Nov 07 2017 Jason Montleon <jmontleo@redhat.com> 1.0.4-1
- Bug 1507111 - Add docs for apb push -o (#161) (dymurray@redhat.com)
- Bug 1507111 - Add support to push to internal openshift registry (#159)
  (dymurray@redhat.com)
- Adding re-list to remove so that the serviceclass is removed. (#160)
  (Shawn.Hurley21@gmail.com)
- Added bind_parameters to apb list --verbose (#157) (cchase@redhat.com)
- Better error handling when logged out of the cluster (#156)
  (dymurray@redhat.com)
- Added constraint on websockets (#147) (andy.block@gmail.com)

* Mon Oct 23 2017 Jason Montleon <jmontleo@redhat.com> 1.0.3-1
- Add missing version (#153) (matzew@apache.org)
- return url instead of unmodified route (#152) (fabian@fabianism.us)

* Thu Oct 19 2017 Jason Montleon <jmontleo@redhat.com> 1.0.2-1
- fix issue with apb-wrapper (#148) (phil.brookes@gmail.com)
- Fix lint errors (#150) (jmrodri@gmail.com)
- Require user to specify full route, including protocol and routing suffix
  (#146) (fabian@fabianism.us)

* Thu Oct 12 2017 Jason Montleon <jmontleo@redhat.com> 1.0.1-1
- update the releasers (#139) (jmrodri@gmail.com)
- Document binding parameters and asynchronous bind. (#138) (cchase@redhat.com)
- Change broker_resource_url to fix apb relist. (#145) (derekwhatley@gmail.com)
- Fix pip install and errors when docker runs with a gid in use in the
  container (#141) (jmontleo@redhat.com)

* Fri Oct 06 2017 Jason Montleon <jmontleo@redhat.com> 1.0.0-1
- added key= to sorted call for Python 2.7.13 (#135) (cchase@redhat.com)
- Order services by name in apb list (#134) (karimboumedhel@gmail.com)
- Bug 1498613 - Add ability to specify Dockerfile name (#132)
  (dymurray@redhat.com)
- Bug 1498185 - Move version declaration into APB spec (#129)
  (dymurray@redhat.com)

* Wed Oct 04 2017 Jason Montleon <jmontleo@redhat.com> 0.2.5-1
- 1497819 - Remove image (#121) (david.j.zager@gmail.com)
- Changed setup.py URL and changed version in apb init (#128)
  (dymurray@redhat.com)
- Update to version 0.2.6 - pypi upload errors on 0.2.5 (dymurray@redhat.com)
- Bumping to 0.2.5-2 (dymurray@redhat.com)
- Update to 0.2.5 (dymurray@redhat.com)
- Added versioning explanation to developers.md (#127) (dymurray@redhat.com)
- [Proposal] Versioning of APBs (#117) (dymurray@redhat.com)
- Relist support (#124) (ernelson@redhat.com)
- fixing issue 125 (#126) (Shawn.Hurley21@gmail.com)
- adding ability to authenticate to the broker. (#123)
  (Shawn.Hurley21@gmail.com)
- This fixes issue-112. (#113) (Shawn.Hurley21@gmail.com)

* Tue Sep 19 2017 Jason Montleon <jmontleo@redhat.com> 0.2.4-1
- Update README.md (#114) (wmeng@redhat.com)
- Adding fix to apb tool to clean up on failed test pod run (#109)
  Shawn.Hurley21@gmail.com)
- Update display_type and display_group parameter docs to match UI (#106)
  (cfc@chasenc.com)
- Add APB testing to the apb tool (#104) (Shawn.Hurley21@gmail.com)
- Added unit testing setup and skeleton (#101) (jason.dobies@redhat.com)
- Fix alias command in README (#107) (jmontleo@redhat.com)

* Tue Aug 29 2017 Jason Montleon <jmontleo@redhat.com> 0.2.3-1
- new package built with tito

