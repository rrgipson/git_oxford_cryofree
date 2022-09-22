'''Commands for contolling the logging of data during connection to the Cryfree System
Will hopefully eventually include both background logging always happening
as well as logging notes during scan collection'''

import os
from time import sleep
from threading import Thread
import csv
import datetime
import builtins

#redefined the print function in order to log errors in error_log.txt
def print(*args, sep=' ', end='\n',**kwargs):
    builtins.print(*args, sep=sep, end=end,**kwargs)
    with open('error_log.txt', 'a+') as f:
        for s in args:
            f.write(str(s))
            f.write(sep)
        f.write(end)
        

class LOGGER:
    def __init__(self):
        #things for background logging 
        self.bg_file = 'background_log.csv'
        self.bg_log_delay = 30 #minutes
        
        self.log_file = 'current_log.csv'
        
        #functions to get data
        self.get_mag_temp = None
        self.get_mag_field = None
        #self.get_mag_examine = None
        self.get_vti_temp = None
        self.get_nv_pressure = None
        self.get_sample_temp = None
        #self.get_temp_error = None #difference between setpoint and measured (+ when set>actual)
        #self.get_heater_output = None

    def set_bg_file(self, newfile): #this is primarily for testing
        self.bg_file = newfile
        
    def set_log_file(self, newfile):
        self.log_file = newfile
    
    def assign_field_log_fxns(self, get_mag_temp=None, get_mag_field=None):
        self.get_mag_temp = get_mag_temp
        self.get_mag_field = get_mag_field
        #self.get_mag_examine = None

        
    def assign_temp_log_fxns(self, get_vti_temp=None, get_sample_temp=None, get_nv_pressure=None):
        self.get_vti_temp = get_vti_temp
        self.get_nv_pressure = get_nv_pressure
        self.get_sample_temp = get_sample_temp
        #self.get_temp_error = get_temp_error #difference between setpoint and measured (+ when set>actual)
        #self.get_heater_output = None
        
    def format_for_csv(self, item_list):
        line = ','.join(str(i) for i in item_list)
        line = line+'\n'
        return line
        
    def send_to_file(self,logfile=None,data=None,header=None):
        f_head=None
        #check if file exists
        if os.path.exists(logfile):
            #open file to read
            with open(logfile, 'r') as f:
                #check if correct header present
                f_head=f.readline()
        
        #open to append only
        f = open(logfile, 'a+')
        #if no header, add it
        if f_head != header:
            f.write(header)
        
        #add data
        f.write(data)
        #close file
        f.close()
                     
    def generate_bg_log(self):
        #add correct things
        #waiting happens in main
        #create dict of data to log
        log_data={}
        log_data['Date']=datetime.datetime.now()
        
        log_fxns={}
        log_fxns['Magnet_Temp']=self.get_mag_temp
        log_fxns['Magnet_Field']=self.get_mag_field
        
        log_fxns['VTI_Temp'] = self.get_vti_temp
        log_fxns['Sample_Temp'] = self.get_sample_temp
        log_fxns['NV_pressure'] = self.get_nv_pressure
        #log_fxns['Temp_Error'] = self.get_temp_error
        
        for k in log_fxns.keys():
            if log_fxns[k] == None:
                log_data[k] = None
            else:
                log_data[k] = log_fxns[k]()
        
        #parse dict into list of keys (for header) and data
        head_list, data_list = zip(*log_data.items())
        
        #convert each to csv format
        header= self.format_for_csv(head_list)
        data= self.format_for_csv(data_list)
        
        #send dict and file to send_to_file
        self.send_to_file(logfile=self.bg_file, data=data, header=header)
        print('Finished Background Log Update')
        
    def generate_vtvh_log(self, scan_num=None):
        #add correct things
        #waiting happens in main
        #create dict of data to log
        log_data={}
        log_data['Date']=datetime.datetime.now()
        log_data['Scan_Num']= scan_num
        
        #setup functions that get other data parameters
        log_fxns={}
        log_fxns['Magnet_Temp']=self.get_mag_temp
        log_fxns['Magnet_Field']=self.get_mag_field
        
        log_fxns['VTI_Temp'] = self.get_vti_temp
        log_fxns['NV_pressure'] = self.get_nv_pressure
        log_fxns['Sample_Temp'] = self.get_sample_temp
        #log_fxns['Temp_Error'] = self.get_temp_error
        
        for k in log_fxns.keys():
            if log_fxns[k] == None:
                log_data[k] = None
            else:
                get_func=log_fxns[k]
                log_data[k] = get_func()
        
        #parse dict into list of keys (for header) and data
        head_list, data_list = zip(*log_data.items())
        
        #convert each to csv format
        header= self.format_for_csv(head_list)
        data= self.format_for_csv(data_list)
        
        #send dict and file to send_to_file
        self.send_to_file(logfile=self.log_file, data=data, header=header)
        print('Logged VTVH Data for Scan', scan_num, 'to', self.log_file)
