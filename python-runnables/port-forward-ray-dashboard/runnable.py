# This file is the actual code for the Python runnable port-forward-ray-dashboard
from dataiku.runnables import Runnable
from raycluster.utils import get_helm_cmd, configure_kubeconfig

import subprocess

class MyRunnable(Runnable):
    """The base interface for a Python runnable"""

    def __init__(self, project_key, config, plugin_config):
        """
        :param project_key: the project in which the runnable executes
        :param config: the dict of the configuration of the object
        :param plugin_config: contains the plugin settings
        """
        self.project_key = project_key
        self.config = config
        self.plugin_config = plugin_config
        
    def get_progress_target(self):
        """
        If the runnable will return some progress info, have this function return a tuple of 
        (target, unit) where unit is one of: SIZE, FILES, RECORDS, NONE
        """
        return None

    def run(self, progress_callback):
        """
        Do stuff here. Can return a string or raise an exception.
        The progress_callback is a function expecting 1 value: current progress
        """
        # Unpack config
        cluster_name = self.config.get("k8s_cluster_name")
        
        # Set kubeconfig environment variable
        configure_kubeconfig(cluster_name)
        
        # Uninstall the KubeRay Cluster and Operator
        try:
            r = subprocess.run(["kubectl", "port-forward", "service/raycluster-kuberay-head-svc", "--address", "0.0.0.0", "8265:8265"], capture_output=True) 
            r.check_returncode()
        except Exception as e:
            raise Exception(f"Port-Forward failed with error: {r.stderr.decode('utf-8')}.") from e
        
        return "port forward successful"