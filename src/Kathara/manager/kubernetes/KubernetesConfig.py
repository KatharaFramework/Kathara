from kubernetes import config, client

from ...setting.Setting import Setting


class KubernetesConfig(object):
    """Class responsible for loading Kubernetes configurations."""
    @staticmethod
    def get_cluster_user() -> str:
        """Return the name of the current cluster user.

        Returns:
            str:
        """
        try:
            # Remote configuration is present, use the API Token as user
            configuration = client.Configuration.get_default_copy()
            return configuration.api_key['authorization']
        except KeyError:
            # In-Cluster configuration, take the context name as user
            _, current_context = config.kube_config.list_kube_config_contexts()
            return current_context['name']

    @staticmethod
    def load_kube_config() -> None:
        """Load a Kubernetes Configuration if Kathara is launched on a k8s master.

        Returns:
            None

        Raises:
            ConnectionError: Cannot read Kubernetes configuration.
        """
        try:
            config.load_kube_config()  # Try to load configuration if Megalos is launched on a k8s master.
        except Exception:  # Not on a k8s master, load Megalos setting to read remote cluster data.
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
