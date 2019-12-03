# -*- coding: utf-8 -*-
import datetime
import fnmatch
import os
import sys
import warnings
from zipfile import ZipFile

execfile(os.path.join(os.path.dirname(sys.argv[0]), 'parser.py'))

pp_filename = str(GETPAR('PULPROG')).strip()
config_filename = "parfile-dirs.prop"
# Current working directory for python files in Bruker TopSpin
# In topspin3.5pl7, it's '/opt/topspin3.5pl7/prog/curdir/go'
# This path is later used to calculate other topspin paths
py_working_dir = os.popen('pwd').read().strip()
# Data directory, i.e, where the TopSpin working dataset is located, in topspin format
dd = CURDATA()

# Calculating the data directory
data_dir = dd[3] + os.sep + dd[0] + os.sep + dd[1]

try:
    FileNotFoundError
except NameError:
    FileNotFoundError = IOError

try:
    from thread import get_ident as _get_ident
except ImportError:
    try:
        from dummy_thread import get_ident as _get_ident
    except:
        pass

try:
    from _abcoll import KeysView, ValuesView, ItemsView
except ImportError:
    pass


class OrderedDict(dict):
    'Dictionary that remembers insertion order'

    # An inherited dict maps keys to values.
    # The inherited dict provides __getitem__, __len__, __contains__, and get.
    # The remaining methods are order-aware.
    # Big-O running times for all methods are the same as for regular dictionaries.

    # The internal self.__map dictionary maps keys to links in a doubly linked list.
    # The circular doubly linked list starts and ends with a sentinel element.
    # The sentinel element never gets deleted (this simplifies the algorithm).
    # Each link is stored as a list of length three:  [PREV, NEXT, KEY].

    def __init__(self, *args, **kwds):
        '''Initialize an ordered dictionary.  Signature is the same as for
        regular dictionaries, but keyword arguments are not recommended
        because their insertion order is arbitrary.

        '''
        if len(args) > 1:
            raise TypeError('expected at most 1 arguments, got %d' % len(args))
        try:
            self.__root
        except AttributeError:
            self.__root = root = []  # sentinel node
            root[:] = [root, root, None]
            self.__map = {}
        self.__update(*args, **kwds)

    def __setitem__(self, key, value, dict_setitem=dict.__setitem__):
        'od.__setitem__(i, y) <==> od[i]=y'
        # Setting a new item creates a new link which goes at the end of the linked
        # list, and the inherited dictionary is updated with the new key/value pair.
        if key not in self:
            root = self.__root
            last = root[0]
            last[1] = root[0] = self.__map[key] = [last, root, key]
        dict_setitem(self, key, value)

    def __delitem__(self, key, dict_delitem=dict.__delitem__):
        'od.__delitem__(y) <==> del od[y]'
        # Deleting an existing item uses self.__map to find the link which is
        # then removed by updating the links in the predecessor and successor nodes.
        dict_delitem(self, key)
        link_prev, link_next, key = self.__map.pop(key)
        link_prev[1] = link_next
        link_next[0] = link_prev

    def __iter__(self):
        'od.__iter__() <==> iter(od)'
        root = self.__root
        curr = root[1]
        while curr is not root:
            yield curr[2]
            curr = curr[1]

    def __reversed__(self):
        'od.__reversed__() <==> reversed(od)'
        root = self.__root
        curr = root[0]
        while curr is not root:
            yield curr[2]
            curr = curr[0]

    def clear(self):
        'od.clear() -> None.  Remove all items from od.'
        try:
            for node in self.__map.itervalues():
                del node[:]
            root = self.__root
            root[:] = [root, root, None]
            self.__map.clear()
        except AttributeError:
            pass
        dict.clear(self)

    def popitem(self, last=True):
        '''od.popitem() -> (k, v), return and remove a (key, value) pair.
        Pairs are returned in LIFO order if last is true or FIFO order if false.

        '''
        if not self:
            raise KeyError('dictionary is empty')
        root = self.__root
        if last:
            link = root[0]
            link_prev = link[0]
            link_prev[1] = root
            root[0] = link_prev
        else:
            link = root[1]
            link_next = link[1]
            root[1] = link_next
            link_next[0] = root
        key = link[2]
        del self.__map[key]
        value = dict.pop(self, key)
        return key, value

    # -- the following methods do not depend on the internal structure --

    def keys(self):
        'od.keys() -> list of keys in od'
        return list(self)

    def values(self):
        'od.values() -> list of values in od'
        return [self[key] for key in self]

    def items(self):
        'od.items() -> list of (key, value) pairs in od'
        return [(key, self[key]) for key in self]

    def iterkeys(self):
        'od.iterkeys() -> an iterator over the keys in od'
        return iter(self)

    def itervalues(self):
        'od.itervalues -> an iterator over the values in od'
        for k in self:
            yield self[k]

    def iteritems(self):
        'od.iteritems -> an iterator over the (key, value) items in od'
        for k in self:
            yield (k, self[k])

    def update(*args, **kwds):
        '''od.update(E, **F) -> None.  Update od from dict/iterable E and F.

        If E is a dict instance, does:           for k in E: od[k] = E[k]
        If E has a .keys() method, does:         for k in E.keys(): od[k] = E[k]
        Or if E is an iterable of items, does:   for k, v in E: od[k] = v
        In either case, this is followed by:     for k, v in F.items(): od[k] = v

        '''
        if len(args) > 2:
            raise TypeError('update() takes at most 2 positional '
                            'arguments (%d given)' % (len(args),))
        elif not args:
            raise TypeError('update() takes at least 1 argument (0 given)')
        self = args[0]
        # Make progressively weaker assumptions about "other"
        other = ()
        if len(args) == 2:
            other = args[1]
        if isinstance(other, dict):
            for key in other:
                self[key] = other[key]
        elif hasattr(other, 'keys'):
            for key in other.keys():
                self[key] = other[key]
        else:
            for key, value in other:
                self[key] = value
        for key, value in kwds.items():
            self[key] = value

    __update = update  # let subclasses override update without breaking __init__

    __marker = object()

    def pop(self, key, default=__marker):
        '''od.pop(k[,d]) -> v, remove specified key and return the corresponding value.
        If key is not found, d is returned if given, otherwise KeyError is raised.

        '''
        if key in self:
            result = self[key]
            del self[key]
            return result
        if default is self.__marker:
            raise KeyError(key)
        return default

    def setdefault(self, key, default=None):
        'od.setdefault(k[,d]) -> od.get(k,d), also set od[k]=d if k not in od'
        if key in self:
            return self[key]
        self[key] = default
        return default

    def __repr__(self, _repr_running={}):
        'od.__repr__() <==> repr(od)'
        call_key = id(self), _get_ident()
        if call_key in _repr_running:
            return '...'
        _repr_running[call_key] = 1
        try:
            if not self:
                return '%s()' % (self.__class__.__name__,)
            return '%s(%r)' % (self.__class__.__name__, self.items())
        finally:
            del _repr_running[call_key]

    def __reduce__(self):
        'Return state information for pickling'
        items = [[k, self[k]] for k in self]
        inst_dict = vars(self).copy()
        for k in vars(OrderedDict()):
            inst_dict.pop(k, None)
        if inst_dict:
            return (self.__class__, (items,), inst_dict)
        return self.__class__, (items,)

    def copy(self):
        'od.copy() -> a shallow copy of od'
        return self.__class__(self)

    @classmethod
    def fromkeys(cls, iterable, value=None):
        '''OD.fromkeys(S[, v]) -> New ordered dictionary with keys from S
        and values equal to v (which defaults to None).

        '''
        d = cls()
        for key in iterable:
            d[key] = value
        return d

    def __eq__(self, other):
        '''od.__eq__(y) <==> od==y.  Comparison to another OD is order-sensitive
        while comparison to a regular mapping is order-insensitive.

        '''
        if isinstance(other, OrderedDict):
            return len(self) == len(other) and self.items() == other.items()
        return dict.__eq__(self, other)

    def __ne__(self, other):
        return not self == other

    # -- the following methods are only used in Python 2.7 --

    def viewkeys(self):
        "od.viewkeys() -> a set-like object providing a view on od's keys"
        return KeysView(self)

    def viewvalues(self):
        "od.viewvalues() -> an object providing a view on od's values"
        return ValuesView(self)

    def viewitems(self):
        "od.viewitems() -> a set-like object providing a view on od's items"
        return ItemsView(self)


