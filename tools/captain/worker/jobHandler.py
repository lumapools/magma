"""
File Info: Handles jobs and launches campaigns
"""

import os
import subprocess
import imageBuilder

"""Launches a fuzzing campaign
Parameters
----------
fuzzer: str
    fuzzer to launch the campaign on
target: str
    target to launch the campaign on
programName: str
    name of the program to run
programArgs: str
    arguments to pass to the program
bound_cpus: str(int)
    set of CPUs bound to the campaign to run
globalconfig: dict
    data containing configuration information for the campaign
job_id: int
    the beanstalk job id this fuzzing campaign corresponds to
repeat_id: int
    the index of the campaign among its potential twins
magma: str
    the path to magma
workdirs: str
    path to the directory where all results will be stored locally (on worker machine)

"""
def launchRun(fuzzer, target, programName, programArgs, fuzzargs, bound_cpus, globalconfig, job_id, repeat_id, magma, workdirs):
    os.environ["WORKDIR"] = f'{workdirs}/workdir_{job_id}'
    os.environ["MAGMA"] = magma
    os.environ["REPEAT_ID"] = repeat_id
    os.environ["FUZZER"] = fuzzer
    os.environ["TARGET"] = target
    os.environ["PROGRAM"] = programName
    os.environ["ARGS"] = programArgs
    if fuzzargs != "":
        os.environ["FUZZARGS"] = fuzzargs
    os.environ["AFFINITY"] = getAffinityArg(list(bound_cpus))
    os.environ["REPEAT"] = str(globalconfig["REPEAT"])

    if globalconfig.get("POLL") != None:
        os.environ["POLL"] = str(globalconfig["POLL"])
    if globalconfig.get("TIMEOUT") != None:
        os.environ["TIMEOUT"] = globalconfig["TIMEOUT"]
    if globalconfig.get("TMPFS_SIZE") != None:
        os.environ["TMPFS_SIZE"] = globalconfig["TMPFS_SIZE"]
    if globalconfig.get("CACHE_ON_DISK") != None:
        os.environ["CACHE_ON_DISK"] = str(globalconfig["CACHE_ON_DISK"])
    if globalconfig.get("POC_EXTRACT") != None:
        os.environ["POC_EXTRACT"] = str(globalconfig["POC_EXTRACT"])
    if globalconfig.get("NO_ARCHIVE") != None:
        os.environ["NO_ARCHIVE"] = str(globalconfig["NO_ARCHIVE"])
    subprocess.Popen(f'{magma}/tools/captain/worker/run.sh', shell=True).wait()



"""Helper: Transforms the set of cpus into a well-formatted affinity argument."""
def getAffinityArg(bound_cpus):
    if len(bound_cpus) == 1:
        return str(bound_cpus[0]) # Only one cpu
    affinity = ""
    for i in range(len(bound_cpus)-1):
        affinity = affinity + str(bound_cpus[i]) + ","
    affinity = affinity + str(bound_cpus[-1])
    return affinity


"""Handles a beanstalk job that has already been fetched.
Parameters
----------
job_id: int
    The id of job to handle
job_body: str
    The body of the job to handle
bound_cpus: set
    The cpus that will be bound to the later to-be fuzzing campaign
dispatcherip: str
    The dispatcher's ip address
workerip: str
    the worker's (public) ip address
magma: str
    the path to magma
feedbackClient: greenstalk.Client
    the client that is in charge of giving feedback to the dispatcher
username: str
    the username of the currently logged-in user
workdirs: str
    path to the directory where all results are stored (worker side)
"""
def handle_job(job_id, job_body, bound_cpus, globalconfig, dispatcherip, workerip, magma, feedbackClient, username, workdirs, build_lock):

    (repeat_id, fuzzer, target, program, fuzzargs) = job_body.split(",")

    with build_lock:
        print(f"[INFO] Building image for {magma}/{fuzzer}/{target}")
        imageBuilder.build_image(fuzzer, target, globalconfig, magma, job_id, workdirs, workerip)

    (programName, programArgs) = ("", "") 
    if " " not in program: # Program does not require arguments
        programName = program
    else:
        (programName, programArgs) = program.split(" ", 1)

    launchRun(fuzzer, target, programName, programArgs, fuzzargs, bound_cpus, globalconfig, job_id, repeat_id, magma, workdirs)

    # Only upload the file if the worker is not running locally
    path_to_file = f'{workdirs}/workdir_{job_id}'
    isLocal = 1 if dispatcherip == "localhost" or dispatcherip == "127.0.0.1" else 0
    feedbackClient.put(f'{str(isLocal)},{username},{workerip},{path_to_file}')
