%{!?python_sitelib: %global python_sitelib %(%{__python} -c "from distutils.sysconfig import get_python_lib; print(get_python_lib())")}
%{!?python_sitearch: %global python_sitearch %(%{__python} -c "from distutils.sysconfig import get_python_lib; print(get_python_lib(1))")}

Name: pulp-docker
Version: 2.0.2
Release: 0.1.beta%{?dist}
Summary: Support for Docker layers in the Pulp platform
Group: Development/Languages
License: GPLv2
URL: http://pulpproject.org
Source0: https://fedorahosted.org/releases/p/u/%{name}/%{name}-%{version}.tar.gz
BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}-root-%(%{__id_u} -n)
BuildArch:      noarch
BuildRequires:  python2-devel
BuildRequires:  python-setuptools
BuildRequires:  rpm-python

%description
Provides a collection of platform plugins and admin client extensions to
provide docker support

%prep
%setup -q

%build
pushd common
%{__python} setup.py build
popd

pushd extensions_admin
%{__python} setup.py build
popd

pushd plugins
%{__python} setup.py build
popd

%install
rm -rf %{buildroot}

mkdir -p %{buildroot}/%{_sysconfdir}/pulp/

pushd common
%{__python} setup.py install --skip-build --root %{buildroot}
popd

pushd extensions_admin
%{__python} setup.py install --skip-build --root %{buildroot}
popd

pushd plugins
%{__python} setup.py install --skip-build --root %{buildroot}
popd

mkdir -p %{buildroot}/%{_var}/lib/pulp/published/docker/app/
mkdir -p %{buildroot}/%{_var}/lib/pulp/published/docker/export/
mkdir -p %{buildroot}/%{_var}/lib/pulp/published/docker/web/

cp -R plugins/etc/httpd %{buildroot}/%{_sysconfdir}

mkdir -p %{buildroot}/%{_bindir}

%clean
rm -rf %{buildroot}



# ---- Docker Common -----------------------------------------------------------

%package -n python-pulp-docker-common
Summary: Pulp Docker support common library
Group: Development/Languages
Requires: python-pulp-common >= 2.8.0
Requires: python-setuptools

%description -n python-pulp-docker-common
Common libraries for python-pulp-docker

%files -n python-pulp-docker-common
%defattr(-,root,root,-)
%dir %{python_sitelib}/pulp_docker
%{python_sitelib}/pulp_docker/__init__.py*
%{python_sitelib}/pulp_docker/common/
%dir %{python_sitelib}/pulp_docker/extensions
%{python_sitelib}/pulp_docker/extensions/__init__.py*
%{python_sitelib}/pulp_docker_common*.egg-info
%doc COPYRIGHT LICENSE AUTHORS


# ---- Plugins -----------------------------------------------------------------
%package plugins
Summary: Pulp Docker plugins
Group: Development/Languages
Requires: python-pulp-common >= 2.8.0
Requires: python-pulp-docker-common = %{version} 
Requires: pulp-server >= 2.8.0
Requires: python-setuptools
Requires: python-nectar >= 1.3.0

%description plugins
Provides a collection of platform plugins that extend the Pulp platform
to provide Docker specific support

%files plugins

%defattr(-,root,root,-)
%{python_sitelib}/pulp_docker/plugins/
%config(noreplace) %{_sysconfdir}/httpd/conf.d/pulp_docker.conf
%{python_sitelib}/pulp_docker_plugins*.egg-info

%defattr(-,apache,apache,-)
%{_var}/lib/pulp/published/docker/

%doc COPYRIGHT LICENSE AUTHORS


# ---- Admin Extensions --------------------------------------------------------
%package admin-extensions
Summary: The Pulp Docker admin client extensions
Group: Development/Languages
Requires: python-pulp-common >= 2.8.0
Requires: python-pulp-docker-common = %{version}
Requires: pulp-admin-client >= 2.8.0
Requires: python-setuptools

%description admin-extensions
pulp-admin extensions for docker support