def split_arraystring(s):
    """
    Helper Function, splits the string and returns a list of separate values
    :param s: input string, eg: "<> <> <3.5> <> <10>".
    :return: output string, eg:  ["", "", "3.5", "", "10]
    Note: each entry is a String
    """
    flag, _s, ret = False, "", []
    for entry in s:
        if entry == '<':
            flag = True
        elif entry == '>':
            ret.append(_s)
            flag, _s = False, ""
        elif flag:
            _s += entry

    return ret


def get_values_and_pulse_filenames(pulse_parameters):
    """

    :param pulse_parameters: Dictionary of relevant parameters and their indices
    :return:
    result_nonaxis: Dictionary of non-axis parameters and their values
    result_axis: Dictionary of axis parameters and their values
    spnam_names: List of names of the Shaped Pulse files
    gpnam_names: List of Names of Gradient Pulse files
    cpdprg_names: List of Names of Decoupling files
    """

    _NONAXIS_PARAMETERS = ['AQ_mod', 'DS', 'NS', 'FW', 'RG', 'DE', 'NBL', 'DQDMODE', 'PH_ref', 'FnTYPE']
    _AXIS_PARAMETERS = ['TD', 'SW', 'AQ']

    _NUC_PARAMETERS = ['NUC', 'O', 'BF']
    _SP_PARAMETERS = ['SPNAM', 'SPOAL', 'SPOFFS', 'SPW']
    _GP_PARAMETERS = ['GPNAM', 'GPZ']
    _CPD_PARAMETERS = ['CPDPRG']

    _aq_mod_map = {'0': 'qf', '1': 'qsim', '2': 'qseq', '3': 'DQD', '4': 'parallelQsim', '5': 'parallelDQD'}
    _dqdmode_map = {'0': 'add', '1': 'subtract'}
    _fntype_map = {'0': 'traditional(planes)', '1': 'full(points)', '2': 'non-uniform_sampling',
                   '3': 'projection-spectroscopy'}

    # Ordered Dictionary: Maintains the order in which elements are inserted
    result_nonaxis = OrderedDict()  # Stores Result for Independent Parameters
    result_axis = OrderedDict()  # Stores Result for Axis Dependent Parameters

    # Get the Non-Axis Parameters directly
    for i in _NONAXIS_PARAMETERS:
        if i == 'AQ_mod':
            result_nonaxis[i] = _aq_mod_map[GETPAR(i)]
        elif i == 'DQDMODE':
            result_nonaxis[i] = _dqdmode_map[GETPAR(i)]
        elif i == 'FnTYPE':
            result_nonaxis[i] = _fntype_map[GETPAR(i)]
        else:
            result_nonaxis[i] = GETPAR(i)

    # Getting each Nuclear Parameter after appending the index name of the parameter, eg:"SFO1"
    for i in range(8):
        if GETPAR("NUC" + str(i + 1)) != "off":
            for j in _NUC_PARAMETERS:
                if j == 'O':
                    _each_param = j + str(i + 1) + 'P'
                    result_nonaxis[_each_param] = GETPAR(_each_param)
                else:
                    _each_param = j + str(i + 1)
                    result_nonaxis[_each_param] = GETPAR(_each_param)

    # Proper Names Of Shape Files, Gradient Files, CPD Programs
    spnam_names = []
    gpnam_names = []
    cpdprg_names = []

    # data_dir_filenames = []  # Names of shape files, gp files and cpd progs in the dataset dir

    # Shaped Pulse Parameters
    if 'sp' in pulse_parameters:
        for i in _SP_PARAMETERS:
            if i == 'SPNAM':
                _spnam_arraystring = GETPAR('SPNAM')
                _spnam_names_all = split_arraystring(_spnam_arraystring)
                for j in pulse_parameters['sp']:
                    # data_dir_filenames.append('spnam' + str(j))
                    _each_param = str(i + " " + str(j))
                    result_nonaxis[_each_param] = _spnam_names_all[j]
                    spnam_names += [_spnam_names_all[j]]
            else:
                for j in pulse_parameters['sp']:
                    _each_param = str(i + " " + str(j))
                    result_nonaxis[_each_param] = GETPAR(_each_param)
    # MSG(str(_spnam_names))

    # Gradient Pulse Parameters
    if 'gp' in pulse_parameters:
        for i in _GP_PARAMETERS:
            if i == 'GPNAM':
                _gpnam_arraystring = GETPAR('GPNAM')
                _gpnam_names_all = split_arraystring(_gpnam_arraystring)
                for j in pulse_parameters['gp']:
                    # data_dir_filenames.append('gpnam' + str(j))
                    _each_param = str(i + " " + str(j))
                    result_nonaxis[_each_param] = _gpnam_names_all[j]
                    gpnam_names += [_gpnam_names_all[j]]
            else:
                for j in pulse_parameters['gp']:
                    _each_param = str(i + " " + str(j))
                    result_nonaxis[_each_param] = GETPAR(_each_param)

    # CPD Programs
    if 'cpd' in pulse_parameters:
        for i in _CPD_PARAMETERS:
            if i == 'CPDPRG':
                cpdprg_arraystring = GETPAR('CPDPRG')
                cpdprg_names_all = split_arraystring(cpdprg_arraystring)
                for j in pulse_parameters['cpd']:
                    # data_dir_filenames.append('cpdprg' + str(j))
                    _each_param = str(i + " " + str(j))
                    result_nonaxis[_each_param] = cpdprg_names_all[j]
                    cpdprg_names += [cpdprg_names_all[j]]
            else:
                for j in pulse_parameters['cpd']:
                    _each_param = str(i + " " + str(j))
                    result_nonaxis[_each_param] = GETPAR(_each_param)

    # Pulse Parameters
    if 'p' in pulse_parameters:
        for i in pulse_parameters['p']:
            _each_param = 'P' + ' ' + str(i)
            result_nonaxis[_each_param] = GETPAR(_each_param)
    if 'pl' in pulse_parameters:
        for i in pulse_parameters['pl']:
            _each_param = 'PLW' + ' ' + str(i)
            result_nonaxis[_each_param] = GETPAR(_each_param)
    # Delays
    if 'd' in pulse_parameters:
        for i in pulse_parameters['d']:
            _each_param = 'D' + ' ' + str(i)
            result_nonaxis[_each_param] = GETPAR(_each_param)
    # Constants
    if 'cnst' in pulse_parameters:
        for i in pulse_parameters['cnst']:
            _each_param = 'CNST' + ' ' + str(i)
            result_nonaxis[_each_param] = GETPAR(_each_param)
    # Loop Counters
    if 'l' in pulse_parameters:
        for i in pulse_parameters['l']:
            _each_param = 'l' + ' ' + str(i)
            result_nonaxis[_each_param] = GETPAR(_each_param)
    # Pulse decoupling
    if 'pcpd' in pulse_parameters:
        for i in pulse_parameters['pcpd']:
            _each_param = 'pcpd' + ' ' + str(i)
            result_nonaxis[_each_param] = GETPAR(_each_param)

    # Axis Dependent Parameters
    for i in _AXIS_PARAMETERS:
        _dimension = GETACQUDIM()
        for j in range(_dimension):
            result_axis[str(j + 1) + " " + i] = (GETPAR(str(j + 1) + " " + i))

    return result_nonaxis, result_axis, spnam_names, gpnam_names, cpdprg_names


