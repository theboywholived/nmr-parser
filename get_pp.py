import collections
import os
import re
from zipfile import ZipFile

pp_file_paths = []
pp_file_name = str(GETPAR('PULPROG')).strip()
spnam_paths_all = []
print(pp_file_name)
pwd = os.popen('pwd').read().strip()

dd = CURDATA()

# Data Directory, i.e, where the working dataset is located
# Calculate the data directory path
dd = dd[3] + '/' + dd[0] + '/' + dd[1]

try:
    with open('parfile-dirs.prop', 'r') as f:
        for i in f:
            if 'PP_DIRS=' in i:
                pp_file_paths += i[8:].strip().split(';')
            if 'SHAPE_DIRS' in i:
                spnam_paths_all += i[11:].strip().split(';')
except IOError:
    raise FileNotFoundError("Couldn't Locate parfile-dirs.prop for the pulse program")
print(spnam_paths_all)
# MSG(str(pp_dirs))
# MSG(pwd)


independent_parameters = ['PULPROG', 'AQ_mod', 'DS', 'NS', 'FW', 'RG', 'DW', 'DE', 'NBL', 'DQDMODE', 'PH_ref']
dependent_parameters = ['TD', 'SW', 'AQ', 'FIDRES']
nuc_parameters = ['NUC', 'O', 'SFO', 'BF']
sp_parameters = ['SPNAM', 'SPOAL', 'SPOFFS', 'SPW']
gp_parameters = ['GPNAM', 'GPZ']


def remove_duplicates(parameters_list):
    return list(set(parameters_list))


def clean_regex(parameters_list):
    for j in range(len(parameters_list)):
        parameters_list[j] = re.sub('[\W_]+', '', parameters_list[j])

    parameters_list = remove_duplicates(parameters_list)

    parameters_list.sort()
    return parameters_list


raw_pulse_parameters = {}
parsed_pulse_parameters = {}


# acqus_file_path = "/home/go/Downloads/vedant/1"
# acqus_file_name = "/acqus"
#

# Get the number from the end of the string
# Example input: 'sp23'
# Example output: 23
def get_trailing_numbers(s):
    m = re.search(r'\d+$', s)
    return int(m.group()) if m else None


# Splits the String and returns a list of separate values,
# Example input: "<> <> <3.5> <> <10>".
# Example output: ["", "", "3.5", "", "10]
# note: each entry is a String
def split_arraystring(s):
    _rec, _s, _ret = False, "", []
    for c in s:
        if c == '<':
            _rec = True
        elif c == '>':
            _ret.append(_s)
            _rec, _s = False, ""
        elif _rec:
            _s += c

    return _ret


# Regular express patterns for all parameters in pulse programs
prefixes = {"p": r"[ (]p\d+",
            "sp": r"[:;=]sp\d+",
            "pl": r"[ ]pl\d+",
            "gp": r"[ :]gp\d+",
            "d": r"[:;=]d\d+",
            "cnst": r"cnst\d+"
            }

# Calculate the working directory for pulse programs
pp_wd = pwd[:pwd.find('/prog/curdir')] + '/exp/stan/nmr'

# Get the names of parameters from the pulse program file
pp_orig = []
for fp in pp_file_paths:
    cwd = ((pp_wd + '/') if fp[0] != '/' else '') + fp + '/'
    # MSG(cwd)
    if os.path.exists(cwd):
        with open(cwd + pp_file_name) as pp:
            for i in pp:
                pp_orig += [i];
                if len(str(i)) >= 1 and str(i)[0] != ';':
                    for prefix in prefixes:
                        raw_pulse_parameters.setdefault(prefix, [])
                        raw_pulse_parameters[prefix] += re.findall(prefixes[prefix], i)
        break
if not pp_orig:
    raise FileNotFoundError("Couldn't find the Pulse Program")

for k, v in raw_pulse_parameters.items():
    raw_pulse_parameters[k] = clean_regex(v)

for key, value in raw_pulse_parameters.items():
    for j in value:
        parsed_pulse_parameters.setdefault(key, [])
        parsed_pulse_parameters[key].append(get_trailing_numbers(j))
    parsed_pulse_parameters[key].sort()

