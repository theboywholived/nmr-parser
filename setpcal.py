# coding=utf-8
import os
import sys
module_path = os.path.join(os.path.dirname(sys.argv[0]), 'parser.py')

if module_path not in sys.path:
    sys.path.append(module_path)
from parser import Parser

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

prosol_path = os.path.join("lists", "prosol", "pulseassign")
prosol_paths = [prosol_path]


nuclear_status_list = {}
for i in range(8):
    j = GETPAR("NUC" + str(i + 1))
    if j != "off":
        nuclear_status_list[j] = i + 1

p = Parser(py_working_dir, pp_filename)
pp_paths = p.get_path_list("PP_DIRS", config_filename)
d = {(pp_filename,): pp_paths}
_, _, pulse_parameters, _, prosol_filenames, pp_map_pl = p.parse_pp_cpd(
    d, pcal = True)
prosol_map_p, prosol_map_pl = p.parse_prosol(prosol_filenames[0], prosol_path)

map_p = {}
map_pl = {}

for i in pp_map_pl:
    if i in prosol_map_pl:
        if pp_map_pl[i].union(prosol_map_pl[i]):
            map_pl[i] = pp_map_pl[i].union(prosol_map_pl[i])

for i in prosol_map_p:
    if prosol_map_p[i].union(pulse_parameters['p']):
        map_p[p] = prosol_map_p[i].union(pulse_parameters['p'])

result_in_file = {}
pcal_filename = "p_calib.txt"
try:
    f = open(os.path.join(data_dir, pcal_filename), 'r')
    for i in f:
        i = i.strip()
        s = i.split()
        if len(s) != 3 and len(s) != '':
            raise IOError("Please rewrite the file: " + pcal_filename)
        nuc = s[0].upper()
        p = s[1]
        plw = s[2]
        try:
            channel = nuclear_status_list[nuc]
        except IndexError:
            raise Exception("Couldn't find the channel for the nucleus: " + nuc)
        result_in_file[channel] = []
        result_in_file[channel].append(map_p[channel])
        result_in_file[channel].append(map_pl[channel])
        result_in_file[channel].append(nuc)
        result_in_file[channel].append(p)
        result_in_file[channel].append(plw)

except IOError:
    raise IOError("Couldn't read file: " + pcal_filename)
f.close()

max_channels_possible = 8
labels = []
default_values = []



for i in range(1, max_channels_possible + 1):
    if i in result_in_file:
        if len(result_in_file[i]) != 5:
            raise IOError("Please check pcal values and formatting in: " + pcal_filename)
        labels.append("P " + str(result_in_file[i][0]))
        default_values.append(result_in_file[i][3])
        labels.append("PLdB " + str(i) + result_in_file[i][1])
        default_values.append(result_in_file[i][4])

values_by_user = INPUT_DIALOG(title="Enter pulsecal values",
                              header="",
                              items=labels,
                              values=default_values,
                              columns=6
                              )
# MSG(str(values_by_user))

current = 0
if values_by_user:
    for i in range(1, max_channels_possible + 1):
        if i in result_in_file:
            # MSG("P " + str(result_in_file[i][0]) + "   " + values_by_user[current])
            PUTPAR("P " + str(result_in_file[i][0]), values_by_user[current])
            current += 1
            # MSG("PLdB " + str(i) + "   " + values_by_user[current])
            PUTPAR("PLdB " + str(i), values_by_user[current])
            current += 1
else:
    MSG("pcal values not set")

