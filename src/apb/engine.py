import errno
import os
import uuid
import base64
import shutil
import string
import random
import subprocess
import json
import requests
import urllib3
import docker
import docker.errors
import ruamel.yaml
import yaml

from ruamel.yaml import YAML
from time import sleep
from openshift import client as openshift_client, config as openshift_config
from openshift.helper.openshift import OpenShiftObjectHelper
from jinja2 import Environment, FileSystemLoader
from kubernetes import client as kubernetes_client, config as kubernetes_config
from kubernetes.client.rest import ApiException
from kubernetes.stream import stream as kubernetes_stream
from requests.packages.urllib3.exceptions import InsecureRequestWarning

# Handle input in 2.x/3.x
try:
    input = raw_input
except NameError:
    pass

# Disable insecure request warnings from both packages
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

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

MAKEFILE = 'Makefile'
EX_MAKEFILE = 'Makefile.j2'
EX_MAKEFILE_PATH = os.path.join(DAT_PATH, EX_MAKEFILE)

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
WATCH_POD_SLEEP = 5


def load_dockerfile(df_path):
    with open(df_path, 'r') as dockerfile:
        return dockerfile.readlines()


def load_makefile(apb_dict, params):
    env = Environment(loader=FileSystemLoader(DAT_PATH), trim_blocks=True)
    template = env.get_template(EX_MAKEFILE)

    if not params:
        params = []

    return template.render(apb_dict=apb_dict, params=params)


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
    cmd = "/bin/grep -R \ image: {} |awk '{print $3}'".format(roles_path)
    output = subprocess.check_output(cmd, stderr=subprocess.STDOUT, shell=True)
    if "{{" in output or "}}" in output:
        print("Detected variables being used for dependent image names. " +
              "Please double check the dependencies in your spec file.")
    return output.split('\n')[:-1]


def get_registry_service_ip(namespace, svc_name):
    ip = None
    try:
        openshift_config.load_kube_config()
        api = kubernetes_client.CoreV1Api()
        service = api.read_namespaced_service(namespace=namespace, name=svc_name)
        if service is None:
            print("Couldn't find docker-registry service in namespace default. Erroring.")
            return None
        if service.spec.ports == []:
            print("Service spec appears invalid. Erroring.")
            return None
        ip = service.spec.cluster_ip + ":" + str(service.spec.ports[0].port)
        print("Found registry IP at: " + ip)

    except ApiException as e:
        print("Exception occurred trying to find %s service in namespace %s: %s" % (svc_name, namespace, e))
        return None
    return ip


def get_asb_route():
    asb_route = None
    try:
        openshift_config.load_kube_config()
        oapi = openshift_client.OapiApi()
        route_list = oapi.list_namespaced_route('ansible-service-broker')
        if route_list.items == []:
            print("Didn't find OpenShift Ansible Broker route in namespace: ansible-service-broker.\
                    Trying openshift-ansible-service-broker")
            route_list = oapi.list_namespaced_route('openshift-ansible-service-broker')
            if route_list.items == []:
                print("Still failed to find a route to OpenShift Ansible Broker.")
                return None
        for route in route_list.items:
            if 'asb' in route.metadata.name and 'etcd' not in route.metadata.name:
                asb_route = route.spec.host
    except Exception:
        asb_route = None
        return asb_route

    url = asb_route + "/ansible-service-broker"
    if url.find("http") < 0:
        url = "https://" + url

    return url


def broker_resource_url(host, broker_name):
    return "{}/apis/servicecatalog.k8s.io/v1beta1/clusterservicebrokers/{}".format(host, broker_name)


