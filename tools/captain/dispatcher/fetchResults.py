import argparse
import greenstalk
import os
import sys

parser = argparse.ArgumentParser("ResultFetcherArgParser")
parser.add_argument('--tmpresultsdir', type=str, help="Temporary results directory")
parser.add_argument('--workdir', type=str, help="Final results directory")
parser.add_argument('--copytype', type=str, help="Copy type (scp or rsync)")
parser.add_argument('--numjobs', type=int, help="Number of jobs to fetch")
args = parser.parse_args()

resultFetcherClient = greenstalk.Client(("127.0.0.1", 11300))
resultFetcherClient.watch("feedback")
resultFetcherClient.ignore("default")

"""Fetches the results of completed (or dead) jobs.
Parameters
----------
currentClient: greenstalk.Client
    the greenstalk client running on the dispatcher side
n_files: int
    the number of previously submitted configuration files (# of results to fetch)
resultdir: str
    the path to the directory where results are stored
"""
def fetch_results():
    print("[INFO] Waiting for the launched jobs to finish...")
    totalNumJobs = args.numjobs # Number of total jobs
    numJobsToFetch = args.numjobs # Number of remaining jobs to fetch
    
    nFetched = 0 # Number of fetched done jobs (by the dispatcher)
    nDead = 0 # Number of dead jobs
    graveyarded = [] # Graveyarded jobs

    # Poll the "feedback" and "graveyard" tubes to check for finished/dead jobs
    while numJobsToFetch != 0:
        resultFetcherClient.watch("feedback")
        resultFetcherClient.ignore("graveyard")
        try:
            job = resultFetcherClient.reserve(timeout=0.1)
            (isLocal, username, workerip, path) = job.body.split(",")
            if isLocal == "0": # File arrived from a remote machine (=> needs to be fetched into the result directory)
                print(f"[INFO] A new file arrived from a worker node (username {username} , ip {workerip})")
                if args.copytype == "scp":
                    os.system(f'scp -r {username}@{workerip}:{path} {args.tmpresultsdir}')
                else:
                    os.system(f'rsync -avP {username}@{workerip}:{path} {args.tmpresultsdir}') 
            else: # File arrived locally (=> just needs to be copied into the results directory)
                os.system(f'cp -r {path} {args.tmpresultsdir}')
                print(f"[INFO] A new job has locally finished, directly copied to resultdir.")
            resultFetcherClient.delete(job)
            numJobsToFetch -= 1
            nFetched += 1
            print(f'[INFO] Fetched {nFetched}/{totalNumJobs}')
        except:
            pass
        finally:
            resultFetcherClient.watch("graveyard")
            resultFetcherClient.ignore("feedback")
        try:
            dead_job = resultFetcherClient.reserve(timeout=0.1)
            # Add the body of the dead job to the graveyard list
            graveyarded.append(dead_job.body.split(",")[1])
            resultFetcherClient.delete(dead_job)
            numJobsToFetch -= 1
            nDead += 1
        except:
            pass
    print(f'[INFO] Out of {totalNumJobs} jobs, {nFetched} have completed and {nDead} have been killed.')
    if nDead != 0:
        print("[INFO] Dead jobs: ")
        # Show graveyarded jobs
        for graveyarded_job in graveyarded:
            print(f'- {graveyarded_job}')

try:
    fetch_results()
    sys.exit(0)
except(KeyboardInterrupt, Exception):
    sys.exit(-1)


