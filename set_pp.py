import collections
from sys import stdout
from time import sleep

dd = CURDATA()

# Data Directory, i.e, where the working dataset is located
# Calculate the data directory path
dd = dd[3] + '/' + dd[0] + '/' + dd[1]

# dd = '/home/go/Downloads/vedant/1'
result = collections.OrderedDict()
try:
    with open(dd + '/' + "pp_modified.txt", 'r') as f:

        for i in f:
            if i == (';' * 25) + '\n':
                break
        for i in f:
            if i == ';***Axis Parameters***\n':
                continue
            each_line = i.strip()
            each_line = each_line.split(';')[1]
            result[each_line.split('=')[0]] = each_line.split('=')[1]
except IOError:
    raise Exception("Couldn't Find/Open the modified pulse program")
stdout.flush()

# print(result)
# MSG("Setting Parameters")
for key, value in result.items():
        PUTPAR(key, value)


