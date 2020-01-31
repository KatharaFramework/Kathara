from kubernetes import config, client


class KubernetesConfig(object):
    @staticmethod
    def load_kube_config():
        try:
            config.load_kube_config()           # Try to load configuration if Kathara is launched on a k8s master.
        except Exception:                       # Not on a k8s master, load Kathara config to read remote cluster data.
            # Try to read configuration. If this fails, throw an Exception.
            # try:
            #     api_url = nc.kat_config['api_url']
            #     token = nc.kat_config['token']
            # except Exception:
            #     raise Exception("Cannot read Kubernetes configuration from Kathara.")
            #
            # # Load the configuration and set it as default.
            # configuration = client.Configuration()
            # configuration.host = api_url
            # configuration.api_key = {"authorization": "Bearer " + token}
            #
            # client.Configuration.set_default(configuration)
            pass
