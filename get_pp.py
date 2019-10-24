import collections
import os
import re
from zipfile import ZipFile


def clean_regex(parameters_list):
    # Helper Function for Cleaning Regex Output
    for j in range(len(parameters_list)):
        parameters_list[j] = re.sub('[\W_]+', '', parameters_list[j])
    parameters_list = list(set(parameters_list))  # Remove Duplicates
    parameters_list.sort()

    return parameters_list


def get_trailing_numbers(s):
    # Helper Function, Gets the number from the end of the string
    # Example input: 'sp23'
    # Example output: 23
    m = re.search(r'\d+$', s)

    return int(m.group()) if m else None


def split_arraystring(s):
    # Helper Function, splits the string and returns a list of separate values,
    # Example input: "<> <> <3.5> <> <10>".
    # Example output: ["", "", "3.5", "", "10]
    # Note: each entry is a String
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


def get_paths():
    # Get list of paths (in priority order) for pulse programs and shaped pulse files
    # Paths are stored in parfile-dirs.prop file located in the Python working directory
    _pp_file_paths = []
    _spnam_paths_all = []
    _cpd_file_paths = []
    _gp_file_paths = []
    try:
        with open('parfile-dirs.prop', 'r') as f:
            for i in f:
                if 'PP_DIRS=' in i:
                    _pp_file_paths += i[8:].strip().split(';')
                elif 'SHAPE_DIRS' in i:
                    _spnam_paths_all += i[11:].strip().split(';')
                elif 'CPD_DIRS' in i:
                    _cpd_file_paths += i[9:].strip().split(';')
                elif 'GP_DIRS' in i:
                    _gp_file_paths += i[8:].strip().split(';')

    except IOError:
        raise FileNotFoundError("Couldn't Locate parfile-dirs.prop for the pulse program")

    return _pp_file_paths, _spnam_paths_all, _cpd_file_paths, _gp_file_paths


def get_parameters(py_working_dir, pp_filename, pp_file_paths):
    # Input: Python working Directory, pp name and paths list
    # Output: _pp_orig, a list of all the lines in the original pulseprogram
    # A list of all the pulse parameters

    _raw_pulse_parameters = {}
    _pp_orig = []
    # Regular expression patterns for all parameters in pulse programs
    _prefixes = {"p": r"[ (]p\d+",
                 "sp": r"[:;=]sp\d+",
                 "pl": r"[ ]pl\d+",
                 "gp": r"[ :]gp\d+",
                 "d": r"[:;=]d\d+",
                 "cnst": r"cnst\d+",
                 "cpd": r"[ :]cpd\d+"
                 }
    _pp_working_dir = py_working_dir[:py_working_dir.find('/prog/curdir')] + '/exp/stan/nmr'
    # Raw Pulse Parameters, eg: {'cnst': ['cnst10', 'cnst4'], 'd': ['d26'], 'gp': ['gp1', 'gp2'], ...}
    # Parsed Pulse Parameters, eg: {'cnst': [4, 10], 'd': [26], 'gp': [1, 2], ...}
    _raw_pulse_parameters = {}
    _parsed_pulse_parameters = {}
    _include_filenames = []
    _prosol_filenames = []
    for fp in pp_file_paths:
        cwd = ((_pp_working_dir + '/') if fp[0] != '/' else '') + fp + '/'
        # MSG(cwd)
        if os.path.exists(cwd):
            with open(cwd + pp_filename) as pp:
                for i in pp:
                    _pp_orig += [i]
                    if len(str(i)) >= 1 and str(i)[0] != ';':
                        for prefix in _prefixes:
                            _raw_pulse_parameters.setdefault(prefix, [])
                            _raw_pulse_parameters[prefix] += re.findall(_prefixes[prefix], i)
                        if (str(i).startswith("#include")):
                            each_include_filename = (str(i).split('<')[1]).split('>')[0]
                            _include_filenames.append(each_include_filename)
                            MSG(each_include_filename)
                        elif (str(i).startswith("prosol")):
                            each_include_filename = (str(i).split('<')[1]).split('>')[0]
                            _prosol_filenames.append(each_include_filename)
                            MSG(each_include_filename)
            break
    if len(_pp_orig) == 0:
        raise FileNotFoundError("Couldn't find the Pulse Program")

    # Cleans Regex Output
    for k, v in _raw_pulse_parameters.items():
        _raw_pulse_parameters[k] = clean_regex(v)

    for _key, _value in _raw_pulse_parameters.items():
        for j in _value:
            _parsed_pulse_parameters.setdefault(_key, [])
            _parsed_pulse_parameters[_key].append(get_trailing_numbers(j))
        _parsed_pulse_parameters[_key].sort()

    return _pp_orig, _parsed_pulse_parameters, _include_filenames, _prosol_filenames


