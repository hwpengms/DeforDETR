import atexit
import os
import sys
import argparse
import azureml.core 
from azureml.core import Experiment, Workspace, Datastore
from azureml.core.compute import ComputeTarget, AmlCompute
from azureml.core.compute_target import ComputeTargetException
from azureml.core.runconfig import MpiConfiguration, RunConfiguration, DEFAULT_GPU_IMAGE
from azureml.train.estimator import Estimator
from azureml.widgets import RunDetails
from azureml.core import Environment
from azureml.contrib.core.compute.k8scompute import AksCompute
from azureml.contrib.core.k8srunconfig import K8sComputeConfiguration
import signal
from azureml.core import Keyvault

def _exit():
    pass

atexit.register(_exit)

run=None

Resources={
    "sharedcl100":{"subscription_id":"f421874b-5496-471b-bb3a-765833465603","resource_group":"shared","workspace_name":"shared_ws","workspace_region":"westeurope",'cluster_name':"sharedcl100",'vm_size':"STANDARD_NC24S_V2"},
    "usscv100cl":{"subscription_id":"d4c59fc3-1b01-4872-8981-3ee8cbd79d68","resource_group":"usscv100","workspace_name":"usscv100ws","workspace_region":"southcentralus",'cluster_name':"usscv100cl",'vm_size':"STANDARD_ND40s_V2"},
    "ussc40rscl":{"subscription_id":"db9fc1d1-b44e-45a8-902d-8c766c255568","resource_group":"ussclowpriv100","workspace_name":"ussclowpriv100ws","workspace_region":"southcentralus",'cluster_name':"ussc40rscl",'vm_size':"STANDARD_ND40rs_V2"},
    "itpseasiav100cl":{"subscription_id":"46da6261-2167-4e71-8b0d-f4a45215ce61","resource_group":"researchvc","workspace_name":"resrchvc","workspace_region":"southeastasia",'cluster_name':"itpseasiav100cl",'vm_size':"STANDARD_ND40S_V2"},
    "itpeastusv100cl":{"subscription_id":"46da6261-2167-4e71-8b0d-f4a45215ce61","resource_group":"researchvc","workspace_name":"resrchvc","workspace_region":"useast",'cluster_name':"itpeastusv100cl",'vm_size':"STANDARD_ND40S_V2"}
}


GPU_NUM={"STANDARD_NC24RS_V3":4,"STANDARD_NC24S_V3":4,"STANDARD_NC24S_V2":4,"STANDARD_NC24RS_V2":4,"STANDARD_NC6S_V3":1,'STANDARD_ND40s_V2':8,'STANDARD_ND40rs_V2':8,'STANDARD_ND40S_V2':8}
PHILLY_SKUS={'G1':1,'G2':2,'G4':4,'G8':8,"G16":16}

def parse_args():
    parser = argparse.ArgumentParser("Azureml Script")
    parser.add_argument("--isPrepare",action="store_true",help="create the workspace and data storage")
    parser.add_argument("--name",type=str,help="experiment name")
    parser.add_argument("--cluster",type=str,help="cluster name", default="itpeastusv100cl")
    parser.add_argument("--gpus",type=int,help="total gpus", default=8)
    parser.add_argument("--philly_sku",type=str,help="philly sku")
    parser.add_argument("--command",type=str,help="command",default='')
    parser.add_argument("--entry_script",type=str,help="remote begin file",default="entry-script.py")
    parser.add_argument("--preemption",action='store_true',help="use promete job")
    parser.add_argument("--debug",action='store_true',help="use debug mode")
    parser.add_argument("--datastore_name", type=str, default="wukan_track_clean")
    # About the pipeline control
    parser.add_argument("--model_name",type=str)
    parser.add_argument("--work-dir", type=str, default="")
    parser.add_argument("--istrain",type=str,choices=['True','False'], default="True")
    parser.add_argument('--tune', action='store_true', default=False)
    parser.add_argument('--no-gpu', action='store_true', default=False)
    return parser



# your blob_container
# blob_container_name = "zhipeng"
# blob_account_name = "test26183922662"
# blob_account_key = "bNI1OEYL+wJMSimN5tjJjOA7FwfEzmbJXcAzOAngx0Hq9q5PtbXHHdhxra6RD6fKRu1gsy6oVdiG5KSrJWYncA=="

blob_container_name = "v-yanbi"
blob_account_name = "azsuse2"
blob_account_key = "HFYUvAX9qBIYkGRZXLlWEIJcxdKQgPetFrRnrmH0hPjMFNakzv7+0W+i5bASaY5SMxE1Ho7cNiQODCs2XSVfyg=="

