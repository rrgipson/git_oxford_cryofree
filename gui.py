import tkinter as tk
from tkinter import filedialog
from tkinter import messagebox

# Settings flags for magnet controller
SWITCH_ENABLED = 'enabled'
SWITCH_WARMING = 'warming'
SWITCH_COOLING = 'cooling'
SWITCH_DISABLED = 'disabled'
FIELD_HOLD = 'hold'
FIELD_GOTO = 'goto'
FIELD_ZERO = 'zero'
FIELD_INACTIVE = 'inactive'
SETPOINT_ACTIVE = 'active'
SETPOINT_INACTIVE = 'inactive'
##New Cryofree Statuses
REFRESHING= 'refreshing'
NOT_REFRESHING = 'not_refreshing'
VTVH_ACTIVE = 'active'
VTVH_INACTIVE = 'inactive'
ACTIVE = 'active'
INACTIVE = 'inactive'
ISOTHERM_DEFAULTS=[0,7,0,-7,0]
TEMP_DEFAULTS=[2,5,10,15,25]

class GUI(tk.Frame):
    def __init__(self, master=tk.Tk()):
        super().__init__(master)
        master.title('Solomon Group Oxford Control Panel')
        master.resizable(False, False)
        self.master = master
        self.pack()

        # Make function identifiers
        self.func_serial_connect = None
        self.func_serial_disconnect = None
        self.func_set_temperature = None
        self.func_get_temperature = None
        self.func_engage_switch_heater = None
        self.func_disengage_switch_heater = None
        self.func_goto_field = None
        self.func_zero_field = None
        self.func_interrupt = None
        self.func_set_field = None
        self.func_get_field = None
        self.func_refresh = None 
        self.func_vtvh = None
        self.func_vtvh_interrupt = None
        self.func_set_nv = None
        self.func_vtvh_browse = self.browse_for_dir
        #set one variable for browse folder
        self.path_vtvh_browse = None
        #container variable for vtvh grids
        self.vtvh_grids_temps = []
        self.vtvh_grids_fields = []

        # Make container frames
        self.frm_connection = tk.Frame(self)
        self.frm_temp_mag = tk.Frame(self)
        
        self.frm_temp_sensor = tk.Frame(self.frm_temp_mag)
        self.frm_temp_setpoint = tk.Frame(self.frm_temp_mag)
        
        self.frm_temp_sensor.grid(row=0, column=0, sticky=tk.N, padx=3)
        self.frm_temp_setpoint.grid(row=1, column=0, sticky=tk.N, padx=3)
        
        self.frm_mag_sensor = tk.Frame(self.frm_temp_mag)
        self.frm_mag_setpoint = tk.Frame(self.frm_temp_mag)
        
        self.frm_mag_sensor.grid(row=0, column=1, sticky=tk.N, padx=3)
        self.frm_mag_setpoint.grid(row=1, column=1, sticky=tk.N, padx=3)
        
        self.frm_connection.grid(row=0, column=0, sticky=tk.N, padx=3)
        self.frm_temp_mag.grid(row=0, column=1, sticky=tk.N, padx=3)
        
        input_font = 'Arial 48'
        med_font = 'Arial 24'
        small_font = 'Arial 10'

        # Connection frame
        self.lbl_com_port = tk.Label(self.frm_connection, text='2COM Port Connection:')
        #self.ent_com_port = tk.Entry(self.frm_connection, fg='red', bg='black', insertbackground='white',
        #                             font=input_font, width=8, disabledforeground='black', disabledbackground='white',
        #                             justify='center')
        self.btn_com_port = tk.Button(self.frm_connection, text='Connect', font='Arial 18')
        #self.ent_com_port.insert(tk.END, '—')
        self.lbl_com_port.grid(row=0)
        #self.ent_com_port.grid(row=1)
        self.btn_com_port.grid(row=1)
        
        #New for CRYOFREE Frame
        self.frm_cryofree=tk.Frame(self.frm_connection)
        self.frm_cryofree.grid(row=2,column=0, sticky=tk.N, padx=3, pady=(10,3))
        self.lbl_cryofree = tk.Label(self.frm_cryofree, text='Additions for Cryofree System:')
        self.lbl_cryofree.grid(row=0)
        #refresh button - added for CYROFREE
        self.btn_refresh = tk.Button(self.frm_cryofree, text='Refresh (Magnet Only)', state='disabled')
        self.btn_refresh.grid(row=1)
        #Quick Cooldown button
        self.btn_qkcool = tk.Button(self.frm_cryofree, text='Quick Cooldown', state='disabled')
        self.btn_qkcool.grid(row=2)
        #VTVH/isotherm entry and button
        self.frm_vtvh=tk.Frame(self.frm_cryofree)
        self.frm_vtvh.grid(row=3, column=0, sticky=tk.N, padx=3, pady=10)
        self.lbl_vtvh=tk.Label(self.frm_vtvh, text='VTVH', font=med_font+' underline')
        self.lbl_vtvh.grid(row=0)
        self.lbl_vtvh_fields=tk.Label(self.frm_vtvh, text='Fields for VTVH (T)')
        self.lbl_vtvh_fields.grid(row=1)
        self.ent_vtvh_field = tk.Entry(self.frm_vtvh, fg='white', bg='black', insertbackground='white',
                                        font=small_font, width=36, disabledforeground='black',
                                        disabledbackground='white', justify='center')
        self.ent_vtvh_field.grid(row=2)
        self.ent_vtvh_field.insert(tk.END, ','.join(map(str,ISOTHERM_DEFAULTS)))
        self.ent_vtvh_field['state'] = 'disabled'
        
        self.lbl_vtvh_temps=tk.Label(self.frm_vtvh, text='Temps for VTVH (K)')
        self.lbl_vtvh_temps.grid(row=3)
        self.ent_vtvh_temps = tk.Entry(self.frm_vtvh, fg='white', bg='black', insertbackground='white',
                                        font=small_font, width=36, disabledforeground='black',
                                        disabledbackground='white', justify='center')
        self.ent_vtvh_temps.grid(row=4)
        self.ent_vtvh_temps.insert(tk.END, ','.join(map(str,TEMP_DEFAULTS)))
        self.ent_vtvh_temps['state'] = 'disabled'
        
        #uncomment below for new grids queue setup
        self.frm_vtvh_btns=tk.Frame(self.frm_vtvh)
        self.frm_vtvh_btns.grid(row=5, column=0, sticky=tk.N, padx=3, pady=3)
        self.btn_vtvh_add = tk.Button(self.frm_vtvh_btns, text='Add Grid to Queue', state='normal')
        self.btn_vtvh_add.grid(row=0,column=0,padx=5)
        self.btn_vtvh_add['command'] = self.add_vtvh_grid
        
        self.btn_vtvh_clear = tk.Button(self.frm_vtvh_btns, text='Clear Grid Queue', state='normal')
        self.btn_vtvh_clear.grid(row=0, column=2, padx=5)
        self.btn_vtvh_clear['command'] = self.clear_vtvh_grid
        
        grid_row=6
        self.frm_grids=tk.Frame(self.frm_vtvh)
        self.frm_grids.grid(row=grid_row, column=0, sticky=tk.N, padx=3)
        gtxt=['#','Fields','Temps']
        self.lbl_gridsHeader=[None]*len(gtxt)
        for i in range(len(gtxt)):
            self.lbl_gridsHeader[i]=tk.Label(self.frm_grids, text=gtxt[i], fg='black', 
                                        font=small_font, width=(3 if i==0 else 20), justify='center',
                                            highlightbackground='black',highlightthickness=1)
            self.lbl_gridsHeader[i].grid(row=0, column=i, sticky=tk.N, padx=0, pady=1)
        self.make_vtvh_grids(self.vtvh_grids_fields,self.vtvh_grids_temps)
        
        self.frm_scanTime=tk.Frame(self.frm_vtvh)
        self.frm_scanTime.grid(row=grid_row+1, column=0, sticky=tk.N, padx=3)
        self.lbl_vtvh_scanTime=tk.Label(self.frm_scanTime, text='How long is J1700 Scan (mins:seconds)?')
        self.lbl_vtvh_scanTime.grid(row=0, column=0)
        self.ent_vtvh_scanTime = tk.Entry(self.frm_scanTime, fg='white', bg='black', insertbackground='white',
                                        font=small_font, width=6, disabledforeground='black',
                                        disabledbackground='white', justify='center')
        self.ent_vtvh_scanTime.grid(row=0, column=1)
        self.ent_vtvh_scanTime.insert(tk.END, '0')
        self.ent_vtvh_scanTime['state'] = 'disabled'
        
        self.btn_vtvh_browse = tk.Button(self.frm_vtvh, text='Browse for Folder', state='normal')
        self.btn_vtvh_browse.grid(row=grid_row+3)
        self.btn_vtvh_browse['command'] = self.func_vtvh_browse
        self.lbl_vtvh_browse = tk.Label(self.frm_vtvh, text='Select Folder that Spectral Measurement is Autosaving to:')
        self.lbl_vtvh_browse.grid(row=grid_row+2)
        self.xe_off = tk.IntVar()
        self.xe_off.set(1)
        self.chk_xe_off = tk.Checkbutton(self.frm_vtvh, text='Turn off Xe-Arc Lamp?', variable=self.xe_off)
        self.chk_xe_off.grid(row=grid_row+4)
        
        self.btn_vtvh = tk.Button(self.frm_vtvh, text='Collect VTVH', state='disabled')
        self.btn_vtvh.grid(row=grid_row+5)
        
        
        
        # Temperature frame
        self.lbl_temp_frame = tk.Label(self.frm_temp_sensor, text='Temperature Control (Kelvin)')
        self.lbl_sensor_1 = tk.Label(self.frm_temp_sensor, text='VTI Sensor (1)')
        self.lbl_sensor_1_temp = tk.Label(self.frm_temp_sensor, text='—', font=input_font, width=10,
                                          relief='groove', justify='center')
        self.lbl_sensor_3 = tk.Label(self.frm_temp_sensor, text='Sample Sensor (3)')
        self.lbl_sensor_3_temp = tk.Label(self.frm_temp_sensor, text='—', font=input_font, width=10,
                                          relief='groove', justify='center')
        self.lbl_temperature = tk.Label(self.frm_temp_setpoint, text='Sample Temp. Set Point')
        self.ent_temperature = tk.Entry(self.frm_temp_setpoint, fg='red', bg='black', insertbackground='white',
                                        font=input_font, width=10, disabledforeground='black',
                                        disabledbackground='white', justify='center')
        self.btn_temp_set = tk.Button(self.frm_temp_setpoint, text='Write Set Point', state='disabled')
        self.btn_temp_get = tk.Button(self.frm_temp_setpoint, text='Read Set Point', state='disabled')
        self.ent_temperature.insert(tk.END, '—')
        self.ent_temperature['state'] = 'disabled'
        self.lbl_temp_frame.grid(row=0)
        self.lbl_sensor_1.grid(row=1, sticky=tk.W)
        self.lbl_sensor_1_temp.grid(row=2)
        self.lbl_sensor_3.grid(row=3, sticky=tk.W)
        self.lbl_sensor_3_temp.grid(row=4)
        self.lbl_temperature.grid(row=0, sticky=tk.W)
        self.ent_temperature.grid(row=1)
        self.btn_temp_set.grid(row=2)
        self.btn_temp_get.grid(row=3)
        #new for Cryofree
        self.frm_temp_nv = tk.Frame(self.frm_temp_setpoint)
        self.frm_temp_nv.grid(row=4, column=0, sticky=tk.N, padx=3)
        #self.lbl_nv = tk.Label(self.frm_temp_nv, text='Needle Valve (Work in Progress)')
        self.lbl_nv_val_top = tk.Label(self.frm_temp_nv, text='Current NV Pressure')
        #self.ent_nv = tk.Entry(self.frm_temp_nv, fg='red', bg='black', insertbackground='white',
        #                                font=med_font, width=7, disabledforeground='black',
        #                                disabledbackground='white', justify='center')
        self.lbl_nv_val = tk.Label(self.frm_temp_nv, text='—', font=med_font, width=11,
                                          relief='groove', justify='center')
        #self.btn_nv_set = tk.Button(self.frm_temp_nv, text='Write NV Set Point', state='disabled')
        #self.ent_nv.insert(tk.END, '—')
        #self.ent_nv['state'] = 'disabled'
        #self.lbl_nv.grid(row=0, column=0)
        self.lbl_nv_val_top.grid(row=0) #, column=1)
        #self.ent_nv.grid(row=1, column=0)
        #self.btn_nv_set.grid(row=2)
        self.lbl_nv_val.grid(row=1) #, column=1)

        # Magnet frame
        self.lbl_magnet_frame = tk.Label(self.frm_mag_sensor, text='Magnet Control (Tesla)')
        self.beep = tk.IntVar()
        self.beep.set(1)
        self.chk_beep = tk.Checkbutton(self.frm_mag_sensor, text='Beep', variable=self.beep)
        self.lbl_current_field = tk.Label(self.frm_mag_sensor, text='Current Field')
        self.lbl_current_field_value = tk.Label(self.frm_mag_sensor, text='—', font=input_font, width=8,
                                                relief='groove', justify='center')
        self.btn_switch_heater = tk.Button(self.frm_mag_sensor, text='Switch Heater', state='disabled')
        self.btn_goto_field = tk.Button(self.frm_mag_sensor, text='Go to Set', state='disabled')
        self.btn_zero_field = tk.Button(self.frm_mag_sensor, text='Go to Zero', state='disabled')
        self.lbl_field_set_point = tk.Label(self.frm_mag_setpoint, text='Field Set Point')
        self.ent_field = tk.Entry(self.frm_mag_setpoint, fg='red', bg='black', insertbackground='white',
                                  font=input_font, width=8, disabledforeground='black',
                                  disabledbackground='white', justify='center')
        self.btn_field_set = tk.Button(self.frm_mag_setpoint, text='Write Set Point', state='disabled')
        self.btn_field_get = tk.Button(self.frm_mag_setpoint, text='Read Set Point', state='disabled')
        self.ent_field.insert(tk.END, '—')
        self.ent_field['state'] = 'disabled'
        self.lbl_magnet_frame.grid(row=0, column=0, columnspan=2)
        self.lbl_current_field.grid(row=1, column=0, sticky=tk.W)
        self.chk_beep.grid(row=1, column=1, sticky=tk.E)
        self.lbl_current_field_value.grid(row=2, column=0, columnspan=2)
        self.btn_switch_heater.grid(row=3, column=0, columnspan=2)
        self.btn_goto_field.grid(row=4, column=0, columnspan=2)
        self.btn_zero_field.grid(row=5, column=0, columnspan=2)
        self.lbl_field_set_point.grid(row=0, sticky=tk.W)
        self.ent_field.grid(row=1)
        self.btn_field_set.grid(row=2)
        self.btn_field_get.grid(row=3)

    def set_functions(self, serial_connect=None, serial_disconnect=None,
                      set_temperature=None, get_temperature=None,
                      engage_switch_heater=None, disengage_switch_heater=None,
                      goto_field=None, zero_field=None, interrupt=None,
                      set_field=None, get_field=None, refresh=None, vtvh=None, vtvh_interrupt=None,
                     set_nv=None, qkcool=None):
        self.func_serial_connect = serial_connect
        self.func_serial_disconnect = serial_disconnect
        self.func_set_temperature = set_temperature
        self.func_get_temperature = get_temperature
        self.func_engage_switch_heater = engage_switch_heater
        self.func_disengage_switch_heater = disengage_switch_heater
        self.func_goto_field = goto_field
        self.func_zero_field = zero_field
        self.func_interrupt = interrupt
        self.func_set_field = set_field
        self.func_get_field = get_field
        #added for cryofree (also in set_functions in main and gui)
        self.func_refresh = refresh 
        self.func_vtvh = vtvh
        self.func_vtvh_interrupt = vtvh_interrupt
        self.func_set_nv = set_nv
        self.func_qkcool = qkcool

    def set_close_method(self, command):
        self.master.protocol('WM_DELETE_WINDOW', command)

    #def user_com_port(self):
    #    return self.ent_com_port.get()

    def user_temperature(self):
        return self.ent_temperature.get().replace(' ', '')

    def user_field(self):
        return self.ent_field.get().replace(' ', '')
    
    def user_vtvh_field(self):
        fields_string=self.ent_vtvh_field.get().replace(' ', '')
        #parse , and ; and return a list of lists
        field_list=[hs.split(',') for hs in fields_string.split(';')]
        return field_list
    
    def user_vtvh_temps(self):
        temps_string=self.ent_vtvh_temps.get().replace(' ', '')
        #parse , and ; and return a list of lists
        temp_list=[ts.split(',') for ts in temps_string.split(';')]
        return temp_list
    
    def user_scanTime(self):
        return self.ent_vtvh_scanTime.get().replace(' ', '')
    
    def user_vtvh_dir(self):
        return self.path_vtvh_browse

    #def user_nv(self):
    #    return self.ent_nv.get().replace(' ', '')

    def update_com_port(self, port):
        self.lbl_com_port['text']=port
    #    state = self.ent_com_port['state']
    #    if state == 'normal':
    #        self.ent_com_port.delete(0, tk.END)
    #        self.ent_com_port.insert(tk.END, str(port))
    #    else:
    #        self.ent_com_port['state'] = 'normal'
    #        self.ent_com_port.delete(0, tk.END)
    #        self.ent_com_port.insert(tk.END, str(port))
    #        self.ent_com_port['state'] = state

    def update_temps(self, sensor1=None, sensor3=None, setpoint=None, current_nv=None, nv_setpoint=None):
        if sensor1 is not None:
            self.lbl_sensor_1_temp['text'] = str(sensor1)
        if sensor3 is not None:
            self.lbl_sensor_3_temp['text'] = str(sensor3)
        if setpoint is not None:
            state = self.ent_temperature['state']
            if state == 'normal':
                self.ent_temperature.delete(0, tk.END)
                self.ent_temperature.insert(tk.END, str(setpoint))
            else:
                self.ent_temperature['state'] = 'normal'
                self.ent_temperature.delete(0, tk.END)
                self.ent_temperature.insert(tk.END, str(setpoint))
                self.ent_temperature['state'] = state
            
        if current_nv is not None:
            self.lbl_nv_val['text'] = str(current_nv)

        if nv_setpoint is not None: #should never be triggered anyways
            #state = self.ent_nv['state']
            #if state == 'normal':
            #    self.ent_nv.delete(0, tk.END)
            #    self.ent_nv.insert(tk.END, str(nv_setpoint))
            #else:
            #    self.ent_nv['state'] = 'normal'
            #    self.ent_nv.delete(0, tk.END)
            #    self.ent_nv.insert(tk.END, str(nv_setpoint))
            #    self.ent_nv['state'] = state
            pass

    def update_fields(self, current_field=None, setpoint=None):
        if current_field is not None:
            self.lbl_current_field_value['text'] = str(current_field)
        if setpoint is not None:
            state = self.ent_field['state']
            if state == 'normal':
                self.ent_field.delete(0, tk.END)
                self.ent_field.insert(tk.END, str(setpoint))
            else:
                self.ent_field['state'] = 'normal'
                self.ent_field.delete(0, tk.END)
                self.ent_field.insert(tk.END, str(setpoint))
                self.ent_field['state'] = state

    def set_connection_frame(self, connected):
        if connected:
            #self.ent_com_port['state'] = 'disabled'
            self.btn_com_port['text'] = 'Disconnect'
            self.btn_com_port['command'] = self.func_serial_disconnect
        else:
            #self.ent_com_port['state'] = 'disabled'
            #self.ent_com_port.bind('<Return>', func=self.func_serial_connect)
            self.btn_com_port['text'] = 'Connect'
            self.btn_com_port['command'] = self.func_serial_connect

    def set_temperature_frame(self, connected):
        if connected:
            self.ent_temperature['state'] = 'normal'
            self.ent_temperature.bind('<Return>', func=self.func_set_temperature)
            self.btn_temp_set['state'] = 'normal'
            self.btn_temp_set['command'] = self.func_set_temperature
            self.btn_temp_get['state'] = 'normal'
            self.btn_temp_get['command'] = self.func_get_temperature
            
            #self.btn_nv_set['state'] = 'disabled'
            #self.btn_nv_set['command'] = self.func_set_nv
            #self.ent_nv['state'] = 'disabled'
        else:
            self.ent_temperature['state'] = 'disabled'
            self.btn_temp_set['state'] = 'disabled'
            self.btn_temp_get['state'] = 'disabled'
            #self.btn_nv_set['state'] = 'disabled'
            #self.ent_nv['state'] = 'disabled'

    def set_field_frame(self, connected, switch_setting=None, field_movement=None, setpoint_change=None):
        if connected:
            self.btn_switch_heater['state'] = 'normal'
            if switch_setting == SWITCH_ENABLED:
                self.btn_switch_heater['text'] = 'Disengage Switch Heater'
                self.btn_switch_heater['command'] = self.func_disengage_switch_heater
            elif switch_setting == SWITCH_WARMING:
                self.btn_switch_heater['text'] = 'Engaging... Interrupt'
                self.btn_switch_heater['command'] = self.func_interrupt
            elif switch_setting == SWITCH_COOLING:
                self.btn_switch_heater['text'] = 'Disengaging... Interrupt'
                self.btn_switch_heater['command'] = self.func_interrupt
            elif switch_setting == SWITCH_DISABLED:
                self.btn_switch_heater['text'] = 'Engage Switch Heater'
                self.btn_switch_heater['command'] = self.func_engage_switch_heater
            if field_movement == FIELD_INACTIVE:
                self.btn_goto_field['text'] = 'Go to Set'
                self.btn_goto_field['command'] = self.func_goto_field
                self.btn_goto_field['state'] = 'disabled'
                self.btn_zero_field['text'] = 'Go to Zero'
                self.btn_zero_field['command'] = self.func_zero_field
                self.btn_zero_field['state'] = 'disabled'
            elif field_movement == FIELD_HOLD:
                self.btn_goto_field['text'] = 'Go to Set'
                self.btn_goto_field['command'] = self.func_goto_field
                self.btn_goto_field['state'] = 'normal'
                self.btn_zero_field['text'] = 'Go to Zero'
                self.btn_zero_field['command'] = self.func_zero_field
                self.btn_zero_field['state'] = 'normal'
            elif field_movement == FIELD_GOTO:
                self.btn_goto_field['text'] = 'Sweeping... Interrupt'
                self.btn_goto_field['command'] = self.func_interrupt
                self.btn_goto_field['state'] = 'normal'
                self.btn_zero_field['text'] = 'Go to Zero'
                self.btn_zero_field['command'] = self.func_zero_field
                self.btn_zero_field['state'] = 'disabled'
            elif field_movement == FIELD_ZERO:
                self.btn_goto_field['text'] = 'Go to Set'
                self.btn_goto_field['command'] = self.func_goto_field
                self.btn_goto_field['state'] = 'disabled'
                self.btn_zero_field['text'] = 'Sweeping... Interrupt'
                self.btn_zero_field['command'] = self.func_interrupt
                self.btn_zero_field['state'] = 'normal'
            if setpoint_change == SETPOINT_ACTIVE:
                self.ent_field['state'] = 'normal'
                self.ent_field.bind('<Return>', func=self.func_set_field)
                self.btn_field_set['state'] = 'normal'
                self.btn_field_set['command'] = self.func_set_field
                self.btn_field_get['state'] = 'normal'
                self.btn_field_get['command'] = self.func_get_field
            elif setpoint_change == SETPOINT_INACTIVE:
                self.ent_field['state'] = 'disabled'
                self.btn_field_set['state'] = 'disabled'
                self.btn_field_get['state'] = 'disabled'
        else:
            self.btn_switch_heater['text'] = 'Switch Heater'
            self.btn_switch_heater['state'] = 'disabled'
            self.btn_goto_field['text'] = 'Go to Set'
            self.btn_goto_field['state'] = 'disabled'
            self.btn_zero_field['text'] = 'Go to Zero'
            self.btn_zero_field['state'] = 'disabled'
            self.ent_field['state'] = 'disabled'
            self.btn_field_set['state'] = 'disabled'
            self.btn_field_get['state'] = 'disabled'
            
    def set_cryofree_frame(self, connected, refresh_status=None, vtvh_status=None, qkcool_status=None):
        if connected:
            
            if qkcool_status!=None:
                if qkcool_status==INACTIVE:
                    self.btn_qkcool['state']='normal'
                    self.btn_qkcool['command']=self.func_qkcool
                    self.btn_qkcool['text']='Quick Cooldown'
                    self.btn_vtvh['state'] = 'normal'
                elif qkcool_status==ACTIVE:
                    self.btn_qkcool['state']='normal'
                    self.btn_qkcool['text']='Interrupt Quick Cool'
                    self.btn_qkcool['command']=self.func_interrupt
                    self.btn_vtvh['state'] = 'disabled'
            
            if refresh_status!=None:
                if refresh_status==REFRESHING:
                    self.btn_refresh['state']='disabled'
                elif refresh_status==NOT_REFRESHING:
                    self.btn_refresh['state']='normal'
                    self.btn_refresh['command'] = self.func_refresh
                    
            if vtvh_status!=None:
                if vtvh_status==VTVH_INACTIVE:
                    self.btn_vtvh['state'] = 'normal'
                    self.btn_vtvh['text'] = 'Collect VTVH'
                    self.btn_vtvh['command'] = self.func_vtvh
                    self.ent_vtvh_field['state'] = 'normal'
                    self.ent_vtvh_temps['state'] = 'normal'
                    self.ent_vtvh_scanTime['state'] = 'normal'
                    self.btn_vtvh_browse['state'] = 'normal'
                    self.btn_qkcool['state']='normal'
                    self.btn_vtvh_clear['state']='normal'
                    self.btn_vtvh_add['state']='normal'
                elif vtvh_status == VTVH_ACTIVE:
                    self.btn_vtvh['state'] = 'normal'
                    self.btn_vtvh['text'] = 'Interrupt VTVH'
                    self.btn_vtvh['command'] = self.func_vtvh_interrupt
                    self.ent_vtvh_field['state'] = 'disabled'
                    self.ent_vtvh_temps['state'] = 'disabled'
                    self.ent_vtvh_scanTime['state'] = 'disabled'
                    self.btn_vtvh_browse['state'] = 'disabled'
                    self.btn_qkcool['state']='disabled'
                    self.btn_vtvh_clear['state']='disabled'
                    self.btn_vtvh_add['state']='disabled'

        else:
            self.btn_refresh['state']='disabled'
            self.btn_qkcool['state']='disabled'
            self.btn_vtvh['state'] = 'disabled'
            self.btn_vtvh['text'] = 'Collect VTVH'
            self.ent_vtvh_field['state'] = 'disabled'
            self.ent_vtvh_temps['state'] = 'disabled'
            self.ent_vtvh_scanTime['state'] = 'disabled'
            
    def browse_for_dir(self):
        dirname = filedialog.askdirectory()
        self.lbl_vtvh_browse['text']='...'+dirname[-40:]
        self.path_vtvh_browse = dirname
        #Change button
        self.btn_vtvh_browse['text']='Remove Folder'
        self.btn_vtvh_browse['command']=self.reset_browse_for_dir
        return dirname
    
    def reset_browse_for_dir(self):
        self.lbl_vtvh_browse['text']='Select Folder that Spectral Measurement is Autosaving to:'
        self.path_vtvh_browse = None
        #Change button
        self.btn_vtvh_browse['text']='Browse'
        self.btn_vtvh_browse['command']=self.browse_for_dir
        return None
    
    def warning_popup(self, title, message):
        messagebox.showwarning(title,message,parent=self)
        
    def make_vtvh_grids(self, fields,temps):
        if len(fields)==len(temps):
            #delete currently shown grids
            try:
                for i in self.lbl_grids:
                    for j in i:
                        j.destroy()
            except: #if havent made the grids yet#
                pass
            #replace with new grids
            row_len=3
            #if there is nothing there indicate that
            if len(fields)==0:
                fields=[['Empty']]
                temps=[['Empty']]
            self.lbl_grids=[[None for i in range(len(temps))] for j in range(row_len)]
            for row in range(len(fields)):
                txt=[row+1,fields[row],temps[row]]
                for col in range(len(txt)):
                    self.lbl_grids[col][row]=tk.Label(self.frm_grids, text=txt[col], fg='black', bg='white', 
                                                font='Arial 10', width=(3 if col==0 else 20), justify='center',
                                                     highlightbackground='black', highlightthickness=1)
                    self.lbl_grids[col][row].grid(row=row+1, column=col, sticky=tk.N, padx=0, pady=0)
    
    def add_vtvh_grid(self):
        for ts,hs in zip(self.user_vtvh_temps(), self.user_vtvh_field()):
        #Add to interal variables
        #TODO CHECK IF THERE ARE NONES IN THE Internally stored ones 
            self.vtvh_grids_fields.append(hs)
            self.vtvh_grids_temps.append(ts)
        
        #Update to Grids in GUI
        self.make_vtvh_grids(self.vtvh_grids_fields,self.vtvh_grids_temps)
        
        #Reset fields to Defaults
        self.ent_vtvh_field.insert(tk.END, ','.join(map(str,ISOTHERM_DEFAULTS)))
        self.ent_vtvh_temps.insert(tk.END, ','.join(map(str,TEMP_DEFAULTS)))
        
    def clear_vtvh_grid(self):
        self.vtvh_grids_fields=[]
        self.vtvh_grids_temps=[]
        #Update to Grids in GUI
        self.make_vtvh_grids(self.vtvh_grids_fields,self.vtvh_grids_temps)

if __name__ == '__main__':
    pass