def get_nucleus_status(dd):
    # Parses the 'acqus' file, returns a list with status of each possible nucleus(corresponding to the index)
    # Example Output: ['1H', 'off', '15N', 'off', 'off', 'off', 'off', 'off'] NUC1, NUC3 are on, others are off
    _nucleus_status_list = []
    aqus_path = dd + '/' + 'acqus'
    try:
        with open(aqus_path) as f:
            for each_line in f:
                if len(each_line) >= 10 and not (each_line.startswith("##$NUCLEUS")) and each_line.startswith(
                        "##$NUC"):
                    each_nuc = (each_line.split("= "))
                    # print(each_nuc[1])
                    each_nuc[1] = each_nuc[1].strip('<>\n')
                    _nucleus_status_list.append(each_nuc[1])
    except IOError:
        raise IOError("Couldn't read acqus file from: " + dd + '/' + 'acqus')

    return _nucleus_status_list


def get_values(pulse_parameters, nucleus_status_list):
    nonaxis_parameters = ['AQ_mod', 'DS', 'NS', 'FW', 'RG', 'DW', 'DE', 'NBL', 'DQDMODE', 'PH_ref']
    nuc_parameters = ['NUC', 'O', 'SFO', 'BF']
    sp_parameters = ['SPNAM', 'SPOAL', 'SPOFFS', 'SPW']
    gp_parameters = ['GPNAM', 'GPZ']
    cpd_parameters = ['CPDPRG']
    axis_parameters = ['TD', 'SW', 'AQ', 'FIDRES']
    aq_mod_map = {'0': 'qf', '1': 'qsim', '2': 'qseq', '3': 'DQD', '4': 'parallelQsim', '5': 'parallelDQD'}
    dqdmode_map = {'0': 'add', '1': 'subtract'}

    _result_nonaxis = collections.OrderedDict()
    _result_axis = collections.OrderedDict()

    for i in nonaxis_parameters:
        if i == 'AQ_mod':
            _result_nonaxis[i] = aq_mod_map[GETPAR(i)]
        elif i == 'DQDMODE':
            _result_nonaxis[i] = dqdmode_map[GETPAR(i)]
        else:
            _result_nonaxis[i] = GETPAR(i)

    # Getting each Nuclear Parameter after
    # appending the index name of the parameter, eg:"SFO1"
    for i in range(len(nucleus_status_list)):
        if nucleus_status_list[i] != 'off':
            for j in nuc_parameters:
                each_param = j + str(i + 1)
                _result_nonaxis[each_param] = GETPAR(each_param)

    # Shaped Pulse Parameters
    _spnam_names = []
    _gpnam_names = []
    _cpdprg_names = []

    _curr_dir_filenames = []
    for i in sp_parameters:
        if 'sp' in pulse_parameters:
            if i == 'SPNAM':
                spnam_arraystring = GETPAR('SPNAM')
                spnam_names_all = split_arraystring(spnam_arraystring)
                for j in pulse_parameters['sp']:
                    _curr_dir_filenames.append('spnam' + str(j))
                    each_param = str(i + " " + str(j))
                    _result_nonaxis[each_param] = spnam_names_all[j]
                    _spnam_names += [spnam_names_all[j]]
            else:
                for j in pulse_parameters['sp']:
                    each_param = str(i + " " + str(j))
                    _result_nonaxis[each_param] = GETPAR(each_param)
    MSG(str(_spnam_names))

    # GP Parameters
    for i in gp_parameters:
        if 'gp' in pulse_parameters:
            if i == 'GPNAM':
                gpnam_arraystring = GETPAR('GPNAM')
                gpnam_names_all = split_arraystring(gpnam_arraystring)
                for j in pulse_parameters['gp']:
                    _curr_dir_filenames.append('gpnam' + str(j))
                    each_param = str(i + " " + str(j))
                    _result_nonaxis[each_param] = gpnam_names_all[j]
                    _gpnam_names += [gpnam_names_all[j]]
            else:
                for j in pulse_parameters['gp']:
                    each_param = str(i + " " + str(j))
                    _result_nonaxis[each_param] = GETPAR(each_param)
    # CPD Parameters
    for i in cpd_parameters:
        if 'cpd' in pulse_parameters:
            if i == 'CPDPRG':
                cpdprg_arraystring = GETPAR('CPDPRG')
                cpdprg_names_all = split_arraystring(cpdprg_arraystring)
                for j in pulse_parameters['cpd']:
                    _curr_dir_filenames.append('cpdprg' + str(j))
                    each_param = str(i + " " + str(j))
                    _result_nonaxis[each_param] = cpdprg_names_all[j]
                    _cpdprg_names += [cpdprg_names_all[j]]
            else:
                for j in pulse_parameters['cpd']:
                    each_param = str(i + " " + str(j))
                    _result_nonaxis[each_param] = GETPAR(each_param)

    # Pulse Parameters
    if 'p' in pulse_parameters:
        for i in pulse_parameters['p']:
            each_param = 'P' + ' ' + str(i)
            _result_nonaxis[each_param] = GETPAR(each_param)

    if 'pl' in pulse_parameters:
        for i in pulse_parameters['pl']:
            each_param = 'PLW' + ' ' + str(i)
            _result_nonaxis[each_param] = GETPAR(each_param)

    # Axis Dependent Parameters
    for i in axis_parameters:
        for j in range(GETACQUDIM()):
            _result_axis[str(j + 1) + " " + i] = (GETPAR(str(j + 1) + " " + i))

    return _result_nonaxis, _result_axis, _spnam_names, _gpnam_names, _cpdprg_names, _curr_dir_filenames


