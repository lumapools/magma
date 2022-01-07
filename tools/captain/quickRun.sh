#!/bin/bash

# Launch a fast campaign that is going to be run only locally
# Requires to have set a configuration before (config.hjson)

MAGMA="$( cd -- "$(dirname "$0")/../../" >/dev/null 2>&1 ; pwd -P )"

if [ -z $1 ]; then
    set -- $(realpath "$MAGMA/tools/captain/dispatcher/dispatcherconfig")
fi

# load the configuration file (dispatcherconfig)
set -a
source "$1"
set +a


source "$MAGMA/tools/captain/common.sh"

prerun_check_dispatcher "$1"

if [ $? != 0 ]; then # Prerun check failed
    exit
fi

if [ -z "$WORKDIRS" ]; then
    echo "[ERROR] WORKDIRS must be specified. Exiting."
    exit
fi

if [ -d "$WORKDIRS" ]; then
    echo "[ERROR] WORKDIRS already exists. Exiting."
    exit
fi

if [ -z $KEEP_WORKDIRS ]; then
    export KEEP_WORKDIRS=0
    echo "[INFO] KEEP_WORKDIRS has been set to 0 by default"
fi

cleanup()
{
    echo "[INFO] Removing pycache"
    rm $DISPATCHER/__pycache__ -r
    kill $(jobs -p)
    echo "[INFO] Stopping beanstalk"
    kill $beanstalkPID
    echo "[INFO] Done."
}

finish()
{
    echo "[INFO] Removing $TEMP_RESULTS"
    rm $TEMP_RESULTS -r
    cleanup
    rm $WORKDIRS -r
    echo "[INFO] Removing beanstalkd"
    rm $beanstalkdDir -rf
    rm $MAGMA/tools/captain/worker/__pycache__ -r
    stty sane
}

check_beanstalkd_is_running
if [ $? != 0 ]; then # beanstalk running
    exit
fi

DISPATCHER="$MAGMA/tools/captain/dispatcher/"
WORKER="$MAGMA/tools/captain/worker/"

echo "[INFO] Preprocessing configuration file"

python3 $DISPATCHER/preprocess.py --configfile $JOBS_CONFIG --magma $MAGMA

if [ $? != 0 ]; then # Error happened during preprocessing phase
    exit -1
fi

clone_beanstalkd    

echo "[INFO] Starting beanstalkd"

$beanstalkdDir/beanstalkd & export beanstalkPID=$(echo $!)

numjobs=$(python3 $DISPATCHER/putJobs.py --configfile $JOBS_CONFIG)

python3 $WORKER/workerMain.py --dispatcherip 127.0.0.1 --workerip 127.0.0.1 --magma=$MAGMA --username $USER --workdirs $WORKDIRS &

python3 $DISPATCHER/fetchResults.py --tmpresultsdir $TEMP_RESULTS  --workdir $WORKDIR --copytype $COPY_TYPE --numjobs $numjobs 


echo "[INFO] Merging result directories"

cd $WORKDIRS

# Merge all directories fetched from local jobs
# (if the dispatcher machine is also used as a worker machine)
for dir in workdir_*/; do
    if [ -d $dir ]; then
        rsync -a $dir $WORKDIR
    rm $dir -r
    fi
done
finish
