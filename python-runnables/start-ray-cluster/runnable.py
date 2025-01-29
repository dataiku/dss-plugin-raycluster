# This file is the actual code for the Python runnable start-ray-cluster
import dataiku
from dataiku.runnables import Runnable, utils
from raycluster.utils import get_helm_cmd, configure_kubeconfig

import os
import time
import shutil
import subprocess
import requests
import json

RAY_CLUSTER_YAML = """
image:
  tag: {image_tag}

head:
  rayVersion: {ray_version}
  resources:
    limits:
      cpu: "{ray_head_cpu}"
      memory: "{ray_head_ram}G"
    requests:
      cpu: "{ray_head_cpu}"
      memory: "{ray_head_ram}G"

worker:
  replicas: {ray_num_workers}
  resources:
    limits:
      cpu: "{ray_worker_cpu}"
      memory: "{ray_worker_ram}G"
    requests:
      cpu: "{ray_worker_cpu}"
      memory: "{ray_worker_ram}G"
"""


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
        Deploys RayCluster onto Dataiku-managed K8S Cluster.
        """
        # Unpack config
        cluster_name = self.config.get("k8s_cluster_name")
        kuberay_version = self.config.get("kuberay_version")
        
        image_tag = self.config.get("image_tag")
        ray_version = self.config.get("ray_version")
        ray_head_cpu = int(self.config.get("ray_head_cpu"))
        ray_head_ram = int(self.config.get("ray_head_ram"))
        ray_num_workers = int(self.config.get("ray_num_workers"))
        ray_worker_cpu = int(self.config.get("ray_worker_cpu")) 
        ray_worker_ram = int(self.config.get("ray_worker_ram"))
        
        # Set kubeconfig environment variable
        configure_kubeconfig(cluster_name)
        
        # Install Helm locally if not installed already
        helm_cmd = get_helm_cmd()
        
        # Install and upgrade KubeRay Helm repository
        try:
            r = subprocess.run([helm_cmd, "repo", "add", "kuberay", "https://ray-project.github.io/kuberay-helm/"], capture_output=True) 
            r.check_returncode()
            
            r = subprocess.run([helm_cmd, "repo", "update"], capture_output=True) 
            r.check_returncode()
        except Exception as e:
            raise Exception(f"KubeRay Helm chart installation failed with error: {r.stderr.decode('utf-8')}") from e
        
        # Install KubeRay operator and RayCluster
        ## Generate raycluster yaml file from inputs
        raycluster_yaml = RAY_CLUSTER_YAML.format(
            image_tag=image_tag,
            ray_version=ray_version,
            ray_head_cpu=ray_head_cpu,
            ray_head_ram=ray_head_ram,
            ray_num_workers=ray_num_workers,
            ray_worker_cpu=ray_worker_cpu,
            ray_worker_ram=ray_worker_ram
        )
        
        ## Start by writing the RayCluster yaml to a tmp file
        timestamp = int(time.time()) 
        ray_yaml_dir = f"/tmp/ray-{timestamp}"
        os.mkdir(ray_yaml_dir)
        
        with open(ray_yaml_dir+"/ray-values.yaml", 'w+') as f:
            f.write(raycluster_yaml)
        
        ## Install operator and cluster
        try:
            r = subprocess.run([helm_cmd, "install", "kuberay-operator", "kuberay/kuberay-operator", "--version", kuberay_version], capture_output=True) 
            r.check_returncode()
            
            r = subprocess.run([helm_cmd, "install", "-f", f"{ray_yaml_dir}/ray-values.yaml", "--version", kuberay_version, "raycluster", "kuberay/ray-cluster"])
            r.check_returncode() 
        except Exception as e:
            raise Exception(
                f"RayCluster installation failed with error: {r.stderr.decode('utf-8')}. " + \
                "Is the selected Elastic AI cluster running? Or else, do you need to remove a previously installed RayCluster with the 'Stop Ray Cluster' macro?"
            ) from e
        
        
        return f"Ray Cluster deployed successfully on Elastic AI cluster {cluster_name}. " + \
                "Run the 'Inspect Ray Cluster' Macro to view deployment status and retrieve the Ray Cluster endpont."
        