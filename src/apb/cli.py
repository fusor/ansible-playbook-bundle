import os
import sys
import argparse

import apb.engine

SKIP_OPTIONS = ['provision', 'deprovision', 'bind', 'unbind', 'roles']

AVAILABLE_COMMANDS = {
    'help': 'Display this help message',
    'init': 'Initialize the directory for APB development',
    'prepare': 'Prepare an ansible-container project for APB packaging',
    'build': 'Build and package APB container',
    'push': 'Push APB spec to an Ansible Service Broker'
}


def subcmd_build_parser(parser, subcmd):
    subcmd.add_argument(
        '--tag', action='store', dest='tag',
        help=u'Tag of APB to build'
    )
    return


def subcmd_init_parser(parser, subcmd):
    subcmd.add_argument(
        'name', action='store',
        help=u'Name of APB to initialize'
    )

    subcmd.add_argument(
        '--org', '-o', action='store', dest='org',
        help=u'Organization of APB to publish to', required=True
    )

    subcmd.add_argument(
        '--force', action='store_true', dest='force',
        help=u'Force re-init on current directory', default=False
    )

    subcmd.add_argument(
        '--async', action='store', dest='async',
        help=u'Specify asynchronous operation on application.', default='optional',
        choices=['required', 'optional', 'unsupported']
    )

    subcmd.add_argument(
        '--not-bindable', action='store_false', dest='bindable',
        help=u'Make application not bindable on the spec.', default=True
    )

    subcmd.add_argument(
        '--param', '-p', action='append', dest='params',
        help=u'Parameter declaration separated by commas'
    )

    for opt in SKIP_OPTIONS:
        subcmd.add_argument(
            '--skip-%s' % opt, action='store_true', dest='skip-%s' % opt,
            help=u'Specify which playbooks to not generate by default.', default=False
        )

    return


def subcmd_prepare_parser(parser, subcmd):
    subcmd.add_argument(
        '--provider', action='store', dest='provider',
        help=u'Targetted cluster type',
        choices=['openshift', 'kubernetes'],
        default='openshift'
    )


def subcmd_push_parser(parser, subcmd):
    subcmd.add_argument(
        'broker_route', action='store',
        help=u'Route to the Ansible Service Broker'
    )


def subcmd_help_parser(parser, subcmd):
    return


def main():
    parser = argparse.ArgumentParser(
        description=u'APB tooling for '
        u'assisting in building and packaging APBs.'
    )

    parser.add_argument(
        '--debug', action='store_true', dest='debug',
        help=u'Enable debug output', default=False
    )

    # TODO: Modify project to accept relative paths
    parser.add_argument(
        '--project', '-p', action='store', dest='base_path',
        help=u'Specify a path to your project. Defaults to CWD.',
        default=os.getcwd()
    )

    subparsers = parser.add_subparsers(title='subcommand', dest='subcommand')
    subparsers.required = True

    for subcommand in AVAILABLE_COMMANDS:
        subparser = subparsers.add_parser(
            subcommand, help=AVAILABLE_COMMANDS[subcommand]
        )
        globals()['subcmd_%s_parser' % subcommand](parser, subparser)

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
