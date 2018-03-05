""" cli module which handles all of the commandline parsing """
import os
import sys
import argparse
import pkg_resources

import apb.engine

SKIP_OPTIONS = ['provision', 'deprovision', 'bind', 'unbind', 'roles']

AVAILABLE_COMMANDS = {
    'help': 'Display this help message',
    'relist': 'Relist the APBs available within the Service Catalog',
    'list': 'List APBs from the target Ansible Service Broker',
    'setup': 'Initialize OpenShift with APB development environment',
    'init': 'Initialize the directory for APB development',
    'prepare': 'Prepare an ansible-container project for APB packaging',
    'build': 'Build and package APB container',
    'push': 'Push local APB spec to an Ansible Service Broker',
    'remove': 'Remove APBs from the target Ansible Service Broker',
    'serviceinstance': 'Create a ServiceInstance template based on apb.yaml',
    'bootstrap': 'Tell Ansible Service Broker to reload APBs from the container repository',
    'test': 'Test the APB',
    'run': 'Run APB',
    'version': 'Get current version of APB tool'
}


def subcmd_list_parser(subcmd):
    """ list subcommand """
    subcmd.add_argument(
        '--broker',
        action='store',
        dest='broker',
        help=u'Route to the Ansible Service Broker'
    )
    subcmd.add_argument(
        '--secure',
        action='store_true',
        dest='verify',
        help=u'Use secure connection to Ansible Service Broker',
        default=False
    )
    subcmd.add_argument(
        '--verbose',
        '-v',
        action='store_true',
        dest='verbose',
        help=u'Output verbose spec information from Ansible Service Broker',
        default=False
    )
    subcmd.add_argument(
        '--output',
        '-o',
        action='store',
        dest='output',
        help=u'Specify verbose output format in yaml (default) or json',
        default='optional',
        choices=['yaml', 'json']
    )
    subcmd.add_argument(
        '--username',
        '-u',
        action='store',
        default=None,
        dest='basic_auth_username',
        help=u'Specify the basic auth username to be used'
    )
    subcmd.add_argument(
        '--password',
        '-p',
        action='store',
        default=None,
        dest='basic_auth_password',
        help=u'Specify the basic auth password to be used'
    )
    return


def subcmd_build_parser(subcmd):
    """ build subcommand """
    subcmd.add_argument(
        '--tag',
        action='store',
        dest='tag',
        help=u'Tag of APB to build (ie. mysql-apb or docker.io/username/mysql-apb)'
    )

    subcmd.add_argument(
        '--dockerfile',
        '-f',
        action='store',
        dest='dockerfile',
        help=u'Name of Dockerfile to build with'
    )

    return


def subcmd_init_parser(subcmd):
    """ init subcommand """
    subcmd.add_argument(
        'tag',
        action='store',
        help=u'Tag (org/name) or name of APB to initialize'
    )

    subcmd.add_argument(
        '--force',
        action='store_true',
        dest='force',
        help=u'Force re-init on current directory',
        default=False
    )

    subcmd.add_argument(
        '--dockerhost',
        action='store',
        help=u'set the dockerhost for this project',
        default="docker.io"
    )

    subcmd.add_argument(
        '--async',
        action='store',
        dest='async',
        help=u'Specify asynchronous operation on application.',
        default='optional',
        choices=['required', 'optional', 'unsupported']
    )

    subcmd.add_argument(
        '--bindable',
        action='store_true',
        dest='bindable',
        help=u'Make application bindable on the spec.',
        default=False
    )

    subcmd.add_argument(
        '--dep',
        '-d',
        action='append',
        dest='dependencies',
        help=u'Add image dependency to APB spec'
    )

    for opt in SKIP_OPTIONS:
        subcmd.add_argument(
            '--skip-%s' % opt,
            action='store_true',
            dest='skip-%s' % opt,
            help=u'Specify which playbooks to not generate by default.',
            default=False
        )

    return


def subcmd_prepare_parser(subcmd):
    """ prepare subcommand """
    subcmd.add_argument(
        '--provider',
        action='store',
        dest='provider',
        help=u'Targeted cluster type',
        choices=['openshift', 'kubernetes'],
        default='openshift'
    )

    subcmd.add_argument(
        '--include-dependencies',
        action='store_true',
        dest='include_deps',
        help=u'Include smart dependency tracking',
        default=False
    )

    subcmd.add_argument(
        '--dockerfile',
        '-f',
        action='store',
        dest='dockerfile',
        help=u'Name of Dockerfile to build with'
    )

    return


