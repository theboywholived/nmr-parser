# coding=utf-8
import os
import sys
import warnings
# Execute the parser.py library for
parser_file = open(os.path.join(os.path.dirname(sys.argv[0]), 'parser.py'))
exec (parser_file.read())
parser_file.close()

config_filename = "parfile-dirs.prop"
pcal_dir = os.path.dirname(sys.argv[0])
pcal_filename = "pulsecalibration"
probhd_conf_filename = "probehead"

# Current working directory for python files in Bruker TopSpin
# In topspin3.5pl7, it's '/opt/topspin3.5pl7/prog/curdir/go'
# This path is later used to calculate other topspin paths
py_working_dir = os.popen('pwd').read().strip()
# Data directory, i.e, where the TopSpin working dataset is located, in topspin format
dd = CURDATA()
# Calculating the data directory
data_dir = os.path.join(dd[3], dd[0], dd[1])
pp_filename = str(GETPAR('PULPROG')).strip()
nmr_wd = os.path.join(py_working_dir[:py_working_dir.find(os.path.join("/", "prog", "curdir"))], "exp", "stan", "nmr")
probhd_dir = os.path.join(py_working_dir[:py_working_dir.find(os.path.join("/", "prog", "curdir"))], "conf", "instr")

prosol_path = os.path.join("lists", "prosol", "pulseassign")
prosol_paths = [prosol_path]
max_channels_possible = 8


def read_file(dir, names, nucleus_channel_map):
    """
    Reads the pcal file and returns the values of the parameters in the file
    :param dir: Directory for the file to be read
    :param names: Names of the possible files to be read
    :param nucleus_channel_map: Map of nucleus to channel number
    :return:
    values_in_file: Channel mapped to a list of Nucleus, Pulse Length and Hard Pulse Power, in that order
    """

    values_in_file = {}
    filename = None
    abs_path = None
    for i in names:
        if os.path.isfile(os.path.join(dir, i)):
            abs_path = os.path.join(dir, i)
            filename = i
            break

    if not abs_path:
        raise IOError("Couldn't find pulsecalibration file.")
    try:
        f = open(os.path.join(dir, i), 'r')
        for i in f:
            i = i.strip()
            s = i.split()
            if len(s) != 3 and len(s) != '':
                raise IOError("Please rewrite the file: " + os.path.join(dir, i))
            nuc = s[0].upper()
            p = s[1]
            plw = s[2]
            try:
                channel = nucleus_channel_map[nuc]
            except IndexError:
                raise Exception("Couldn't find the channel for the nucleus: " + nuc)
            values_in_file[channel] = []
            # values_in_file[channel].append(list(map_p[channel])[0])
            # values_in_file[channel].append(list(map_pl[channel])[0])
            values_in_file[channel].append(nuc)
            values_in_file[channel].append(p)
            values_in_file[channel].append(plw)
        f.close()
    except IOError:
        raise IOError("Couldn't read file: " + abs_path)
    # MSG(values_in_file)
    return values_in_file, filename


def write_file(dir, name, values_dict):
    """

    :param dir: Directory for the file to be written
    :param name: Name of the file to be written
    :param values_dict:
    """
    abs_path = os.path.join(dir, name)
    try:
        f = open(abs_path, 'w')
        for i in range(1, max_channels_possible + 1):
            if i in values_dict:
                try:
                    f.write(values_dict[i][0] + " " + values_dict[i][1] + " " + values_dict[i][2])
                    f.write('\n')
                except IndexError:
                    raise IndexError("Error with storing the values of parameters")
    except IOError:
        raise IOError("Couldn't create: " + abs_path)


def get_probehead_name(dir, name):
    """

    :param dir: Directory for the configuration file for the probehead
    :param name: Name for the configuration file
    :return: Probehead name
    """
    abs_path = os.path.join(dir, name)
    try:
        f = open(abs_path, 'r')
        s = f.readline()
        f.close()
    except IOError:
        warnings.warn("Couldn't find: " + abs_path)
        return None
    return s


