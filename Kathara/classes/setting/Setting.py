import json
import os

MAX_DOCKER_LAN_NUMBER = 256 * 256
MAX_K8S_NUMBER = (1 << 24) - 20

DOCKER = "docker"
K8S = "k8s"


class Setting(object):
    __slots__ = ['setting_path', 'image', 'deployer_type', 'net_counter', 'terminal', 'no_terminals', 'hosthome_mount',
                 'net_prefix', 'machine_prefix']

    __instance = None

    @staticmethod
    def get_instance():
        if Setting.__instance is None:
            Setting()

        return Setting.__instance

    def __init__(self):
        if Setting.__instance is not None:
            raise Exception("This class is a singleton!")
        else:
            self.setting_path = "config.json"

            self.image = 'kathara/netkit_base'
            self.deployer_type = 'docker'
            self.net_counter = 0
            self.terminal = 'xterm -T'
            self.no_terminals = False
            self.hosthome_mount = True
            self.net_prefix = 'kathara'
            self.machine_prefix = 'kathara'

            self.load()

            Setting.__instance = self

    def load(self):
        if not os.path.exists(self.setting_path):
            self.save()
        else:
            with open(self.setting_path, 'r') as settings_file:
                try:
                    settings = json.load(settings_file)

                    for (name, value) in settings.items():
                        setattr(self, name, value)

                    self.check()
                except Exception:
                    raise Exception("Settings file is not a valid JSON. Fix it or delete it before launching.")

    def save(self):
        with open(self.setting_path, 'w') as settings_file:
            settings_file.write(json.dumps(self._to_dict(), indent=True))

    def check(self):
        if self.deployer_type not in [DOCKER, K8S]:
            raise Exception("Deployer Type not allowed.")

        try:
            self.net_counter = int(self.net_counter)

            if self.net_counter < 0:
                raise Exception("Network Counter must be greater or equal than zero.")
            else:
                if self.deployer_type == DOCKER and self.net_counter > MAX_DOCKER_LAN_NUMBER:
                    raise Exception("Network Counter must be lesser than %d." % MAX_DOCKER_LAN_NUMBER)
                elif self.deployer_type == K8S and self.net_counter > MAX_K8S_NUMBER:
                    raise Exception("Network Counter must be lesser than %d." % MAX_K8S_NUMBER)
        except ValueError:
            raise Exception("Network Counter must be an integer.")

    def _to_dict(self):
        return {"image": self.image,
                "deployer_type": self.deployer_type,
                "net_counter": self.net_counter,
                "terminal": self.terminal,
                "no_terminals": self.no_terminals,
                "hosthome_mount": self.hosthome_mount,
                "net_prefix": self.net_prefix,
                "machine_prefix": self.machine_prefix
                }