def relist_service_broker(kwargs):
    try:
        openshift_config.load_kube_config()
        token = openshift_client.Configuration().get_api_key_with_prefix('authorization')
        cluster_host = openshift_client.Configuration().host
        broker_name = kwargs['broker_name']
        headers = {}
        if kwargs['basic_auth_username'] is not None and kwargs['basic_auth_password'] is not None:
            headers = {'Authorization': "Basic " +
                       base64.b64encode("{0}:{1}".format(kwargs['basic_auth_username'],
                                                         kwargs['basic_auth_password']))
                       }
        else:
            headers = {'Authorization': token}

        response = requests.request(
            "get",
            broker_resource_url(cluster_host, broker_name),
            verify=kwargs['verify'], headers=headers)

        if response.status_code != 200:
            errMsg = "Received non-200 status code while retrieving broker: {}\n".format(broker_name) + \
                "Response body:\n" + \
                str(response.text)
            raise Exception(errMsg)

        spec = response.json().get('spec', None)
        if spec is None:
            errMsg = "Spec not found in broker reponse. Response body: \n{}".format(response.text)
            raise Exception(errMsg)

        relist_requests = spec.get('relistRequests', None)
        if relist_requests is None:
            errMsg = "relistRequests not found within the spec of broker: {}\n".format(broker_name) + \
                     "Are you sure you are using a ServiceCatalog of >= v0.0.21?"
            raise Exception(errMsg)

        inc_relist_requests = relist_requests + 1

        headers['Content-Type'] = 'application/strategic-merge-patch+json'
        response = requests.request(
            "patch",
            broker_resource_url(cluster_host, broker_name),
            json={'spec': {'relistRequests': inc_relist_requests}},
            verify=kwargs['verify'], headers=headers)

        if response.status_code != 200:
            errMsg = "Received non-200 status code while patching relistRequests of broker: {}\n".format(
                broker_name) + \
                "Response body:\n{}".format(str(response.text))
            raise Exception(errMsg)

        print("Successfully relisted the Service Catalog")
    except Exception as e:
        print("Relist failure: {}".format(e))


def create_project(project):
    print("Creating project {}".format(project))
    try:
        openshift_config.load_kube_config()
        api = openshift_client.OapiApi()
        api.create_project_request({
            'apiVersion': 'v1',
            'kind': 'ProjectRequest',
            'metadata': {
                'name': project
            }
        })
        print("Created project")

        # TODO: Evaluate the project request to get the actual project name
        return project
    except ApiException as e:
        if e.status == 409:
            print("Project {} already exists".format(project))
            return project
        else:
            raise e


def delete_project(project):
    print("Deleting project {}".format(project))
    try:
        openshift_config.load_kube_config()
        api = openshift_client.OapiApi()
        api.delete_project(project)
        print("Project deleted")
    except ApiException as e:
        print("Delete project failure: {}".format(e))
        raise e


def create_service_account(name, namespace):
    print("Creating service account in {}".format(namespace))
    try:
        kubernetes_config.load_kube_config()
        api = kubernetes_client.CoreV1Api()
        api.create_namespaced_service_account(
            namespace,
            {
                'apiVersion': 'v1',
                'kind': 'ServiceAccount',
                'metadata': {
                    'name': name,
                    'namespace': namespace,
                },
            }
        )
        print("Created service account")
        return name
    except ApiException as e:
        if e.status == 409:
            print("Service account {} already exists".format(name))
            return name
        raise e


def create_cluster_role_binding(name, user_name, role="cluster-admin"):
    print("Creating role binding of {} for {}".format(role, user_name))
    try:
        kubernetes_config.load_kube_config()
        api = openshift_client.OapiApi()
        # TODO: Use generateName when it doesn't throw an exception
        api.create_cluster_role_binding(
            {
                'apiVersion': 'v1',
                'kind': 'ClusterRoleBinding',
                'metadata': {
                    'name': name,
                },
                'roleRef': {
                    'name': role,
                },
                'userNames': [user_name]
            }
        )
    except ApiException as e:
        raise e
    except Exception as e:
        # TODO:
        # Right now you'll see something like --
        #   Exception occurred! 'module' object has no attribute 'V1RoleBinding'
        # Looks like an issue with the openshift-restclient...well the version
        # of k8s included by openshift-restclient. Keeping this from below.
        pass
    print("Created Role Binding")
    return name


def create_role_binding(name, namespace, service_account, role="admin"):
    print("Creating role binding for {} in {}".format(service_account, namespace))
    try:
        kubernetes_config.load_kube_config()
        api = openshift_client.OapiApi()
        # TODO: Use generateName when it doesn't throw an exception
        api.create_namespaced_role_binding(
            namespace,
            {
                'apiVersion': 'v1',
                'kind': 'RoleBinding',
                'metadata': {
                    'name': name,
                    'namespace': namespace,
                },
                'subjects': [{
                    'kind': 'ServiceAccount',
                    'name': service_account,
                    'namespace': namespace,
                }],
                'roleRef': {
                    'name': role,
                },
            }
        )
    except ApiException as e:
        if e.status == 409:
            print("Role binding {} already exists".format(name))
            return name
        raise e
    except Exception as e:
        # TODO:
        # Right now you'll see something like --
        #   Exception occurred! 'module' object has no attribute 'V1RoleBinding'
        # Looks like an issue with the openshift-restclient...well the version
        # of k8s included by openshift-restclient
        pass
    print("Created Role Binding")
    return name