%files admin-extensions
%defattr(-,root,root,-)
%{python_sitelib}/pulp_docker/extensions/admin/
%{python_sitelib}/pulp_docker_extensions_admin*.egg-info
%doc COPYRIGHT LICENSE AUTHORS


%changelog
* Mon Mar 14 2016 Dennis Kliban <dkliban@redhat.com> 2.0.0-1
- Bumping version to 2.0.0-1 (dkliban@redhat.com)

* Tue Mar 08 2016 Dennis Kliban <dkliban@redhat.com> 2.0.0-0.9.rc
- Bumping version to 2.0.0-0.9.rc (dkliban@redhat.com)

* Fri Mar 04 2016 Dennis Kliban <dkliban@redhat.com> 2.0.0-0.8.beta
- Bumping version to 2.0.0-0.8.beta (dkliban@redhat.com)

* Thu Mar 03 2016 Dennis Kliban <dkliban@redhat.com> 2.0.0-0.7.beta
- Bumping version to 2.0.0-0.7.beta (dkliban@redhat.com)

* Wed Mar 02 2016 Dennis Kliban <dkliban@redhat.com> 2.0.0-0.6.beta
- Merge pull request #142 from dkliban/check-unique (dkliban@redhat.com)
- Adds check for duplicate unit key (dkliban@redhat.com)
- Merge pull request #139 from asmacdo/index-deprecated (asmacdo@gmail.com)
- Merge pull request #140 from seandst/413 (sean.myers@redhat.com)
- add v1 deprecation to recipe (asmacdo@gmail.com)
- Merge pull request #138 from asmacdo/1693-require-image-id
  (asmacdo@gmail.com)
- Allow users to --enable-v{1,2} with repo update. (rbarlow@redhat.com)
- Bumping version to 2.0.0-0.6.beta (dkliban@redhat.com)
- Block attempts to load server.conf when running tests (sean.myers@redhat.com)
- Force search to include all required fields (asmacdo@gmail.com)

* Fri Feb 19 2016 Dennis Kliban <dkliban@redhat.com> 2.0.0-0.5.beta
- Merge pull request #137 from pcreech/issues/1672 (pcreech17@gmail.com)
- Manifest.digest static method was renamed (pcreech@redhat.com)
- Update the documentation to reflect the v2 changes. (rbarlow@redhat.com)
- Merge pull request #135 from pcreech/issues/1650 (pcreech17@gmail.com)
- Merge branch 'fix_setups' (rbarlow@redhat.com)
- Fix upload step attributes for v1 (pcreech@redhat.com)
- Pass the old-style repo object to the UploadStep. (rbarlow@redhat.com)
- Merge pull request #131 from pcreech/issues/1638 (pcreech17@gmail.com)
- Merge branch '1217' (rbarlow@redhat.com)
- Add release notes for pulp-docker-2.0. (rbarlow@redhat.com)
- Merge pull request #132 from pcreech/authors (pcreech17@gmail.com)
- Update tag and manifest counts during sync (pcreech@redhat.com)
- Add Patrick to authors file (pcreech@redhat.com)
- Merge pull request #130 from dkliban/remove-unit-key-index
  (dkliban@redhat.com)
- Merge pull request #125 from jortel/issue-1597 (jortel@redhat.com)
- Merge pull request #129 from pcreech/issues/1404 (pcreech17@gmail.com)
- Removes uniqueness constraint on unit key (dkliban@redhat.com)
- Add library namespace to docker hub images (pcreech@redhat.com)
- Ensure that successesful downloads are reported (asmacdo@gmail.com)
- Merge remote-tracking branch 'pulp/master' into issue-1597
  (jortel@redhat.com)
- Mark setup.pys as executable. (rbarlow@redhat.com)
- Merge pull request #121 from asmacdo/v2-get-token (asmacdo@gmail.com)
- Make requests to docker registry with bearer tokens (asmacdo@gmail.com)
- Support v2 enabled importer configuration property. closes #1597
  (jortel@redhat.com)
