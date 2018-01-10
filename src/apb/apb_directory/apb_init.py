import errno
import os
import requests
import shutil
import string

from jinja2 import Environment, FileSystemLoader

from apb_directory import Apb_Directory


class Apb_Init(Apb_Directory):
    '''
    Initialize a directory for apb development
    '''

    def __init__(self, kwargs):
        super(Apb_Init, self).__init__(kwargs)

        self.dat_dir = 'dat'
        self.dat_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), self.dat_dir)

        self.spec_file = 'apb.yml'
        self.dockerfile = 'Dockerfile'
        self.makefile = 'Makefile'

        self.spec_file = 'apb.yml'
        self.ex_spec_file = 'apb.yml.j2'
        self.ex_spec_file_path = os.path.join(self.dat_path, self.ex_spec_file)

        self.dockerfile = 'Dockerfile'
        self.ex_dockerfile = 'Dockerfile.j2'
        self.ex_dockerfile_path = os.path.join(self.dat_path, self.ex_dockerfile)

        self.makefile = 'Makefile'
        self.ex_makefile = 'Makefile.j2'
        self.ex_makefile_path = os.path.join(self.dat_path, self.ex_makefile)


        self.action_template_dict = {
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

        self.apb_init()


    def _mkdir_p(self, path):
        try:
            os.makedirs(path)
        except OSError as exc:
            if exc.errno == errno.EEXIST and os.path.isdir(path):
                pass
            else:
                raise

    def _load_dockerfile(self, df_path):
        with open(df_path, 'r') as dockerfile:
            return dockerfile.readlines()


    def _load_makefile(self, apb_dict, params):
        env = Environment(loader=FileSystemLoader(self.dat_path), trim_blocks=True)
        template = env.get_template(self.ex_makefile)

        if not params:
            params = []

        return template.render(apb_dict=apb_dict, params=params)


    def _load_example_specfile(self, apb_dict, params):
        env = Environment(loader=FileSystemLoader(self.dat_path), trim_blocks=True)
        template = env.get_template(self.ex_spec_file)

        if not params:
            params = []

        return template.render(apb_dict=apb_dict, params=params)


    def _write_playbook(self, project_dir, apb_dict, action):
        env = Environment(loader=FileSystemLoader(self.dat_path))
        templates = self.action_template_dict[action]
        playbook_template = env.get_template(templates['playbook_template'])
        playbook_out = playbook_template.render(apb_dict=apb_dict, action_name=action)

        playbook_pathname = os.path.join(project_dir,
                                         templates['playbook_dir'],
                                         templates['playbook_file'])
        self._mkdir_p(os.path.join(project_dir, templates['playbook_dir']))
        self._write_file(playbook_out, playbook_pathname, True)


    def _write_role(self, project_path, apb_dict, action):
        env = Environment(loader=FileSystemLoader(self.dat_path))
        templates = self.action_template_dict[action]
        template = env.get_template(templates['role_task_main_template'])
        main_out = template.render(apb_dict=apb_dict, action_name=action)

        role_name = action + '-' + apb_dict['name']
        dir_tpl = string.Template(templates['role_tasks_dir'])
        dir = dir_tpl.substitute(role_name=role_name)
        role_tasks_dir = os.path.join(project_path, dir)

        self._mkdir_p(role_tasks_dir)
        main_filepath = os.path.join(role_tasks_dir, templates['role_task_main_file'])
        self._write_file(main_out, main_filepath, True)


    def _generate_playbook_files(self, project_path, skip, apb_dict):
        print("Generating playbook files")

        for action in self.action_template_dict.keys():
            if not skip[action]:
                self._write_playbook(project_path, apb_dict, action)
                if not skip['roles']:
                    self._write_role(project_path, apb_dict, action)


    def apb_init(self):
        current_path = self.args['base_path']
        bindable = self.args['bindable']
        async = self.args['async']
        dockerhost = self.args['dockerhost']
        skip = {
            'provision': self.args['skip-provision'],
            'deprovision': self.args['skip-deprovision'],
            'bind': self.args['skip-bind'] or not self.args['bindable'],
            'unbind': self.args['skip-unbind'] or not self.args['bindable'],
            'roles': self.args['skip-roles']
        }

        apb_tag_arr = self.args['tag'].split('/')
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
            if not self.args['force']:
                raise Exception('ERROR: Project directory: [%s] found and force option not specified' % project)
            shutil.rmtree(project)

        print("Initializing %s for an APB." % project)

        os.mkdir(project)

        spec_path = os.path.join(project, self.spec_file)
        dockerfile_path = os.path.join(os.path.join(project, self.dockerfile))
        makefile_path = os.path.join(os.path.join(project, self.makefile))

        specfile_out = self._load_example_specfile(apb_dict, [])
        self._write_file(specfile_out, spec_path, self.args['force'])

        dockerfile_out = self._load_dockerfile(self.ex_dockerfile_path)
        self._write_file(dockerfile_out, dockerfile_path, self.args['force'])

        makefile_out = self._load_makefile(apb_dict, [])
        self._write_file(makefile_out, makefile_path, self.args['force'])

        self._generate_playbook_files(project, skip, apb_dict)
        print("Successfully initialized project directory at: %s" % project)
        print("Please run *apb prepare* inside of this directory after editing files.")
