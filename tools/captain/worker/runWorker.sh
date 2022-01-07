#!/bin/bash

if [ -z "$MAGMA" ]; then
    export MAGMA="$( cd -- "$(dirname "$0")/../../../" >/dev/null 2>&1 ; pwd -P )"
fi


if [ -z $QUICK_RUN ]; then
    source "$MAGMA/tools/captain/worker/workerconfig"
fi

source $MAGMA/tools/captain/common.sh


GREENSTALK="$(pip list | grep greenstalk)"
if [ -z "$GREENSTALK" ]; then
    echo "[ERROR] greenstalk is needed to run this script (pip install greenstalk)"
    exit -1
fi

HJSON=$(pip list | grep hjson)
if [ -z "$HJSON" ]; then
    echo "[ERROR] hjson is required to run this script (pip install hjson)"
    exit
fi

if [ -z "$KEEP_WORKDIRS" ]; then
    export KEEP_WORKDIRS=0
    echo "[INFO] KEEP_WORKDIRS is unset, it has been set to 0 by default"
fi

if [ ! -d $WORKDIRS ]; then
    mkdir $WORKDIRS -p
else
    echo "[ERROR] (Worker side: when creating $WORKDIRS for workdirs) Directory already exists from previous job, could lead to data loss."
    exit -1
fi

if [[ $DISPATCHER_IP != "localhost" ]] && [[ $DISPATCHER_IP != "127.0.0.1" ]]; then
    clone_beanstalkd
	$beanstalkdDir/beanstalkd & beanstalkdPID=$(echo $!)
fi

WORKER="$MAGMA/tools/captain/worker/"

python3 $WORKER/workerMain.py --dispatcherip $DISPATCHER_IP --workerip $WORKER_IP --magma=$MAGMA --username $USER --workdirs $WORKDIRS

echo "[INFO] All jobs sent out by the dispatcher have finished."

echo "[INFO] Removing pycache"
rm -r $WORKER/__pycache__

if [[ "$KEEP_WORKDIRS" -eq 0 ]]; then
    echo "[INFO] Deleting workdirs"
    rm -r $WORKDIRS
fi

if [ ! -z $beanstalkdPID ]; then
    echo "[INFO] Stopping beanstalkd"
    kill $beanstalkdPID
    rm $beanstalkdDir -rf
    echo "[INFO] Done."
    exit
fi