def main():
    global pcal_filename
    nucleus_channel_map = {}
    for i in range(max_channels_possible):
        j = GETPAR("NUC" + str(i + 1))
        if j != "off":
            nucleus_channel_map[j] = i + 1

    p = Parser(py_working_dir, pp_filename)
    pp_paths = p.get_path_list("PP_DIRS", config_filename)
    d = {(pp_filename,): pp_paths}
    _, _, pulse_parameters, _, prosol_filenames, pp_map_pl = p.parse_pp_cpd(
        d, pcal=True)
    prosol_map_p, prosol_map_pl = p.parse_prosol(prosol_filenames[0], os.path.join(nmr_wd, prosol_path))

    map_p = {}
    map_pl = {}

    for key in nucleus_channel_map:
        channel_num = nucleus_channel_map[key]

        if channel_num in pp_map_pl and channel_num in prosol_map_pl:
            if pp_map_pl[channel_num].intersection(prosol_map_pl[channel_num]):
                map_pl[channel_num] = pp_map_pl[channel_num].intersection(prosol_map_pl[channel_num])
                # MSG('PL' + str(channel_num) + " " + str(map_pl[channel_num]))

        if channel_num in prosol_map_p:
            if prosol_map_p[channel_num].intersection(pulse_parameters['p']):
                map_p[channel_num] = prosol_map_p[channel_num].intersection(pulse_parameters['p'])
                # MSG('P' + str(channel_num) + " " + str(map_p[channel_num]))
    # MSG(str(map_pl))
    # MSG(str(map_p))
    possible_names = []
    if get_probehead_name(probhd_dir, probhd_conf_filename):
        s = get_probehead_name(probhd_dir, probhd_conf_filename)
        s = s.replace('/', ' ')
        pcal_filename_with_probhd = "_".join(s.split()) + '_' + pcal_filename
        possible_names += [pcal_filename_with_probhd]
    possible_names += [pcal_filename]

    if len(sys.argv) == 1:
        values_in_file, _ = read_file(pcal_dir, possible_names, nucleus_channel_map)
        MSG(str(values_in_file))
        labels = []
        default_values = []

        for i in range(1, max_channels_possible + 1):
            if i in values_in_file:
                if len(values_in_file[i]) != 3:
                    raise IOError("Please check pcal values and formatting in: " + pcal_filename)
                labels.append(str(values_in_file[i][0]) + "  P" + str(list(map_p[i])[0]))
                default_values.append(values_in_file[i][1])
                labels.append(str(values_in_file[i][0]) + "  PLdB" + str(list(map_pl[i])[0]))
                default_values.append(values_in_file[i][2])

        values_by_user = INPUT_DIALOG(title="Enter pulsecal values",
                                      header="",
                                      items=labels,
                                      values=default_values,
                                      columns=6
                                      )

        current = 0
        if values_by_user:
            for i in range(1, max_channels_possible + 1):
                if i in values_in_file:
                    # MSG("P " + str(values_in_file[i][0]) + "   " + values_by_user[current])
                    PUTPAR("P " + str(list(map_p[i])[0]), values_by_user[current])
                    current += 1
                    # MSG("PLdB " + str(i) + "   " + values_by_user[current])
                    PUTPAR("PLdB " + str(list(map_pl[i])[0]), values_by_user[current])
                    current += 1
            MSG("pcal values set")
        else:
            MSG("pcal values not set")
    elif len(sys.argv) >= 3 and sys.argv[1] == "store":
        nuc = sys.argv[2].upper()
        values_to_write = {}
        try:
            values_in_file, fn = read_file(pcal_dir, possible_names, nucleus_channel_map)
            values_to_write = values_in_file
        except IOError:
            pass
        try:
            channel = nucleus_channel_map[nuc]
            values_for_channel = [nuc, GETPAR("P " + str((list(map_p[channel]))[0])),
                                  GETPAR("PLdB " + str(list(map_pl[channel])[0]))]
            values_to_write[channel] = values_for_channel
            write_file(pcal_dir, possible_names[0], values_to_write)
        except KeyError:
            MSG("Couldn't find channel for " + nuc + ".\nNo Changes made.")


if __name__ == '__main__':
    main()
