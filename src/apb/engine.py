import errno
import os
import uuid
import base64
import yaml
import string
import requests

import shutil
import docker

from jinja2 import Environment, FileSystemLoader, Template

ROLES_DIR = 'roles'

DAT_DIR = 'dat'
DAT_PATH = os.path.join(os.path.dirname(__file__), DAT_DIR)

SPEC_FILE = 'apb.yml'
EX_SPEC_FILE = 'apb.yml.j2'
EX_SPEC_FILE_PATH = os.path.join(DAT_PATH, EX_SPEC_FILE)
SPEC_FILE_PARAM_OPTIONS = ['name', 'description', 'type', 'default']

DOCKERFILE = 'Dockerfile'
EX_DOCKERFILE = 'Dockerfile.j2'
EX_DOCKERFILE_PATH = os.path.join(DAT_PATH, EX_DOCKERFILE)

ACTION_TEMPLATE_DICT = {
    'provision': {
        'playbook_template': 'playbooks/playbook.yml.j2',
        'playbook_dir': 'playbooks',
        'playbook_file': 'provision.yml',
        'role_task_main_template': 'roles/provision/tasks/main.yml.j2',
        'role_tasks_dir': 'roles/$role_name/tasks',
        'role_task_main_file': 'main.yml'
    },
    'deprovision': {
        'playbook_template': 'playbooks/playbook.yml.j2',
        'playbook_dir': 'playbooks',
        'playbook_file': 'deprovision.yml',
        'role_task_main_template': 'roles/deprovision/tasks/main.yml.j2',
        'role_tasks_dir': 'roles/$role_name/tasks',
        'role_task_main_file': 'main.yml'
    },
    'bind': {
        'playbook_template': 'playbooks/playbook.yml.j2',
        'playbook_dir': 'playbooks',
        'playbook_file': 'bind.yml',
        'role_task_main_template': 'roles/bind/tasks/main.yml.j2',
        'role_tasks_dir': 'roles/$role_name/tasks',
        'role_task_main_file': 'main.yml'
    },
    'unbind': {
        'playbook_template': 'playbooks/playbook.yml.j2',
        'playbook_dir': 'playbooks',
        'playbook_file': 'unbind.yml',
        'role_task_main_template': 'roles/unbind/tasks/main.yml.j2',
        'role_tasks_dir': 'roles/$role_name/tasks',
        'role_task_main_file': 'main.yml'
    },
}

SKIP_OPTIONS = ['provision', 'deprovision', 'bind', 'unbind', 'roles']
ASYNC_OPTIONS = ['required', 'optional', 'unsupported']

SPEC_LABEL = 'com.redhat.apb.spec'
VERSION_LABEL = 'com.redhat.apb.version'


def load_dockerfile(df_path):
    with open(df_path, 'r') as dockerfile:
        return dockerfile.readlines()


def convert_params_to_dict(params):
    param_dict = {}
    param_list = []

    for param in params:
        param_split = param.split(',')
        for key in param_split:
            # Each keypair is represented by '='
            first, second = key.split('=')

            # Check if key is in list of valid options
            if first in SPEC_FILE_PARAM_OPTIONS:
                param_dict.update({first: second})
            else:
                print("Valid parameter options: %s" % SPEC_FILE_PARAM_OPTIONS)
                raise Exception(
                    "ERROR: %s is not a valid parameter option." %
                    first
                )

        param_list.append(param_dict)

        # Reset param_dict
        param_dict = {}

    return param_list


def load_example_specfile(apb_dict, params):
    ENV = Environment(loader=FileSystemLoader(DAT_PATH))
    template = ENV.get_template(EX_SPEC_FILE)

    if params:
        params = convert_params_to_dict(params)
    else:
        params = []

    return template.render(apb_dict=apb_dict, params=params)


def write_file(file_out, destination, force):
    touch(destination, force)
    with open(destination, 'w') as outfile:
        outfile.write(''.join(file_out))


def insert_encoded_spec(dockerfile, encoded_spec_lines):
    apb_spec_idx = [i for i, line in enumerate(dockerfile)
                    if SPEC_LABEL in line][0]
    if not apb_spec_idx:
        raise Exception(
            "ERROR: %s missing from dockerfile while inserting spec blob" %
            SPEC_LABEL
        )

    # Set end_spec_idx to a list of all lines ending in a quotation mark
    end_spec_idx = [i for i, line in enumerate(dockerfile)
                    if line.endswith('"\n')]

    # Find end of spec label if it already exists
    if end_spec_idx:
        for correct_end_idx in end_spec_idx:
            if correct_end_idx > apb_spec_idx:
                end_spec_idx = correct_end_idx
                del dockerfile[apb_spec_idx + 1:end_spec_idx + 1]
                break

    split_idx = apb_spec_idx + 1
    offset = apb_spec_idx + len(encoded_spec_lines) + 1

    # Insert spec label
    dockerfile[split_idx:split_idx] = encoded_spec_lines

    # Insert newline after spec label
    dockerfile.insert(offset, "\n")

    return dockerfile


