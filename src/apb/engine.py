import errno
import os
import uuid
import base64
import string
import subprocess
import json
import docker
import docker.errors
import ruamel.yaml
import yaml

from ruamel.yaml import YAML
from time import sleep
from jinja2 import Environment, FileSystemLoader

import request
from broker_request.apb_list import Apb_List
from broker_request.apb_push import Apb_Push
from broker_request.apb_relist import Apb_Relist

# Handle input in 2.x/3.x
try:
    input = raw_input
except NameError:
    pass

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


class CmdRun(object):
    def __init__(self, **args):
        self.r = request.Request(args)
        self.args = args

    def run(self, cmd):
        try:
            getattr(self, u'cmdrun_{}'.format(cmd))()
        except Exception as e:
            print("%s failure: {}".format(e) % cmd)

    def cmdrun_list(self):
        Apb_List(self.args)

    def cmdrun_push(self):
        Apb_Push(self.args)
        if not self.args['no_relist']:
            Apb_Relist(self.args)

    def cmdrun_init(self):
        return self.r.apb_init()


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


def relist_service_broker(kwargs):
    try:
        r = request.Request(kwargs)
        response = r.relist_service_broker()

        if response is not None:
            raise response
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
        service_account = api.create_namespaced_service_account(
            namespace,
            {
                'apiVersion': 'v1',
                'kind': 'ServiceAccount',
                'metadata': {
                    'generateName': name,
                    'namespace': namespace,
                },
            }
        )
        print("Created service account")
        return service_account.metadata.name
    except ApiException as e:
        raise e


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
    try:
        kubernetes_config.load_kube_config()
        api = kubernetes_client.CoreV1Api()

        while True:
            pod_phase = api.read_namespaced_pod(name, namespace).status.phase
            if pod_phase == 'Succeeded' or pod_phase == 'Failed':
                return pod_phase
            sleep(WATCH_POD_SLEEP)
    except ApiException as e:
        print("Get pod failure: {}".format(e))
        raise e


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
            api_response = api.connect_post_namespaced_pod_exec(
                name, namespace,
                command="/usr/bin/test-retrieval",
                tty=False)
            if "non-zero exit code" not in api_response:
                return api_response
        except ApiException as e:
            if count >= 50:
                return None
            pod_phase = api.read_namespaced_pod(name, namespace).status.phase
            if pod_phase == 'Succeeded' or pod_phase == 'Failed':
                print("Pod phase {} without returning test results".format(pod_phase))
                return None
            sleep(WATCH_POD_SLEEP)
        except Exception as e:
            print("execption: %s" % e)
            return None


def broker_request(broker, service_route, method, **kwargs):
    try:
        r = request.Request(kwargs)
        if broker is None:
            broker = r.get_asb_route()
        else:
            broker = "%s/ansible-service-broker" % broker

        if response is not None:
            raise response
    except Exception as e:
        print("broker_request failure: {}".format(e))

    print("Contacting the ansible-service-broker at: %s%s" % (broker, service_route))

    if broker is None:
        raise Exception("Could not find route to ansible-service-broker. "
                        "Use --broker or log into the cluster using \"oc login\"")

    url = broker + service_route

    from openshift import client as openshift_client, config as openshift_config
    import requests

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
        client = docker.DockerClient(base_url='unix://var/run/docker.sock', version='auto')
        client.images.build(path=project, tag=tag, dockerfile=dockerfile)
    except docker.errors.DockerException:
        print("Error accessing the docker API. Is the daemon running?")
        raise

    print("Successfully built APB image: %s" % tag)
    return tag


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


def cmdrun_remove(**kwargs):
    if kwargs["all"]:
        route = "/v2/apb"
    elif kwargs["id"] is not None:
        route = "/v2/apb" + kwargs["id"]
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


def cmdrun_test(**kwargs):
    project = kwargs['base_path']
    image = build_apb(
        project,
        kwargs['dockerfile'],
        kwargs['tag']
    )

    spec = get_spec(project)
    test_name = 'apb-test-{}'.format(spec['name'])
    name, namespace = run_apb(
        project=test_name,
        image=image,
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
    image = build_apb(
        apb_project,
        kwargs['dockerfile'],
        kwargs['tag']
    )

    spec = get_spec(apb_project)
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
            # Take the default if nothing
            if val == "" and 'default' in parm:
                val = parm['default']
                break
            # If not required move on
            if val == "" and ('required' not in parm) or (not parm['required']):
                break
            # Tell the user if the parameter is required
            if val == "" and 'default' not in parm and 'required' in parm and parm['required']:
                print("ERROR: Please provide value for required parameter")
        parameters[parm['name']] = val

    name, namespace = run_apb(
        project=kwargs['project'],
        image=image,
        name='apb-run-{}'.format(spec['name']),
        action=kwargs['action'],
        parameters=parameters
    )
    if not name or not namespace:
        print("Failed to run apb")
        return

    print("APB run started")
    print("APB run complete: {}".format(watch_pod(name, namespace)))
