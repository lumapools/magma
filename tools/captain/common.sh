export TARBALL_BASENAME="ball"

echo_time() {
    date "+[%F %R] $*"
}
export -f echo_time

get_var_or_default() {
    ##
    # Pre-requirements:
    # - $1..N: placeholders
    ##
    function join_by { local IFS="$1"; shift; echo "$*"; }
    pattern=$(join_by _ "${@}")

    name="$(eval echo ${pattern})"
    name="${name}[@]"
    value="${!name}"
    if [ -z "$value" ] || [ ${#value[@]} -eq 0 ]; then
        set -- "DEFAULT" "${@:2}"
        pattern=$(join_by _ "${@}")
        name="$(eval echo ${pattern})"
        name="${name}[@]"
        value="${!name}"
        if [ -z "$value" ] || [ ${#value[@]} -eq 0 ]; then
            set -- "${@:2}"
            pattern=$(join_by _ "${@}")
            name="$(eval echo ${pattern})"
            name="${name}[@]"
            value="${!name}"
        fi
    fi
    echo "${value[@]}"
}
export -f get_var_or_default

# Check if beanstalkd is already running or not
# There might be a better way of doing it but the user is warned, and can therefore bypass this check
# with the -f flag if the system detected a non-beanstalkd instance.
check_beanstalkd_is_running() {
    echo "[INFO] Checking if beanstalkd is running"
    beanstalkdProcess="$(ps -aux | grep beanstalkd | wc -l)"
    if [[ $beanstalkdProcess > 1 ]] && [[ -z $FORCE ]]; then
        echo "[ERROR] An instance of beanstalkd might already be running in the background."
        echo "------- Kill it or, if it is not a beanstalkd instance, relaunch this script with a -f flag."
        echo "------- If another beanstalkd instance is already running and the -f flag is used, the program will misbehave."
        echo "Program detected:"
        echo "$(ps -aux | grep beanstalkd)"
        exit -1
    fi
}
export -f check_beanstalkd_is_running

clone_beanstalkd() {
    cd $MAGMA/tools/captain
    if [ ! -d beanstalkd ]; then # If beanstalkd does not exist
        echo "Cloning beanstalkd"
        git clone git@github.com:beanstalkd/beanstalkd.git
        export beanstalkdDir=$(realpath beanstalkd)
        echo "Clone successful"
        cd beanstalkd && make && cd -
    fi
}
export -f clone_beanstalkd

prerun_check_dispatcher() {
    ##
    # Pre-requireents:
    # - $1: path to dispatcherconfig
    ##

    source "$1"

    echo "[INFO] Running prerun check on $1"

    GREENSTALK=$(pip list | grep greenstalk)
    if [ -z "$GREENSTALK" ]; then
        echo "[ERROR] greenstalk is required to run this script (pip install greenstalk)"
        exit -1
    fi

    HJSON=$(pip list | grep hjson)
    if [ -z "$HJSON" ]; then
        echo "[ERROR] hjson is required to run this script (pip install hjson)"
        exit -1
    fi

    if [ -z "$TEMP_RESULTS" ]; then
        echo "[ERROR] Specify TEMP_RESULTS in dispatcherconfig. Exiting."
        exit -1
    fi

    if [ -d "$TEMP_RESULTS" ]; then
        echo "[ERROR] TEMP_RESULTS already exists, exiting."
        exit -1
    fi

    if [ -z "$WORKDIR" ]; then
        echo "[ERROR] Specify WORKDIR in dispatcherconfig. Exiting."
        exit -1
    fi

    if [ -d "$WORKDIR" ]; then
        echo "[ERROR] WORKDIR "$WORKDIR" already exists. Exiting."
        exit -1
    fi

    mkdir -p $TEMP_RESULTS
    mkdir -p $WORKDIR
    if [[ "$(realpath $WORKDIR)/" == "$(realpath $TEMP_RESULTS)/"* ]]; then
        echo "[ERROR] WORKDIR cannot be equal to, or a subdirectory of TEMP_RESULTS. Exiting."
        rm -r $TEMP_RESULTS
        exit -1
    fi
    rm -r $TEMP_RESULTS
    rm -r $WORKDIR

    if [ -z "$COPY_TYPE" ]; then
        echo "[ERROR] Error: Specify COPY_TYPE in dispatcherconfig. Exiting."
        exit -1
    fi

    if [ -z "$JOBS_CONFIG" ]; then
        echo "[ERROR] Error: Specify JOBS_CONFIG in dispatcherconfig. Exiting."
        exit -1
    fi

    if [ ! -f $JOBS_CONFIG ]; then
        echo "[ERROR] Job configuration file $JOBS_CONFIG does not exist. Exiting."
        exit -1
    fi

    echo "[INFO] Finished prerun check"
}
export -f prerun_check_dispatcher
