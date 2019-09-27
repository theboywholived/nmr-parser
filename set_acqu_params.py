import collections
import os, time
import sys

time_to_wait = 10  # set maximum time to check for file creation
time_counter = 0

# TODO
name_of_file = "/home/go/Pycharm/nmr-parser/pulseprogs"  # Name of the generated file

while not os.path.exists(name_of_file):
    time.sleep(1)
    time_counter += 1
    if time_counter > time_to_wait:
        raise Exception("Couldn't find file in the path")

with open(name_of_file, 'r') as pulseprogs_file:
    for i in pulseprogs_file.readlines():
        if i == ';' * 50:
            break



print(acqu_params_names)
acqu_params_with_values = collections.OrderedDict()  # dictionary to store acquisition parameters, names as keys and values as umm... values


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

#print(sp_str("<> <> <garp> <garp> <mlev> <mlev> <mlev> <mlev> <mlev>"))


def get_value(each_param):
    if '[' in each_param:
        # Get the name and array index of the parameter, array_parameter is in format, eg: "CONST[4]"
        head, sep, tail = each_param.partition('[')
        # MSG(tail.partition(']'))
        index = tail.partition(']')[0]

        arraystring = GETPAR(head)  # Format of returned string from bruker(arraystring) is, eg: "<> <> <3.5> <> <10>"

        return str(
            split_arraystring(arraystring)[int(index) - 1])  # Typecasting to Float is needed as each entry is a String
    else:
        return GETPAR(each_param)


for each_param in acqu_params_names:
    # To check for Array Parameters
    each_value = get_value(each_param)
    acqu_params_with_values[each_param] = each_value

section_1 = ""
try:
    with open(os.path.join(sys.path[0], "parameters_file.txt"), "r") as f:
        for count, each_line in enumerate(f):
            MSG(each_line)
            if each_line.strip() == ";" * 50:
                MSG('broke')
                break
            else:
                section_1 += each_line
except IOError:
    pass

section_2 = ""

for each_param, each_value in acqu_params_with_values.items():
    if each_value is None:
        section_2 += ";" + each_param + " = None" + "\n"
    else:
        section_2 += ";" + each_param + " = " + each_value + "\n"
# section_2 = section_2 + "\n" + f"; {each_param} = {each_value}"

with open(os.path.join(sys.path[0], "parameters_file.txt"), "w") as f:
    if section_1 != "":
        f.write(section_1)
        f.write("\n")
    f.write(";" * 50)
    f.write(";\n")
    f.write(section_2)