def get_matching_filenames(pattern, path):
    """
    Gets matching filenames from the path, using unix shell wildcards
    :param pattern: Unix shell-style wildcards for filenames
    :param path: Path for the files
    :return: list of matching filenames
    """
    names = []
    for root, dirs, files in os.walk(path):
        for name in files:
            if fnmatch.fnmatch(name, pattern):
                names.append(name)
    return names


def write_to_file(path, name, pp_original, result_nonaxis, result_axis):
    """
    Writes relevant data to a new file in the data directory
    :param path:
    :param name: Filename for the new file to be written
    :param pp_original: Original pulseprogram
    :param result_nonaxis: Names and values of non axis parameters
    :param result_axis: Names and values of the axis parameters
    """
    abs_path = os.path.join(path, name)
    try:
        f = open(abs_path, 'w')
        for i in pp_original:
            f.write(i)
        f.write(";***Axis Parameters***")
        f.write('\n')
        for i in result_axis:
            f.write(';')
            f.write(i + '=' + str(result_axis[i]))
            f.write('\n')  # Separator after the Original Pulse Program
        f.write(";***Non-Axis Parameters***")
        f.write('\n')
        for i in result_nonaxis:
            f.write(';')
            f.write(i + '=' + str(result_nonaxis[i]))
            f.write('\n')
        f.close()
    except IOError:
        raise Exception("Couldn't create" + abs_path)


