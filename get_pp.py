import collections
import os
import re

file_path = []
file_name = str(GETPAR('PULPROG')).strip()
pwd = os.popen('pwd').read()
with open('parfile-dirs.prop', 'r') as f:
    for i in f:
        if 'PP_DIRS=' in i:
            file_path += i[8:].strip().split(';')
            break

# MSG(str(pp_dirs))
# MSG(pwd)


dimension = [{}] * 8  # TODO get number of parameters using GETACQUDIM()

independent_parameters = ['PULPROG', 'AQ_mod', 'DS', 'NS', 'TD0', 'TDAV', 'FW', 'RG', 'DW', 'DWOV', 'DECIM', 'DSPFIRM',
                          'DIGTYP', 'DIGMOD', 'DR', 'DDR', 'DE', 'NBL', 'HPPRGN', 'PRGAIN', 'DQDMODE', 'PH_ref',
                          'OVERFLW', 'FRQLO3N']
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

acqus_file_path = "/home/go/Downloads/vedant/1"
acqus_file_name = "/acqus"


def get_trailing_numbers(s):
    m = re.search(r'\d+$', s)
    return int(m.group()) if m else None


# Split the String, eg: "<> <> <3.5> <> <10>" into a list of separate values, eg: ["", "", "3.5", "", "10]
# note: each entry is a String
def split_arraystring(s):
    _rec, _s, ret = False, "", []
    for c in s:
        if c == '<':
            _rec = True
        elif c == '>':
            ret.append(_s)
            _rec, _s = False, ""
        elif _rec:
            _s += c

    return ret


def parse_acqus_file(file_location):
    nuc_list = []
    with open(file_location) as f:
        for each_line in f:
            if len(each_line) >= 10 and not (each_line.startswith(("##$NUCLEUS"))) and each_line.startswith("##$NUC"):
                each_nuc = (each_line.split("= "))
                # print(each_nuc[1])
                each_nuc[1] = each_nuc[1].strip('<>\n')
                nuc_list.append(each_nuc[1])
    return nuc_list


prefixes = {"p": r"[ (]p\d+",
            "sp": r"[:;=]sp\d+",
            "pl": r"[ ]pl\d+",
            "gp": r"[ :]gp\d+",
            "d": r"[:;=]d\d+",
            "cnst": r"cnst\d+"
            }

for fp in file_path:
    MSG(pwd + '/' + fp)
    if os.path.exists(pwd + '/' + fp):
        with open(fp + file_name) as pp:
            for i in pp:
                if len(str(i)) >= 1 and str(i)[0] != ';':
                    for prefix in prefixes:
                        raw_pulse_parameters.setdefault(prefix, [])
                        raw_pulse_parameters[prefix] += re.findall(prefixes[prefix], i)
        break

MSG(fp)

for k, v in raw_pulse_parameters.items():
    raw_pulse_parameters[k] = clean_regex(v)

nucleus_status_list = parse_acqus_file(acqus_file_path + acqus_file_name)

for key, value in raw_pulse_parameters.items():
    for j in value:
        parsed_pulse_parameters.setdefault(key, [])
        print(j)
        parsed_pulse_parameters[key].append(get_trailing_numbers(j))
    parsed_pulse_parameters[key].sort()

result = collections.OrderedDict()

# TODO Independent Parameters
for i in independent_parameters:
    value = "None"
    result[i] = GETPAR(i)

# # TODO Dependent Parameters
# # for i in dependent_parameters:
# #
#
# Getting each Nuclear Parameter after appending the number from parsed parameters to the name of the parameter, eg:"SFO1"
for i in range(len(nucleus_status_list)):
    if nucleus_status_list[i] != 'off':
        for j in nuc_parameters:
            each_param = j + str(i + 1)
            result[each_param] = GETPAR(each_param)

for i in sp_parameters:
    if i != 'SPNAM':
        for j in parsed_pulse_parameters['sp']:
            each_param = str(i + " " + str(j))
            result[each_param] = GETPAR(each_param)
    else:
        each_arraystring = GETPAR('SPNAM')
        spnam_list = split_arraystring(each_arraystring)
        for j in parsed_pulse_parameters['sp']:
            each_param = str(i + " " + str(j))
            result[each_param] = spnam_list[j]

for i in gp_parameters:
    for j in parsed_pulse_parameters['gp']:
        each_param = str(i + " " + str(j))
        result[each_param] = GETPAR(each_param)

# Appending Pulse Lengths
for i in parsed_pulse_parameters['p']:
    each_param = 'P' + ' ' + str(i)
    result[each_param] = GETPAR(each_param)

for i in parsed_pulse_parameters['pl']:
    each_param = 'PLW' + ' ' + str(i)
    result[each_param] = GETPAR(each_param)

print(nucleus_status_list)
print(raw_pulse_parameters)
print(parsed_pulse_parameters)

with open("PARAM_FINAL.txt", 'w') as f:
    for i in result:
        f.write(i + '=' + str(result[i]))
        f.write('\n')

    f.write("Axis Parameters:\n")
    for i in dependent_parameters:
        for j in range(GETACQUDIM()):
            f.write(str(j + 1) + " " + i + "=" + (GETPAR(str(j + 1) + " " + i)))
            f.write('\n')
