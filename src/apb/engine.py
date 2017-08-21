import errno
import os
import uuid
import base64
import shutil
import string
import subprocess
import ruamel.yaml
import json
import requests
import urllib3
from requests.packages.urllib3.exceptions import InsecureRequestWarning
# Disable insecure request warnings from both packages
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

import docker

from ruamel.yaml import YAML
from openshift import client as openshift_client, config as openshift_config
from jinja2 import Environment, FileSystemLoader
from kubernetes import client as kubernetes_client

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


def load_example_specfile(apb_dict, params):
    env = Environment(loader=FileSystemLoader(DAT_PATH), trim_blocks=True)
    template = env.get_template(EX_SPEC_FILE)

    if not params:
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


def write_playbook(project_dir, apb_dict, action):
    env = Environment(loader=FileSystemLoader(DAT_PATH))
    templates = ACTION_TEMPLATE_DICT[action]
    playbook_template = env.get_template(templates['playbook_template'])
    playbook_out = playbook_template.render(apb_dict=apb_dict, action_name=action)

    playbook_pathname = os.path.join(project_dir,
                                     templates['playbook_dir'],
                                     templates['playbook_file'])
    mkdir_p(os.path.join(project_dir, templates['playbook_dir']))
    write_file(playbook_out, playbook_pathname, True)


def write_role(project_path, apb_dict, action):
    env = Environment(loader=FileSystemLoader(DAT_PATH))
    templates = ACTION_TEMPLATE_DICT[action]
    template = env.get_template(templates['role_task_main_template'])
    main_out = template.render(apb_dict=apb_dict, action_name=action)

    role_name = action + '-' + apb_dict['name']
    dir_tpl = string.Template(templates['role_tasks_dir'])
    dir = dir_tpl.substitute(role_name=role_name)
    role_tasks_dir = os.path.join(project_path, dir)

    mkdir_p(role_tasks_dir)
    main_filepath = os.path.join(role_tasks_dir, templates['role_task_main_file'])
    write_file(main_out, main_filepath, True)


def generate_playbook_files(project_path, skip, apb_dict):
    print("Generating playbook files")

    for action in ACTION_TEMPLATE_DICT.keys():
        if not skip[action]:
            write_playbook(project_path, apb_dict, action)
            if not skip['roles']:
                write_role(project_path, apb_dict, action)


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
    error = False
    spec_keys = ['name', 'description', 'bindable', 'async', 'metadata', 'plans']
    for key in spec_keys:
        if key not in spec:
            print("Spec is not valid. `%s` field not found." % key)
            error = True
    if error:
        return False

    if spec['async'] not in ASYNC_OPTIONS:
        print("Spec is not valid. %s is not a valid `async` option." % spec['async'])
        error = True

    if not isinstance(spec['metadata'], dict):
        print("Spec is not valid. `metadata` field is invalid.")
        error = True

    for plan in spec['plans']:
        plan_keys = ['description', 'free', 'metadata', 'parameters']
        if 'name' not in plan:
            print("Spec is not valid. Plan name not found.")
            return False

        for key in plan_keys:
            if key not in plan:
                print("Spec is not valid. Plan %s is missing a `%s` field." % (plan['name'], key))
                return False

        if not isinstance(plan['metadata'], dict):
            print("Spec is not valid. Plan %s's `metadata` field is invalid." % plan['name'])
            error = True

        if not isinstance(plan['parameters'], list):
            print("Spec is not valid. Plan %s's `parameters` field is invalid." % plan['name'])
            error = True
    if error:
        return False
    return True


def load_spec_dict(spec_path):
    with open(spec_path, 'r') as spec_file:
        return YAML().load(spec_file.read())


def load_spec_str(spec_path):
    with open(spec_path, 'r') as spec_file:
        return spec_file.read()


def get_spec(project, output="dict"):
    spec_path = os.path.join(project, SPEC_FILE)

    if not os.path.exists(spec_path):
        raise Exception('ERROR: Spec file: [ %s ] not found' % spec_path)

    try:
        if output == 'string':
            spec = load_spec_str(spec_path)
        else:
            spec = load_spec_dict(spec_path)
    except Exception as e:
        print('ERROR: Failed to load spec!')
        raise e

    return spec


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


def update_deps(project):
    spec = get_spec(project)
    spec_path = os.path.join(project, SPEC_FILE)
    roles_path = os.path.join(project, ROLES_DIR)

    expected_deps = load_source_dependencies(roles_path)
    if 'metadata' not in spec:
        spec['metadata'] = {}
    if 'dependencies' not in spec['metadata']:
        spec['metadata']['dependencies'] = []
    current_deps = spec['metadata']['dependencies']
    for dep in expected_deps:
        if dep not in current_deps:
            spec['metadata']['dependencies'].append(dep)

    if not is_valid_spec(spec):
        fmtstr = 'ERROR: Spec file: [ %s ] failed validation'
        raise Exception(fmtstr % spec_path)

    return ruamel.yaml.dump(spec, Dumper=ruamel.yaml.RoundTripDumper)


