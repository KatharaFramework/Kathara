import os
import shutil
import json

from flask import Flask, request, jsonify, abort
import re
import sqlite3

from Resources.utils import generate_urlsafe_hash, get_lab_temp_path
from Resources.model.Lab import Lab
from Resources.manager.ManagerProxy import ManagerProxy
from Resources.exceptions import MachineAlreadyExistsError

app = Flask('Kathara Server')


def _read_scenarios():
    con = sqlite3.connect('scenarios.db')
    cur = con.cursor()
    result = dict(cur.execute('''SELECT * FROM scenarios;'''))
    con.close()
    return result


def _write_scenarios_entry(scenario_name, scenario_hash):
    con = sqlite3.connect('scenarios.db')
    cur = con.cursor()
    cur.execute('''INSERT INTO scenarios (scenario_name, scenario_hash) VALUES ("%s","%s");''' % (
        scenario_name,
        scenario_hash))
    con.commit()
    con.close()


def _delete_scenarios_entry(scenario_name):
    con = sqlite3.connect('scenarios.db')
    cur = con.cursor()
    cur.execute('''DELETE FROM scenarios WHERE scenario_name="%s";''' % scenario_name)
    con.commit()
    con.close()


def _delete_scenarios_table():
    print("Deleting Scenarios Table...")
    for scenario_name, scenario_hash in _read_scenarios().items():
        _wipe_scenario(scenario_name)


def _create_scenarios_table():
    con = sqlite3.connect('scenarios.db')
    cur = con.cursor()

    print("Creating Scenarios Table...")
    # Create table
    cur.execute('''CREATE TABLE IF NOT EXISTS scenarios
                   (scenario_name text, scenario_hash text)''')
    con.commit()
    con.close()


def _parse_device_argument(args):
    default_args = {
        'bridged': False,
        'cpus': None,
        'dry_mode': False,
        'eths': None,
        'exec_commands': None,
        'image': None,
        'mem': None,
        'name': None,
        'no_hostname': None,
        'no_shared': False,
        'num_terms': None,
        'ports': None,
        'privileged': False,
        'shell': None,
        'sysctls': None,
        'terminals': False,
        'xterm': None,
        'filesystem': {},
        'startup': None
    }

    for key, v in args.items():
        if key not in default_args:
            raise Exception('Argument %s not supported for device' % key)
        default_args[key] = v

    return default_args


def _wipe_scenario(scenario_name):
    lab_dir = get_lab_temp_path(_read_scenarios()[scenario_name])
    lab = Lab(lab_dir)
    ManagerProxy.get_instance().undeploy_lab(lab.folder_hash)

    shutil.rmtree(lab_dir)


@app.errorhandler(404)
def resource_not_found(e):
    return jsonify(error=str(e)), 404


@app.errorhandler(400)
def bad_request(e):
    return jsonify(error=str(e)), 400


@app.route('/scenarios')
def get_scenarios():
    return jsonify({'scenarios': _read_scenarios()}), 200


@app.route('/scenarios/<scenario_name>', methods=["POST"])
def create_scenario(scenario_name):
    scenarios = _read_scenarios()

    if scenario_name in scenarios:
        return abort(400, description='Scenario %s already exists' % scenario_name)

    _write_scenarios_entry(scenario_name, generate_urlsafe_hash(scenario_name))

    return jsonify({}), 201


@app.route('/scenarios/<scenario_name>', methods=["DELETE"])
def delete_scenario(scenario_name):
    _wipe_scenario(scenario_name)

    _delete_scenarios_entry(scenario_name)

    return jsonify({}), 200


@app.route('/scenarios/<scenario_name>/device', methods=['POST'])
def create_device(scenario_name):
    lab_dir = get_lab_temp_path(_read_scenarios()[scenario_name])
    lab = Lab(lab_dir)
    args = _parse_device_argument(json.loads(request.form.get('data')))

    machine_name = args['name'].strip()
    matches = re.search(r"^[a-z0-9_]{1,30}$", machine_name)
    if not matches:
        raise abort(400, description='Invalid device name `%s`.' % machine_name)

    machine = lab.get_or_new_machine(machine_name)

    machine.add_meta_from_args(args)

    lab_conf_path = os.path.join(lab.path, 'lab.conf')
    with open(lab_conf_path, 'a') as lab_file:
        for number, link in machine.interfaces.items():
            lab_file.write("%s[%s]='%s'\n" % (machine_name, number, link.name))

    machine_directory = os.path.join(lab.path, machine_name)
    print(machine_directory)
    os.makedirs(machine_directory, exist_ok=True)
    print(machine_directory)
    # print(request.files)
    if 'startup' in request.files:
        startup = request.files['startup']
        startup_path = os.path.join(lab.path, 'startup')
        startup.save(startup_path)

    for path, file_name in args['filesystem'].items():
        machine_path = os.path.join(machine_directory, path)
        os.makedirs(machine_path, exist_ok=True)
        path_to_upload = os.path.join(os.path.join(path, file_name))
        request.files[path_to_upload].save(os.path.join(machine_directory, path_to_upload))

    try:
        ManagerProxy.get_instance().deploy_lab(lab, privileged_mode=args['privileged'])
    except MachineAlreadyExistsError as e:
        return abort(400, description=str(e))
    except Exception as e:
        return abort(400, description=str(e))

    return jsonify({}), 201


@app.route('/scenarios/<scenario_name>/device/<device_name>')
def get_device(scenario_name, device_name):
    lab_dir = get_lab_temp_path(_read_scenarios()[scenario_name])
    lab = Lab(lab_dir)

    try:
        machine_info = ManagerProxy.get_instance().get_machine_info(device_name,
                                                                    lab_hash=lab.folder_hash)
    except Exception as e:
        return abort(404, description=str(e))

    return jsonify({'device_info': machine_info}), 200


@app.route('/scenarios/<scenario_name>/device/<device_name>', methods=['DELETE'])
def delete_device(scenario_name, device_name):
    lab_dir = get_lab_temp_path(_read_scenarios()[scenario_name])
    lab = Lab(lab_dir)

    ManagerProxy.get_instance().undeploy_lab(lab.folder_hash,
                                             selected_machines={device_name}
                                             )

    return jsonify({}), 200


if __name__ == '__main__':
    _create_scenarios_table()
    app.run(host='localhost', port=5000)
    _delete_scenarios_table()
