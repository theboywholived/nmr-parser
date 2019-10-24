# PUTPAR('AQ_mod', 'qsim')
# MSG(GETPAR('DQDMODE'))
# MSG(GETPAR('CPDPRG'))
#
# Data directory, i.e, where the TopSpin working dataset is located
dd = CURDATA()

# Calculating the data directory
data_dir = dd[3] + '/' + dd[0] + '/' + dd[1]
MSG(data_dir)