- Merge pull request #124 from rbarlow/dont_install_tests (rbarlow@redhat.com)
- Do not install tests. (rbarlow@redhat.com)
- Merge branch '1598' (ipanova@redhat.com)
- 1598 - Clarify in docs that index.docker.io only supported for v1
  (ipanova@redhat.com)
- 1492 - migration fails when /v1 directory already exists (ipanova@redhat.com)
- Do not install tests. (rbarlow@redhat.com)
- Bumping version to 2.0.0-0.5.beta (dkliban@redhat.com)

* Thu Jan 28 2016 Dennis Kliban <dkliban@redhat.com> 2.0.0-0.4.beta
- Use the new new steps API during publishing. (rbarlow@redhat.com)
- Merge pull request #118 from pcreech/issues/1457 (pcreech17@gmail.com)
- Ensure file objects are cleaned up on error (pcreech@redhat.com)
- Bumping version to 2.0.0-0.4.beta (dkliban@redhat.com)

* Tue Jan 19 2016 Dennis Kliban <dkliban@redhat.com> 2.0.0-0.3.beta
- Bumping version to 2.0.0-0.3.beta (dkliban@redhat.com)

* Wed Jan 13 2016 Dennis Kliban <dkliban@redhat.com> 2.0.0-0.2.beta
- Bumping version to 2.0.0-0.2.beta (dkliban@redhat.com)

* Mon Jan 11 2016 Dennis Kliban <dkliban@redhat.com> 2.0.0-0.1.beta
- Bumping version to 2.0.0-0.1.beta (dkliban@redhat.com)
- Add a formal Tag Unit model to track repository tags. (rbarlow@redhat.com)
- Can sync v1 and v2 APIs together, and optionally disable v1 sync
  (mhrivnak@redhat.com)
- passing new-style Repo object to controllers & saving before import_content
  (mhrivnak@redhat.com)
- ref #1422 - compatibility with lazy changes. (jortel@redhat.com)
- Merge branch '863' (rbarlow@redhat.com)
- Convert the plugin to use mongoengine models. (rbarlow@redhat.com)
- Convert shebang to python2 (ipanova@redhat.com)
- Merge branch '1.1-dev' (dkliban@redhat.com)
- Merge branch '1.0-dev' into 1.1-dev (dkliban@redhat.com)
- Adds fc23 to dist_list.txt config and removes fc21. (dkliban@redhat.com)
- Removing a Docker repository can cause a TypeError. (ipanova@redhat.com)
- Merge branch 'fix_pr_comments' (rbarlow@redhat.com)
- Merge branch 'use_devel_flake8' (rbarlow@redhat.com)
- Fix a few style issues mentioned in review comments. (rbarlow@redhat.com)
- Use flake8 from the pulp.devel test runner. (rbarlow@redhat.com)
- Merge branch 'docker_v2_api' into merge_v2_upstream (rbarlow@redhat.com)
- Require mock<1.1 for test compatibility. (rbarlow@redhat.com)
- Depend on Pulp 2.8 in the spec file, since we use features only present in
  2.8. (rbarlow@redhat.com)
- Repair some unit tests that fail against Pulp master. (rbarlow@redhat.com)
- Revert "Update pulp_docker to use mongoengine based units"
  (rbarlow@redhat.com)
- Merge branch '1331' into docker_v2_api (rbarlow@redhat.com)
- Merge branch '1316' into docker_v2_api (rbarlow@redhat.com)
- Add the ability for users to be able to sync from other Pulp servers.
  (rbarlow@redhat.com)
- Fix repo deletion. (rbarlow@redhat.com)
- Merge branch '1.0-dev' into 1.1-dev (ipanova@redhat.com)
- Removing shutil.move and copytree where /var/cache/pulp is involved.
  (ipanova@redhat.com)
- Merge pull request #96 from midnightercz/docker_v2_api (rbarlow@redhat.com)
- Merge pull request #93 from rbarlow/1256 (rbarlow@redhat.com)
- Merge pull request #92 from rbarlow/1241 (rbarlow@redhat.com)
- - typo fix (jluza@redhat.com)
- Reconfigure the httpd vhost to better suit the Docker client.
  (rbarlow@redhat.com)