def add_files_to_zip(paths, filenames, zf, folder_name, files_taken_from, curr_dir=False):
    """
    Using the list of paths, filenames and the zipfile object, zip up the files
    :param files_taken_from: Dictionary of Tuples(containing file name and path) of the zipped files
    :param paths: List of possible paths for each list
    :param filenames: List of filenames
    :param zf: The ZipFile Object
    :param folder_name: Name of the folder name
    :param curr_dir: Whether the filenames exist in the dataset directory or not, False by default
    """
    _nmr_wd = os.path.join(py_working_dir[:py_working_dir.find(
        os.sep + "prog" + os.sep + "curdir")], "exp", "stan", "nmr")
    # MSG(_nmr_wd)
    for idx, each_name in enumerate(filenames):
        if each_name != '':
            flag = False
            for fp in paths:
                each_abs_path = ((_nmr_wd + os.sep) if not os.path.isabs(fp) else '') + fp + os.sep + each_name
                if os.path.exists(each_abs_path):
                    flag = True
                    encoded_each_name = each_name.encode('ascii', 'replace')
                    if curr_dir:
                        path_to_write = os.path.join("data-dir-files", folder_name, encoded_each_name)
                    else:
                        path_to_write = os.path.join(folder_name, encoded_each_name)
                    if not (path_to_write in zf.namelist()):
                        # files_created.append((encoded_each_name, path_to_write))
                        files_taken_from.append((each_name, each_abs_path))
                        zf.write(each_abs_path, path_to_write)
                    break
            if not flag:
                warnings.warn("Couldn't find file:" + str(idx + 1) + " : " + each_name)


