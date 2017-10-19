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
import docker.errors

from ruamel.yaml import YAML
from openshift import client as openshift_client, config as openshift_config
from jinja2 import Environment, FileSystemLoader
from kubernetes import client as kubernetes_client
from kubernetes.client.rest import ApiException

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


def update_dockerfile(project, dockerfile):
    spec_path = os.path.join(project, SPEC_FILE)
    dockerfile_path = os.path.join(os.path.join(project, dockerfile))

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


def broker_resource_url(host, broker_name):
    return "{}/apis/servicecatalog.k8s.io/v1beta1/clusterservicebrokers/{}".format(host, broker_name)


def relist_service_broker(kwargs):
    try:
        openshift_config.load_kube_config()
        token = openshift_client.configuration.api_key['authorization']
        cluster_host = openshift_client.configuration.host
        broker_name = kwargs['broker_name']
        headers = {}
        if kwargs['basic_auth_username'] is not None and kwargs['basic_auth_password'] is not None:
            headers = {'Authorization': "Basic " +
                       base64.b64encode("{0}:{1}".format(kwargs['basic_auth_username'],
                                                         kwargs['basic_auth_password']))
                       }
        else:
            headers = {'Authorization': token}

        response = requests.request("get",
                broker_resource_url(cluster_host, broker_name),
                verify=kwargs['verify'], headers=headers)

        if response.status_code != 200:
            errMsg = "Received non-200 status code while retrieving broker: {}\n".format(broker_name) + \
                "Response body:\n" + \
                str(response.text)
            raise Exception(errMsg)

        spec = response.json().get('spec', None)
        if spec == None:
            errMsg = "Spec not found in broker reponse. Response body: \n{}".format(response.text)
            raise Exception(errMsg)

        relist_requests = spec.get('relistRequests', None)
        if relist_requests == None:
            errMsg = "relistRequests not found within the spec of broker: {}\n".format(broker_name) + \
                    "Are you sure you are using a ServiceCatalog of >= v0.0.21?"
            raise Exception(errMsg)

        inc_relist_requests = relist_requests + 1

        headers['Content-Type'] = 'application/strategic-merge-patch+json'
        response = requests.request("patch",
                broker_resource_url(cluster_host, broker_name),
                json={'spec': {'relistRequests': inc_relist_requests}},
                verify=kwargs['verify'], headers=headers)

        if response.status_code != 200:
            errMsg = "Received non-200 status code while patching relistRequests of broker: {}\n".format(broker_name) + \
                "Response body:\n" + \
                str(response.text)
            raise Exception(errMsg)

        print("Successfully relisted the Service Catalog")
    except Exception as e:
        print("Relist failure: {}".format(e))


def create_role_binding():
    try:
        openshift_config.load_kube_config()
        api = openshift_client.OapiApi()
        role_binding = {
            'apiVersion': 'v1',
            'kind': 'RoleBinding',
            'metadata': {
                'name': 'service-account-1',
                'namespace': 'default',
            },
            'subjects': [{
                'kind': 'ServiceAccount',
                'name': 'service-account-1',
                'namespace': 'default',
            }],
            'roleRef': {
                'name': 'cluster-admin',
            },
        }
        api.create_namespaced_role_binding("default", role_binding)
    except Exception as e:
        api = openshift_client.OapiApi()
        # HACK: this is printing an error but is still actually creating the
        # role binding.
        # print("failed -%s" % e)

    print("Created Role Binding")


def create_service_account():
    try:
        openshift_config.load_kube_config()
        api = kubernetes_client.CoreV1Api()
        service_account = {
            'apiVersion': 'v1',
            'kind': 'ServiceAccount',
            'metadata': {
                'name':'service-account-1',
                'namespace': 'default',
            },
        }
        api.create_namespaced_service_account("default", service_account)
        print("Created Serice Account")
    except Exception as e:
        pod_name = None
        print("failed - %s" % e)


