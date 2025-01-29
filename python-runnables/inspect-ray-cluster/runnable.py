import dataiku
from dataiku.runnables import Runnable, utils, ResultTable
from raycluster.utils import get_helm_cmd, configure_kubeconfig

import os
import subprocess
import json


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
        Inspect running RayCluster.
        Return pods listing and cluster endpoint URL.
        """
        # Unpack config
        cluster_name = self.config.get("k8s_cluster_name")
        
        # Set kubeconfig environment variable
        configure_kubeconfig(cluster_name)
        
        # Retrieve a list of all RayCluster pods
        try:
            r = subprocess.run(["kubectl", "get", "pods", "--selector=ray.io/cluster=raycluster-kuberay", "-o", "json"], capture_output=True) 
            r.check_returncode()
        except Exception as e:
            raise Exception(f"Error listing KubeRay pods: {r.stderr.decode('utf-8')}. Is the Elastic AI cluster running?") from e
        
        kuberay_pods = json.loads(r.stdout.decode("utf-8").strip())
        
        # Extract required information from pods and start building result table
        # e.g. name, ready, statys, restarts, and age
        rt = ResultTable()
        
        rt.add_column("name", "Pod Name", "STRING")
        rt.add_column("phase", "Phase", "STRING")
        rt.add_column("ip", "IP", "STRING")
        
        for pod in kuberay_pods.get("items", []):
            record = []
            record.append(pod.get("metadata", {}).get("name"))
            record.append(pod.get("status", {}).get("phase"))
            record.append(pod.get("status", {}).get("podIP", "Not Assigned"))
            rt.add_record(record)
            
        # Attempt to retrieve kuberay cluster endpoint
        try:
            r = subprocess.run(["kubectl", "get", "pods", "--selector=ray.io/group=headgroup", "-o", "json"], capture_output=True) 
            r.check_returncode()
        except Exception as e:
            raise Exception(f"Error listing KubeRay pods: {r.stderr.decode('utf-8')}. Is the Elastic AI cluster running?") from e
        
        kuberay_head_pods = json.loads(r.stdout.decode("utf-8").strip()) # this may return no pods if ray cluster is not running
        
        if len(kuberay_head_pods["items"]):
            head_pod_name = kuberay_head_pods["items"][0]["metadata"]["name"]
      
            try:
                r = subprocess.run(["kubectl", "get", "pod", head_pod_name, "--template", "'{{.status.podIP}}'"], capture_output=True) 
                r.check_returncode()
            except Exception as e:
                raise Exception(f"Error listing KubeRay pods: {r.stderr.decode('utf-8')}. Is the Elastic AI cluster running?") from e

            head_pod_ip = r.stdout.decode("utf-8").strip()

            # Add the ray cluster IP to the results table
            record = []
            record.append(" ")
            rt.add_record(record)
            
            record = []
            record.append("Ray Cluster endpoint: ")
            record.append(f"http://{head_pod_ip[1:-1]}:8265")
            rt.add_record(record)
            
        return rt
        