def mkdir_p(path):
    try:
        os.makedirs(path)
    except OSError as exc:
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else:
            raise


def write_playbook(project_dir, apb_name, action):
    env = Environment(loader=FileSystemLoader(DAT_PATH))
    template = env.get_template(ACTION_TEMPLATE_DICT[action]['playbook_template'])
    playbook_out = template.render(apb_name=apb_name, action_name=action)

    playbook_pathname = os.path.join(project_dir,
                                     ACTION_TEMPLATE_DICT[action]['playbook_dir'],
                                     ACTION_TEMPLATE_DICT[action]['playbook_file'])
    mkdir_p(os.path.join(project_dir, ACTION_TEMPLATE_DICT[action]['playbook_dir']))
    write_file(playbook_out, playbook_pathname, True)


def write_role(project_path, apb_name, action):
    env = Environment(loader=FileSystemLoader(DAT_PATH))
    template = env.get_template(ACTION_TEMPLATE_DICT[action]['role_task_main_template'])
    main_out = template.render(apb_name=apb_name, action_name=action)

    role_name = action + '-' + apb_name
    role_tasks_dir = string.Template(ACTION_TEMPLATE_DICT[action]['role_tasks_dir']).substitute(role_name=role_name)
    role_tasks_full_dir = os.path.join(project_path, role_tasks_dir)

    mkdir_p(role_tasks_full_dir)
    main_filepath= os.path.join(role_tasks_full_dir, ACTION_TEMPLATE_DICT[action]['role_task_main_file'])
    write_file(main_out, main_filepath, True)


def generate_playbook_files(project_path, bindable, skip, apb_name):
    print("Generating playbook files")

    for action in ACTION_TEMPLATE_DICT.keys():
        if not skip[action]:
            write_playbook(project_path, apb_name, action)
            if not skip['roles']:
                write_role(project_path, apb_name, action)


def gen_spec_id(spec, spec_path):
    new_id = str(uuid.uuid4())
    spec['id'] = new_id

    with open(spec_path, 'r') as spec_file:
        lines = spec_file.readlines()
        insert_i = 1 if lines[0] == '---' else 0
        id_kvp = "id: %s\n" % new_id
        lines.insert(insert_i, id_kvp)

    with open(spec_path, 'w') as spec_file:
        spec_file.writelines(lines)


def is_valid_spec(spec):
    # TODO: Implement
    # NOTE: spec is a loaded spec
    return True


def load_spec_dict(spec_path):
    with open(spec_path, 'r') as spec_file:
        return yaml.load(spec_file.read())


def load_spec_str(spec_path):
    with open(spec_path, 'r') as spec_file:
        return spec_file.read()


# NOTE: Splits up an encoded blob into chunks for insertion into Dockerfile
def make_friendly(blob):
    line_break = 76
    count = len(blob)
    chunks = count / line_break
    mod = count % line_break

    flines = []
    for i in range(chunks):
        fmtstr = '{0}\\\n'

        # Corner cases
        if chunks == 1:
            # Exactly 76 chars, two quotes
            fmtstr = '"{0}"\n'
        elif i == 0:
            fmtstr = '"{0}\\\n'
        elif i == chunks - 1 and mod == 0:
            fmtstr = '{0}"\n'

        offset = i * line_break
        line = fmtstr.format(blob[offset:(offset + line_break)])
        flines.append(line)

    if mod != 0:
        # Add incomplete chunk if we've got some left over,
        # this is the usual case
        flines.append('{0}"'.format(blob[line_break * chunks:]))

    return flines


def touch(fname, force):
    if os.path.exists(fname):
        os.utime(fname, None)
        if force:
            os.remove(fname)
            open(fname, 'a').close()
    else:
        open(fname, 'a').close()


def update_dockerfile(spec_path, dockerfile_path):
    # TODO: Defensively confirm the strings are encoded
    # the way the code expects
    blob = base64.b64encode(load_spec_str(spec_path))
    dockerfile_out = insert_encoded_spec(
        load_dockerfile(dockerfile_path), make_friendly(blob)
    )

    write_file(dockerfile_out, dockerfile_path, False)
    print('Finished writing dockerfile.')