def create_pod(image, name, namespace, command, service_account):
    print("Creating pod with image {} in {}".format(image, namespace))
    try:
        kubernetes_config.load_kube_config()
        api = kubernetes_client.CoreV1Api()
        pod = api.create_namespaced_pod(
            namespace,
            {
                'apiVersion': 'v1',
                'kind': 'Pod',
                'metadata': {
                    'generateName': name,
                    'namespace': namespace
                },
                'spec': {
                    'containers': [{
                        'image': image,
                        'imagePullPolicy': 'IfNotPresent',
                        'name': name,
                        'command': command,
                        'env': [
                            {
                                'name': 'POD_NAME',
                                'valueFrom': {
                                    'fieldRef': {'fieldPath': 'metadata.name'}
                                }
                            },
                            {
                                'name': 'POD_NAMESPACE',
                                'valueFrom': {
                                    'fieldRef': {'fieldPath': 'metadata.namespace'}
                                }
                            }
                        ],
                    }],
                    'restartPolicy': 'Never',
                    'serviceAccountName': service_account,
                }
            }
        )
        print("Created Pod")
        return (pod.metadata.name, pod.metadata.namespace)
    except Exception as e:
        print("failed - %s" % e)
        return ("", "")


def watch_pod(name, namespace):
    kubernetes_config.load_kube_config()
    api = kubernetes_client.CoreV1Api()

    while True:
        sleep(WATCH_POD_SLEEP)

        pod_status = api.read_namespaced_pod(name, namespace).status
        pod_phase = pod_status.phase
        print("Pod in phase: {}".format(pod_phase))
        if pod_phase == 'Succeeded' or pod_phase == 'Failed':
            print(api.read_namespaced_pod_log(name, namespace))
            return pod_phase
        if pod_phase == 'Pending':
            try:
                reason = pod_status.container_statuses[0].state.waiting.reason
            except ApiException:
                pass
            if reason == 'ImagePullBackOff':
                raise ApiException("APB failed {} - check name".format(reason))


def run_apb(project, image, name, action, parameters={}):
    ns = create_project(project)
    sa = create_service_account(name, ns)
    create_role_binding(name, ns, sa)

    parameters['namespace'] = ns
    command = ['entrypoint.sh', action, "--extra-vars", json.dumps(parameters)]

    return create_pod(
        image=image,
        name=name,
        namespace=ns,
        command=command,
        service_account=sa
    )


def retrieve_test_result(name, namespace):
    count = 0
    try:
        openshift_config.load_kube_config()
        api = kubernetes_client.CoreV1Api()
    except Exception as e:
        print("Failed to get api client: {}".format(e))
    while True:
        try:
            count += 1
            api_response = kubernetes_stream(
                api.connect_get_namespaced_pod_exec,
                name,
                namespace,
                command="/usr/bin/test-retrieval",
                stderr=True, stdin=False,
                stdout=True, tty=False)
            if "test results are not available" not in api_response:
                return api_response
            sleep(WATCH_POD_SLEEP)
        except ApiException as e:
            if count >= 50:
                return None
            pod_phase = api.read_namespaced_pod(name, namespace).status.phase
            if pod_phase == 'Succeeded' or pod_phase == 'Failed':
                print("Pod phase {} without returning test results".format(pod_phase))
                return None
            sleep(WATCH_POD_SLEEP)
        except Exception as e:
            print("exception: %s" % e)
            return None


