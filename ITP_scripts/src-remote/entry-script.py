#
# AML Generic Launcher.
#
# Author: Philly Beijing Team <PhillyBJ@microsoft.com>
#
# This Python script works as the entry script of the AML job. Specifically,
# it will be uploaded by run.py, be executed on remote VM, set up necessary
# runtime environments, and then execute a designated user command.
#

import os
import argparse

parser = argparse.ArgumentParser(description="AML Generic Launcher")
parser.add_argument('--environ', default="", help="The list of environment variables.")
parser.add_argument('--workdir', default="", help="The working directory.")
parser.add_argument('--command', default="/bin/true", help="The command to run.")
parser.add_argument('--model_name', type=str)
args, _ = parser.parse_known_args()

#os.chdir(args.workdir)
os.system("export %s WORKDIR=%s MKL_THREADING_LAYER=GNU && %s" % (args.environ, args.workdir, args.command))