def subcmd_push_parser(subcmd):
    """ push subcommand """
    subcmd.add_argument(
        '--broker',
        action='store',
        dest='broker',
        help=u'Route to the Ansible Service Broker'
    )
    subcmd.add_argument(
        '--registry-service-name',
        action='store',
        dest='reg_svc_name',
        help=u'Name of service for internal OpenShift registry',
        default=u'docker-registry'
    )
    subcmd.add_argument(
        '--registry-namespace',
        action='store',
        dest='reg_namespace',
        help=u'Namespace of internal OpenShift registry',
        default=u'default'
    )
    subcmd.add_argument(
        '--namespace',
        action='store',
        dest='namespace',
        help=u'Namespace to push APB in OpenShift registry',
        default=u'openshift'
    )
    subcmd.add_argument(
        '--registry-route',
        action='store',
        dest='reg_route',
        help=u'Route of internal OpenShift registry'
    )
    subcmd.add_argument(
        '--dockerfile',
        '-f',
        action='store',
        dest='dockerfile',
        help=u'Dockerfile to build internal registry image with',
        default=u'Dockerfile'
    )
    subcmd.add_argument(
        '--secure',
        action='store_true',
        dest='verify',
        help=u'Use secure connection to Ansible Service Broker',
        default=False
    )
    subcmd.add_argument(
        '--username',
        '-u',
        action='store',
        default=None,
        dest='basic_auth_username',
        help=u'Specify the basic auth username to be used'
    )
    subcmd.add_argument(
        '--password',
        '-p',
        action='store',
        default=None,
        dest='basic_auth_password',
        help=u'Specify the basic auth password to be used'
    )
    subcmd.add_argument(
        '--no-relist',
        action='store_true',
        dest='no_relist',
        help=u'Do not relist the catalog after pushing an apb to the broker',
        default=False
    )
    subcmd.add_argument(
        '--broker-name',
        action='store',
        dest='broker_name',
        help=u'Name of the ServiceBroker k8s resource',
        default=u'ansible-service-broker'
    )
    subcmd.add_argument(
        '--push-to-broker',
        action='store_true',
        dest='broker_push',
        help=u'Use Broker development endpoint at /v2/apb/',
        default=False
    )
    return


def subcmd_remove_parser(subcmd):
    """ remove subcommand """
    subcmd.add_argument(
        '--broker',
        action='store',
        dest='broker',
        help=u'Route to the Ansible Service Broker'
    )
    subcmd.add_argument(
        '--local', '-l',
        action='store_true',
        dest='local',
        help=u'Remove image from internal OpenShift registry',
        default=False
    )
    subcmd.add_argument(
        '--all',
        action='store_true',
        dest='all',
        help=u'Remove all stored APBs',
        default=False
    )
    subcmd.add_argument(
        '--id',
        action='store',
        dest='id',
        help=u'ID of APB to remove'
    )
    subcmd.add_argument(
        '--secure',
        action='store_true',
        dest='verify',
        help=u'Use secure connection to Ansible Service Broker',
        default=False
    )
    subcmd.add_argument(
        '--username',
        '-u',
        action='store',
        default=None,
        dest='basic_auth_username',
        help=u'Specify the basic auth username to be used'
    )
    subcmd.add_argument(
        '--password',
        '-p',
        action='store',
        default=None,
        dest='basic_auth_password',
        help=u'Specify the basic auth password to be used'
    )
    subcmd.add_argument(
        '--no-relist',
        action='store_true',
        dest='no_relist',
        help=u'Do not relist the catalog after pushing an apb to the broker',
        default=False
    )
    subcmd.add_argument(
        '--broker-name',
        action='store',
        dest='broker_name',
        help=u'Name of the ServiceBroker k8s resource',
        default=u'ansible-service-broker'
    )
    return


def subcmd_bootstrap_parser(subcmd):
    """ bootstrap subcommand """
    subcmd.add_argument(
        '--broker',
        action='store',
        dest='broker',
        help=u'Route to the Ansible Service Broker'
    )
    subcmd.add_argument(
        '--secure',
        action='store_true',
        dest='verify',
        help=u'Use secure connection to Ansible Service Broker',
        default=False
    )
    subcmd.add_argument(
        '--no-relist',
        action='store_true',
        dest='no_relist',
        help=u'Do not relist the catalog after bootstrapping the broker',
        default=False
    )
    subcmd.add_argument(
        '--username',
        '-u',
        action='store',
        default=None,
        dest='basic_auth_username',
        help=u'Specify the basic auth username to be used'
    )
    subcmd.add_argument(
        '--password',
        '-p',
        action='store',
        default=None,
        dest='basic_auth_password',
        help=u'Specify the basic auth password to be used'
    )
    subcmd.add_argument(
        '--broker-name',
        action='store',
        dest='broker_name',
        help=u'Name of the ServiceBroker k8s resource',
        default=u'ansible-service-broker'
    )
    return