- Form the redirect URL using the Docker API version. (rbarlow@redhat.com)
- Have each step use its own space inside the working_dir. (rbarlow@redhat.com)
- Merge branch '1049' into docker_v2_api (rbarlow@redhat.com)
- Merge branch '1217' into docker_v2_api (rbarlow@redhat.com)
- Merge branch 'adjust_api_endpoints' into docker_v2_api (rbarlow@redhat.com)
- Rework the "app" file for Docker v2. (rbarlow@redhat.com)
- Serve Docker v2 at /pulp/docker/v2 instead of /v2. (rbarlow@redhat.com)
- Add a migration for users to move to pulp-docker-2 (rbarlow@redhat.com)
- ref #1219 - repo sections arranged consistent with other plugins.
  (jortel@redhat.com)
- ref #1203 - support manifest search, copy and remove. (jortel@redhat.com)
- Add support for publishing Docker v2 content. (rbarlow@redhat.com)
- Merge pull request #79 from barnabycourt/bump-version (bcourt@redhat.com)
- Merge branch '1.2-release-notes' (bcourt@redhat.com)
- Merge branch '1.1-dev' (bcourt@redhat.com)
- Create a new Blob model. (rbarlow@redhat.com)
- Add support to sync with Docker v2 repositories. (rbarlow@redhat.com)
- compat with platform db model. (jortel@redhat.com)
- Update to version 1.2.x (bcourt@redhat.com)
- Add 1.2.x release notes (bcourt@redhat.com)
- Add 1.1.x release notes (bcourt@redhat.com)
- Update pulp_docker to use mongoengine based units (bcourt@redhat.com)
- Merge branch 'docker_v2_api' (rbarlow@redhat.com)
- Merge branch '967' into docker_v2_api (rbarlow@redhat.com)
- Add a unit for the new Docker metadata type. (rbarlow@redhat.com)
- Merge pull request #78 from asmacdo/use-mongoengine-repo (asmacdo@gmail.com)
- Merge branch '1.0-dev' (dkliban@redhat.com)
- Merge branch '1.0-testing' into 1.0-dev (dkliban@redhat.com)
- Removed fc20 from dist_list.txt (dkliban@redhat.com)
- Merge branch '1.0-dev' (dkliban@redhat.com)
- Merge branch '1.0-testing' into 1.0-dev (dkliban@redhat.com)
- Merge branch '1.0-release' into 1.0-testing (dkliban@redhat.com)
- Merge pull request #74 from dkliban/add_f22_build (dkliban@redhat.com)
- Added Fedora 22 to dist list (dkliban@redhat.com)
- Automatic commit of package [pulp-docker] release [1.0.2-0.2.beta]. (pulp-
  infra@redhat.com)
- Bumping version to 1.0.3 alpha (dkliban@redhat.com)
- Bumping version for 1.0.2 beta release (dkliban@redhat.com)
- Automatic commit of package [pulp-docker] release [1.0.2-0.1.alpha]. (pulp-
  infra@redhat.com)
- convert to stop using managers that no longer exist (asmacdo@gmail.com)
- Merge branch '1.0-dev' (ipanova@redhat.com)
- Merge branch 'issue966' into 1.0-dev (ipanova@redhat.com)
- Automatic commit of package [pulp-docker] release [1.0.1-1]. (pulp-
  infra@redhat.com)
- Merge branch '1.0-dev' (dkliban@redhat.com)
- Merge branch '1.0-testing' into 1.0-dev (dkliban@redhat.com)
- Merge pull request #72 from dkliban/1.0-testing (dkliban@redhat.com)
- Added release notes (dkliban@redhat.com)
- Bumping version for GA release (dkliban@redhat.com)
- Fixing discrepancy "canceled" vs. "cancelled (ipanova@redhat.com)
- Automatic commit of package [pulp-docker] release [1.0.1-0.3.rc]. (pulp-
  infra@redhat.com)
