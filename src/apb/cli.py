""" cli module which handles all of the commandline parsing """
import os
import sys
import argparse

import apb.engine

SKIP_OPTIONS = ['provision', 'deprovision', 'bind', 'unbind', 'roles']

AVAILABLE_COMMANDS = {
    'help': 'Display this help message',
    'list': 'List APBs from the target Ansible Service Broker',
    'init': 'Initialize the directory for APB development',
    'prepare': 'Prepare an ansible-container project for APB packaging',
    'build': 'Build and package APB container',
    'push': 'Push local APB spec to an Ansible Service Broker',
    'remove': 'Remove APBs from the target Ansible Service Broker',
    'bootstrap': 'Tell Ansible Service Broker to reload APBs from the container repository'
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
        '-k',
        action='store_false',
        dest='verify',
        help=u'Use insecure connection to Ansible Service Broker'
    )
    return


def subcmd_build_parser(subcmd):
    """ build subcommand """
    subcmd.add_argument(
        '--tag',
        action='store',
        dest='tag',
        help=u'Tag of APB to build'
    )

    subcmd.add_argument(
        '--include-dependencies',
        action='store_true',
        dest='include_deps',
        help=u'Include smart dependency tracking',
        default=False
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
        '--org',
        '-o',
        action='store',
        dest='org',
        help=u'Organization of APB to publish to'
    )

    subcmd.add_argument(
        '--force',
        action='store_true',
        dest='force',
        help=u'Force re-init on current directory',
        default=False
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
        '--param',
        '-p',
        action='append',
        dest='params',
        help=u'Parameter declaration separated by commas'
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
        help=u'Targetted cluster type',
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
        '-k',
        action='store_false',
        dest='verify',
        help=u'Use insecure connection to Ansible Service Broker'
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
        '-k',
        action='store_false',
        dest='verify',
        help=u'Use insecure connection to Ansible Service Broker'
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
        '-k',
        action='store_false',
        dest='verify',
        help=u'Use insecure connection to Ansible Service Broker'
    )
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

    try:
        getattr(apb.engine,
                u'cmdrun_{}'.format(args.subcommand))(**vars(args))
    except Exception as e:
        print("Exception occurred! %s" % e)
        sys.exit(1)