def subcmd_test_parser(subcmd):
    """ test subcommand """
    subcmd.add_argument(
        '--dockerfile',
        '-f',
        action='store',
        dest='dockerfile',
        help=u'Name of Dockerfile to build with'
    )

    subcmd.add_argument(
        '--registry-service-name',
        action='store',
        dest='reg_svc_name',
        help=u'Name of service for internal OpenShift registry',
        default=u'docker-registry'
    )

    subcmd.add_argument(
        '--registry-namespace',
        action='store',
        dest='reg_namespace',
        help=u'Namespace of internal OpenShift registry',
        default=u'default'
    )

    subcmd.add_argument(
        '--namespace',
        action='store',
        dest='namespace',
        help=u'Namespace to push APB in OpenShift registry',
        default=u'openshift'
    )

    subcmd.add_argument(
        '--registry-route',
        action='store',
        dest='reg_route',
        help=u'Route of internal OpenShift registry'
    )

    return


def subcmd_run_parser(subcmd):
    """ provision subcommand """
    subcmd.add_argument(
        '--project',
        action='store',
        dest='project',
        required=True,
        help=u'Project where the APB should be run'
    )
    subcmd.add_argument(
        '--action',
        action='store',
        dest='action',
        required=False,
        help=u'The action to perform when running the APB',
        default='provision'
    )
    subcmd.add_argument(
        '--registry-service-name',
        action='store',
        dest='reg_svc_name',
        help=u'Name of service for internal OpenShift registry',
        default=u'docker-registry'
    )
    subcmd.add_argument(
        '--registry-namespace',
        action='store',
        dest='reg_namespace',
        help=u'Namespace of internal OpenShift registry',
        default=u'default'
    )
    subcmd.add_argument(
        '--namespace',
        action='store',
        dest='namespace',
        help=u'Namespace to push APB in OpenShift registry',
        default=u'openshift'
    )
    subcmd.add_argument(
        '--registry-route',
        action='store',
        dest='reg_route',
        help=u'Route of internal OpenShift registry'
    )
    subcmd.add_argument(
        '--dockerfile',
        '-f',
        action='store',
        dest='dockerfile',
        help=u'Dockerfile to build internal registry image with',
        default=u'Dockerfile'
    )
    return


def subcmd_setup_parser(subcmd):
    return


def subcmd_serviceinstance_parser(subcmd):
    return


def subcmd_relist_parser(subcmd):
    """ relist subcommand """
    subcmd.add_argument(
        '--broker-name',
        action='store',
        dest='broker_name',
        help=u'Name of the ServiceBroker k8s resource',
        default=u'ansible-service-broker'
    )
    subcmd.add_argument(
        '--secure',
        action='store_true',
        dest='verify',
        help=u'Use secure connection to Ansible Service Broker',
        default=False
    )
    subcmd.add_argument(
        '--username',
        '-u',
        action='store',
        default=None,
        dest='basic_auth_username',
        help=u'Specify the basic auth username to be used'
    )
    subcmd.add_argument(
        '--password',
        '-p',
        action='store',
        default=None,
        dest='basic_auth_password',
        help=u'Specify the basic auth password to be used'
    )
    return


def subcmd_version_parser(subcmd):
    """ version subcommand """
    return


def subcmd_help_parser(subcmd):
    """ help subcommand """
    return


def main():
    """ main """
    parser = argparse.ArgumentParser(
        description=u'APB tooling for '
        u'assisting in building and packaging APBs.'
    )

    parser.add_argument(
        '--debug',
        action='store_true',
        dest='debug',
        help=u'Enable debug output',
        default=False
    )

    # TODO: Modify project to accept relative paths
    parser.add_argument(
        '--project',
        '-p',
        action='store',
        dest='base_path',
        help=u'Specify a path to your project. Defaults to CWD.',
        default=os.getcwd()
    )

    subparsers = parser.add_subparsers(title='subcommand', dest='subcommand')
    subparsers.required = True

    for subcommand in AVAILABLE_COMMANDS:
        subparser = subparsers.add_parser(
            subcommand, help=AVAILABLE_COMMANDS[subcommand]
        )
        globals()['subcmd_%s_parser' % subcommand](subparser)

    args = parser.parse_args()

    if args.subcommand == 'help':
        parser.print_help()
        sys.exit(0)

    if args.subcommand == 'version':
        version = pkg_resources.require("apb")[0].version
        print("Version: apb-%s" % version)
        sys.exit(0)

    try:
        getattr(apb.engine,
                u'cmdrun_{}'.format(args.subcommand))(**vars(args))
    except Exception as e:
        print("Exception occurred! %s" % e)
        sys.exit(1)