- Bumping version for RC (dkliban@redhat.com)
- Add nosexcover to test_requirements.txt. (rbarlow@redhat.com)
- Automatic commit of package [pulp-docker] release [1.0.1-0.2.beta]. (pulp-
  infra@redhat.com)
- Bumping version (dkliban@redhat.com)
- Add a test_requirement.txt file. (rbarlow@redhat.com)
- Merge branch '1.0-dev' (asmacdo@gmail.com)
- Correct the repo-registry-id validation error (asmacdo@gmail.com)
- Merge branch 'syncbug' (mhrivnak@redhat.com)
- The API for fetching tags from a remote registry or index changed. This uses
  the new API. (mhrivnak@redhat.com)
- Failure to sync no longer logs tracebacks, also reports a more helpful
  message. (mhrivnak@redhat.com)
- bumping version to 1.1.0 (mhrivnak@redhat.com)
- Merge branch '1.0-dev' (asmacdo@gmail.com)
- add repo-registry-id validation information to docs (asmacdo@gmail.com)

* Thu Nov 19 2015 Randy Barlow <rbarlow@redhat.com> 2.0.0-1
- Remove the types file

* Fri Jan 16 2015 Chris Duryee <cduryee@redhat.com> 0.2.2-1
- 1148556 - Validate repo-registry-id to ensure compatibility with Docker
  (asmacdo@gmail.com)
- Merge pull request #50 from beav/specfix (cduryee@redhat.com)
- Merge pull request #49 from barnabycourt/1159828 (bcourt@redhat.com)
- pulp-docker requires Pulp 2.5 or later (cduryee@redhat.com)

* Fri Nov 21 2014 Chris Duryee <cduryee@redhat.com> 0.2.1-1
- bump release to 1 (cduryee@redhat.com)
- 1160272 - Adjusting configuration files' path for docker plugins.
  (ipanova@redhat.com)
- Add intersphinx and extlinks support to pulp_docker (cduryee@redhat.com)
- 1150592 - set default auto-publish value (cduryee@redhat.com)
- 1150605 - fix error in docker recipe (cduryee@redhat.com)
- Merge branch 'merge_docs' (rbarlow@redhat.com)
- Merge the two Sphinx projects together. (rbarlow@redhat.com)
- Merge branch 'dev_install' (rbarlow@redhat.com)
- pulp-dev.py installs the packages. (rbarlow@redhat.com)
- Merge pull request #41 from pulp/mhrivnak-install-docs (mhrivnak@hrivnak.org)
- requiring python-nectar (mhrivnak@redhat.com)
- changing installation doc to use RPMs instead of git (mhrivnak@redhat.com)
- Merge branch 'master' of github.com:pulp/pulp_docker (rbarlow@redhat.com)
- 1103232 - Document importer settings. (rbarlow@redhat.com)
- Update for PR comments (bcourt@redhat.com)
- Clean up docs & fix export config name (bcourt@redhat.com)

* Thu Oct 02 2014 Chris Duryee <cduryee@redhat.com> 0.2.1-0.2.beta
- making the default size None when a layer's metadata lacks the Size attribute
  (mhrivnak@redhat.com)
- adding several publish directories that need to be in the package
  (mhrivnak@redhat.com)

* Thu Sep 11 2014 Chris Duryee <cduryee@redhat.com> 0.2.1-0.1.alpha
- declare correct package version in spec file (cduryee@redhat.com)

* Tue Sep 09 2014 Chris Duryee <cduryee@redhat.com> 0.2.0-1
  bump to 0.2.0
- 

* Mon Sep 08 2014 Chris Duryee <cduryee@redhat.com> 0.1.2-1
- adding cancellation support (mhrivnak@redhat.com)
- adding sync (mhrivnak@redhat.com)

* Mon Jul 07 2014 Chris Duryee <cduryee@redhat.com> 0.1.1-1
- new package built with tito

