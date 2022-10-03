from logger import *

def make_string1():
    return 'test1'

def make_string2():
    return 'test2'

test_log = LOGGER()
test_log.set_bg_file('test_bg_log.csv')
test_log.assign_field_log_fxns(get_mag_temp=make_string1,get_mag_field=make_string2)
test_log.generate_bg_log()