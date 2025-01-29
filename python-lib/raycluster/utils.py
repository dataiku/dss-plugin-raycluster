import dataiku
import os
import subprocess
import requests
import shutil

def configure_kubeconfig(cluster_name):
    """
    Sets environment variable for kubeconfig of cluster.
    """
    client = dataiku.api_client()
    cluster = client.get_cluster(cluster_name)
    
    kubeconfig_path = cluster.get_settings().settings["data"]["kube_config_path"]
    os.environ["KUBECONFIG"] = kubeconfig_path
    
    
def get_helm_cmd():
    """
    Retrieve path to Helm command in PATH, 
    or install a local version of Helm if not installed.
    """
    try:
        helm_cmd = subprocess.check_output(["which", "helm"]).strip().decode("utf8")
        print("Found helm on the machine")
    except Exception:
        local_helm_folder = os.path.join(os.environ["DIP_HOME"], "tmp", "local_helm")
        helm_cmd = os.path.join(local_helm_folder+"/linux-amd64", "helm")
        print("Using helm from %s" % local_helm_folder)

        if not os.path.exists(local_helm_folder):
            os.makedirs(local_helm_folder)

        if not os.path.exists(helm_cmd):
            # Retrieve latest version
            r = requests.get(
                "https://get.helm.sh/helm-latest-version",
                stream=True,
                headers={"User-Agent": "DSS Ray Plugin"}
            )
            helm_latest_version = r.content.decode("utf-8").strip()

            # Download helm locally
            print("Downloading helm")
            r = requests.get(
                f"https://get.helm.sh/helm-{helm_latest_version}-linux-amd64.tar.gz",
                stream=True,
                headers={"User-Agent": "DSS Ray Plugin"}
            )
            local_helm_archive = os.path.join(local_helm_folder, "helm.tar.gz")
            with open(local_helm_archive, "wb") as f:
                shutil.copyfileobj(r.raw, f)
            subprocess.check_call(["tar", "-xzf", local_helm_archive], cwd=local_helm_folder)
            
    return helm_cmd