def update_dockerfile(project):
    spec_path = os.path.join(project, SPEC_FILE)
    dockerfile_path = os.path.join(os.path.join(project, DOCKERFILE))

    # TODO: Defensively confirm the strings are encoded
    # the way the code expects
    blob = base64.b64encode(load_spec_str(spec_path))
    dockerfile_out = insert_encoded_spec(
        load_dockerfile(dockerfile_path), make_friendly(blob)
    )

    write_file(dockerfile_out, dockerfile_path, False)
    print('Finished writing dockerfile.')


def load_source_dependencies(roles_path):
    print('Trying to guess list of dependencies for APB')
    output = subprocess.check_output("/bin/grep -R \ image: "+roles_path+"|awk '{print $3}'", stderr=subprocess.STDOUT, shell=True)
    if "{{" in output or "}}" in output:
        print("Detected variables being used for dependent image names. Please double check the dependencies in your spec file.")
    return output.split('\n')[:-1]


def get_asb_route():
    asb_route = None
    try:
        openshift_config.load_kube_config()
        oapi = openshift_client.OapiApi()
        route_list = oapi.list_namespaced_route('ansible-service-broker')
        for route in route_list.items:
            if route.metadata.name.find('asb-') >= 0:
                asb_route = route.spec.host
    except:
        asb_route = None
    return asb_route

def delete_controller_manager_pod():
    pod_name = None
    try:
        openshift_config.load_kube_config()
        api = kubernetes_client.CoreV1Api()
        pod_list = api.list_namespaced_pod('service-catalog')
        for pod in pod_list.items:
            if pod.metadata.name.find('controller-manager-') >= 0:
                pod_name = pod.metadata.name
    except Exception as e:
        pod_name = None

    if pod_name:
        api.delete_namespaced_pod(pod_name, 'service-catalog', kubernetes_client.V1DeleteOptions())


def broker_request(broker, service_route, method, **kwargs):
    if broker is None:
        broker = get_asb_route()

    if broker is None:
        raise Exception("Could not find route to ansible-service-broker. "
                        "Use --broker or log into the cluster using \"oc login\"")

    url = broker + service_route
    if url.find("http") < 0:
        url = "https://" + url

    try:
        response = requests.request(method, url, **kwargs)
    except Exception as e:
        print("ERROR: Failed broker request (%s) %s" % (method, url))
        raise e

    return response


def cmdrun_list(**kwargs):
    response = broker_request(kwargs["broker"], "/v2/catalog", "get", verify=kwargs["verify"])

    if response.status_code != 200:
        print("Error: Attempt to list APBs in the broker returned status: %d" % response.status_code)
        print("Unable to list APBs in Ansible Service Broker.")
        exit(1)

    services = response.json()['services']

    if not services:
        print("No APBs found")
    elif kwargs["output"] == 'json':
        print_json_list(services)
    elif kwargs["verbose"]:
        print_verbose_list(services)
    else:
        print_list(services)


def print_json_list(services):
    print json.dumps(services, indent=4, sort_keys=True)


def print_verbose_list(services):
    for service in services:
        print_service(service)


def print_service(service):
    cmap = ruamel.yaml.comments.CommentedMap()

    if 'name' in service:
        cmap['name'] = service['name']
    if 'id' in service:
        cmap['id'] = service['id']
    if 'description' in service:
        cmap['description'] = service['description']
    if 'bindable' in service:
        cmap['bindable'] = service['bindable']
    if 'metadata' in service:
        cmap['metadata'] = service['metadata']
    if 'plans' in service:
        cmap['plans'] = pretty_plans(service['plans'])

    print(ruamel.yaml.dump(cmap, Dumper=ruamel.yaml.RoundTripDumper))


def pretty_plans(plans):
    pp = []
    if plans is None:
        return
    for plan in plans:
        cmap = ruamel.yaml.comments.CommentedMap()
        if 'name' in plan:
            cmap['name'] = plan['name']
        if 'description' in plan:
            cmap['description'] = plan['description']
        if 'free' in plan:
            cmap['free'] = plan['free']
        if 'metadata' in plan:
            cmap['metadata'] = plan['metadata']

        try:
            plan_params = plan['schemas']['service_instance']['create']['parameters']['properties']
        except KeyError:
            plan_params = []

        cmap['parameters'] = plan_params
        pp.append(cmap)
    return pp


def print_list(services):
    max_id = 10
    max_name = 10
    max_desc = 10

    for service in services:
        max_id = max(max_id, len(service["id"]))
        max_name = max(max_name, len(service["name"]))
        max_desc = max(max_desc, len(service["description"]))

    template = "{id:%d}{name:%d}{description:%d}" % (max_id + 2, max_name + 2, max_desc + 2)
    print(template.format(id="ID", name="NAME", description="DESCRIPTION"))
    for service in services:
        print(template.format(**service))


