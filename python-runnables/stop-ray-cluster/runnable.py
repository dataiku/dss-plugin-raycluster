# This file is the actual code for the Python runnable stop-ray-cluster
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
        Stop Ray Cluster.
        """
        # Unpack config
        cluster_name = self.config.get("k8s_cluster_name")
        
        # Set kubeconfig environment variable
        configure_kubeconfig(cluster_name)
        
        # Install Helm locally if not installed already
        helm_cmd = get_helm_cmd()
        
        # Uninstall the KubeRay Cluster and Operator
        try:
            r = subprocess.run([helm_cmd, "uninstall", "kuberay-operator"], capture_output=True) 
            r.check_returncode()
            
            r = subprocess.run([helm_cmd, "uninstall", "raycluster"])
            r.check_returncode() 
        except Exception as e:
            raise Exception(
                f"RayCluster or KubeRay operator uninstall failed with error: {r.stderr.decode('utf-8')}. " + \
                "Is the selected Elastic AI cluster running? Or else, do you need to first start a RayCluster with the 'Start Ray Cluster' macro?"
            ) from e
        
        return f"RayCluster uninstalled successfully from Dataiku Elastic AI Cluster {cluster_name}."
        