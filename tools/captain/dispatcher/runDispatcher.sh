#!/bin/bash

## Main dispatcher script to launch on the worker side
#
# Optional args:
# -f : forces the beanstalkd launch (will lead to misbehaviour if 
#      another instance of beanstalkd is already running)
# 
# Requirements: 
# + $1: path to dispatcherconfig (default: ./dispatcherconfig)
#
##

cleanup()
{
    echo "[INFO] Removing pycache"
    rm $DISPATCHER/__pycache__ -r
    echo "[INFO] Stopping beanstalk"
    kill $beanstalkdPID
    echo "[INFO] Removing beanstalkd"
    rm $beanstalkdDir -rf
    echo "[INFO] Done."
    exit
}

finish()
{
    echo "Removing $TEMP_RESULTS"
    rm $TEMP_RESULTS -rf
    cleanup

}

if [ -z "$MAGMA" ]; then    
    export MAGMA="$( cd -- "$(dirname "$0")/../../../" >/dev/null 2>&1 ; pwd -P )"
fi

DISPATCHER=$MAGMA/tools/captain/dispatcher

if [ -z $1 ]; then
    set -- "$DISPATCHER/dispatcherconfig"
fi

# load the configuration file (dispatcherconfig)
set -a
source "$1"
set +a

source $MAGMA/tools/captain/common.sh

prerun_check_dispatcher "$1"


### Process arguments ###
while getopts "f" arg; do
    case $arg in
        f) export FORCE=1;;
    esac
done

check_beanstalkd_is_running
if [ $? != 0 ]; then # Beanstalkd exists
    exit -1
fi

DISPATCHER="$MAGMA/tools/captain/dispatcher/"

echo "[INFO] Preprocessing data"
python3 $DISPATCHER/preprocess.py --configfile $JOBS_CONFIG --magma $MAGMA

if [ $? != 0 ]; then # Error happened during preprocessing phase
    exit -1
fi

echo "[INFO] Preprocessing data"
python3 $DISPATCHER/preprocess.py --configfile $JOBS_CONFIG --magma $MAGMA

if [ $? != 0 ]; then # Error happened during preprocessing phase
    exit -1
fi

echo "[INFO] Creating temporary results directory"
mkdir -p $TEMP_RESULTS

clone_beanstalkd

echo "[INFO] Starting beanstalk."
# Get the beanstalkd pid to kill later when everything finished
$beanstalkdDir/beanstalkd & export beanstalkdPID=$(echo $!) 

trap finish SIGINT

echo "[INFO] Starting putting jobs into the tubes"

numjobs=$(python3 $DISPATCHER/putJobs.py --configfile $JOBS_CONFIG)

echo "[INFO] Starting result fetcher"

python3 $DISPATCHER/fetchResults.py --tmpresultsdir $TEMP_RESULTS  --workdir $WORKDIR --copytype $COPY_TYPE --numjobs $numjobs

if [ $? != 0 ]; then
    echo "[ERROR] An error occured while fetching results."
    cleanup
fi

echo "[INFO] Merging result directories"

cd $TEMP_RESULTS

# Merge all directories fetched from remote jobs
for dir in */; do
    if [ -d $dir ]; then
        rsync -a $dir $WORKDIR
    fi
done

rm -r $TEMP_RESULTS

cd $MAGMA/tools/captain/

# Merge all directories fetched from local jobs
# (if the dispatcher machine is also used as a worker machine)
for dir in workdir_*/; do
    if [ -d $dir ]; then
        rsync -a $dir $WORKDIR
    rm $dir -r
    fi
done

finish