def create_image_pod(image_name):
    try:
        openshift_config.load_kube_config()
        api = kubernetes_client.CoreV1Api()
        pod_manifest = {
            'apiVersion': 'v1',
            'kind': 'Pod',
            'metadata': {
                'name': "test",
            },
            'spec': {
                'containers': [{
                    'image': image_name,
                    'imagePullPolicy': 'IfNotPresent',
                    'name': 'test',
                    'command': ['entrypoint.sh', 'test']
                }],
                'restartPolicy': 'Never',
                'serviceAccountName': 'service-account-1',
            }

        }
        create_service_account()
        create_role_binding()
        api.create_namespaced_pod("default", pod_manifest)
        print("Created Pod")
    except Exception as e:
        pod_name = None
        print("failed - %s" % e)


def retrieve_test_result():
    cont = True
    count = 0
    while cont:
        try:
            count += 1
            openshift_config.load_kube_config()
            api = kubernetes_client.CoreV1Api()
            api_response = api.connect_post_namespaced_pod_exec("test", "default", command="/usr/bin/test-retrieval", tty=False)
            if "non-zero exit code" not in api_response:
                return api_response
        except ApiException as e:
            if count >= 50:
                cont = False
        except Exception as e:
            print("execption: %s" % e)
            cont = False


def clean_up_image_run():
    try:
        openshift_config.load_kube_config()
        api = kubernetes_client.CoreV1Api()
        oapi = openshift_client.OapiApi()
        body = kubernetes_client.V1DeleteOptions()
        api.delete_namespaced_service_account("service-account-1", "default", body)
        api.delete_namespaced_pod("test", "default", body)
        oapi.delete_namespaced_role_binding("service-account-1", "default", body)
    except Exception as e:
        print("unable to clean up image - %s" % e)


def broker_request(broker, service_route, method, **kwargs):
    if broker is None:
        broker = get_asb_route()

    if broker is None:
        raise Exception("Could not find route to ansible-service-broker. "
                        "Use --broker or log into the cluster using \"oc login\"")

    url = broker + "/ansible-service-broker" + service_route
    if url.find("http") < 0:
        url = "https://" + url

    try:
        openshift_config.load_kube_config()
        headers = {}
        if kwargs['basic_auth_username'] is not None and kwargs['basic_auth_password'] is not None:
            headers = {'Authorization': "Basic " +
                       base64.b64encode("{0}:{1}".format(kwargs['basic_auth_username'],
                                                         kwargs['basic_auth_password']))
                       }
        else:
            token = openshift_client.configuration.api_key.get("authorization", "")
            headers = {'Authorization': token}
        response = requests.request(method, url, verify=kwargs["verify"],
                                    headers=headers, data=kwargs.get("data"))
    except Exception as e:
        print("ERROR: Failed broker request (%s) %s" % (method, url))
        raise e

    return response


