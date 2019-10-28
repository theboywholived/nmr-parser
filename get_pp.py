import collections
import os
import re
from zipfile import ZipFile
import warnings

def clean_regex(parameters_list):
    # Helper Function for Cleaning Regex Output
    for j in range(len(parameters_list)):
        parameters_list[j] = re.sub('[\W_]+', '', parameters_list[j])
    parameters_list = list(set(parameters_list))  # Remove Duplicates
    parameters_list.sort()

    return parameters_list


def get_trailing_numbers(s):
    # Helper Function, gets the number from the end of the string
    # Example input: 'sp23'
    # Example output: 23
    _m = re.search(r'\d+$', s)

    return int(_m.group()) if _m else None


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


def get_paths(pattern):
    # Get list of paths (in priority order) for pulse program and useful parameter files
    # Paths are stored in parfile-dirs.prop file located in the Python working directory
    _filepaths = []
    try:
        with open('parfile-dirs.prop', 'r') as f:
            for i in f:
                if pattern in i:
                    _filepaths += i[(len(pattern) + 1):].strip().split(';')

    except IOError:
        raise FileNotFoundError("Couldn't Locate parfile-dirs.prop for the pulse program")

    return _filepaths


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
                            # MSG(each_include_filename)
                        elif (str(i).startswith("prosol")):
                            each_include_filename = (str(i).split('<')[1]).split('>')[0]
                            _prosol_filenames.append(each_include_filename)
                            # MSG(each_include_filename)
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
    # Takes the Data Directory Path as Input
    # Example Output: ['1H', 'off', '15N', 'off', 'off', 'off', 'off', 'off'] NUC1, NUC3 are on, others are off
    _nucleus_status_list = []
    _aqus_path = dd + '/' + 'acqus'
    try:
        with open(_aqus_path) as f:
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
    # Takes the list of relevant parameters and the nucleus status
    # Uses GETPAR() to find out the values of parameters. Returns two dictionaries for each axis and non axis parameters
    # Also Returns lists with names of the useful files

    _nonaxis_parameters = ['AQ_mod', 'DS', 'NS', 'FW', 'RG', 'DW', 'DE', 'NBL', 'DQDMODE', 'PH_ref', 'FnTYPE']
    _nuc_parameters = ['NUC', 'O', 'SFO', 'BF']
    _sp_parameters = ['SPNAM', 'SPOAL', 'SPOFFS', 'SPW']
    _gp_parameters = ['GPNAM', 'GPZ']
    _cpd_parameters = ['CPDPRG']
    _axis_parameters = ['TD', 'SW', 'AQ', 'FIDRES']

    _aq_mod_map = {'0': 'qf', '1': 'qsim', '2': 'qseq', '3': 'DQD', '4': 'parallelQsim', '5': 'parallelDQD'}
    _dqdmode_map = {'0': 'add', '1': 'subtract'}
    _fntype_map = {'0': 'traditional(planes)', '1': 'full(points)', '2': 'non-uniform_sampling',
                   '3': 'projection-spectroscopy'}

    # Ordered Dictionary: Maintains the order in which elements are inserted
    _result_nonaxis = collections.OrderedDict()  # Stores Result for Independent Parameters
    _result_axis = collections.OrderedDict()  # Stores Result for Axis Dependent Parameters

    # Get the Non-Axis Parameters directly
    for i in _nonaxis_parameters:
        if i == 'AQ_mod':
            _result_nonaxis[i] = _aq_mod_map[GETPAR(i)]
        elif i == 'DQDMODE':
            _result_nonaxis[i] = _dqdmode_map[GETPAR(i)]
        elif i == 'FnTYPE':
            _result_nonaxis[i] = _fntype_map[GETPAR(i)]
        else:
            _result_nonaxis[i] = GETPAR(i)

    # Getting each Nuclear Parameter after appending the index name of the parameter, eg:"SFO1"
    for i in range(len(nucleus_status_list)):
        if nucleus_status_list[i] != 'off':
            for j in _nuc_parameters:
                each_param = j + str(i + 1)
                _result_nonaxis[each_param] = GETPAR(each_param)

    # Proper Names Of Shape Files, Gradient Files, CPD Programs
    _spnam_names = []
    _gpnam_names = []
    _cpdprg_names = []

    _curr_dir_filenames = []  # Names of shape files, gp files and cpd progs in the dataset dir

    # Shaped Pulse Parameters
    for i in _sp_parameters:
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
    # MSG(str(_spnam_names))

    # Gradient Pulse Parameters
    for i in _gp_parameters:
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

    # CPD Programs
    for i in _cpd_parameters:
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
    for i in _axis_parameters:
        for j in range(GETACQUDIM()):
            _result_axis[str(j + 1) + " " + i] = (GETPAR(str(j + 1) + " " + i))

    # Check for Non-Uniform Sampling
    if _result_nonaxis["FnTYPE"] == "non-uniform_sampling":
        _curr_dir_filenames.append('nuslist')

    return _result_nonaxis, _result_axis, _spnam_names, _gpnam_names, _cpdprg_names, _curr_dir_filenames


