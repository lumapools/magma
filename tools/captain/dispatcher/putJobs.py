import argparse
import greenstalk
import configParser
import subprocess

parser = argparse.ArgumentParser("PutJobsArgParser")
parser.add_argument('--configfile', type=str, help="JSON configuration file")
args = parser.parse_args()

# Set up clients
putJobsClient = greenstalk.Client(("127.0.0.1", 11300))
broadcasterClient = greenstalk.Client(("127.0.0.1",11300))
feedbackHandlerClient = greenstalk.Client(("127.0.0.1", 11300))
putJobsClient.use("jobs")
broadcasterClient.use("broadcast")
broadcasterClient.watch("broadcast")
broadcasterClient.ignore("default")
feedbackHandlerClient.watch("feedback")
feedbackHandlerClient.ignore("default")

"""Clears the feedback queue to make sure no stale jobs are left,
prevents desynchronization between the dispatcher and the workers.
"""
def clearFeedback():
    while True:
        try:
            # Delete all the jobs present in the feedback queue
            feedbackHandlerClient.delete(feedbackHandlerClient.reserve(timeout=0.2))
        except:
            break

"""
Broadcasts a single message
Parameters
----------
client: greenstalk.Client
    the greenstalk client running on the dispatcher side
message: str
    the message to be broadcasted

Returns
-------
int
    the id of the broadcasted message
"""
def broadcast(message):
    try:
        to_delete = broadcasterClient.reserve(timeout=0.1)
        broadcasterClient.delete(to_delete)
    except: # Nothing is present => this is the first broadcast
        pass
    finally:
        broadcast_id = broadcasterClient.put(message)
        return broadcast_id

def put_jobs():
    all_jobs = configParser.get_jobs(args.configfile)
    total_num_jobs = len(all_jobs)

    # Broadcast the configuration to all workers and store the returned id
    config_id = broadcast(configParser.get_broadcast(args.configfile))
    jobs_put = 0

    # Put jobs into the "jobs" tube
    print(f"{total_num_jobs}")
    for job in all_jobs:
        put_id = putJobsClient.put(f'{config_id},{job}')
        jobs_put += 1
        #print(f'[INFO] Job ID {put_id}, Config ID {config_id}: \"{job}\" added to queue. ({jobs_put}/{total_num_jobs})')

clearFeedback()
put_jobs()
