#!/bin/bash -e

MAGMA=${MAGMA:-"$(cd "$(dirname "${BASH_SOURCE[0]}")/../../" >/dev/null 2>&1 \
    && pwd)"}
export MAGMA
source "$MAGMA/tools/captain/common.sh"

TMPFS_SIZE=${TMPFS_SIZE:-50g}
export POLL=${POLL:-5}
export TIMEOUT=${TIMEOUT:-1m}

WORKDIR="$(realpath "$WORKDIR")"
export ARDIR="$WORKDIR/ar"
export CACHEDIR="$WORKDIR/cache"
export LOGDIR="$WORKDIR/log"
export POCDIR="$WORKDIR/poc"
mkdir -p "$ARDIR"
mkdir -p "$CACHEDIR"
mkdir -p "$LOGDIR"
mkdir -p "$POCDIR"

# Creates the folder corresponding to the repeat id of the job
create_folder()
{
    ##
    # Pre-requirements:
    # - $1: the directory where campaings are stored
    ## 
    echo $REPEAT_ID
    dir="$1/$REPEAT_ID"
    # Ensure the directory is created to prevent races
    mkdir -p "$dir"
    while [ ! -d "$dir" ]; do sleep 1; done
}
export -f create_folder

start_campaign()
{
    export CAMPAIGN_CACHEDIR="$CACHEDIR/$FUZZER/$TARGET/$PROGRAM"
    export CACHECID=$(create_folder "$CAMPAIGN_CACHEDIR")
    export CAMPAIGN_ARDIR="$ARDIR/$FUZZER/$TARGET/$PROGRAM"
    export ARCID=$(create_folder "$CAMPAIGN_ARDIR")


    export SHARED="$CAMPAIGN_CACHEDIR/$CACHECID"
    mkdir -p "$SHARED" && chmod 777 "$SHARED"

    echo_time "Container $FUZZER/$TARGET/$PROGRAM/$ARCID started on CPU $AFFINITY"
    "$MAGMA"/tools/captain/worker/start.sh &> \
        "${LOGDIR}/${FUZZER}_${TARGET}_${PROGRAM}_${ARCID}_container.log"
    echo_time "Container $FUZZER/$TARGET/$PROGRAM/$ARCID stopped"

    if [ ! -z $POC_EXTRACT ]; then
        "$MAGMA"/tools/captain/worker/extract.sh
    fi

    if [ -z $NO_ARCHIVE ]; then
        # only one tar job runs at a time, to prevent out-of-storage errors
        tar -cf "${CAMPAIGN_ARDIR}/${ARCID}/${TARBALL_BASENAME}.tar" -C "$SHARED" . &>/dev/null && rm -rf "$SHARED"
    else
        # overwrites empty $ARCID directory with the $SHARED directory
        mv -T "$SHARED" "${CAMPAIGN_ARDIR}/${ARCID}"
    fi
}
export -f start_campaign

start_ex()
{
    start_campaign
    exit 0
}
export -f start_ex

# set up a RAM-backed fs for fast processing of canaries and crashes
if [ -z $CACHE_ON_DISK ]; then
    echo_time "Obtaining sudo permissions to mount tmpfs"
    if mountpoint -q -- "$CACHEDIR"; then
        sudo umount -f "$CACHEDIR"
    fi
    sudo mount -t tmpfs -o size=$TMPFS_SIZE,uid=$(id -u $USER),gid=$(id -g $USER) \
        tmpfs "$CACHEDIR"
fi

cleanup()
{
    if [ -z $CACHE_ON_DISK ]; then
        echo_time "Obtaining sudo permissions to umount tmpfs"
        sudo umount "$CACHEDIR"
    fi
}

trap cleanup EXIT

##
# Since configrc(.hjson) (in targets/target) does not yet contain a FUZZARGS part, 
# and the implementation requirements are not yet completely explicit in terms of 
# how FUZZARGS should be defaulted w.r.t (fuzzer, target), FUZZARGS will be set 
# by default to "" if FUZZARGS is unset, because that is what common.sh's 
# get_var_or_default would have done for all pairs (FUZZER,TARGET)".
##
if [ -z $FUZZARGS ]; then
    FUZZARGS=""
fi

export FUZZARGS=$FUZZARGS
start_ex