def get_fqlist_filenames():
    """
    Get the names of the 8 files used for fqlist
    :return: List of filenames for fqlist
    """
    index_limit = 8
    result = []

    for i in range(1, index_limit + 1):
        each_fq_list = "FQ" + str(i) + "LIST"
        result.append(str(GETPAR(each_fq_list)).strip())
    return result


def main():
    """
    It all begins here.
    """
    files_taken_from = []
    p = Parser(py_working_dir, pp_filename)
    # Get a list of paths for each kind of file.//
    pp_paths = p.get_path_list("PP_DIRS", config_filename)
    spnam_paths = p.get_path_list("SHAPE_DIRS", config_filename)
    cpd_paths = p.get_path_list("CPD_DIRS", config_filename)
    gpnam_paths = p.get_path_list("GP_DIRS", config_filename)
    va_paths = p.get_path_list("VA_DIRS", config_filename)
    vc_paths = p.get_path_list("VC_DIRS", config_filename)
    vd_paths = p.get_path_list("VD_DIRS", config_filename)
    vp_paths = p.get_path_list("VP_DIRS", config_filename)
    vt_paths = p.get_path_list("VT_DIRS", config_filename)
    fq_paths = p.get_path_list("F1_DIRS", config_filename)
    prosol_path = os.path.join("lists", "prosol", "pulseassign")
    prosol_paths = [prosol_path]

    # Get names of the files required from the dataset directory
    spnam_data_dir_filenames = get_matching_filenames("spnam*", data_dir)
    gpnam_data_dir_filenames = get_matching_filenames("gpnam*", data_dir)
    cpd_data_dir_filenames = get_matching_filenames("cpdprg*", data_dir)
    nus_data_dir_filenames = get_matching_filenames("nuslist", data_dir)
    # Get names of the fqlist files
    fq_filenames = get_fqlist_filenames()

    names_paths_dict = {(pp_filename,): pp_paths, tuple(cpd_data_dir_filenames): [data_dir]}

    # Get a copy of the orig pulseprogram, list of parameters, names of include and prosol files from the pulseprogram

    pp_original, pp_original_abs_path, pulse_parameters, include_filenames, prosol_filenames, _ = p.parse_pp_cpd(
        names_paths_dict)
    # p, pl = p.parse_prosol(prosol_filenames[0], prosol_path)
    # print(p, pl)
    # MSG(str(pulse_parameters))
    result_nonaxis, result_axis, spnam_filenames, gpnam_filenames, cpd_filenames = get_values_and_pulse_filenames(
        pulse_parameters)

    mr_path = os.path.join(data_dir, "mr")
    if not os.path.exists(os.path.dirname(mr_path + os.sep)):
        os.makedirs(os.path.dirname(mr_path + os.sep))

    # Specify name of the txt file to store parameters and the original pulse program
    pp_modified_filename = "MRpulseprogram"
    pp_modified_path = mr_path
    write_to_file(pp_modified_path, pp_modified_filename, pp_original, result_nonaxis, result_axis)

    pp_sep = '_'
    pp_global_filename = pp_filename + pp_sep + dd[0] + pp_sep + dd[1] + pp_sep + ''.join(
        (str(datetime.date.today()).split('-')))
    pp_global_path = os.path.join(os.path.expanduser('~'), "pp_logs")
    # MSG(os.path.dirname(pp_global_path + os.sep))
    if not os.path.exists(os.path.dirname(pp_global_path + os.sep)):
        os.makedirs(os.path.dirname(pp_global_path + os.sep))
    write_to_file(pp_global_path, pp_global_filename, pp_original, result_nonaxis, result_axis)

    # Specify name of the zip to contain the required files
    zipfile_name = "MRfiles.zip"
    zipfile_path = mr_path + os.sep + zipfile_name

    # Delete the existing zip file(from a previous run) in the dataset directory, if present
    if os.path.exists(zipfile_path):
        os.remove(zipfile_path)

    # Create a new zipped file
    zf = ZipFile(zipfile_path, 'w')
    # Add a type of file to the zip, with each function call; also specify folder name
    add_files_to_zip(spnam_paths, spnam_filenames, zf, "spnam", files_taken_from)
    add_files_to_zip(pp_paths, include_filenames, zf, "include_files", files_taken_from)
    add_files_to_zip(gpnam_paths, gpnam_filenames, zf, "gpnam", files_taken_from)
    add_files_to_zip(cpd_paths, cpd_filenames, zf, "cpdprg", files_taken_from)
    add_files_to_zip(prosol_paths, prosol_filenames, zf, "prosols", files_taken_from)
    add_files_to_zip(va_paths, [str(GETPAR("VALIST").strip())], zf, "valist", files_taken_from)
    add_files_to_zip(vc_paths, [str(GETPAR("VCLIST").strip())], zf, "vclist", files_taken_from)
    add_files_to_zip(vd_paths, [str(GETPAR("VDLIST").strip())], zf, "vdlist", files_taken_from)
    add_files_to_zip(vp_paths, [str(GETPAR("VPLIST").strip())], zf, "vplist", files_taken_from)
    add_files_to_zip(vt_paths, [str(GETPAR("VTLIST").strip())], zf, "vtlist", files_taken_from)
    add_files_to_zip(fq_paths, fq_filenames, zf, "fqlists", files_taken_from)

    add_files_to_zip([data_dir], spnam_data_dir_filenames, zf, "spnam", files_taken_from, curr_dir=True)
    add_files_to_zip([data_dir], gpnam_data_dir_filenames, zf, "gpnam", files_taken_from, curr_dir=True)
    add_files_to_zip([data_dir], cpd_data_dir_filenames, zf, "cpdprg", files_taken_from, curr_dir=True)
    add_files_to_zip([data_dir], nus_data_dir_filenames, zf, "nus", files_taken_from, curr_dir=True)

    # Close the created zip file (IMPORTANT)
    zf.close()

    output_topspin = ""
    newline = '\n'
    output_topspin += "Python script run from:" + newline
    output_topspin += sys.argv[0] + newline
    output_topspin += "Input: pulseprogram taken from:" + newline
    output_topspin += pp_original_abs_path + newline
    output_topspin += "Output: pulseprogram annotated with parameters:" + newline
    output_topspin += pp_modified_path + os.sep + pp_modified_filename + newline
    output_topspin += newline

    output_topspin += "Files copied into zip directory:" + newline
    for i in files_taken_from:
        output_topspin += i[1] + newline
    output_topspin += newline
    output_topspin += "zipfile created:" + newline
    output_topspin += zipfile_path

    MSG(title=os.path.basename(sys.argv[0]), message=output_topspin)


if __name__ == '__main__':
    main()