def broker_request(broker, service_route, method, **kwargs):
    if broker is None:
        broker = get_asb_route()

    if broker is None:
        raise Exception("Could not find route to ansible-service-broker. "
                        "Use --broker or log into the cluster using \"oc login\"")

    if not broker.endswith('/ansible-service-broker'):
        if not broker.endswith('/'):
            broker = broker + '/'
        broker = broker + 'ansible-service-broker'

    if not broker.startswith('http'):
        broker = 'https://' + broker

    url = broker + service_route
    print("Contacting the ansible-service-broker at: %s" % url)

    try:
        openshift_config.load_kube_config()
        headers = {}
        if kwargs['basic_auth_username'] is not None and kwargs['basic_auth_password'] is not None:
            headers = {'Authorization': "Basic " +
                       base64.b64encode("{0}:{1}".format(kwargs['basic_auth_username'],
                                                         kwargs['basic_auth_password']))
                       }
        else:
            token = openshift_client.Configuration().get_api_key_with_prefix('authorization')
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

        try:
            plan_bind_params = plan['schemas']['service_binding']['create']['parameters']['properties']
        except KeyError:
            plan_bind_params = []

        cmap['bind_parameters'] = plan_bind_params

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
    for service in sorted(services, key=lambda s: s['name']):
        print(template.format(**service))


def build_apb(project, dockerfile=None, tag=None):
    if dockerfile is None:
        dockerfile = "Dockerfile"
    spec = get_spec(project)
    if 'version' not in spec:
        print("APB spec does not have a listed version. Please update apb.yml")
        exit(1)

    if not tag:
        tag = spec['name']

    update_dockerfile(project, dockerfile)

    print("Building APB using tag: [%s]" % tag)

    try:
        client = create_docker_client()
        client.images.build(path=project, tag=tag, dockerfile=dockerfile)
    except docker.errors.DockerException:
        print("Error accessing the docker API. Is the daemon running?")
        raise

    print("Successfully built APB image: %s" % tag)
    return tag


def get_registry(kwargs):
    namespace = kwargs['reg_namespace']
    service = kwargs['reg_svc_name']
    registry_route = kwargs['reg_route']

    if registry_route:
        return registry_route
    elif is_minishift():
        return get_minishift_registry()
    else:
        registry = get_registry_service_ip(namespace, service)
        if registry is None:
            print("Failed to find registry service IP address.")
            raise Exception("Unable to get registry IP from namespace %s" % namespace)
        return registry


def delete_old_images(image_name):
    # Let's ignore the registry prefix for now because sometimes our tag doesn't match the registry
    registry, image_name = image_name.split('/', 1)
    try:
        openshift_config.load_kube_config()
        oapi = openshift_client.OapiApi()
        image_list = oapi.list_image(_preload_content=False)
        image_list = json.loads(image_list.data)
        for image in image_list['items']:
            image_fqn, image_sha = image['dockerImageReference'].split("@")
            if image_name in image_fqn:
                print("Found image: %s" % image_fqn)
                if registry not in image_fqn:
                    # This warning will only get displayed if a user has used --registry-route
                    # This is because the route name gets collapsed into the service hostname
                    # when pushed to the registry.
                    print("Warning: Tagged image registry prefix doesn't match. Deleting anyway. Given: %s; Found: %s"
                          % (registry, image_fqn.split('/')[0]))
                oapi.delete_image(name=image_sha, body={})
                print("Successfully deleted %s" % image_sha)

    except Exception as e:
        print("Exception deleting old images: %s" % e)
        print("Not erroring out, this may cause duplicate images in the registry. Try: `oc get images`.")
    return


def push_apb(registry, tag):
    try:
        client = create_docker_client()
        openshift_config.load_kube_config()
        api_key = openshift_client.Configuration().get_api_key_with_prefix('authorization')
        if api_key is None:
            raise Exception("No api key found in kubeconfig. NOTE: system:admin" +
                            "*cannot* be used with apb, since it does not have a token.")
        token = api_key.split(" ")[1]
        username = "developer" if is_minishift() else "unused"
        client.login(username=username, password=token, registry=registry, reauth=True)
        delete_old_images(tag)

        print("Pushing the image, this could take a minute...")
        client.images.push(tag)
        print("Successfully pushed image: " + tag)
    except docker.errors.DockerException:
        print("Error accessing the docker API. Is the daemon running?")
        raise
    except docker.errors.APIError:
        print("Failed to login to the docker API.")
        raise


def cmdrun_setup(**kwargs):
    try:
        create_docker_client()
    except Exception as e:
        print("Error! Failed to connect to Docker client. Please ensure it is running. Exception: %s" % e)
        exit(1)

    try:
        openshift_config.load_kube_config()

