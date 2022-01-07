"""
File Info: Parses the configuration files and runs post_extract.
"""

from dispatcher.configParser import get_config_data
import subprocess
import os
import argparse

parser = argparse.ArgumentParser("WorkerMainArgParser")
parser.add_argument('--jobsconfig', type=str, help="Path to configuration file", required=False)
parser.add_argument('--dispatcherconfig', type=str, help="Path to the dispatcherconfig file", required=False)
parser.add_argument('--extract', type=str, help="Path to extract script", required=False)
args = parser.parse_args()

configfile = args.jobsconfig if args.jobsconfig != None else "config.hjson"
dispatcherconfig = args.dispatcherconfig if args.dispatcherconfig != None else ""
extract = args.extract if args.extract != None else ""
    

config_data = get_config_data(configfile)
os.environ["MAGMA"] = config_data["MAGMA"]
os.environ["REPEAT"] = str(config_data["REPEAT"])
if config_data.get("CANARY_MODE") != None:
    os.environ["CANARY_MODE"] = str(config_data["CANARY_MODE"])
if config_data.get("HARDEN") != None:
    os.environ["HARDEN"] = str(config_data["HARDEN"])
if config_data.get("ISAN") != None:
    os.environ["ISAN"] = str(config_data["ISAN"])

os.environ["PYTHON_RUN"] = "1"

print("Starting post extract")
subprocess.Popen(f"./post_extract.sh {dispatcherconfig} {extract}", shell=True).wait()
print("Done")
