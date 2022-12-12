'''Commands for contolling the logging of data during connection to the Cryfree System
Will hopefully eventually include both background logging always happening
as well as logging notes during scan collection'''

import os
import sys
from time import sleep
from threading import Thread
import csv
import datetime
import builtins
from tkinter import filedialog

#redefined the print function in order to log errors in error_log.txt
def print(*args, sep=' ', end='\n',**kwargs):
    builtins.print(*args, sep=sep, end=end,**kwargs)
    with open('UserLogs/error_log.txt', 'a+') as f:
        for s in args:
            f.write(str(s))
            f.write(sep)
        f.write(end)

def print_to_log(string):
    with open('UserLogs/error_log.txt', 'a+') as f:
        f.write(string + '\n')

class LOGGER:
    def __init__(self):
        #things for background logging 
        self.bg_file = 'background_log.csv'
        self.bg_log_delay = 120 #minutes
        
        self.log_file = 'current_log.csv'
        
        #functions to get data
        self.get_mag_temp = None
        self.get_mag_field = None
        self.get_field_set = None
        #self.get_mag_examine = None
        self.get_vti_temp = None
        self.get_sample_temp = None
        self.get_pt2_temp = None
        self.get_nv_pressure = None
        self.get_nv_percent = None
        self.get_temp_set = None
        #self.get_heater_output = None
        
        #where are the jasco files autosaving
        self.dirpath = None

    def set_bg_file(self, newfile): #this is primarily for testing
        self.bg_file = newfile
        
    def set_log_file(self, newfile):
        self.log_file = newfile
        
    def set_dirpath(self, path):
        self.dirpath = path
    
    def assign_field_log_fxns(self, get_mag_temp=None, get_mag_field=None, get_field_set=None):
        self.get_mag_temp = get_mag_temp
        self.get_mag_field = get_mag_field
        self.get_field_set = get_field_set
        #self.get_mag_examine = None

        
    def assign_temp_log_fxns(self, get_vti_temp=None, get_sample_temp=None, get_pt2_temp=None, 
                             get_nv_pressure=None, get_nv_percent=None, get_temp_set=None):
        self.get_vti_temp = get_vti_temp
        self.get_sample_temp = get_sample_temp
        self.get_pt2_temp = get_pt2_temp
        self.get_nv_pressure = get_nv_pressure
        self.get_nv_percent = get_nv_percent
        self.get_temp_set = get_temp_set
        #self.get_heater_output = None
        
    def format_for_csv(self, item_list):
        line = ','.join(str(i) for i in item_list)
        line = line+'\n'
        return line
        
    def send_to_file(self,logfile=None,data=None,header=None):
        f_head=None
        #check if file exists
        if os.path.exists(logfile):
            headnext=True
            #open file to read
            with open(logfile, 'r') as f:
                #check if correct header present as most recent header
                for line in f:
                    if headnext==True:
                        f_head=line
                        headnext=False
                    if line=='\n':
                        headnext=True
        
        #open log file to append
        try:
            f = open(logfile, 'a+') #open to append only
        #if don't have permission (open already by user), try open a "new" file
        except PermissionError:
            print('Please close the log file.')
            logfile=logfile.replace('.','_new.')
            f = open(logfile, 'a+')
            print('Wrote to %s instead (you may want to merge later)'%logfile)
        
        #if no header, add it
        if f_head != header:
            f.write('\n')
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
        log_fxns['Magnet_Temp(K)']=self.get_mag_temp
        log_fxns['Magnet_Field(T)']=self.get_mag_field
        log_fxns['Field_SetPoint(T)']=self.get_field_set
        
        log_fxns['Sample_Temp(K)']=self.get_sample_temp
        log_fxns['VTI_Temp(K)']=self.get_vti_temp
        log_fxns['PT2_Temp(K)']=self.get_pt2_temp
        log_fxns['NV_Pressure(mB)']=self.get_nv_pressure
        log_fxns['NV_Percent']=self.get_nv_percent
        log_fxns['SampleTemp_SetPt(K)']=self.get_temp_set
        
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
        
    def generate_vtvh_log(self, scan_num=None, after=False, extras=None):
        #add correct things
        #waiting happens in main
        #create dict of data to log
        log_data={}
        log_data['Date']=datetime.datetime.now()
        log_data['Scan_Num']= scan_num
        
        #setup functions that get other data parameters
        log_fxns={}
        log_fxns['Magnet_Temp(K)']=self.get_mag_temp
        #log_fxns['Magnet_Field(T)']=self.get_mag_field
        log_fxns['Field_SetPoint(T)']=self.get_field_set
        
        #log_fxns['Sample_Temp(K)']=self.get_sample_temp
        log_fxns['VTI_Temp(K)']=self.get_vti_temp
        log_fxns['NV_Pressure(mB)']=self.get_nv_pressure
        log_fxns['SampleTemp_SetPt(K)']=self.get_temp_set
        
        
        for k in log_fxns.keys():
            if log_fxns[k] == None:
                log_data[k] = None
            else:
                get_func=log_fxns[k]
                log_data[k] = get_func()
        
        if extras is not None:
            log_data = log_data | extras #merge the two dicts
        
        #say what file the scan is saved to
        if after == True:
            log_data['File']=self.get_newest_file(self.dirpath)
        else:
            log_data['File']=None
        
        #parse dict into list of keys (for header) and data
        head_list, data_list = zip(*log_data.items())
        
        #convert each to csv format
        header= self.format_for_csv(head_list)
        data= self.format_for_csv(data_list)
        
        #send dict and file to send_to_file
        self.send_to_file(logfile=self.log_file, data=data, header=header)
        print('Logged VTVH Data for Scan', scan_num, 'to', self.log_file)
        
    def get_newest_file(self, dirpath):
        if dirpath == None or (not os.path.exists(dirpath)) or len(os.listdir(dirpath))==0:
            return None
        else:
            files = os.listdir(dirpath)
            paths = [os.path.join(dirpath, basename) for basename in files]
            newest = max(paths, key=os.path.getctime)
            return newest.replace(dirpath, '').replace('\\','')
            