def cmdrun_init(**kwargs):
    current_path = kwargs['base_path']
    bindable = kwargs['bindable']
    async = kwargs['async']
    skip = {
        'provision': kwargs['skip-provision'],
        'deprovision': kwargs['skip-deprovision'],
        'bind': kwargs['skip-bind'] or not kwargs['bindable'],
        'unbind': kwargs['skip-unbind'] or not kwargs['bindable'],
        'roles': kwargs['skip-roles']
    }

    apb_tag_arr = kwargs['tag'].split('/')
    apb_name = apb_tag_arr[-1]
    if apb_name.lower().endswith("-apb"):
        app_name = apb_name[:-4]
    else:
        app_name = apb_name

    organization = kwargs['org']
    if organization is None:
        if len(apb_tag_arr) > 1:
            organization = apb_tag_arr[-2]
        else:
            raise Exception('Organization must be specified as in '
                            '"apb init org/apb-name" or with the --org flag')

    description = "This is a sample application generated by apb init"

    apb_dict = {
        'name': apb_name,
        'app_name': app_name,
        'image': organization+'/'+apb_name,
        'description': description,
        'bindable': bindable,
        'async': async
    }

    project = os.path.join(current_path, apb_name)

    if os.path.exists(project):
        if not kwargs['force']:
            raise Exception('ERROR: Project directory: [%s] found and force option not specified' % project)
        shutil.rmtree(project)

    print("Initializing %s for an APB." % project)

    os.mkdir(project)

    spec_path = os.path.join(project, SPEC_FILE)
    dockerfile_path = os.path.join(os.path.join(project, DOCKERFILE))

    specfile_out = load_example_specfile(apb_dict, [])
    write_file(specfile_out, spec_path, kwargs['force'])

    dockerfile_out = load_dockerfile(EX_DOCKERFILE_PATH)
    write_file(dockerfile_out, dockerfile_path, kwargs['force'])

    generate_playbook_files(project, skip, apb_dict)
    print("Successfully initialized project directory at: %s" % project)
    print("Please run *apb prepare* inside of this directory after editing files.")


def cmdrun_prepare(**kwargs):
    project = kwargs['base_path']
    roles_path = os.path.join(project, ROLES_DIR)
    spec_path = os.path.join(project, SPEC_FILE)
    include_deps = kwargs['include_deps']
    # Removing dependency work for now
    if include_deps:
        spec = update_deps(project)
        write_file(spec, spec_path, True)

    if not is_valid_spec(get_spec(project)):
        print("Error! Spec failed validation check. Not updating Dockerfile.")
        exit(1)

    update_dockerfile(project)


def cmdrun_build(**kwargs):
    project = kwargs['base_path']
    spec = get_spec(project)

    update_dockerfile(project)

    if not kwargs['tag']:
        tag = spec['image']
    else:
        tag = kwargs['tag']

    if kwargs['registry']:
        tag = kwargs['registry'] + '/' + tag

    print("Building APB using tag: [%s]" % tag)

    client = docker.DockerClient(base_url='unix://var/run/docker.sock', version='auto')
    client.images.build(path=project, tag=tag)

    print("Successfully built APB image: %s" % tag)


def cmdrun_push(**kwargs):
    project = kwargs['base_path']
    spec = get_spec(project, 'string')
    blob = base64.b64encode(spec)
    data_spec = {'apbSpec': blob}
    response = broker_request(kwargs["broker"], "/apb/spec", "post", data=data_spec, verify=kwargs["verify"])

    if response.status_code != 200:
        print("Error: Attempt to add APB to the Broker returned status: %d" % response.status_code)
        print("Unable to add APB to Ansible Service Broker.")
        exit(1)

    # Temporary workaround to delete controller_manager pod to catch new APB
    delete_controller_manager_pod()

    print("Successfully added APB to Ansible Service Broker")


def cmdrun_remove(**kwargs):
    if kwargs["all"]:
        route = "/apb/spec"
    elif kwargs["id"] is not None:
        route = "/apb/spec/" + kwargs["id"]
    else:
        raise Exception("No APB ID specified.  Use --id.")

    response = broker_request(kwargs["broker"], route, "delete", verify=kwargs["verify"])

    if response.status_code != 204:
        print("Error: Attempt to remove an APB from Broker returned status: %d" % response.status_code)
        print("Unable to remove APB from Ansible Service Broker.")
        exit(1)

    print("Successfully deleted APB")


def cmdrun_bootstrap(**kwargs):
    response = broker_request(kwargs["broker"], "/v2/bootstrap", "post", data={}, verify=kwargs["verify"])

    if response.status_code != 200:
        print("Error: Attempt to bootstrap Broker returned status: %d" % response.status_code)
        print("Unable to bootstrap Ansible Service Broker.")
        exit(1)

    print("Successfully bootstrapped Ansible Service Broker")
