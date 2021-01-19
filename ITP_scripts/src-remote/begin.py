import os
import random
import time
import argparse
import threading
import base64
def parse_args():
    """
    args for training.
    """
    parser = argparse.ArgumentParser(description='Train model')
    parser.add_argument('--model_name', type=str)
    parser.add_argument('--istrain',type=str,choices=['True','False'])
    parser.add_argument("--work-dir", type=str, default="")
    parser.add_argument("--command", type=str, default="")
    args = parser.parse_args()

    return args
args = parse_args()
home_dir = os.getenv("HOME")
work_dir = os.getenv("WORKDIR")

print('********** there are following files under WORKDIR**********')
print(os.listdir(work_dir))
print('********** there are following files under HOME**********')
print(os.listdir(home_dir))

'''
sudo apt update
sudo apt install libgl1-mesa-glx
'''
#os.system("yes | apt update")
#os.system("yes | apt install libgl1-mesa-glx")

# test write
assert len(args.work_dir) > 0
model_work_dir = os.path.join(work_dir, "wukan", "track", 'track3', args.work_dir)
data_dir = os.path.join(work_dir, "coco_data")
if os.path.exists(model_work_dir):
    print(f"[WARNING] {model_work_dir} exists!!!")
os.makedirs(model_work_dir, exist_ok=True)

os.system("nvidia-smi")

os.chdir(home_dir)
print("current dir is {}:".format(os.getcwd()))

# os.system("rm -rf Xtrack*")


time_str = time.strftime('%Y-%m-%d-%H-%M-%S', time.localtime())
rand_num = random.randint(0, 1000000)
proj_name = 'Xtrack_' + time_str + '_' + str(rand_num)
print("Project Name: ", proj_name)

# xtrack dev
url = ''

os.system(f"git clone {url} " + proj_name)

os.chdir('./' + proj_name)

os.system("git checkout dev") # branch

os.system("export PYTHONPATH=$PYTHONPATH:.")

os.system("pwd")
os.system("ls")

os.system("sh ./install_env.sh")
os.system(f"PYTHONPATH=. python preload_dataset.py {data_dir}")

os.system("nvidia-smi")

cmd = f'PYTHONPATH=.;GPUS_PER_NODE=8; ./tools/run_dist_launch.sh 8 ./configs/r50_deformable_detr.sh --coco_path {data_dir} --output_dir {model_work_dir}'
if args.command:
    cmd += ' --command "%s"' % (args.command)
print("COMMAND:", cmd)

os.system("pwd")
os.system("ls")

os.system(cmd)

time.sleep(60)

os.chdir(os.environ['HOME'])
os.system("rm -rf " + proj_name)
