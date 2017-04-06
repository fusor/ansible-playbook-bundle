from setuptools import setup, find_packages
from pip.req import parse_requirements

install_reqs = parse_requirements('src/requirements.txt', session=False)
reqs = [str(ir.req) for ir in install_reqs]

setup(
    name="ansibleapp",
    version="0.1.0",
    description="Tooling for managing ansibleapp projects",
    author="Fusor",
    author_email="ansible-apps@redhat.com",
    package_dir={'': 'src'},
    packages=find_packages('src'),
    install_requires=reqs,
    entry_points={
        'console_scripts': ['ansibleapp = ansibleapp.cli:main']
    }
)