#        base64.b64decode(username = kubernetes_client.configuration.get_basic_auth_token().split(' ')[1]))
#        print(kubernetes_client.configuration.password)
        oapi = openshift_client.OapiApi()
        projlist = oapi.list_project()

    except Exception as e:
        print("\nError! Failed to list namespaces on OpenShift cluster. Please ensure OCP is running.")
        print("Exception: %s" % e)
        exit(1)

    try:
        helper = OpenShiftObjectHelper(api_version='v1', kind='user')
        user_body = {'metadata': {'name': 'apb-developer'}}
        helper.create_object(body=user_body)
    except Exception as e:
        print("\nError! Failed to create APB developer user. Exception: %s" % e)

    try:
        crb = create_cluster_role_binding('apb-development', 'apb-developer')
        print(crb)
    except Exception as e:
        print("\nError! %s" % e)

    broker_installed = False
    svccat_installed = False
    proj_default_access = False

    for project in projlist.items:
        name = project.metadata.name
        if name == "default":
            proj_default_access = True
        elif "ansible-service-broker" in name:
            broker_installed = True
        elif "service-catalog" in name:
            svccat_installed = True
    if broker_installed is False:
        print("Error! Could not find OpenShift Ansible Broker namespace. Please ensure that the broker is\
                installed and that the current logged in user has access.")
        exit(1)
    if svccat_installed is False:
        print("Error! Could not find OpenShift Service Catalog namespace. Please ensure that the Service\
                Catalog is installed and that the current logged in user has access.")
    if proj_default_access is False:
        print("Error! Could not find the Default namespace. Please ensure that the current logged in user has access.")