def write_to_file(data_dir, name, pp_original, result_nonaxis, result_axis):
    try:
        with open(data_dir + '/' + name, 'w') as f:
            for i in pp_original:
                f.write(i)

            f.write(';' * 25)
            f.write('\n')

            for i in result_nonaxis:
                f.write(';')
                f.write(i + '=' + str(result_nonaxis[i]))
                f.write('\n')

            f.write(";***Axis Parameters***\n")
            for i in result_axis:
                f.write(';')
                f.write(i + '=' + str(result_axis[i]))
                f.write('\n')
    except IOError:
        raise Exception("Couldn't create the modified pulse program")


def zip_files(data_dir, py_working_dir, paths, filenames):
    _nmr_wd = py_working_dir[:py_working_dir.find('/prog/curdir')] + '/exp/stan/nmr'
    _abs_paths = []

    for each_name in filenames:
        for fp in paths:
            each_abs_path = ((_nmr_wd + '/') if fp[0] != '/' else '') + fp + '/' + each_name
            # MSG(cwd)
            if os.path.exists(each_abs_path):
                _abs_paths.append(each_abs_path)
                break

    with ZipFile(data_dir + '/' + "useful_files.zip", 'a') as zip:
        for i in range(len(_abs_paths)):
            zip.write(_abs_paths[i], filenames[i])
    MSG(str(_abs_paths))


def main():
    pp_filename = str(GETPAR('PULPROG')).strip()

    # Current working directory for python files in Bruker TopSpin
    # In topspin3.5pl7, it's '/opt/topspin3.5pl7/prog/curdir/go'
    # This path is later used to calculate other topspin paths
    py_working_dir = os.popen('pwd').read().strip()

    # Data directory, i.e, where the TopSpin working dataset is located
    dd = CURDATA()

    # Calculating the data directory
    data_dir = dd[3] + '/' + dd[0] + '/' + dd[1]

    pp_paths, spnam_paths, cpd_paths, gp_paths = get_paths()
    pp_original, pulse_parameters, include_filenames, prosol_filenames = get_parameters(py_working_dir, pp_filename,
                                                                                        pp_paths)
    nucleus_status = get_nucleus_status(data_dir)
    print(nucleus_status)
    print(pulse_parameters)

    result_nonaxis, result_axis, spnam_filenames, gpnam_filenames, cpdprg_filenames, curr_dir_filenames = get_values(
        pulse_parameters,
        nucleus_status)
    write_to_file(data_dir, "pp_modified.txt", pp_original, result_nonaxis, result_axis)

    zip_files(data_dir, py_working_dir, spnam_paths, spnam_filenames)
    zip_files(data_dir, py_working_dir, pp_paths, include_filenames)
    zip_files(data_dir, py_working_dir, gp_paths, gpnam_filenames)
    zip_files(data_dir, py_working_dir, cpd_paths, cpdprg_filenames)
    zip_files(data_dir, py_working_dir, [data_dir], curr_dir_filenames)
    zip_files(data_dir, py_working_dir, ['lists/prosol/pulseassign'], prosol_filenames)


if __name__ == '__main__':
    main()
