## PRE-REQUIREMENTS:
- [greenstalk](https://greenstalk.readthedocs.io/en/stable/) (`pip install greenstalk`)
- [hjson](https://hjson.github.io/) (`pip install hjson`)
- port 11300 allowed in firewall

## Running Jobs Locally (in **magma/tools/captain**)
1. Configure the dispatcher, some settings and the jobs (in **config.hjson** and **dispatcher/dispatcherconfig**)
2. Launch `./quickRun.sh` (replaces the old `run.sh`)
Or
1. Configure the dispatcher, some settings and the jobs (in **config.hjson** and **dispatcher/dispatcherconfig**)
2. Configure the worker locally (in **worker/workerconfig**) using localhost as both worker and dispatcher parameters
3. Launch `dispatcher/runDispatcher` and `worker/runWorker` in two different shells.

## Running Jobs Remotely (in **magma/tools/captain**)
1. Configure the dispatcher, some settings and the jobs (in **config.hjson**)
2. Configure the workers on machines you want to use as workers (**worker/workerconfig**).
   Make sure to enter the worker's IP correctly (and being findable by the dispatcher machine), 
   otherwise the dispatcher and worker won't be able to communicate.
4. Run `dispatcher/runDispatcher.sh` on the dispatcher side
5. Run `worker/runWorker.sh` on all the worker machines.

## Notes
- When fetching jobs, we use `rsync` and `scp`, and a password prompt is issued for every new incoming file (result).
- On worker machines, the password still needs to be input when *`Obtaining sudo permissions to (u)mount tmpfs`*
- Used `hjson` instead of `json` to be able to comment lines (for easier understanding)

## Crashes
- Since crashes are handled to some extent but these handlings don't cover all corner cases, if an error message is shown when launching the dispatcher or the worker script, it is best to 
   1) stop the beanstalkd global process if it is still running (dispatcher and worker side), 
   2) remove the **beanstalkd/** directory (dispatcher and worker side)
   3) remove temp_results and workdir folders (**dispatcher side**), and 
   4) remove workdirs folder (on worker side defined in **workerconfig**).
