import os
from setuptools import setup, find_packages

with open(os.path.join(current_directory, "requirements.txt"), "r") as f:
    requirements = [
        line.strip()
        for line in f.read().splitlines()
        if line.strip()
    ]

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
    install_requires=requirements,
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
