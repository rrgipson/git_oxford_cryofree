from logger import *

def make_string1():
    return 'test1'

def make_string2():
    return 'test2'

print('testing error log')

test_log = LOGGER()
test_log.set_bg_file('test_bg_log.csv')
test_log.assign_field_log_fxns(get_mag_temp=make_string1,get_mag_field=make_string2)
test_log.generate_bg_log()

test_vtvh_log = LOGGER()
test_vtvh_log.set_log_file('test_vtvh_log.csv')
test_vtvh_log.set_dirpath('./UserLogs')
test_vtvh_log.generate_vtvh_log()