def cmdrun_init(**kwargs):
    current_path = kwargs['base_path']
    bindable = kwargs['bindable']
    async = kwargs['async']
    dockerhost = kwargs['dockerhost']
    skip = {
        'provision': kwargs['skip-provision'],
        'deprovision': kwargs['skip-deprovision'],
        'bind': kwargs['skip-bind'] or not kwargs['bindable'],
        'unbind': kwargs['skip-unbind'] or not kwargs['bindable'],
        'roles': kwargs['skip-roles']
    }

    apb_tag_arr = kwargs['tag'].split('/')
    apb_name = apb_tag_arr[-1]
    app_org = apb_tag_arr[0]
    if apb_name.lower().endswith("-apb"):
        app_name = apb_name[:-4]
    else:
        app_name = apb_name

    description = "This is a sample application generated by apb init"

    apb_dict = {
        'name': apb_name,
        'app_name': app_name,
        'app_org': app_org,
        'description': description,
        'bindable': bindable,
        'async': async,
        'dockerhost': dockerhost
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
    makefile_path = os.path.join(os.path.join(project, MAKEFILE))

    specfile_out = load_example_specfile(apb_dict, [])
    write_file(specfile_out, spec_path, kwargs['force'])

    dockerfile_out = load_dockerfile(EX_DOCKERFILE_PATH)
    write_file(dockerfile_out, dockerfile_path, kwargs['force'])

    makefile_out = load_makefile(apb_dict, [])
    write_file(makefile_out, makefile_path, kwargs['force'])

    generate_playbook_files(project, skip, apb_dict)
    print("Successfully initialized project directory at: %s" % project)
    print("Please run *apb prepare* inside of this directory after editing files.")


def cmdrun_prepare(**kwargs):
    project = kwargs['base_path']
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
    build_apb(
        project,
        kwargs['dockerfile'],
        kwargs['tag']
    )


def cmdrun_relist(**kwargs):
    relist_service_broker(kwargs)


def cmdrun_push(**kwargs):
    project = kwargs['base_path']
    spec = get_spec(project, 'string')
    dict_spec = get_spec(project, 'dict')
    blob = base64.b64encode(spec)
    data_spec = {'apbSpec': blob}
    broker = kwargs["broker"]
    if broker is None:
        broker = get_asb_route()
    print(spec)
    if kwargs['broker_push']:
        response = broker_request(broker, "/v2/apb", "post", data=data_spec,
                                  verify=kwargs["verify"],
                                  basic_auth_username=kwargs.get("basic_auth_username"),
                                  basic_auth_password=kwargs.get("basic_auth_password"))

        if response.status_code != 200:
            print("Error: Attempt to add APB to the Broker returned status: %d" % response.status_code)
            print("Unable to add APB to Ansible Service Broker.")
            exit(1)

        print("Successfully added APB to Ansible Service Broker")
        return

    registry = get_registry(kwargs)
    tag = registry + "/" + kwargs['namespace'] + "/" + dict_spec['name']

    build_apb(project, kwargs['dockerfile'], tag)
    push_apb(registry, tag)
    bootstrap(
        broker,
        kwargs.get("basic_auth_username"),
        kwargs.get("basic_auth_password"),
        kwargs["verify"]
    )

    if not kwargs['no_relist']:
        relist_service_broker(kwargs)


def cmdrun_remove(**kwargs):
    if kwargs["all"]:
        route = "/v2/apb"
    elif kwargs["id"] is not None:
        route = "/v2/apb/" + kwargs["id"]
    elif kwargs["local"] is True:
        print("Attempting to delete associated registry image.")
        project = kwargs['base_path']
        spec = get_spec(project, 'dict')
        kwargs['reg_namespace'] = "default"
        kwargs['reg_svc_name'] = "docker-registry"
        kwargs['reg_route'] = None
        kwargs['namespace'] = "openshift"

        registry = get_registry(kwargs)
        tag = registry + "/" + kwargs['namespace'] + "/" + spec['name']
        print("Image: [%s]" % tag)
        delete_old_images(tag)
        bootstrap(
            kwargs["broker"],
            kwargs.get("basic_auth_username"),
            kwargs.get("basic_auth_password"),
            kwargs["verify"]
        )
        exit()
    else:
        raise Exception("No flag specified.  Use --id or --local.")

    response = broker_request(kwargs["broker"], route, "delete",
                              verify=kwargs["verify"],
                              basic_auth_username=kwargs.get("basic_auth_username"),
                              basic_auth_password=kwargs.get("basic_auth_password"))

    if response.status_code != 204:
        print("Error: Attempt to remove an APB from Broker returned status: %d" % response.status_code)
        print("Unable to remove APB from Ansible Service Broker.")
        exit(1)

    if not kwargs['no_relist']:
        relist_service_broker(kwargs)

    print("Successfully deleted APB")


def bootstrap(broker, username, password, verify):
    response = broker_request(broker, "/v2/bootstrap", "post", data={},
                              verify=verify,
                              basic_auth_username=username,
                              basic_auth_password=password)

    if response.status_code != 200:
        print("Error: Attempt to bootstrap Broker returned status: %d" % response.status_code)
        print("Unable to bootstrap Ansible Service Broker.")
        exit(1)

    print("Successfully bootstrapped Ansible Service Broker")


def cmdrun_bootstrap(**kwargs):
    bootstrap(kwargs["broker"], kwargs.get("basic_auth_username"), kwargs.get("basic_auth_password"), kwargs["verify"])

    if not kwargs['no_relist']:
        relist_service_broker(kwargs)


def cmdrun_serviceinstance(**kwargs):
    project = kwargs['base_path']
    spec = get_spec(project)

    defaultValue = "ansibleplaybookbundle"
    params = {}
    plan_names = "(Plans->"
    first_plan = 0
    for plan in spec['plans']:
        plan_names = "%s|%s" % (plan_names, plan['name'])

        # Only save the vars from the first plan
        if first_plan == 0:
            print("Only displaying vars from the '%s' plan." % plan['name'])
            for param in plan['parameters']:
                try:
                    if param['required']:
                        # Save a required param name and set a defaultValue
                        params[param['name']] = defaultValue
                except Exception:
                    pass
        first_plan += 1

    plan_names = "%s)" % plan_names
    serviceInstance = dict(apiVersion="servicecatalog.k8s.io/v1beta1",
                           kind="ServiceInstance",
                           metadata=dict(
                               name=spec['name']
                           ),
                           spec=dict(
                               clusterServiceClassExternalName="dh-" + spec['name'],
                               clusterServicePlanExternalName=plan_names,
                               parameters=params
                           )
                           )

    with open(spec['name'] + '.yaml', 'w') as outfile:
        yaml.dump(serviceInstance, outfile, default_flow_style=False)


def rand_str(size=5, chars=string.ascii_lowercase + string.digits):
    return ''.join(random.choice(chars) for _ in range(size))


def cmdrun_test(**kwargs):
    project = kwargs['base_path']
    registry = get_registry(kwargs)
    spec = get_spec(project)
    tag = registry + "/" + kwargs['namespace'] + "/" + spec['name']

    build_apb(project, kwargs['dockerfile'], tag)
    push_apb(registry, tag)

    spec = get_spec(project)
    test_name = 'apb-test-{}-{}'.format(spec['name'], rand_str())
    name, namespace = run_apb(
        project=test_name,
        image=tag,
        name=test_name,
        action='test'
    )
    if not name or not namespace:
        print("Failed to run apb")
        return

    test_result = retrieve_test_result(name, namespace)
    test_results = []
    if test_result is None:
        print("Unable to retrieve test result.")
        delete_project(test_name)
        return
    else:
        test_results = test_result.splitlines()

    if len(test_results) > 0 and "0" in test_results[0]:
        print("Test successfully passed")
    elif len(test_results) == 0:
        print("Unable to retrieve test result.")
    else:
        print(test_result)

    delete_project(test_name)


def cmdrun_run(**kwargs):
    apb_project = kwargs['base_path']
    registry = get_registry(kwargs)
    spec = get_spec(apb_project)
    tag = registry + "/" + kwargs['namespace'] + "/" + spec['name']

    image = build_apb(
        apb_project,
        kwargs['dockerfile'],
        tag
    )
    push_apb(registry, tag)

    plans = [plan['name'] for plan in spec['plans']]
    if len(plans) > 1:
        plans_str = ', '.join(plans)
        while True:
            try:
                plan = plans.index(input("Select plan [{}]: ".format(plans_str)))
                break
            except ValueError:
                print("ERROR: Please enter valid plan")
    else:
        plan = 0

    parameters = {
        '_apb_plan_id': spec['plans'][plan]['name'],
    }
    for parm in spec['plans'][plan]['parameters']:
        while True:
            # Get the value for the parameter
            val = input("{}{}{}: ".format(
                parm['name'],
                "(required)" if 'required' in parm and parm['required'] else '',
                "[default: {}]".format(parm['default']) if 'default' in parm else ''
            ))
            # Take the value if something
            if val:
                break
            else:
                # Take the default if nothing
                if 'default' in parm:
                    val = parm['default']
                    break
                # If not required move on
                if ('required' not in parm) or (not parm['required']):
                    break
                # Tell the user if the parameter is required
                if 'default' not in parm and 'required' in parm and parm['required']:
                    print("ERROR: Please provide value for required parameter")
        parameters[parm['name']] = val

    name, namespace = run_apb(
        project=kwargs['project'],
        image=image,
        name='apb-run-{}-{}'.format(kwargs['action'], spec['name']),
        action=kwargs['action'],
        parameters=parameters
    )
    if not name or not namespace:
        print("Failed to run apb")
        return

    print("APB run started")
    try:
        pod_completed = watch_pod(name, namespace)
        print("APB run complete: {}".format(pod_completed))
    except Exception as e:
        print("APB run failed: {}".format(e))
        exit(1)


def create_docker_client():
    # In order to build and push to the minishift registry, it's required that
    # users have configured their shell to use the minishift docker daemon
    # instead of a local daemon:
    # https://docs.openshift.org/latest/minishift/using/docker-daemon.html
    if is_minishift():
        cert_path = os.environ.get('DOCKER_CERT_PATH')
        docker_host = os.environ.get('DOCKER_HOST')
        if docker_host is None or cert_path is None:
            raise Exception("Attempting to target minishift, but missing required \
                            env vars. Try running: \"eval $(minishift docker-env)\"")
        client_cert = os.path.join(cert_path, 'cert.pem')
        client_key = os.path.join(cert_path, 'key.pem')
        ca_cert = os.path.join(cert_path, 'ca.pem')
        tls = docker.tls.TLSConfig(
            ca_cert=ca_cert,
            client_cert=(client_cert, client_key),
            verify=True,
            assert_hostname=False
        )
        client = docker.DockerClient(tls=tls, base_url=docker_host, version='auto')
    else:
        client = docker.DockerClient(base_url='unix://var/run/docker.sock', version='auto')
    return client


def is_minishift():
    # Assume user is using minishift if the shell has been configured to use
    # a minishift docker daemon.
    docker_cert_path = os.environ.get('DOCKER_CERT_PATH')
    if docker_cert_path is None:
        return False
    return "minishift" in docker_cert_path


def get_minishift_registry():
    cmd = "minishift openshift registry"
    return os.environ.get('MINISHIFT_REGISTRY') or \
        subprocess.check_output(cmd, stderr=subprocess.STDOUT, shell=True).rstrip()
