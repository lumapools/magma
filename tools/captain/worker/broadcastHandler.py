"""
File Info: Fetches and handles broadcasts from the dispatcher.
"""

import subprocess
from multiprocessing import Queue
import hjson
import math
import os

"""Helper: Fills in the cpu list."""
def fill_cpus_list(cpu_sets_list, cpu_map):
    numWorkers = 0
    for elem in cpu_map:
        cpu_sets_list.append(cpu_map[elem])
        numWorkers += 1
    return numWorkers

"""Helper: Fetches the usable cpus (controlled by nWorkers)."""
def get_usable_cpus(nWorkers, cpu_sets_list):
    num_cpus_per_node = len(cpu_sets_list[0])
    cpu_range = math.ceil(nWorkers/num_cpus_per_node)
    # Use max amount of logical cores if nWorkers is not specified or if nWorkers > nCores
    usable_cpus = cpu_sets_list if nWorkers > len(cpu_sets_list) else cpu_sets_list[0:cpu_range]
    return usable_cpus

"""Helper: Interprets the campaign_workers parameter and fuses sets of cpus 
together to allocate more resources per thread later on."""
def rearrange_cpus(usable_cpus, campaign_workers, num_cpus_per_node):
    rearranged_cpus = []
    step = math.ceil(campaign_workers/num_cpus_per_node)
    start = 0
    end = step # excluded
    while end <= len(usable_cpus):
        accumulator = set()
        for i in range(start, end):
            accumulator = accumulator.union(usable_cpus[i])
        rearranged_cpus.append(accumulator)
        start = end
        end += step
    return rearranged_cpus


"""Fetches broadcasts from the dispatcher.
Parameters
----------
currentClient : greenstalk.Client
    The broadcast greenstalk client running on the worker side

Returns
-------
int, dict
    the id and data of the fetched broadcast
"""
def fetch_broadcast(currentClient):
    while True:
        try:
            broadcastJob = currentClient.peek_ready()
            globalconfig = hjson.loads(broadcastJob.body)
            return broadcastJob.id, globalconfig
        except:
            continue

"""Transforms a broadcast into a queue of sets of CPU IDs
Parameters
----------
globalconfig: dict
    The configuration dictionary to interpret

Returns
-------
multiprocessing.Queue, int
    The queue containing all the sets of CPUs belonging to the same group,
    and the maximum number of worker threads that can later be used
"""
def interpret(globalconfig):
    # Get output of lscpu -bp and only keep the useful information
    lscpu_output = subprocess.run(['lscpu', '-bp'], stdout=subprocess.PIPE).stdout.decode('UTF-8').strip().split("\n")[4:]
    lscpu_output = list(map(lambda elem:elem.split(",")[0:3], lscpu_output))
    cpuType = globalconfig["WORKER_MODE"]
    cpu_type_int = 0 if cpuType == "logical" else (1 if cpuType == "physical" else 2)

    nWorkers = globalconfig.get("WORKERS")
    worker_pool = globalconfig.get("WORKER_POOL")
    campaign_workers = globalconfig.get("CAMPAIGN_WORKERS")

    cpu_set = set()
    cpu_map = {}
    
    # Populate the cpu set (Random identifier element chosen for each cpu node)
    for i in range(len(lscpu_output)):
        cpu_set.add(lscpu_output[i][cpu_type_int])

    logical_cpu_list = [] # To check later if worker_pool is actually in bounds

    # Initialize the map (each element maps to a set of cpus belonging to the same cpu node)
    for elem in cpu_set:
        cpu_map[elem] = set()
        logical_cpu_list.append(int(elem))

    # Add the correct element to the key in the correct map
    for line in lscpu_output:
        cpu_map[line[cpu_type_int]].add(int(line[0]))

    # Initialize output queue
    cpu_queue = Queue()

    # Sets of CPUs without any rearrangements 
    cpu_sets_list = []

    # Fill in the lists of CPUs with the previously populated sets
    numWorkers = fill_cpus_list(cpu_sets_list, cpu_map) # Number of threads to spawn later

    usable_cpus = cpu_sets_list if nWorkers == None else [] # nWorkers === `WORKERS` config parameter

    if nWorkers != None: # Interpret WORKERS parameter
        usable_cpus = get_usable_cpus(nWorkers, cpu_sets_list)
        # Use max amount of logical cores if nWorkers is not specified or if nWorkers > nCores
    elif worker_pool != None: # Interpret WORKER_POOL parameter
        usable_cpus = []
        for index in worker_pool:
            if index in logical_cpu_list:
                usable_cpus.append({index})
            else:
                print(f"[WARNING] Unknown CPU index: {index}, skipping.")
        """
        Note: As each remote machine has a different type of layout (w.r.t. indices of logical CPUs),
              the program cannot enforce a particular list of CPUs to use if the user wants to use 
              physical or socket mode. If we consider the example "physical" mode (it is the same 
              for socket mode), then this means that either
              1. Few/None of the physical CPUs will be used, if we decide to drop all CPUs that are not 
                in a pair with another CPU in the worker_pool => minimizes the resources to be used by 
                jobs, and leaves many resources for the personal use of the user.
              2. Many/All of the physical CPUs will be used, if we decide to keep all physical CPUs that
                contains at least one element present in worker_pool => maximizes the resources to be used
                by jobs, and could leave no resources for the personal use of the user.
              In both cases, we could be massively cutting down on resources (either for the user, or for 
              the job), therefore, if worker_pool is specified, we will enforce logical mode.
        """

    rearranged_cpus = usable_cpus
    num_cpus_per_node = len(cpu_sets_list[0])

    # Interpret campaign_workers parameter
    if campaign_workers != None:
        rearranged_cpus = rearrange_cpus(usable_cpus, campaign_workers, num_cpus_per_node)

    if len(rearranged_cpus) == 0: # Something wrong happened during configuration
        print(f'[ERROR] Configuration file yields no possible usable CPUs.')
        os.system("exit")

    print(f"[INFO] CPU (sets) to be used: {rearranged_cpus}")

    # Populate the queue
    for elem in rearranged_cpus:
        cpu_queue.put(elem)

    return cpu_queue, numWorkers

"""Gets the number of campaign workers for `fuzzer`
Parameters
----------
fuzzer: String
    the fuzzer to get the number of campaign workers for
globalconfig: dict
    the configuration dictionary

Returns
-------
int 
    the number of campaign workers for `fuzzer`
"""
def get_num_campaign_workers(fuzzer, target, globalconfig):
    if globalconfig.get("FUZZER_CAMPAIGN_WORKERS") != None:
        if globalconfig["FUZZER_CAMPAIGN_WORKERS"].get(f"{fuzzer},{target}") != None:
            return globalconfig["FUZZER_CAMPAIGN_WORKERS"][f"{fuzzer},{target}"]
    return globalconfig["CAMPAIGN_WORKERS"] if globalconfig.get("CAMPAIGN_WORKERS") != None else 1 