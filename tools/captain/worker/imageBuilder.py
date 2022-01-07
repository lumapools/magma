"""
File Info: File in charge of building the docker image needed for a particular fuzzer/target pair
"""

import os
import subprocess

"""Calls the build.sh script to build docker images for jobs, based on the global configuration.
Parameters
----------
fuzzer: str
    The fuzzer to build the image for
target: str
    The target to build the image for
globalconfig: dict
    JSON configuration dictionary
magma: str
    The path to magma
"""
def build_image(fuzzer, target, globalconfig, magma, jobId, workdirs, workerip):
    os.environ["FUZZER"] = fuzzer
    os.environ["TARGET"] = target
    os.environ["MAGMA"] = magma
    if globalconfig.get("ISAN") != None:
        os.environ["ISAN"] = globalconfig["ISAN"]
    if globalconfig.get("HARDEN") != None:
        os.environ["HARDEN"] = globalconfig["HARDEN"]
    if globalconfig.get("CANARY_MODE") != None:
        os.environ["CANARY_MODE"] = globalconfig["CANARY_MODE"]

    logdir = f"{workdirs}/workdir_{jobId}/log"
    logfile = f"{fuzzer}_{target}_build_{workerip}.log"

    os.system(f"mkdir -p {logdir}")
    # Log build output now, as we need one build log per thread (even though the builds are synchronized)
    subprocess.Popen(f'{magma}/tools/captain/build.sh > {logdir}/{logfile}', shell=True).wait()
    print(f"[INFO] Docker image build for {fuzzer}/{target} finished.")