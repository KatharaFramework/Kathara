import requests
import json
import os


def build_url(request):
    return "http://localhost:5000/%s" % request


def create_scenario(name):
    request_url = build_url('scenarios/%s' % name)
    response = requests.post(request_url,
                             json={},
                             timeout=None)
    return response.json()


def get_scenarios():
    request_url = build_url('scenarios')
    response = requests.get(request_url,
                            json={},
                            timeout=None)

    result = None
    while result is None:
        try:
            result = response.json()['scenarios']
        except json.decoder.JSONDecodeError:
            pass

    return result


def wipe_scenario(name):
    request_url = build_url('scenarios/%s' % name)
    response = requests.delete(request_url,
                               json={},
                               timeout=None)
    return response.json()


def create_device(scenario_name, args):
    request_url = build_url('scenarios/%s/device' % scenario_name)

    files = {}
    if 'startup' in args:
        files['startup'] = open(args['startup'], 'r')
    for remote_path, (file_name, local_path) in args['filesystem'].items():
        files[os.path.join(remote_path, file_name)] = open(os.path.join(local_path, file_name), 'r')
        args['filesystem'][remote_path] = args['filesystem'][remote_path][0]

    response = requests.post(request_url,
                             data={'data': json.dumps(args)},
                             timeout=None,
                             files=files)
    return response.json()


def get_device(scenario_name, device_name):
    request_url = build_url('scenarios/%s/device/%s' % (scenario_name, device_name))
    response = requests.get(request_url,
                            json={},
                            timeout=None)

    return response.json()


def delete_device(scenario_name, device_name):
    request_url = build_url('scenarios/%s/device/%s' % (scenario_name, device_name))
    response = requests.delete(request_url,
                               json={},
                               timeout=None)

    return response.json()


if __name__ == '__main__':
    print('Getting Scenarios...')
    print(get_scenarios())

    print('Creating Scenario...')
    print(create_scenario("scenario2"))
    # create_scenario("scenario3")
    #
    # scenarios = get_scenarios()
    # print(scenarios)
    #
    # print(wipe_scenario('scenario2'))
    # wipe_scenario('scenario3')
    print('Getting Scenarios...')
    print(get_scenarios())
    #
    device_info = {
        'name': 'pc1',
        'eths': ['0:A', '1:B'],
        'startup': 'pc1.startup',
        'filesystem': {
            'etc': ('pc1.config',  '.')
        }
    }

    device_info2 = {
        'name': 'pc2',
        'eths': ['0:A', '1:B'],
        # 'startup': 'pc2.startup',
        'filesystem': {
            'etc': ('pc1.config',  '.')
        }
    }

    print('Create Device... ', device_info)
    print(create_device('scenario2', device_info))
    print('Create Device... ', device_info2)
    print(create_device('scenario2', device_info2))
    print('Getting Device...')
    print(get_device('scenario2', 'pc1'))
    print('Deleting Device pc1...')
    print(delete_device('scenario2', 'pc1'))
    print('Getting Device pc1...')
    print(get_device('scenario2', 'pc1'))

    # print('Deleting scenarios')
    # print(wipe_scenario('scenario2'))