def write_to_file(data_dir, name, pp_original, result_nonaxis, result_axis):
    # Takes the data_dir path, name of the modified file, list with original pulse program and results
    # Writes it to a new file in the data directory
    try:
        with open(data_dir + '/' + name, 'w') as f:
            for i in pp_original:
                f.write(i)

            f.write(';' * 25)  # Separator after the Original Pulse Program
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


def zip_files(data_dir, py_working_dir, paths, filenames, zipfile_name):
    _nmr_wd = py_working_dir[:py_working_dir.find('/prog/curdir')] + '/exp/stan/nmr'
    _abs_paths = []

    for idx, each_name in enumerate(filenames):
        if each_name != '':

            flag = False
            for fp in paths:
                each_abs_path = ((_nmr_wd + '/') if fp[0] != '/' else '') + fp + '/' + each_name
                # MSG(cwd)
                if os.path.exists(each_abs_path):
                    MSG("File name: " +each_name + ", File Path:"+ each_abs_path)
                    flag = True
                    _abs_paths.append(each_abs_path)
                    break
            if not flag:
                warnings.warn("Couldn't find file {}: {}".format(idx+1, each_name))

        with ZipFile(data_dir + '/' + zipfile_name, 'a') as zip:
            for i in range(len(_abs_paths)):
                zip.write(_abs_paths[i], filenames[i])
        # MSG(str(_abs_paths))


def get_fqlist_filenames():
    index_limit = 8
    result = []

    for i in range(1, index_limit + 1):
        each_fq_list = "FQ" + str(i) + "LIST"
        result.append(str(GETPAR(each_fq_list)).strip())
        # MSG(each_fq_list)
    # MSG("FQLIST LIST:" + str(result))
    return result

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

    pp_paths = get_paths("PP_DIRS")
    spnam_paths = get_paths("SHAPE_DIRS")
    cpd_paths = get_paths("CPD_DIRS")
    gp_paths = get_paths("GP_DIRS")

    va_paths = get_paths("VA_DIRS")
    vc_paths = get_paths("VC_DIRS")
    vd_paths = get_paths("VD_DIRS")
    vp_paths = get_paths("VP_DIRS")
    vt_paths = get_paths("VT_DIRS")
    # MSG(str(va_paths))
    # MSG(str(vc_paths))
    # MSG(str(vd_paths))
    fq_paths = get_paths("F1_DIRS")
    MSG("FQLIST PATH:" + str(fq_paths))

    pp_original, pulse_parameters, include_filenames, prosol_filenames = get_parameters(py_working_dir, pp_filename,
                                                                                       pp_paths)
    fq_filenames = get_fqlist_filenames()
    MSG("FQLIST:" + str(fq_filenames))

    nucleus_status = get_nucleus_status(data_dir)
    # print(nucleus_status)
    # print(pulse_parameters)

    result_nonaxis, result_axis, spnam_filenames, gpnam_filenames, cpd_filenames, curr_dir_filenames = get_values(
        pulse_parameters,
        nucleus_status)

    pp_modified_filename = "pp_modified.txt"
    write_to_file(data_dir, pp_modified_filename, pp_original, result_nonaxis, result_axis)

    zipfile_name = "useful_files.zip"
    zipfile_path = data_dir + '/' + zipfile_name
    if(os.path.exists(zipfile_path)):
        os.remove(zipfile_path)

    zip_files(data_dir, py_working_dir, spnam_paths, spnam_filenames, zipfile_name)
    zip_files(data_dir, py_working_dir, pp_paths, include_filenames, zipfile_name)
    zip_files(data_dir, py_working_dir, gp_paths, gpnam_filenames, zipfile_name)
    zip_files(data_dir, py_working_dir, cpd_paths, cpd_filenames, zipfile_name)

    zip_files(data_dir, py_working_dir, [data_dir], curr_dir_filenames, zipfile_name)

    prosol_path = 'lists/prosol/pulseassign'
    prosol_paths = [prosol_path]
    zip_files(data_dir, py_working_dir, prosol_paths, prosol_filenames, zipfile_name)

    zip_files(data_dir, py_working_dir, va_paths, [str(GETPAR("VALIST").strip())], zipfile_name)
    zip_files(data_dir, py_working_dir, vc_paths, [str(GETPAR("VCLIST").strip())], zipfile_name)
    zip_files(data_dir, py_working_dir, vd_paths, [str(GETPAR("VDLIST").strip())], zipfile_name)
    zip_files(data_dir, py_working_dir, vp_paths, [str(GETPAR("VPLIST").strip())], zipfile_name)
    zip_files(data_dir, py_working_dir, vt_paths, [str(GETPAR("VTLIST").strip())], zipfile_name)

    zip_files(data_dir, py_working_dir, fq_paths, fq_filenames, zipfile_name)

if __name__ == '__main__':
    main()