def create_source(args):
    # Configuration
    
    subscription_id = Resources[args.cluster]['subscription_id']
    resource_group = Resources[args.cluster]['resource_group']
    workspace_name = Resources[args.cluster]['workspace_name']
    workspace_region = Resources[args.cluster]['workspace_region']

    vm_size = Resources[args.cluster]['vm_size']



    datastore_name = args.datastore_name

    # prepare the workspace
    ws = None
    try:
        print("Connecting to workspace '%s'..." % workspace_name)
        ws = Workspace(subscription_id = subscription_id, resource_group = resource_group, workspace_name = workspace_name)
    except:
        print("Workspace not accessible. Creating a new one...")
        try:
            ws = Workspace.create(
                name = workspace_name,
                subscription_id = subscription_id,
                resource_group = resource_group, 
                location = workspace_region,
                create_resource_group = False,
                exist_ok = True)
        except:
            print("Failed to connect to workspace. Quit with error.")
    print(ws.get_details())
    ws.write_config()

    # prepare the compute in the workspace
    try:
        ct = ComputeTarget(workspace=ws, name=args.cluster)
        print("Found existing cluster '%s'. Skip." % args.cluster)
    except ComputeTargetException:
        print("Creating new cluster '%s'..." % args.cluster)
        compute_config = AmlCompute.provisioning_configuration(vm_size=vm_size, min_nodes=1, max_nodes=5)
        ct = ComputeTarget.create(ws, args.cluster, compute_config)
        ct.wait_for_completion(show_output=True)
    # print(ct.get_status().serialize())
    
    if datastore_name not in ws.datastores:
        Datastore.register_azure_blob_container(
        workspace=ws, 
        datastore_name=datastore_name,
        container_name=blob_container_name,
        account_name=blob_account_name,
        account_key=blob_account_key
        )
        print("Datastore '%s' registered." % datastore_name)
    else:
        print("Datastore '%s' has already been regsitered." % datastore_name)

def submit_job(args):
    experiment_name = args.name
    subscription_id = Resources[args.cluster]['subscription_id']
    resource_group = Resources[args.cluster]['resource_group']
    workspace_name = Resources[args.cluster]['workspace_name']
    workspace_region = Resources[args.cluster]['workspace_region']

    vm_size = Resources[args.cluster]['vm_size']
    gpu_per_node=4
    if vm_size in GPU_NUM.keys() and args.philly_sku is None:
        gpu_per_node = GPU_NUM[vm_size]
    elif args.philly_sku is not None:
        gpu_per_node = PHILLY_SKUS[args.philly_sku]
    else:
        print("----!! sku error----")

    datastore_name = args.datastore_name
    # ws = Workspace.from_config()
    ws = Workspace(subscription_id = subscription_id,
                resource_group = resource_group,  
                workspace_name = workspace_name) 

    if datastore_name not in ws.datastores:
        Datastore.register_azure_blob_container(
        workspace=ws, 
        datastore_name=datastore_name,
        container_name=blob_container_name,
        account_name=blob_account_name,
        account_key=blob_account_key
        )
        print("Datastore '%s' registered." % datastore_name)
    else:
        print("Datastore '%s' has already been regsitered." % datastore_name)

    target_name_list=[]
    for key, target in ws.compute_targets.items():
        target_name_list.append(target.name)
        if type(target) is AksCompute:
            print('Found compute target:{}\ttype:{}\tprovisioning_state:{}\tlocation:{}'.format(target.name, target.type, target.provisioning_state, target.location))
    assert args.cluster in target_name_list
    ct = ComputeTarget(workspace=ws, name=args.cluster)
    ds = Datastore(workspace=ws, name=datastore_name)

    myenv = Environment(name="myenv")
    myenv.docker.enabled = True
    myenv.docker.base_image = "wkcn/azureml:latest"
    myenv.docker.shm_size = "16G"
    myenv.docker.gpu_support = args.gpus > 0 and not args.no_gpu # new
    myenv.python.user_managed_dependencies = True

    run_fname = 'begin.py' if not args.tune else 'begin_tune.py'
    print("Run:", run_fname, args.gpus, gpu_per_node)
    command = 'python %s --model_name %s --istrain %s --work-dir %s --command "%s"'%(run_fname, args.model_name, args.istrain, args.work_dir, args.command)

    est =Estimator(
        compute_target=ct,
        node_count = args.gpus//gpu_per_node,
        source_directory="./src-remote",
        entry_script=args.entry_script,
        script_params={
        "--workdir": ds.as_mount(),
        "--command": command,
        },
        environment_definition=myenv
    )
    global run
    exp = Experiment(workspace=ws, name=experiment_name)
    
    if ws.compute_targets[args.cluster].type in ['Cmk8s']:
        k8sconfig = K8sComputeConfiguration()
        k8s = dict()
        k8s['gpu_count'] = args.gpus if not     args.no_gpu else 0 # new
        if args.debug:
            k8s['enable_ssh']=True
            k8s['ssh_public_key']=''
        if args.preemption:
            k8s['preemption_allowed'] = True
            k8s['node_count_min'] = 1
        k8sconfig.configuration = k8s
        est.run_config.cmk8scompute = k8sconfig

    run = exp.submit(est)
    if 'ipykernel' in sys.modules:
        RunDetails(run).show()
    else:
        run.wait_for_completion(show_output=True)
    # print(run.get_details())

if __name__=="__main__":
    parse = parse_args()
    args = parse.parse_args()
    if args.isPrepare:
        create_source(args)
    # signal.signal(signal.SIGINT,cancel_job)
    submit_job(args)