def cmdrun_init(**kwargs):
    current_path = kwargs['base_path']
    apb_name = kwargs['name']
    organization = kwargs['org']
    bindable = kwargs['bindable']
    async = kwargs['async']
    params = kwargs['params']
    skip = {
        'provision': kwargs['skip-provision'],
        'deprovision': kwargs['skip-deprovision'],
        'bind': kwargs['skip-bind'],
        'unbind': kwargs['skip-unbind'],
        'roles': kwargs['skip-roles']
    }

    description = "This is a sample application generated by apb init"

    apb_dict = {'apb-name': apb_name, 'organization': organization, 'description': description, 'bindable': bindable, 'async': async}
    project = os.path.join(current_path, apb_name)

    if os.path.exists(project):
        if not kwargs['force']:
            raise Exception('ERROR: Project directory: [%s] found and force option not specified' % project)
        shutil.rmtree(project)

    print("Initializing %s for an APB." % project)

    os.mkdir(project)

    spec_path = os.path.join(project, SPEC_FILE)
    dockerfile_path = os.path.join(os.path.join(project, DOCKERFILE))

    specfile_out = load_example_specfile(apb_dict, params)
    write_file(specfile_out, spec_path, kwargs['force'])

    dockerfile_out = load_dockerfile(EX_DOCKERFILE_PATH)
    write_file(dockerfile_out, dockerfile_path, kwargs['force'])

    generate_playbook_files(project, bindable, skip, apb_name)
    print("Successfully initialized project directory at: %s" % project)
    print("Please run *apb prepare* inside of this directory after editing files.")


def cmdrun_prepare(**kwargs):
    project = kwargs['base_path']
    spec_path = os.path.join(project, SPEC_FILE)
    dockerfile_path = os.path.join(os.path.join(project, DOCKERFILE))

    if not os.path.exists(spec_path):
        raise Exception('ERROR: Spec file: [ %s ] not found' % spec_path)

    try:
        spec = load_spec_dict(spec_path)
    except Exception as e:
        print('ERROR: Failed to load spec!')
        raise e

    # ID specfile if it hasn't already been done
    if 'id' not in spec:
        gen_spec_id(spec, spec_path)

    if not is_valid_spec(spec):
        fmtstr = 'ERROR: Spec file: [ %s ] failed validation'
        raise Exception(fmtstr % spec_path)

    update_dockerfile(spec_path, dockerfile_path)


def cmdrun_build(**kwargs):
    project = kwargs['base_path']
    spec_path = os.path.join(project, SPEC_FILE)
    dockerfile_path = os.path.join(os.path.join(project, DOCKERFILE))

    if not os.path.exists(spec_path):
        raise Exception('ERROR: Spec file: [ %s ] not found' % spec_path)

    try:
        spec = load_spec_dict(spec_path)
    except Exception as e:
        print('ERROR: Failed to load spec!')
        raise e

    if not kwargs['tag']:
        tag = spec['image']
    else:
        tag = kwargs['tag']
    print("Building APB using tag: [%s]" % tag)

    # Restamp Dockerfile with base64 encoded spec before building
    update_dockerfile(spec_path, dockerfile_path)
    client = docker.DockerClient(base_url='unix://var/run/docker.sock', version='auto')

    client.images.build(path=project, tag=tag)

    print("Successfully built APB image: %s" % tag)


def cmdrun_push(**kwargs):
    print("Pushing APB spec to: [%s]" % kwargs['broker_route'])
    project = kwargs['base_path']
    spec_path = os.path.join(project, SPEC_FILE)

    if not os.path.exists(spec_path):
        raise Exception('ERROR: Spec file: [ %s ] not found' % spec_path)

    try:
        spec = load_spec_str(spec_path)
    except Exception as e:
        print('ERROR: Failed to load spec!')
        raise e

    blob = base64.b64encode(spec)
    dataSpec = {'apbSpec': blob}
    try:
        r = requests.post(kwargs['broker_route']+'/apb/spec', data=dataSpec)
    except Exception as e:
        # Try again with http in front of the route
        try:
            r = requests.post('http://'+kwargs['broker_route']+'/apb/spec', data=dataSpec)
        except Exception as e2:
            print('ERROR: Failed to POST spec to %s' % kwargs['broker_route'])
            raise e2

    if r.status_code != 200:
        print("Error: Attempt to add APB to the Broker returned status: %d" % r.status_code)
        print("Unable to add APB to Ansible Service Broker.")
        exit(1)

    print("Successfully added APB to Ansible Service Broker")
