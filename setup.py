from setuptools import setup, find_packages

try: # for pip >= 10
    from pip._internal.req import parse_requirements
except ImportError:
    try: # for pip <= 9.0.3
        from pip.req import parse_requirements
    except ImportError:
        pass

try: # for EL7 RPM builds without pip
  install_reqs = parse_requirements('src/requirements.txt', session=False)
  reqs = [str(ir.req) for ir in install_reqs]
except NameError:
  reqs = ""

setup(
    name="apb",
    version="1.2.3",
    description="Tooling for managing Ansible Playbook Bundle (APB) projects",
    author="Fusor",
    author_email="ansible-service-broker@redhat.com",
    url='https://github.com/ansibleplaybookbundle/ansible-playbook-bundle',
    download_url='https://github.com/ansibleplaybookbundle/ansible-playbook-bundle/archive/apb-0.2.6.tar.gz',
    keywords=['ansible', 'playbook', 'bundle'],
    package_dir={'': 'src'},
    packages=find_packages('src'),
    install_requires=reqs,
    package_data={'apb': [
        'dat/Dockerfile.j2',
        'dat/apb.yml.j2',
        'dat/Makefile.j2',
        'dat/playbooks/playbook.yml.j2',
        'dat/roles/provision/tasks/main.yml.j2',
        'dat/roles/deprovision/tasks/main.yml.j2',
        'dat/roles/bind/tasks/main.yml.j2',
        'dat/roles/unbind/tasks/main.yml.j2'
    ]},
    entry_points={
        'console_scripts': ['apb = apb.cli:main']
    }
)
