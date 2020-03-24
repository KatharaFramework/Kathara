from kubernetes import config, client

from ...setting.Setting import Setting


class KubernetesConfig(object):
    @staticmethod
    def get_cluster_user():
        _, current_context = config.kube_config.list_kube_config_contexts()
        return current_context['name']

    @staticmethod
    def load_kube_config():
        try:
            config.load_kube_config()           # Try to load configuration if Kathara is launched on a k8s master.
        except Exception:                       # Not on a k8s master, load Kathara setting to read remote cluster data.
            api_url = Setting.get_instance().api_server_url
            token = Setting.get_instance().api_token

            if not api_url or not token:
                raise ConnectionError("Cannot read Kubernetes configuration.")

            # Load the configuration and set it as default.
            configuration = client.Configuration()
            configuration.host = api_url
            configuration.api_key = {"authorization": "Bearer " + token}

            client.Configuration.set_default(configuration)
