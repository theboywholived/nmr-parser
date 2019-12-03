import os
import re


class Parser(object):
    def __init__(self, py_working_dir, pp_filename):
        self.py_working_dir = py_working_dir
        self.pp_filename = pp_filename

    @staticmethod
    def __remove_empty_elements(dict):
        for i in dict.copy():
            if not dict.copy()[i]:
                dict.pop(i)

    def parse_pp_cpd(self, names_paths, pcal=False):
        """
        Parses the pulseprogram, cpdprg files to output the original pulseprog, relevant parameters and required filenames
        :param names_paths: Dictionary of tuple of names of files as keys and list of possible paths as values
        :return:
        pp_orig: a list of all the lines in the original pulseprogram,
        parsed_pulse_parameters: Dictionary containing the names and indices of the pulse parameters
        include_filenames: Names of the filenames included in the pulseprogram
        prosol_filenames: Names of the filenames included in the pulseprogram
        """
        pattern_pl = ""
        map_pl = {}
        # Regular expression patterns for all parameters in pulseprogram
        _prefixes = {"p": r"[^sg]p(\d+)",
                     "sp": r"sp(\d+)",
                     "pl": r"pl(\d+)",
                     "gp": r"gp(\d+)",
                     "d": r"[^a-z]d(\d+)",
                     "cnst": r"cnst(\d+)",
                     "cpd": r"[^p]cpds?(\d+)",
                     "l": r"[^p]l(\d+)",
                     "pcpd": r"pcpd(\d+)",
                     }
        if pcal:
            pattern_pl = "pl(\d+):f(\d+)"

        _working_dir = os.path.join(self.py_working_dir[:self.py_working_dir.find(os.sep + "prog" + os.sep + "curdir")],
                                    "exp", "stan", "nmr")
        _raw_pulse_parameters = {}
        # Raw Pulse Parameters, eg: {'cnst': ['cnst10', 'cnst4'], 'd': ['d26'], 'gp': ['gp1', 'gp2'], ...}
        # Parsed Pulse Parameters, eg: {'cnst': [4, 10], 'd': [26], 'gp': [1, 2], ...}
        parsed_pulse_parameters = {}
        include_filenames = []
        prosol_filenames = []
        pp_orig = []  # Stores the original pulse program

        _declared_parameters = {}
        # Navigates in each path for the pulse program, finds the first one which contains pp_filename. Iterates line
        # by line, storing the original pulse program and matching the prefixes to find the pulse parameters in use.
        # Stores the pulse parameters in _raw_pulse_parameters
        pp_abs_path = ""
        for names in names_paths:
            for name in names:
                for fp in names_paths[names]:
                    # MSG(name + " " + fp)
                    _abs_path = ((_working_dir + os.sep) if not os.path.isabs(fp) else '') + fp + os.sep + name
                    if os.path.exists(_abs_path):
                        f = open(_abs_path)
                        for i in f:
                            if name == self.pp_filename:
                                pp_abs_path = _abs_path
                                pp_orig += [i]
                            if i.startswith('\"'):
                                i = i.split('=', 1)[0]
                                for prefix in _prefixes:
                                    if re.findall(_prefixes[prefix], i):
                                        _declared_parameters.setdefault(prefix, set([]))
                                        _declared_parameters[prefix] = _declared_parameters[prefix].union(
                                            [int(x) for x in re.findall(_prefixes[prefix], i)])
                                        # print(set(re.findall(_prefixes[prefix], i)))
                                continue
                            try:
                                i = i.split(';', 1)[0]  # Ignores comments
                                for prefix in _prefixes:
                                    if re.findall(_prefixes[prefix], i):
                                        _raw_pulse_parameters.setdefault(prefix, set([]))
                                        _raw_pulse_parameters[prefix] = _raw_pulse_parameters[prefix].union(
                                            [int(x) for x in re.findall(_prefixes[prefix], i)])
                                if pcal:
                                    # MSG("YES")
                                    l = re.findall(pattern_pl, i)
                                    for tup in l:
                                        pp_pl = int(tup[0])
                                        pp_f = int(tup[1])
                                        map_pl.setdefault(pp_f, set([]))
                                        map_pl[pp_f] = map_pl[pp_f].union({pp_pl})
                                # Get the names of the include and prosol files
                            except IndexError:
                                raise Exception("Couldn't parse " + name)
                            try:
                                if str(i).startswith("#include"):
                                    _filename = (str(i).split('<')[1]).split('>')[0]
                                    include_filenames.append(_filename)
                                elif str(i).startswith("prosol"):
                                    _filename = (str(i).split('<')[1]).split('>')[0]
                                    prosol_filenames.append(_filename)
                            except IndexError:
                                raise Exception("Couldn't parse include/prosol fields")

                        f.close()
                        break
        if len(pp_orig) == 0:
            raise IOError("Couldn't find the Pulse Program")
        parsed_pulse_parameters = _raw_pulse_parameters
        for key in _declared_parameters:
            if key in parsed_pulse_parameters:
                for i in _declared_parameters[key]:
                    if i in parsed_pulse_parameters[key]:
                        parsed_pulse_parameters[key].remove(i)
        self.__remove_empty_elements(parsed_pulse_parameters)

        # MSG("parsed after" + str(parsed_pulse_parameters))
        # MSG(str(map_pl))
        return pp_orig, pp_abs_path, parsed_pulse_parameters, include_filenames, prosol_filenames, map_pl

    def parse_prosol(self, name, path):
        """

        :param self:
        :param name:
        :param path:
        :return:
        """
        abs_path = os.path.join(path, name)
        pattern_p = r"P\[(\d+)\]=PW90;(\d+)"
        pattern_pl = r"PLW\[(\d+)\]=PL90;(\d+)"
        channel_p = {}
        channel_pl = {}
        try:
            f = open(abs_path, 'r')
            content = f.read()
            match_p = re.findall(pattern_p, content)
            match_pl = re.findall(pattern_pl, content)
        except IOError:
            raise IOError("Couldn't open:" + abs_path)
        f.close()

        for i in match_p:
            channel_p.setdefault(int(i[1]), set([]))
            channel_p[int(i[1])] = channel_p[int(i[1])].union({int(i[0])})
        for i in match_pl:
            channel_pl.setdefault(int(i[1]), set([]))
            channel_pl[int(i[1])] = channel_pl[int(i[1])].union({int(i[0])})

        return channel_p, channel_pl

    def get_path_list(self, pattern, config_filename):
        """
        Gets list of paths (in priority order) for pulse program and useful parameter files from the Bruker configuration
        file,"parfile-dirs.prop" located in the Python working directory
        :param pattern: heading under which it is stored in the Bruker configuration file
        :return: list of paths for the pattern
        """
        filepaths = []

        try:
            f = open(config_filename, 'r')
            for i in f:
                if pattern in i:
                    filepaths += i[(len(pattern) + 1):].strip().split(';')
            f.close()

        except FileNotFoundError:
            raise FileNotFoundError("Couldn't find parfile-dirs.prop in /topspin.../prog/curdir/go/")
        except IndexError:
            raise IndexError("Couldn't parse paths from parfile-dirs.prop file. Please correct the file.")
        return filepaths
