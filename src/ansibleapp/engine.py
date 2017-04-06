import os
import uuid
import base64
import yaml

from shutil import copyfile

SPEC_FILE = 'ansibleapp.yml'
SPEC_LABEL = 'com.redhat.ansibleapp.spec'
ACTIONS_DIR = os.path.join('ansibleapp', 'actions')


def load_dockerfile(df_path):
    with open(df_path, 'r') as dockerfile:
        return dockerfile.readlines()


def write_dockerfile(dockerfile, destination):
    touch(destination)
    with open(destination, 'w') as outfile:
        outfile.write(''.join(dockerfile))


def insert_encoded_spec(dockerfile, encoded_spec_lines):
    apb_spec_idx = [i for i, line in enumerate(dockerfile) if SPEC_LABEL in line][0]
    end_encoding_idx = [i for i, line in enumerate(dockerfile) if line.endswith('"\n')]

    if end_encoding_idx:
        # Make sure we grab the correct ending to the encoded message
        # since multiple lines can end in '"\n'
        for correct_ending_idx in end_encoding_idx:
            if correct_ending_idx > apb_spec_idx:
                end_encoding_idx = correct_ending_idx
                del dockerfile[apb_spec_idx+1:end_encoding_idx+1]
                break

    if not apb_spec_idx:
        raise Exception(
            "ERROR: %s missing from dockerfile while inserting spec blob" %
            SPEC_LABEL
        )

    split_idx = apb_spec_idx + 1

    dockerfile[split_idx:split_idx] = encoded_spec_lines

    # Add a new line after we add the encoding
    encoding_offset = apb_spec_idx + len(encoded_spec_lines) + 1
    dockerfile.insert(encoding_offset, "\n")

    return dockerfile


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
        elif i == line_break - 1:
            fmtstr = '{0}"\n'

        offset = i * line_break
        line = fmtstr.format(blob[offset:(offset + line_break)])
        flines.append(line)

    if mod != 0:
        # Add incomplete chunk if we've got some left over,
        # this is the usual case
        flines.append('{0}"'.format(blob[line_break * chunks:]))

    return flines


def touch(fname):
    if os.path.exists(fname):
        os.utime(fname, None)
    else:
        open(fname, 'a').close()


def init_actions(project_path, provider):
    actions_path = os.path.join(project_path, ACTIONS_DIR)
    src_file = 'shipit-%s.yml' % provider
    provision_src_path = os.path.join(project_path, 'ansible', src_file)
    provision_dest_path = os.path.join(actions_path, 'provision.yaml')

    if not os.path.exists(actions_path):
        os.makedirs(actions_path)

    ansible_dir = os.path.join(project_path, 'ansible')
    ansible_dir_exists = os.path.exists(ansible_dir)
    if ansible_dir_exists:
        # Only write over provision.yml if the file doesn't already exist
        if not os.path.exists(provision_dest_path):
            copyfile(provision_src_path, provision_dest_path)
    else:
        print('NOTE: No ansible dir found at project root.' +
              'Assuming manual authoring.')


def init_dockerfile(spec_path, dockerfile_path):
    # TODO: Defensively confirm the strings are encoded
    # the way the code expects
    blob = base64.b64encode(load_spec_str(spec_path))
    dockerfile_out = insert_encoded_spec(
        load_dockerfile(dockerfile_path), make_friendly(blob)
    )

    write_dockerfile(dockerfile_out, dockerfile_path)
    print('Finished writing dockerfile.')


def cmdrun_prepare(**kwargs):
    project = kwargs['base_path']
    spec_path = os.path.join(project, SPEC_FILE)
    dockerfile_path = os.path.join(os.path.join(project, 'Dockerfile'))

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

    dockerfile_exists = os.path.exists(os.path.join(project, 'Dockerfile'))

    init_actions(project, kwargs['provider'])
    init_dockerfile(spec_path, dockerfile_path)


def cmdrun_build(**kwargs):
    raise Exception('ERROR: BUILD NOT YET IMPLEMENTED!')