def cmdrun_list(**kwargs):
    response = broker_request(kwargs['broker'], "/v2/catalog", "get",
                              verify=kwargs["verify"],
                              basic_auth_username=kwargs.get("basic_auth_username"),
                              basic_auth_password=kwargs.get("basic_auth_password"))

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
    print(json.dumps(services, indent=4, sort_keys=True))


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
    for service in sorted(services, key=lambda s:s['name']):
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

    description = "This is a sample application generated by apb init"

    apb_dict = {
        'name': apb_name,
        'app_name': app_name,
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
    dockerfile = DOCKERFILE
    include_deps = kwargs['include_deps']

    if kwargs['dockerfile']:
        dockerfile = kwargs['dockerfile']

    # Removing dependency work for now
    if include_deps:
        spec = update_deps(project)
        write_file(spec, spec_path, True)

    if not is_valid_spec(get_spec(project)):
        print("Error! Spec failed validation check. Not updating Dockerfile.")
        exit(1)

    update_dockerfile(project, dockerfile)


def cmdrun_build(**kwargs):
    project = kwargs['base_path']
    dockerfile = "Dockerfile"
    spec = get_spec(project)
    if 'version' not in spec:
        print("APB spec does not have a listed version. Please update apb.yml")
        exit(1)

    if not kwargs['tag']:
        tag = spec['name']
    else:
        tag = kwargs['tag']

    if kwargs['org']:
        tag = kwargs['org'] + '/' + tag

    if kwargs['registry']:
        tag = kwargs['registry'] + '/' + tag

    if kwargs['dockerfile']:
        dockerfile = kwargs['dockerfile']

    update_dockerfile(project, dockerfile)

    print("Building APB using tag: [%s]" % tag)

    try:
        client = docker.DockerClient(base_url='unix://var/run/docker.sock', version='auto')
        client.images.build(path=project, tag=tag, dockerfile=dockerfile)
    except docker.errors.DockerException as e:
        print("Error accessing the docker API. Is the daemon running?")
        raise

    print("Successfully built APB image: %s" % tag)


def cmdrun_relist(**kwargs):
    relist_service_broker(kwargs)


def cmdrun_push(**kwargs):
    project = kwargs['base_path']
    spec = get_spec(project, 'string')
    blob = base64.b64encode(spec)
    data_spec = {'apbSpec': blob}
    print(spec)
    response = broker_request(kwargs["broker"], "/apb/spec", "post", data=data_spec,
                              verify=kwargs["verify"],
                              basic_auth_username=kwargs.get("basic_auth_username"),
                              basic_auth_password=kwargs.get("basic_auth_password"))

    if response.status_code != 200:
        print("Error: Attempt to add APB to the Broker returned status: %d" % response.status_code)
        print("Unable to add APB to Ansible Service Broker.")
        exit(1)

    print("Successfully added APB to Ansible Service Broker")

    if not kwargs['no_relist']:
        relist_service_broker(kwargs)


def cmdrun_remove(**kwargs):
    if kwargs["all"]:
        route = "/apb/spec"
    elif kwargs["id"] is not None:
        route = "/apb/spec/" + kwargs["id"]
    else:
        raise Exception("No APB ID specified.  Use --id.")

    response = broker_request(kwargs["broker"], route, "delete",
                              verify=kwargs["verify"],
                              basic_auth_username=kwargs.get("basic_auth_username"),
                              basic_auth_password=kwargs.get("basic_auth_password"))

    if response.status_code != 204:
        print("Error: Attempt to remove an APB from Broker returned status: %d" % response.status_code)
        print("Unable to remove APB from Ansible Service Broker.")
        exit(1)

    print("Successfully deleted APB")


def cmdrun_bootstrap(**kwargs):
    response = broker_request(kwargs["broker"], "/v2/bootstrap", "post", data={},
                              verify=kwargs["verify"],
                              basic_auth_username=kwargs.get("basic_auth_username"),
                              basic_auth_password=kwargs.get("basic_auth_password"))

    if response.status_code != 200:
        print("Error: Attempt to bootstrap Broker returned status: %d" % response.status_code)
        print("Unable to bootstrap Ansible Service Broker.")
        exit(1)

    print("Successfully bootstrapped Ansible Service Broker")

    if not kwargs['no_relist']:
        relist_service_broker(kwargs)


def cmdrun_test(**kwargs):
    project = kwargs['base_path']
    spec = get_spec(project)

    update_dockerfile(project, DOCKERFILE)

    if not kwargs['tag']:
        tag = spec['name']
    else:
        tag = kwargs['tag']
    print("Building APB using tag: [%s]" % tag)

    client = docker.DockerClient(base_url='unix://var/run/docker.sock', version='auto')
    client.images.build(path=project, tag=tag)

    print("Successfully built APB image: %s" % tag)

    # run image that was just created.
    create_image_pod(tag)
    test_result = retrieve_test_result()
    test_results = []
    if test_result is None:
        print("Unable to retrieve test result.")
        clean_up_image_run()
        return
    else:
        test_results = test_result.splitlines()

    if len(test_results) > 0 and "0" in test_results[0]:
        print("Test successfully passed")
    elif len(test_results) == 0:
        print("Unable to retrieve test result.")
    else:
        print(test_result)

    clean_up_image_run()
