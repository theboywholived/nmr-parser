# # PUTPAR('AQ_mod', 'qsim')
# # MSG(GETPAR("L 2"))
# dd = CURDATA()
#
# # Calculating the data directory
# MSG(str(dd))
# # import os
# MSG(os.sep)
# PUTPAR("1 TD", 1254)
#
# Data directory, i.e, where the TopSpin working dataset is located
# dd = CURDATA()
#
# # Calculating the data directory
# data_dir = dd[3] + '/' + dd[0] + '/' + dd[1]
# MSG(data_dir)
#MSG(GETPAR("VCLIST"))

# def get_matching_filenames(pattern, path):
#     names = []
#     for root, dirs, files in os.walk(path):
#         for name in files:
#             if fnmatch.fnmatch(name, pattern):
#                 names.append(name)3
#     return names
#

# (PUTPAR("P 21", "2"))
MSG(GETPAR("PROBHD"))
# PUTPAR("1 FnMODE", "QSEQ")