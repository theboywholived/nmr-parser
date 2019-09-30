import re

file_path = "/home/go"
file_name = "/hsqcNwg.go"


dimension = [{}] * 8
independent_parameters = ['DS','NS', 'TD0', 'TDAV', 'INF', 'FW', 'RG', 'DW', 'DWOV', 'DECIM', 'DSPFIRM', 'DIGTYP', 'DIGMOD', 'DR', 'DDR', ]

def remove_duplicates(parameters_list):
    return list(set(parameters_list))


def clean_regex(parameters_list):
    for j in range(len(parameters_list)):
        parameters_list[j] = re.sub('[\W_]+', '', parameters_list[j])

    parameters_list = remove_duplicates(parameters_list)

    parameters_list.sort()
    return parameters_list


prefixes = {"p": r"[ (]p\d+",
            "sp": r"[:;=]sp\d+",
            "spnam": r"[ (:;=]spnam\d+",
            "spoffs": r"[ (:;=]spoffs\d+",
            "spoal": r"[ (:;=]spoal\d+",
            "spw": r"[ (:;=]spw\d+",
            "d": r"[:;=]d\d+",
            "cnst": r"cnst\d+"}

results = {}

with open(file_path + file_name) as pp:
    for i in pp:
        if len(str(i)) >= 1 and str(i)[0] != ';':
            for prefix in prefixes:
                results.setdefault(prefix, [])
                results[prefix] += re.findall(prefixes[prefix], i)

for k, v in results.items():
    results[k] = clean_regex(v)

print(results)
