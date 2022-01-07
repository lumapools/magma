"""
File Info: Preprocesses the data in the hjson object and gives feedback to the user about mistakes
"""

import hjson
import os
import argparse
import sys


parser = argparse.ArgumentParser("PreprocessArgParser")
parser.add_argument('--configfile', type=str, help="Configuration file path")
parser.add_argument('--magma', type=str, help="Path to magma")
args = parser.parse_args()

configFile = open(args.configfile)

data = hjson.load(configFile)

configFile.close()

"""Logs attribute error"""
def log_err_attr(prefix, attr):
    print(f"{prefix} Missing attribute ({attr})")

"""Logs value error"""
def log_err_value(obj, prefix, attr):
    print(f"{prefix} {attr} (not recognized: {obj.get(attr)})")

"logs type error"
def log_err_type(prefix, attr, expected):
    print(f"{prefix} {attr} (type mismatch: {attr} expects {expected}")

prefix = "[ERROR] config file:"

# Check MAGMA
if data.get("MAGMA") == None:
    log_err_attr(prefix, "MAGMA")
    sys.exit(-1)

# Check WORKER_MODE
if data.get("WORKER_MODE") == None:
    log_err_attr(prefix, "WORKER_MODE")
    sys.exit(-1)
if data["WORKER_MODE"] not in ["logical", "physical", "socket"]:
    log_err_value(data, prefix, "WORKER_MODE")
    sys.exit(-1)

# Check WORKERS
if data.get("WORKERS") != None and not(type(data["WORKERS"]) is int):
    log_err_type(prefix, "WORKERS", "int")
    sys.exit(-1)
if data.get("WORKERS") != None and data["WORKERS"] <= 0:
    print("WORKERS attribute must be positive nonzero")
    sys.exit(-1)
# Check WORKER_POOL
if data.get("WORKER_POOL") != None and not(type(data["WORKER_POOL"]) is list):
    log_err_type(prefix, "WORKER_POOL", "list")
    sys.exit(-1)
if data.get("WORKER_POOL") != None and all(wId > 0 for wId in data["WORKER_POOL"]):
    print(f"{prefix} WORKER_POOL can only contain positive integers")
    sys.exit(-1)
# Check if WORKERS and WORKER_POOL are not set at the same time
if data.get("WORKERS") != None and data["WORKER_POOL"] != None:
    print(f"{prefix} WORKERS and WORKER_POOL cannot be set in tandem.")
    sys.exit(-1) 
# Check CAMPAIGN_WORKERS
if data.get("CAMPAIGN_WORKERS") != None and not(type(data["CAMPAIGN_WORKERS"]) is int):
    log_err_type(prefix, "CAMPAIGN_WORKERS", "int")
    sys.exit(-1)
if data.get("CAMPAIGN_WORKERS") != None and data["CAMPAIGN_WORKERS"] <= 0:
    print("CAMPAIGN_WORKERS attribute must be positive nonzero")
    sys.exit(-1)
# Check FUZZER_CAMPAIGN_WORKERS
if data.get("FUZZER_CAMPAIGN_WORKERS") != None:
    fuzzer_target_keys = set(data["FUZZER_CAMPAIGN_WORKERS"].keys())
    for elem in fuzzer_target_keys:
        fuzzerFA = elem.split(",")[0]
        targetFA = elem.split(",")[1]
        if data.get("WORKERS") != None and data["WORKERS"] < data["FUZZER_CAMPAIGN_WORKERS"][elem]:
            print(f"{prefix} FUZZER_CAMPAIGN_WORKERS for {elem} has to be less than WORKERS.")
            sys.exit(-1)
        if fuzzerFA not in set(os.listdir(f"{args.magma}/fuzzers/")):
            print(f"{prefix} FUZZER \"{fuzzerFA}\" in  FUZZER_CAMPAIGN_WORKERS is not an element of {args.magma}/fuzzers")
            sys.exit(-1)
        if targetFA not in set(os.listdir(f"{args.magma}/targets/")):
            print(f"{prefix} TARGET \"{targetFA}\" for \"{fuzzerFA}\" in FUZZER_CAMPAIGN_WORKERS is not an element of {args.magma}/targets")
            sys.exit(-1)
        if not(type(data["FUZZER_CAMPAIGN_WORKERS"][elem])) is int:
            log_err_type(prefix, f"FUZZER_CAMPAIGN_WORKERS[{elem}]", "int")
            sys.exit(-1)
        if data["FUZZER_CAMPAIGN_WORKERS"][elem] <= 0:
            print(f"{elem}'s FUZZER_CAMPAIGN_WORKERS must be positive nonzero.")
            sys.exit(-1)
    
