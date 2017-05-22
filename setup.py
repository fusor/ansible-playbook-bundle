from setuptools import setup, find_packages
from pip.req import parse_requirements

install_reqs = parse_requirements('src/requirements.txt', session=False)
reqs = [str(ir.req) for ir in install_reqs]

setup(
    name="apb",
    version="0.1.0",
    description="Tooling for managing Ansible Playbook Bundle (APB) projects",
    author="Fusor",
    author_email="ansible-service-broker@redhat.com",
    url = 'https://github.com/fusor/ansible-playbook-bundle',
    download_url = 'https://github.com/fusor/ansible-playbook-bundle/archive/apb-0.1.0.tar.gz',
    keywords = ['ansible', 'playbook', 'bundle'],
    package_dir={'': 'src'},
    packages=find_packages('src'),
    install_requires=reqs,
    package_data={'apb': ['dat/ex.Dockerfile', 'dat/apb.yml.j2', 'dat/playbook.yml.j2']},
    entry_points={
        'console_scripts': ['apb = apb.cli:main']
    }
)
