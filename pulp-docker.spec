%{!?python_sitelib: %global python_sitelib %(%{__python} -c "from distutils.sysconfig import get_python_lib; print(get_python_lib())")}
%{!?python_sitearch: %global python_sitearch %(%{__python} -c "from distutils.sysconfig import get_python_lib; print(get_python_lib(1))")}

Name: pulp-docker
Version: 0.2.1
Release: 0.2.beta%{?dist}
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

mkdir -p %{buildroot}/%{_usr}/lib/pulp/plugins/types
mkdir -p %{buildroot}/%{_var}/lib/pulp/published/docker/app/
mkdir -p %{buildroot}/%{_var}/lib/pulp/published/docker/export/
mkdir -p %{buildroot}/%{_var}/lib/pulp/published/docker/web/

cp -R plugins/etc/httpd %{buildroot}/%{_sysconfdir}
# Types
cp -R plugins/types/* %{buildroot}/%{_usr}/lib/pulp/plugins/types/

mkdir -p %{buildroot}/%{_bindir}

# Remove tests
rm -rf %{buildroot}/%{python_sitelib}/test

%clean
rm -rf %{buildroot}



# ---- Docker Common -----------------------------------------------------------

%package -n python-pulp-docker-common
Summary: Pulp Docker support common library
Group: Development/Languages
Requires: python-pulp-common >= 2.4.0
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
Requires: python-pulp-common >= 2.4.0
Requires: python-pulp-docker-common = %{version} 
Requires: pulp-server >= 2.4.0
Requires: python-setuptools

%description plugins
Provides a collection of platform plugins that extend the Pulp platform
to provide Docker specific support

%files plugins

%defattr(-,root,root,-)
%{python_sitelib}/pulp_docker/plugins/
%config(noreplace) %{_sysconfdir}/httpd/conf.d/pulp_docker.conf
%{_usr}/lib/pulp/plugins/types/docker.json
%{python_sitelib}/pulp_docker_plugins*.egg-info

%defattr(-,apache,apache,-)
%{_var}/lib/pulp/published/docker/

%doc COPYRIGHT LICENSE AUTHORS


# ---- Admin Extensions --------------------------------------------------------
%package admin-extensions
Summary: The Pulp Docker admin client extensions
Group: Development/Languages
Requires: python-pulp-common >= 2.4.0
Requires: python-pulp-docker-common = %{version}
Requires: pulp-admin-client >= 2.4.0
Requires: python-setuptools

%description admin-extensions
pulp-admin extensions for docker support

%files admin-extensions
%defattr(-,root,root,-)
%{python_sitelib}/pulp_docker/extensions/admin/
%{python_sitelib}/pulp_docker_extensions_admin*.egg-info
%doc COPYRIGHT LICENSE AUTHORS


%changelog
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

