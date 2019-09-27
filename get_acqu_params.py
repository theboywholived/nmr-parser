import collections
import os, time

# ASED()  # command to generate the format.ased file
import sys

time_to_wait = 10  # set maximum time to check for file creation
time_counter = 0

name_of_file = "/home/go/Pycharm/nmr-parser/format.ased"  # Name of the generated file

acqu_params_names = []  # list to store names of acquisition parameters

while not os.path.exists(name_of_file):
    time.sleep(1)
    time_counter += 1
    if time_counter > time_to_wait:
        raise Exception("Couldn't find file in the path")

with open(name_of_file) as ased_file:
    for line in ased_file.readlines():
        words = line.split()  # list of words of each line
        # print(words)
        if len(words) >= 2 and (str(words[0]) == 'NAME' or str(words[0]) == 'T_NAME'):
            acqu_params_names.append(words[1])

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


# print(sp_str("<> <> <garp> <garp> <mlev> <mlev> <mlev> <mlev> <mlev>"))
def parse_value_from_end(s):
    value = ""
    name = ""
    for i in reversed(s):
        if (not i.isdigit()):
            break
        value = i + value
    for i in s:
        if (i.isdigit()):
            break
        name += i
    return name, value


def get_value(each_param):
    if '[' in each_param:
        # Get the name and array index of the parameter, array_parameter is in format, eg: "CONST[4]"
        head, sep, tail = each_param.partition('[')
        # MSG(tail.partition(']'))
        index = tail.partition(']')[0]

        arraystring = GETPAR(head)  # Format of returned string from bruker(arraystring) is, eg: "<> <> <3.5> <> <10>"

        return str(
            split_arraystring(arraystring)[int(index) - 1])  # Typecasting to Float is needed as each entry is a String
    elif each_param[-1].isdigit():
        name, value = parse_value_from_end(each_param)
        if name == 'd' or name == 'in' or name == 'PLW' or name == 'PLdB':
            return "None"
        # MSG(name + " " + value)
        return GETPAR(value + " " + name)
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
            # MSG(each_line)
            if each_line.strip() == ";" * 50:
                # MSG('broke')
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
