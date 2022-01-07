"""
File Info: Main script that runs on one of the worker machines. 
The worker checks for jobs from the dispatcher, and gives them 
to worker threads to execute.
"""

import greenstalk
import argparse
import jobHandler
import broadcastHandler
import threading
from multiprocessing.pool import ThreadPool
from multiprocessing import Queue
import sys
sys.tracebacklimit = 0

parser = argparse.ArgumentParser("WorkerMainArgParser")
parser.add_argument('--dispatcherip', type=str, help="Dispatcher IP")
parser.add_argument('--workerip', type=str, help="Worker machine IP")
parser.add_argument("--magma", type=str, help="path_to_magma")
parser.add_argument("--workdirs", type=str, help="Path to worker directories")
parser.add_argument("--username", type=str, help="Current username")
args = parser.parse_args()

"""Checks if all args are valid for the workerMain.py script
Parameters
----------
args: argparse.Namespace
    the arguments to check

Returns
-------
bool
    False if the args are invalid, True otherwise
"""
def check_args(args):
    if args.dispatcherip == None:
        print("[ERROR] Set a dispatcher ip (--dispatcherip [ip])")
        return False
    if args.workerip == None:
        print("[ERROR] Set a worker ip (--workerip [ip])")
        return False
    if args.magma == None:
        print("[ERROR] Set the path to magma (--magma [path_to_magma])")
        return False
    if args.workdirs == None:
        print("[ERROR] Set the workdirs location (--workdirs [path_to_workdir])")
        return False
    return True

# Check if all args are valid
if not(check_args(args)):
    exit()

# Create greenstalk worker clients
jobFetchClient = greenstalk.Client((args.dispatcherip, 11300))
feedbackClient = greenstalk.Client((args.dispatcherip, 11300))
broadcastFetchClient = greenstalk.Client((args.dispatcherip, 11300))
graveyardClient = greenstalk.Client((args.dispatcherip, 11300))

# Set up which client watches/uses which tube
jobFetchClient.use("jobs")
jobFetchClient.watch("jobs")
jobFetchClient.ignore("default")
broadcastFetchClient.use("broadcast")
broadcastFetchClient.watch("broadcast")
broadcastFetchClient.ignore("default")
feedbackClient.watch("feedback")
feedbackClient.use("feedback")
feedbackClient.ignore("default")
graveyardClient.use("graveyard")
graveyardClient.watch("graveyard")
graveyardClient.ignore("default")

worker_threads = ThreadPool(1) # Worker Threads
free_cpuranges = Queue() # Sets of CPUs that worker threads pop
global_config_id = -1 # For checking if configuration id's are stale or not
globalconfig = None # Body of the broadcasted configuration (global configuration)
num_free_workers = 0 # Number of unused worker threads

running_jobs = set() # Currently running jobs
set_lock = threading.Lock() # Lock used to do operations on running_jobs
worker_counter_lock = threading.Lock() # Lock used for counting the number of free workers
docker_build_lock = threading.Lock() # Lock used for building docker images sequentially

"""Resets the configuration and status of the worker machine"""
def reset():
    global global_config_id, globalconfig, free_cpuranges, worker_threads, set_lock, num_free_workers
    global_config_id, globalconfig = broadcastHandler.fetch_broadcast(broadcastFetchClient)
    free_cpuranges, num_workers = broadcastHandler.interpret(globalconfig) # list of sets of cpus belonging to the same cluster
    num_free_workers = num_workers
    worker_threads = ThreadPool(num_workers) # resize pool
    with set_lock:
        # Move currently running jobs into the "graveyard" tube
        for running_job in running_jobs:
            graveyardClient.put(running_job)
        running_jobs.clear()
    set_lock = threading.Lock() # Set up a new lock for threads to use to avoid deadlocks

"""Task given to a thread in the pool
Parameters
----------
jobTuple: (int, str)
    (id, body) of the job to take care of

Returns
-------
int
    The id of the completed job
"""
def thread_task(jobTuple):
    job_id = jobTuple[0]
    job_body = jobTuple[1]
    globalconfig = jobTuple[2] # Configuration to pass onto the container starter later on
    with set_lock:
        running_jobs.add(f'{job_id},{job_body}')
    (fuzzer, target) = job_body.split(",")[1:3]
    print("fuzzer, target = " + fuzzer + "," + target)
    numCampaignWorkers = broadcastHandler.get_num_campaign_workers(fuzzer, target, globalconfig)
    cpu_pops = [] # Popped sets of CPUs
    bound_cpus = set() # Set of CPUs to be used
    # Pop the queue until the right number of FUZZER_CAMPAIGN_WORKERS is satisfied
    while len(bound_cpus) < numCampaignWorkers:
        popped_set = free_cpuranges.get()
        bound_cpus = bound_cpus.union(popped_set.copy())
        cpu_pops.append(popped_set.copy())
        
    global num_free_workers
    jobHandler.handle_job(job_id, job_body, bound_cpus, globalconfig, args.dispatcherip, args.workerip, 
        args.magma, feedbackClient, args.username, args.workdirs, docker_build_lock)
    for cpu_set in cpu_pops: # Put back all previously popped sets of CPUs 
        free_cpuranges.put(cpu_set)
    else:
        free_cpuranges.put(bound_cpus)
    with worker_counter_lock:
        num_free_workers += 1
    with set_lock:
        running_jobs.remove(f'{job_id},{job_body}')
    return job_id

"""Generator of jobs
Yields
------
(int, str)
    The relevant information of a job to execute (job_id, job_body)
"""
def job_generator():
    while True:
        global num_free_workers
        if num_free_workers > 0: # Only reserve jobs when there are free threads 
            next_job = jobFetchClient.reserve()
            job_id = next_job.id
            (config_id, job_body) = next_job.body.split(",", 1) # Split the body into (configId, job)
            # Check if the configuration id is stale
            if config_id != str(global_config_id):
                reset()
                # Graveyard the job if the configuration id is still stale after a reset
                if config_id != str(global_config_id):
                    graveyardClient.put(f'{job_id},{job_body}')
                else:
                    jobFetchClient.release(next_job)
                break
            jobFetchClient.delete(next_job)
            with worker_counter_lock:
                num_free_workers -= 1
            yield (job_id, job_body, globalconfig)

reset()
while True:
    jobInfo = job_generator()
    # Give each thread in the thread pool (of workers) a job to execute
    for result in worker_threads.imap_unordered(thread_task, jobInfo):
        feedbackClient.put(f'jobresult_{result}')
        print(f"[INFO] Job ID {result} added to feedback queue.")
    reset()
        