# Check REPEAT
if data.get("REPEAT") == None:
    log_err_attr(prefix, "REPEAT")
    sys.exit(-1)
if not(type(data["REPEAT"]) is int):
    log_err_type(prefix, "REPEAT", "int")
    sys.exit(-1)
if data["REPEAT"] <= 0:
    print(f"{prefix} REPEAT must be positive nonzero.")
    sys.exit(-1)
# Check POLL
if data.get("POLL") != None:
    if not(type(data["POLL"]) is int) or data["POLL"] <= 0:
        print(f"{prefix} POLL must be a positive nonzero integer")
        sys.exit(-1)
# Check CANARY_MODE
if data.get("CANARY_MODE") != None and not(type(data["CANARY_MODE"]) is int):
    log_err_type(prefix, "CANARY_MODE", "int")
    sys.exit(-1)

all_fuzzers = set(os.listdir(f"{args.magma}/fuzzers"))
all_targets = set(os.listdir(f"{args.magma}/targets"))
# Check FUZZERS
if data.get("FUZZERS") != None:
    if not(type(data["FUZZERS"]) is list):
        log_err_type(prefix, "FUZZERS", "list")
        sys.exit(-1)
    if not(set(data["FUZZERS"]).issubset(all_fuzzers)):
        print(f"{prefix} FUZZERS must be a subset of fuzzers in {args.magma}/fuzzers")
        sys.exit(-1)

# Check TARGETS
if data.get("TARGETS") != None:
    if not(type(data["TARGETS"]) is list):
        log_err_type(prefix, "TARGETS", "list")
        sys.exit(-1)
    if not(set(data["TARGETS"]).issubset(all_targets)):
        print(f"{prefix} TARGETS must be a subset of targets in {args.magma}/targets")
        sys.exit(-1)

fuzzers_to_use = all_fuzzers if data.get("FUZZERS") == None else set(data["FUZZERS"])
targets_to_use = all_targets if data.get("TARGETS") == None else set(data["TARGETS"])

# Check OVERRIDDEN_TARGETS
if data.get("OVERRIDDEN_TARGETS") != None:
    if not(fuzzers_to_use.issubset(all_fuzzers)):
        print(f"{prefix} keys in OVERRIDDEN FUZZERS must all be in {args.magma}/fuzzers")
        sys.exit(-1)
    for fuzzer in fuzzers_to_use:
        or_targets = data["OVERRIDDEN_TARGETS"]
        if or_targets.get(fuzzer) != None and not(set(or_targets[fuzzer]).issubset(all_targets)):
            print(f"{prefix} OVERRIDDEN_TARGETS of {fuzzer} must be a subset of targets in {args.magma}/targets")
            sys.exit(-1)

# Check PROGRAMS
if data.get("PROGRAMS") != None:
    fuzzer_map = {}
    for fuzzer in fuzzers_to_use:
        if data.get("OVERRIDDEN_TARGETS") != None and data["OVERRIDDEN_TARGETS"].get(fuzzer) != None:
            fuzzer_map[fuzzer] = data["OVERRIDDEN_TARGETS"][fuzzer]
        else:
            fuzzer_map[fuzzer] = targets_to_use
    possible_pairs = set()
    for fuzzer in set(fuzzer_map.keys()):
        for target in fuzzer_map[fuzzer]:
            possible_pairs.add((f"{fuzzer},{target}"))
    program_keys = set(data["PROGRAMS"].keys())
    # Check if specified fuzzers exist (in program key pair)
    for elem in program_keys:
        pair_fuzzer = elem.split(",")[0]
        if pair_fuzzer not in set(os.listdir(f"{args.magma}/fuzzers/")):
            # Fuzzer does not exist at all (invalid name)
            print(f"{prefix} {pair_fuzzer} is not a fuzzer in {args.magma}/fuzzers")
            sys.exit(-1)
        if elem not in possible_pairs:
            # Fuzzer exists but the (fuzzer, target) pair the program is specified for won't run
            print(f"{prefix} {elem} is not a (fuzzer,target) pair that will run")
            sys.exit(-1)
    # Check if programs are part of the target's programs
    for pair in program_keys:
        pair_target = pair.split(",")[1]
        for program in data["PROGRAMS"][pair]:
            path_to_configrc = f'{args.magma}/targets/{pair_target}/configrc.hjson'
            configrc = open(path_to_configrc)
            configrc_data = hjson.load(configrc)
            configrc.close()
            target_programs = set(configrc_data["programs"])
            if program not in target_programs:
                print(f"{prefix} program {program} is not part of {pair_target}")
                sys.exit(-1)
sys.exit(0)