from kubernetes import config, client

from ...setting.Setting import Setting


class KubernetesConfig(object):
    @staticmethod
    def get_cluster_user():
        configuration = client.api_client.Configuration()
        return configuration.api_key['authorization']

    @staticmethod
    def load_kube_config():
        try:
            config.load_kube_config()           # Try to load configuration if Megalos is launched on a k8s master.
        except Exception:                       # Not on a k8s master, load Megalos setting to read remote cluster data.
            api_url = Setting.get_instance().api_server_url
            token = Setting.get_instance().api_token

            if not api_url or not token:
                raise ConnectionError("Cannot read Kubernetes configuration.")

            # Load the configuration and set it as default.
            configuration = client.Configuration()
            configuration.host = api_url
            configuration.api_key_prefix['authorization'] = "Bearer"
            configuration.api_key['authorization'] = token

            client.Configuration.set_default(configuration)