# Parses the 'acqus' file, returns a list with status of each possible nucleus(corresponding to the index)
# Example Output: ['1H', 'off', '15N', 'off', 'off', 'off', 'off', 'off']
# In the example, NUC1 and NUC3 are on while others are off
nucleus_status_list = []
try:
    with open(dd + '/' + 'acqus') as f:
        for each_line in f:
            if len(each_line) >= 10 and not (each_line.startswith(("##$NUCLEUS"))) and each_line.startswith("##$NUC"):
                each_nuc = (each_line.split("= "))
                # print(each_nuc[1])
                each_nuc[1] = each_nuc[1].strip('<>\n')
                nucleus_status_list.append(each_nuc[1])
except IOError:
    raise IOError("Couldn't read acqus file from: " + dd + '/' + 'acqus')

result = collections.OrderedDict()

# TODO Independent Parameters
for i in independent_parameters:
    value = "None"
    result[i] = GETPAR(i)

# Getting each Nuclear Parameter after appending the number from parsed_parameters to the name of the parameter, eg:"SFO1"
for i in range(len(nucleus_status_list)):
    if nucleus_status_list[i] != 'off':
        for j in nuc_parameters:
            each_param = j + str(i + 1)
            result[each_param] = GETPAR(each_param)

# Shaped Pulse Parameters
spnam_names_current = []
for i in sp_parameters:
    if 'sp' in parsed_pulse_parameters:
        if i == 'SPNAM':
            spnam_arraystring = GETPAR('SPNAM')
            spnam_names_all = split_arraystring(spnam_arraystring)
            for j in parsed_pulse_parameters['sp']:
                each_param = str(i + " " + str(j))
                result[each_param] = spnam_names_all[j]
                spnam_names_current += [spnam_names_all[j]]
        else:
            for j in parsed_pulse_parameters['sp']:
                each_param = str(i + " " + str(j))
                result[each_param] = GETPAR(each_param)
MSG(str(spnam_names_current))
# GP Parameters
for i in gp_parameters:
    if 'gp' in parsed_pulse_parameters:
        for j in parsed_pulse_parameters['gp']:
            each_param = str(i + " " + str(j))
            result[each_param] = GETPAR(each_param)

# Pulse Parameters
if 'p' in parsed_pulse_parameters:
    for i in parsed_pulse_parameters['p']:
        each_param = 'P' + ' ' + str(i)
        result[each_param] = GETPAR(each_param)

if 'pl' in parsed_pulse_parameters:
    for i in parsed_pulse_parameters['pl']:
        each_param = 'PLW' + ' ' + str(i)
        result[each_param] = GETPAR(each_param)

print(nucleus_status_list)
print(raw_pulse_parameters)
print(parsed_pulse_parameters)

try:
    with open(dd + '/' + "pp_modified.txt", 'w') as f:
        for i in pp_orig:
            f.write(i)

        f.write(';' * 25)
        f.write('\n')

        for i in result:
            f.write(';')
            f.write(i + '=' + str(result[i]))
            f.write('\n')

        f.write(";***Axis Parameters***\n")
        for i in dependent_parameters:
            for j in range(GETACQUDIM()):
                f.write(';' + str(j + 1) + " " + i + "=" + (GETPAR(str(j + 1) + " " + i)))
                f.write('\n')
except IOError:
    raise Exception("Couldn't create the modified pulse program")

sp_wd = pwd[:pwd.find('/prog/curdir')] + '/exp/stan/nmr'
spnam_paths_current = []
for each_spnam_name in spnam_names_current:
    for fp in spnam_paths_all:
        each_spnam_abs_path = ((sp_wd + '/') if fp[0] != '/' else '') + fp + '/' + each_spnam_name
        # MSG(cwd)
        if os.path.exists(each_spnam_abs_path):
            spnam_paths_current.append(each_spnam_abs_path)
            break

with ZipFile(dd + '/' + "spnam.zip", 'w') as zip:
    for i in range(len(spnam_paths_current)):
        zip.write(spnam_paths_current[i], spnam_names_current[i])

MSG(str(spnam_paths_current))