"""
File Info: Dispatcher side: Parses config.hjson to extract information to send off as jobs and/or broadcast. 
"""

import hjson
import os



"""Retrieves JSON data from file path
Parameters
----------
path_to_file: The path to the desired file to parse

Returns
-------
dict
    The desired data
"""
def get_config_data(path_to_file):
    config_file = open(path_to_file)
    config_data = hjson.load(config_file)
    config_file.close()
    return config_data

"""Retrieves data on programs for a particular target
Parameters
----------
data: dict
    the configuration file
target: str
    the target to fetch program data for

Returns
-------
dict
    The information on programs for `target`
"""
def get_configrc_data(data, target):
    path_to_configrc = f'{data["MAGMA"]}/targets/{target}/configrc.hjson'
    configrc = open(path_to_configrc)
    configrc_data = hjson.load(configrc)
    configrc.close()
    return configrc_data



"""Fetches all available programs (and corresponding args) for a particular target
Parameters
----------
data: dict
    the configuration file
target: str
    the target to fetch all the programs for

Returns
-------
list(str)
    The list containing all programs (concatenated with eventual args) for `target`
"""
def get_programs_from_target(data, target):
    configrc_data = get_configrc_data(data, target)
    programs = configrc_data['programs'] # Fetch all programs
    return add_args(data, programs, target)



"""Adds arguments to programs for a particular target
Parameters
----------
data: dict
    the configuration file
programs: list(str)
    the programs to add the (potential) arguments to
target: str
    the target whose programs we need to check

Returns
-------
list(str)
    The list of programs but with their respective args added
"""
def add_args(data, programs, target):
    configrc_data = get_configrc_data(data, target)
    if configrc_data.get("args") != None: # If the args attribute exists
        for i in range(len(programs)):
            program_args = configrc_data["args"].get(f'{programs[i]}')
            if program_args != None:
                # Update programs with their arguments (because they exist)
                programs[i] = f'{programs[i]} {program_args}'
    return programs
    

def get_fuzzargs(data, fuzzer, target):
    if data.get("FUZZARGS") != None:
        specified_args = data["FUZZARGS"].get(f'{fuzzer},{target}')
        fuzzargs = "" if specified_args == None else specified_args
        return fuzzargs
    return "" # No args specified (and if I understand if correctly, no fuzzargs are defaulted yet)

"""Fetches the broadcast information from the global configuration file
Returns
-------
str
    the parsed configuration needed to be later broadcasted by the dispatcher
"""
def get_broadcast(configpath):
    configfile = open(configpath)
    data = hjson.load(configfile)
    configfile.close()
    return hjson.dumps(data) # Stringified global configuration


"""Fetches all the possible jobs from the global configuration file
Returns
-------
list(str)
    A list of all possible consistent jobs 
    ("fuzzer,target,program args") repeated as many times as needed according to `REPEAT`
"""
def get_jobs(path_to_configfile):
    config_file = open(path_to_configfile)
    # Load the configuration file into a dictionary
    data = hjson.load(config_file)
    config_file.close()
    # Note: data.get(key) does not raise an error if key does not 
    # exist in the file, data[key] does. By using the .get() implementation,
    # the user is free to delete some fields, they don't have to leave them
    # empty. Reason => disambiguate the interpretation of an empty list/set,
    # and set default parameters.

    fuzzers = data.get('FUZZERS')
    if fuzzers == None or len(fuzzers) == 0: # Use all fuzzers since no fuzzers specified
        fuzzers = os.listdir(f"{data['MAGMA']}/fuzzers") # Get fuzzers from directory of fuzzers

    targets = data.get('TARGETS')
    if targets == None or len(targets) == 0: # Use all targets since no targets specified
        targets = os.listdir(f"{data['MAGMA']}/targets") # Get targets from directory of targets


    overridden_targets = data.get('OVERRIDDEN_TARGETS') # Overridden targets (per fuzzer)

    programs = data.get('PROGRAMS') # Values are identified by ("fuzzer,target")

    fuzzers_targets = set() # Set of pairs of fuzzer and targets

    # Pair fuzzers with targets
    for fuzzer in fuzzers:
        # Allows user to delete the overriden_targets key in the config file
        new_targets = None if overridden_targets == None else overridden_targets.get(fuzzer)
        if new_targets == None: # No overriden targets specified
            for target in targets: # Add non-overridden targets
                fuzzers_targets.add(f'{fuzzer},{target}')
        else:
            for new_target in new_targets: # Overridden targets specified for a particular fuzzer
                fuzzers_targets.add(f'{fuzzer},{new_target}') # Add new targets instead of initial ones
    jobs = []

    # Pair (fuzzer,target)s with programs and arguments
    for fuzzer_target in fuzzers_targets:
        # Allows user to delete the programs key in the config file
        specified_programs = None if programs == None else programs.get(fuzzer_target)
        (desired_fuzzer, desired_target) = fuzzer_target.split(",")
        fuzzargs = get_fuzzargs(data, fuzzer, target)
        # Use the target's default programs if none is specified
        progs = add_args(data, specified_programs, desired_target) if specified_programs != None else get_programs_from_target(data, desired_target)
        for program in progs:
            # Duplicate repeated jobs as many times as needed
            for i in range(data['REPEAT']):
                jobs.append(f'{i},{desired_fuzzer},{desired_target},{program},{fuzzargs}')
    return jobs


