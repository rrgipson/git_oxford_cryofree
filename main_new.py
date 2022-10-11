import numpy as np
from time import sleep
from threading import Thread
from oxford import SerialPort, default_comport_m, default_comport_t
from gui import *
import spectrometer as j1700
from logger import *
from scpi_iTC import *

# Appearance settings, delay settings, and default COM port
delay_sensor = 5  # time between updates for sensors

# Temperature controller settings
isobus_temp = '@2' 
isobus_temp_version = '81'
min_temp, max_temp = 0, 300

# Magnet controller settings - UPDATED FOR CRYOFREE
isobus_magnet = '@1'
isobus_magnet_version = 'IPS    Version  4.01 (c) OXFORD 2011'
magnet_return_control = 'C1'  # return instrument to 'C0' (LOCAL?), 'C1' (REMOTE & UNLOCKED) or 'C2' (REMOTE & LOCKED)
max_field = 7  # maximum strength of magnetic field
switch_wait = 5  # seconds to wait when turning switch heater on/off

#send stderr to file - uncomment to write errors to file
sys.stderr = open('UserLogs/error_log.txt', 'a+')

def format_temp(temperature):
    """
    The temperature controller uses three decimal places below 20 K, and two at/above 20 K.

    :type temperature: float
    :param temperature: converts an integer/float to a string with appropriate decimal points

    :rtype: str
    :return: string of temperature with correct decimal places
    """
    if 0 <= temperature < 20:
        return '{:.3f}'.format(temperature)
    elif 20 <= temperature:
        return '{:.2f}'.format(temperature)
    else:
        return str(temperature)


def format_field(field, zero=0):
    """
    Returns the supplied field as a string to four decimal points. Zero is treated as unsigned by default, but the
    magnet distinguishes +0 & -0, so a sign can be added by setting `zero' to 1 (gives +0.0000) or -1 (gives -0.0000).

    :type field: float
    :param field: converts an integer/float to a string with four decimal points

    :type zero: int
    :param zero: indicates the sign of zero being used, default 0 (unsigned)

    :rtype: str
    :return: string of magnetic field with sign (+/-) and four decimal places
    """
    if field > 0:
        return '+{:.4f}'.format(field)
    elif field < 0:
        return '{:.4f}'.format(field)
    elif field == 0:
        if zero == 1:  # positive zero
            return '+0.0000'
        elif zero == -1:  # negative zero
            return '-0.0000'
        else:  # unsigned zero otherwise
            return '0.0000'
    else:  # if we've received something strange, just spit it back out
        return str(field)


class Application:
    def __init__(self):
        self.serial_t = SerialPort()
        self.serial_m = SerialPort()
        self._temp_connect, self._field_connect = False, False
        self._temp_thread, self._field_thread = None, None
        self._temp_delay, self._field_delay = delay_sensor, delay_sensor
        self._switch_status = SWITCH_DISABLED
        self._action_thread, self._action_interrupt = None, False
        self._vtvh_thread, self._vtvh_interrupt = None, False
        self.gui = GUI()
        self.gui.set_functions(serial_connect=self.serial_connect, serial_disconnect=self.serial_disconnect,
                               set_temperature=self.set_temperature, get_temperature=self.get_temperature,
                               engage_switch_heater=self.engage_switch_heater,
                               disengage_switch_heater=self.disengage_switch_heater,
                               goto_field=self.goto_field, zero_field=self.zero_field, interrupt=self.interrupt,
                               set_field=self.set_field, get_field=self.get_field, 
                               refresh=self.refresh_magnet_gui, vtvh=self.start_vtvh, 
                               vtvh_interrupt=self.vtvh_interrupt, set_nv=self.set_nv) #cryofree added 
        self.gui.set_close_method(self.on_closing)
        self.gui.update_com_port(port='2 COMs')
        self.gui.set_connection_frame(connected=False)
        self.gui.set_cryofree_frame(connected=False)
        self.gui.set_temperature_frame(connected=False)
        self.gui.set_field_frame(connected=False)
        
        self.bglogger = LOGGER()
        self._bglog_thread = None
        
        self.vtvh_logger = LOGGER()

    def run(self):
        self.gui.mainloop()

    def on_closing(self):
        if self.serial_m.is_open or self.serial_t.is_open:
            self.serial_disconnect()
        self.gui.master.destroy()

    def serial_connect(self):
        """
        Attempts to connect to the Oxford instrument through the requested COM port. Sends several messages to both the
        temperature control and magnet control:
            'Q2' asks for a \n at the end of each message (helps Windows find the end of each communication)
            'V' to check that the version matches the one expected
            'C1' to switch control to REMOTE & unLOCKED 
            'X' to inspect the current state of the system
        Based on the current state of the system, prepares the system in a specific state.
        """
        print_to_log('Initializing serial_connect Procedure')
        # Try to open communication to the COM port, and switch 'Connect' button to 'Disconnect' if successful
        self.serial_m.port = default_comport_m
        self.serial_t.port = default_comport_t
        for s in [self.serial_m, self.serial_t]:
            if s.is_open:  # if the port is somehow already open, close it
                s.close()
        if not self.serial_m.open() or not self.serial_t.open():  # if open() returns False, then opening has failed
            self.gui.update_com_port(port='fail')
            self.gui.set_connection_frame(connected=False)
            self.gui.set_cryofree_frame(connected=False)
            self.gui.set_temperature_frame(connected=False)
            self.gui.set_field_frame(connected=False)
            return
        self.gui.set_connection_frame(connected=self.serial_m.is_open and self.serial_t.is_open)
        self._temp_connect = False
        self._field_connect = False

        # Connect to temperature controller
        success = True  # flag to monitor successful communication to temperature controller
        version = self.serial_t.transmit(isobus_temp+READ_VERSION, 'TempControl: Error receiving version')
        if version.split(':')[-1] == isobus_temp_version:  # if version matches expectation
            status = self.serial_t.transmit(isobus_temp+READ_ALARMS, 'TempControl: Error retrieving alarms')
            # Check if any alarms have been triggered
            if status.split(':')[-1] != '':
                success = False
        else:
            print('TempControl: Version error', '('+str(version)+')')
            success = False
        if success:
            self._temp_connect = True
            self._temp_thread = Thread(target=self._monitor_temperature, daemon=True)
            self._temp_thread.start()
            self.get_temperature()
        else:
            self.gui.update_temps(setpoint='fail')
        self.gui.set_temperature_frame(connected=self._temp_connect)

        # Connect to magnet controller
        success = True  # flag to monitor successful communication to temperature controller
        version = self.serial_m.transmit(isobus_magnet+'V', 'Magnet: Error receiving version')
        field_movement = FIELD_INACTIVE
        if version == isobus_magnet_version:  # if version matches expectation
            status = self.serial_m.transmit(isobus_magnet+'X', 'Magnet: Error receiving status')
            # `status' takes form `XnAnCnSnnHn' 
            if len(status) != 12 or ''.join([list(status)[i] for i in [0, 3, 5, 7, 9]]) != 'XACHM':
                print('Magnet: Uninterpretable status', status)
                success = False
            if status[0:3] != 'X00':  # If not `X00', status is not normal so don't initiate control
                print('Magnet: Non-normal status error', status[0:3], 'in', status)
                success = False
            if status[7:9] in ['H0', 'H2']:  # if switch heater off ('H0' at zero field, 'H2' at nonzero field)
                self._switch_status = SWITCH_DISABLED
            elif status[7:9] == 'H1':
                self._switch_status = SWITCH_ENABLED
                field_movement = FIELD_HOLD
                print('Waiting 5 mins for Heater Warming') #CRYOFREE
                sleep(300) #CRYOFREE
            else:  # if 'H5' (fault) or 'H8' (missing), don't proceed
                print('Magnet: Switch heater fault or missing', status[7:9], 'in', status)
                success = False
            # DEBUG what `Xmn', `Mmn', and `Pmn' settings are allowed?
        else:
            print('Magnet: Version error', '('+str(version)+')')
            success = False
        if success:
            self.serial_m.transmit(isobus_magnet+'C1')  # set STATUS to REMOTE & UNLOCKED
            if 'A4' in status: #if magnet is clamped ##ADDED FOR CRYOFREE
                self.serial_m.transmit(isobus_magnet+'A0')  # set ACTIVITY to HOLD 
            self._field_connect = True
            self._field_thread = Thread(target=self._monitor_field, daemon=True)
            self._field_thread.start()
            self.get_field()
            setpoint = SETPOINT_ACTIVE
        else:
            self.gui.update_fields(setpoint='fail')
            setpoint = SETPOINT_INACTIVE
        self.gui.set_field_frame(connected=self._field_connect, switch_setting=self._switch_status,
                                 field_movement=field_movement, setpoint_change=setpoint)
        self.gui.set_cryofree_frame(connected=self.serial_m.is_open, refresh_status=NOT_REFRESHING, vtvh_status=VTVH_INACTIVE) #cryofree

        #start logging
        self.start_bg_logging()

        print_to_log('Finished serial_connect Procedure')
    
                
    def serial_disconnect(self):
        print_to_log('Initializing serial_disconnect Procedure')
        if self.serial_t.is_open:
            self.serial_t.close()
        if self.serial_m.is_open:
            if self._field_connect:
                self.serial_m.transmit(isobus_magnet+'A0')  # set ACTIVITY to HOLD ##NEED THIS FOR CRYOFREE??
                if self._action_thread is not None:
                    self._action_interrupt = True
                    self._action_thread.join()  # interrupt any background events
                self.serial_m.transmit(isobus_magnet + magnet_return_control)  # relinquish control to front panel
            self.serial_m.close()
        self._temp_connect = False
        self.gui.update_temps(setpoint='—', nv_setpoint='—')
        self.gui.set_temperature_frame(connected=False)
        self._field_connect = False
        self.gui.update_fields(setpoint='—')
        self.gui.set_field_frame(connected=False)
        self.gui.set_cryofree_frame(connected=False) #cryofree

        sleep(max(self._temp_delay, self._field_delay))  # wait to update to '—'
        self.gui.set_connection_frame(connected=False)
        print('Completed Disconnect Procedure')

    def _monitor_temperature(self): 
        """
        Daemon thread function to update the temperature every `_temp_delay' seconds. Does not print each
        message/response to std_out so as to prevent clutter from background monitoring operations.
        """
        while self.serial_t.is_open and self._temp_connect:
            sensor1 = self.serial_t.transmit(isobus_temp +READ+VTI+CURRENT_TEMP, 'TempControl: Error reading VTI sensor', False)
            if len(sensor1) > 0:
                if sensor1.split(':')[-1] != 'INVALID':
                    sensor1 = sensor1.split(':')[-1]
                else:
                    sensor1 = '—'
            else:
                sensor1 = '—'
            sensor3 = self.serial_t.transmit(isobus_temp +READ+SAMPLE+CURRENT_TEMP, 'TempControl: Error reading sample sensor', False)
            if len(sensor3) > 0:
                if sensor3.split(':')[-1] != 'INVALID':
                    sensor3 = sensor3.split(':')[-1]
                else:
                    sensor3 = '—'
            else:
                sensor3 = '—'
                
            #CRYOFREE Added NV
            current_nv= self.get_nv_pressure(print_out=False)
            
            self.gui.update_temps(sensor1=sensor1, sensor3=sensor3, current_nv=current_nv+'mB')
            sleep(self._temp_delay)
        # after 'while' loop breaks
        self.gui.update_temps(sensor1='—', sensor3='—', current_nv= '—')
        return

    def set_temperature(self, *args):
        if self.serial_t.is_open and self._temp_connect:
            self.serial_t.transmit(isobus_temp+SET+SAMPLE+AUTO_SET+':Auto', 'TempControl: Error setting sample heater to Auto') #Sets both heaters to auto
            self.serial_t.transmit(isobus_temp+SET+VTI+AUTO_SET+':Auto', 'TempControl: Error setting sample heater to Auto')
            temperature = self.gui.user_temperature()
            shift = 0
            if len(temperature) > 0:
                if temperature[-1] == 'K':
                    temperature = temperature[:-1]
                elif temperature[-1] == 'C':
                    temperature = temperature[:-1]
                    shift = 273.15
            try:
                temperature = float(temperature) + shift
                if not (max(0, min_temp) <= temperature <= max_temp):  # if not in allowed range
                    temperature = None
            except (ValueError, TypeError):
                temperature = None
            if temperature is None:
                print('TempControl: Invalid set point request of', self.gui.user_temperature(), '\a')  # try to beep
            else:
                #UPDATED FOR CRYOFREE
                if temperature < 1.7:
                    temperature = 1.7 #base temp
                    
                if temperature <= 10:
                    vti_temp= (0.988*float(temperature)) - 0.063 #based on regression of factory tested temp offsets
                else: 
                    vti_temp= (0.984*float(temperature)) - 0.999

                stop=False
                print("Setting VTI Temp to", vti_temp)
                vti_response = self.serial_t.transmit(isobus_temp + SET+VTI+SETPT_TEMP+':'+ format_temp(vti_temp))
                if vti_response.split(':')[-1]=='INVALID':
                    print('TempControl: Instrument confused by VTI Temp Setting', '\a')  # try to beep
                    stop=True
                    
                if not stop:
                    print("Setting Sample Temp to", temperature)
                    response = self.serial_t.transmit(isobus_temp +SET+SAMPLE+SETPT_TEMP+':'+ format_temp(temperature))
                    if response.split(':')[-1]=='INVALID':
                        print('TempControl: Instrument confused by', self.gui.user_temperature(), '\a')  # try to beep

        self.get_temperature()

    def get_temperature(self): #Gets temp set point
        temperature = '—'
        if self.serial_t.is_open and self._temp_connect:
            response = self.serial_t.transmit(isobus_temp+READ+SAMPLE+SETPT_TEMP, 'TempControl: Error reading set point')
            if response.split(':')[-1]!='INVALID':
                temperature = response.split(':')[-1]
        self.gui.update_temps(setpoint=temperature)
        if temperature == '—':
            return None
        return temperature.replace('K','')

    def engage_switch_heater(self):
        if self._switch_status == SWITCH_DISABLED:
            if self._action_thread is not None:
                self.interrupt()
                self._action_thread.join()  # interrupt and wait to finish
            self._action_interrupt = False
            self._switch_status = SWITCH_WARMING
        elif self._switch_status in [SWITCH_WARMING, SWITCH_COOLING]:
            self._action_interrupt = True  # ask any background thread to cancel
            sleep(2)  # wait for any background thread to cancel
            self._action_interrupt = True  # set flag to interrupt switch heater action immediately
            print('Magnet: Confusing switch heater request; interrupting...\a')
        else:
            self._action_interrupt = True  # interrupt switch heater action immediately
            print('Magnet: Switch heater is already on\a')
        self._action_thread = Thread(target=self._switch_delayed_action, args=('H1', 'H0', 'A0')) #WHAT DOES A0 DO WHEN SENT- CRYOFREE??
        self._action_thread.start()

    def disengage_switch_heater(self):
        if self._switch_status == SWITCH_ENABLED:
            if self._action_thread is not None:
                self.interrupt()
                self._action_thread.join()  # interrupt and wait to finish
            self._action_interrupt = False
            self._switch_status = SWITCH_COOLING
        elif self._switch_status in [SWITCH_WARMING, SWITCH_COOLING]:
            self._action_interrupt = True  # ask any background thread to cancel
            sleep(2)  # wait for any background thread to cancel
            self._action_interrupt = True  # set flag to interrupt switch heater action immediately
            print('Magnet: Confusing switch heater request; interrupting...\a')
        else:
            self._action_interrupt = True  # interrupt switch heater action immediately
            print('Magnet: Switch heater is already off\a')
        self._action_thread = Thread(target=self._switch_delayed_action, args=('A0', 'H1', 'H0'))
        self._action_thread.start()

    def _switch_delayed_action(self, initial, interrupt, final):
        count = switch_wait
        self.gui.set_field_frame(connected=self._field_connect, switch_setting=self._switch_status,
                                 setpoint_change=SETPOINT_INACTIVE)
        if initial is not None:
            response = self.serial_m.transmit(isobus_magnet+initial, 'Magnet: Error initiating switch heater change')
            # if there's a problem, abort by interruption
            if len(response) > 0:
                if response[0] == '?':
                    print('Magnet: Response to initiating switch heater change was ?')
                    self._action_interrupt = True
            else:  # empty string
                print('Magnet: No response to initiating switch heater change')
                self._action_interrupt = True
        while count > 0:
            if self._action_interrupt:
                break
            self.gui.update_fields(setpoint='Wait '+str(count)+'s')
            count = count - 1
            sleep(1)
        if self._action_interrupt:  # if we were interrupted, abort task
            if interrupt is not None:
                response = self.serial_m.transmit(isobus_magnet+interrupt,
                                                'Magnet: Error interrupting switch heater change')
                if len(response) > 0:
                    if response[0] == '?':
                        print('Magnet: Response to interruption of switch heater change was ?')
                else:
                    print('Magnet: No response to interruption of switch heater change')
        else:  # otherwise, finish task as expected
            response = self.serial_m.transmit(isobus_magnet+final,
                                            'Magnet: Error finalizing switch heater change')
            if final is not None:
                if len(response) > 0:
                    if response[0] == '?':
                        print('Magnet: Response to finalizing switch heater change was ?')
                else:
                    print('Magnet: No response to finalizing switch heater change')
        self._action_interrupt = False
        sleep(5) #wait for switch heater change to be finalized by the iPS (CRYOFREE UPDATE)
        response = self.serial_m.transmit(isobus_magnet+'X', 'Magnet: Error retrieving status')
        field_movement = FIELD_INACTIVE
        if response[7:9] in ['H0', 'H2']:
            self._switch_status = SWITCH_DISABLED
        elif response[7:9] == 'H1':
            self._switch_status = SWITCH_ENABLED
            #CRYOFREE TO-DO
            #add a wait 5 minutes loop while the switch warms up before can ramp to field
            
            
            field_movement = FIELD_HOLD
        elif response[7:9] in ['H5', 'H8']:
            print('Magnet: Switch heater fault; disconnecting...')
            if self.serial_m.is_open or self.serial_t.is_open:
                self.serial_disconnect()
        else:
            print('Magnet: No status returned')
        self._action_thread = None
        setpoint = SETPOINT_INACTIVE
        if self.serial_m.is_open and self._field_connect:
            setpoint = SETPOINT_ACTIVE
        if self.gui.beep.get():
            print('\a', end='')
        self.gui.set_field_frame(connected=self._field_connect, switch_setting=self._switch_status,
                                 field_movement=field_movement, setpoint_change=setpoint)
        self.get_field()
        return

    def _monitor_field(self):
        """
        Daemon thread function to update the field every `_field_delay' seconds. Does not print each message/response
        to std_out so as to prevent clutter from background monitoring operations.
        """
        while self.serial_m.is_open and self._field_connect:
            field = self.serial_m.transmit(isobus_magnet + 'R7', 'MagControl: Error reading field output', False)
            if len(field) > 0:
                if field[0] == 'R':
                    field = field[1:]
                else:
                    field = '—'
            else:
                field = '—'
            self.gui.update_fields(current_field=field)
            sleep(self._field_delay)
        # after 'while' loop breaks
        self.gui.update_fields(current_field='—')
        return

    def _monitor_sweep(self, gotoset):
        if self.serial_m.is_open and self._field_connect and self._switch_status == SWITCH_ENABLED:
            if gotoset:
                self.serial_m.transmit(isobus_magnet+'A1')  # go to set point
            else:
                self.serial_m.transmit(isobus_magnet+'A2')  # go to zero
            self._field_delay = 1
            while self.serial_m.is_open and self._field_connect and self._switch_status == SWITCH_ENABLED:
                if self._action_interrupt:
                    break
                current = self.serial_m.transmit(isobus_magnet+'R7', 'MagControl: Error reading field output', False)
                target = self.serial_m.transmit(isobus_magnet+'R8', 'MagControl: Error reading field set point', False)
                if not gotoset:
                    target = 'R0' #what should be return message at Zero Field
                try:
                    current = float(current[1:])
                    target = float(target[1:])
                except ValueError:
                    print('MagControl: Error at field', str(current), 'with target', str(target))
                    break  # if we have communication problems, quit
                if abs(current - target) < 0.0001:
                    break
                sleep(1)
            self._field_delay = delay_sensor
            self._action_interrupt = False
            self._action_thread = None
            if self.gui.beep.get():
                print('\a', end='')
            if 'A0' not in self.serial_m.transmit(isobus_magnet + 'X', 'MagControl: Error with Examine'): #added for CRYOFREE - used to always send the A0 command
                self.serial_m.transmit(isobus_magnet + 'A0')  # hold - NEED FOR CRYOFREE?
            self.gui.set_field_frame(connected=self._field_connect, switch_setting=self._switch_status,
                                     field_movement=FIELD_HOLD)
        return

    def goto_field(self):
        if self.serial_m.is_open and self._field_connect and self._switch_status == SWITCH_ENABLED:
            if self._action_thread is not None:  # if an action is already being taken
                print('Magnet: Action is currently being taken; interrupt or try again afterwards')
            else:  # if there are no background threads taking action
                self.gui.set_field_frame(connected=self._field_connect, field_movement=FIELD_GOTO)
                self._action_thread = Thread(target=self._monitor_sweep, args=(True,))
                self._action_thread.start()
        else:
            print('Magnet: Switch heater must be enabled to alter field strength')

    def zero_field(self):
        if self.serial_m.is_open and self._field_connect and self._switch_status == SWITCH_ENABLED:
            if self._action_thread is not None:  # if an action is already being taken
                print('Magnet: Action is currently being taken; interrupt or try again afterwards')
            else:  # if there are no background threads taking action
                self.gui.set_field_frame(connected=self._field_connect, field_movement=FIELD_ZERO)
                self._action_thread = Thread(target=self._monitor_sweep, args=(False,))
                self._action_thread.start()
        else:
            print('Magnet: Switch heater must be enabled to alter field strength')

    def interrupt(self):
        if self._action_thread is not None:
            self._action_interrupt = True
        else:
            self._action_interrupt = False

    def set_field(self, *args):
        if self.serial_m.is_open and self._field_connect:
            field = self.gui.user_field()
            if len(field) > 0:
                if field[-1] == 'T':  # tolerate Tesla unit
                    field = field[:-1]
            try:
                field = float(field)
                if abs(field) > max_field:  # if not in allowed range
                    field = None
            except (ValueError, TypeError):
                field = None
            if field is None:
                print('Magnet: Invalid set point request of', self.gui.user_field(), '\a')  # try to beep
            else:
                response = self.serial_m.transmit(isobus_magnet + 'J' + format_field(field, 1))
                if response[0] == '?':
                    print('Magnet: Instrument confused by', self.gui.user_field(), '\a')  # try to beep
        self.get_field()

    def get_field(self): #gets field set point
        field = '—'
        if self.serial_m.is_open and self._field_connect:
            response = self.serial_m.transmit(isobus_magnet + 'R8', 'Magnet: Error reading set point')
            if response[0] == 'R':
                field = response[1:]
        self.gui.update_fields(setpoint=field)
        if field == '—':
            return None
        return field
        
        
    ### ROB'S UPDATES FOR THE CRYOFREE SYSTEM
    def get_ramp_rate(self): #gets field set point
        ramp_rate = '—'
        if self.serial_m.is_open and self._field_connect:
            response = self.serial_m.transmit(isobus_magnet + 'R9', 'Magnet: Error reading ramp rate', False)
            if response[0] == 'R':
                ramp_rate = response[1:]
        print('Magnet Ramp Rate:',ramp_rate, 'T/min')
        return ramp_rate
    
    def get_magnet_temp(self): #gets magnet temperature
        mag_temp = '—'
        if self.serial_m.is_open and self._field_connect:
            response = self.serial_m.transmit(isobus_magnet + 'R10', 'Magnet: Error reading temperature', False)
            if response[0] == 'R':
                mag_temp = response[1:]
        print('Magnet Temp:',mag_temp, 'K')
        return mag_temp
    
    def get_current_magnet_field(self):
        if self.serial_m.is_open and self._field_connect:
            field = self.serial_m.transmit(isobus_magnet + 'R7', 'MagControl: Error reading field output', False)
            if len(field) > 0:
                if field[0] == 'R':
                    field = field[1:]
                else:
                    field = None
            else:
                field = None
        print('Current Magnet Field: %s T'%field)
        return field
    
    def get_sample_temp(self):
        if self.serial_t.is_open and self._temp_connect:
            temp3 = self.serial_t.transmit(isobus_temp +READ+SAMPLE+CURRENT_TEMP, 'TempControl: Error reading sample temp sensor')
            if len(temp3) > 0:
                if temp3.split(':')[-1] != 'INVALID':
                    temp3 = temp3.split(':')[-1]
                else:
                    temp3 = None
            else:
                temp3 = None
        return temp3.replace('K','')

    def get_vti_temp(self):
        if self.serial_t.is_open and self._temp_connect:
            temp1 = self.serial_t.transmit(isobus_temp +READ+VTI+CURRENT_TEMP, 'TempControl: Error reading temp sensor 1')
            if len(temp1) > 0:
                if temp1.split(':')[-1] != 'INVALID':
                    temp1 = temp1.split(':')[-1]
                else:
                    temp1 = None
            else:
                temp1 = None
        return temp1.replace('K','')
    
    def get_pt2_temp(self):
        if self.serial_t.is_open and self._temp_connect:
            temp1 = self.serial_t.transmit(isobus_temp +READ+PT2+CURRENT_TEMP, 'TempControl: Error reading PT2 Temp sensor')
            if len(temp1) > 0:
                if temp1.split(':')[-1] != 'INVALID':
                    temp1 = temp1.split(':')[-1]
                else:
                    temp1 = None
            else:
                temp1 = None
        return temp1.replace('K','')
        
    def get_nv_pressure(self, print_out=True):
        if self.serial_t.is_open and self._temp_connect:
            val = self.serial_t.transmit(isobus_temp +READ+NV+CURRENT_PRES, 'TempControl: Error reading Needle Valve Pressure', print_out)
            if len(val) > 0:
                if val.split(':')[-1] != 'INVALID':
                    val = val.split(':')[-1]
                else:
                    val = None
            else:
                val = None
        return val.replace('mB','')

    def get_nv_percent(self):
        if self.serial_t.is_open and self._temp_connect:
            val = self.serial_t.transmit(isobus_temp +READ_NV_PERC, 'TempControl: Error reading Needle Valve Percent')
            if len(val) > 0:
                if val.split(':')[-1] != 'INVALID':
                    val = val.split(':')[-1]
                else:
                    val = None
            else:
                val = None
        return val
    
    def set_nv(self, *args): # NEEDS NEW COMMAND UPDATE
        if self.serial_t.is_open and self._temp_connect:
            nv_val = self.gui.user_nv()
            
            try:
                nv_val = float(nv_val)
                if nv_val<0 or nv_val>100:  # if not in allowed range
                    nv_val = None
            except (ValueError, TypeError):
                nv_val = None
            if nv_val is None:
                print('TempControl: Invalid NV set point request of', self.gui.user_nv(), '\a')  # try to beep
            else:
                self.serial_t.transmit(isobus_temp+SET+NV+AUTO_SET+':OFF', 'TempControl: Error setting heater to Auto and NV to Manual') #Set NV control to Manual
                print('Setting NV to Manual')
                response = self.serial_t.transmit(isobus_temp +SET+NV+SETPT_PERC+':'+str(nv_val))
                if response[0] == '?':
                    print('TempControl: Instrument (NV) confused by', self.gui.user_nv(), '\a')  # try to beep
                
        
    def refresh_magnet_gui(self):
        # Check the magnet controller
        success = True  # flag to monitor successful communication to temperature controller
        version = self.serial_m.transmit(isobus_magnet+'V', 'Magnet: Error receiving version')
        field_movement = FIELD_INACTIVE
        if version == isobus_magnet_version:  # if version matches expectation
            status = self.serial_m.transmit(isobus_magnet+'X', 'Magnet: Error receiving status')
            # `status' takes form `XnAnCnSnnHn' 
            if len(status) != 12 or ''.join([list(status)[i] for i in [0, 3, 5, 7, 9]]) != 'XACHM':
                print('Magnet: Uninterpretable status', status)
                success = False
                
            if status[0:3] != 'X00':  # If not `X00', status is not normal so don't initiate control
                print('Magnet: Non-normal status error', status[0:3], 'in', status)
                success = False
                
            if status[7:9] in ['H0', 'H2']:  # if switch heater off ('H0' at zero field, 'H2' at nonzero field)
                self._switch_status = SWITCH_DISABLED
            elif status[7:9] == 'H1':
                self._switch_status = SWITCH_ENABLED
            else:  # if 'H5' (fault) or 'H8' (missing), don't proceed
                print('Magnet: Switch heater fault or missing', status[7:9], 'in', status)
                success = False
                
            if status[3:5]=='A0': #check movement of the field
                field_movement = FIELD_HOLD
            elif status[3:5]=='A1':
                field_movement = FIELD_GOTO
            elif statu[3:5]=='A2':
                field_movement = FIELD_ZERO
            else:
                print('Magnet Error: Field Status', status[3:5], 'in', status)
                success=False
            # DEBUG what `Xmn', `Mmn', and `Pmn' settings are allowed?
        else:
            print('Magnet: Version error', '('+str(version)+')')
            success = False
        if success:
            self._field_connect = True
            self.get_field()
            setpoint = SETPOINT_ACTIVE
        else:
            self.gui.update_fields(setpoint='fail')
            setpoint = SETPOINT_INACTIVE
        self.gui.set_field_frame(connected=self._field_connect, switch_setting=self._switch_status,
                                 field_movement=field_movement, setpoint_change=setpoint)
        
    def set_field_and_go(self,newfield = 0.0):
        self.gui.update_fields(setpoint=newfield) #update field setpoint in GUI
        self.set_field() #update field setpoint at instrument
        self.goto_field() #go to new field
        #Wait for new field to be reached
        while self._action_thread is not None:
            sleep(10)
        print('At New Field:', newfield, 'T')
        
    def vtvh_interrupt(self):
        print('Interrupting VTVH')
        self.interrupt()
        if self._vtvh_thread is not None:
            self._vtvh_interrupt = True
        else:
            self._vtvh_interrupt = False
        
        
    def _collect_full_vtvh(self, field_list, temp_list, scanTime):      
        print('Starting Full VTVH Run')
        #measure scan duration??

        #Check if fields are in correct range
        if any(abs(float(h)) > 7 for h in field_list):
            print('Error in Fields: Must be between -7 and 7 T')
            self.vtvh_interrupt()
        else:
            print('Fields Read in Correctly')
            
        #Check if temps are in correct range
        if any(float(t) < 0 for t in temp_list) or any(float(t) > 300 for t in temp_list):
            print('Error in Temps: Must be between 0 and 300 K')
            self.vtvh_interrupt()
        else:
            print('Temps Read in Correctly')
        
        #Read the inputted time for scan and use as delay
        scanDelay=int(scanTime)
        if scanDelay > 0:
            print('Each scan takes %i seconds.'%scanDelay)
        else:
            print('Invalid Time Delay for Scan')
            self.vtvh_interrupt()
            
        #estimate time for run and print 
        runtime=self.estimate_runtime(field_list,temp_list,scanDelay)
        print('Est. Time for VTVH: %.2f hours'%runtime)
        
        #turn on switch heater
        if self._switch_status in [SWITCH_DISABLED, SWITCH_WARMING, SWITCH_COOLING] and not self._vtvh_interrupt:
            self.engage_switch_heater()
            print('Waiting for switch heater to warm up (5 mins).')
            sleep(300)
        elif self._switch_status == SWITCH_ENABLED and not self._vtvh_interrupt:
            print('Switch Heater ON: Waiting 5 Mins.')
            sleep(300) #Wait 5 minutes even if switch heater is on
        else: #interrupt or switch error
            self.vtvh_interrupt()
        
        #setup logging
        if self._field_connect:
            self.vtvh_logger.assign_field_log_fxns(get_mag_temp=self.get_magnet_temp, get_mag_field=self.get_current_magnet_field, get_field_set=self.get_field)
        if self._temp_connect:
             self.vtvh_logger.assign_temp_log_fxns(get_vti_temp=self.get_vti_temp, get_sample_temp=self.get_sample_temp, get_pt2_temp=self.get_pt2_temp, get_nv_pressure=self.get_nv_pressure, get_nv_percent=self.get_nv_percent, get_temp_set=self.get_temperature)
        if os.path.exists(self.gui.user_vtvh_dir()):
            self.vtvh_logger.set_dirpath(self.gui.user_vtvh_dir())
            self.vtvh_logger.set_log_file(self.gui.user_vtvh_dir()+'/vtvh_log.csv')
        else:
            self.vtvh_logger.set_log_file('UserLogs/vtvh_log.csv')
            
        #go to each field
        scan_num=1
        for h in field_list:
            #check if interrupt was pressed
            if self._vtvh_interrupt == True:
                break
            #check ramp rate
            if float(self.get_ramp_rate()) > 0.154:
                print('RAMP RATE EXCEEDS LIMIT: Ending VTVH. Change Rate before proceeding.')
                self.vtvh_interrupt()
                break
            #check magnet temp
            if float(self.get_magnet_temp()) > 4.00:
                print('Magnet is Too Warm: Ending VTVH')
                self.vtvh_interrupt()
                break

            #Go to first temp in list while going to next field
            self.gui.update_temps(setpoint=str(temp_list[0])+'K')
            self.set_temperature()
            
            #go to next field
            self.set_field_and_go(newfield=h)
            #Let field stabilize
            sleep(30)
            print('Next Field Reached %s T'%str(h))
            
            #go to each temperature and scan
            for t in temp_list:
                #check if interrupt was pressed
                if self._vtvh_interrupt == True:
                    break

                #update temp setpoint on gui then on instrument
                self.gui.update_temps(setpoint=str(t)+'K')
                self.set_temperature()
                #wait 5 mins for temp to be reached/stabilize
                print('Waiting 5 mins for temp to stabilize')
                sleep(300)

                #check every minute to see if have reached the correct temp
                tempcheck_iters=0
                last3_temps=[float(self.get_sample_temp())]
                #old_criteria=abs(float(t)-float(self.get_sample_temp())) > 0.05
                while not (len(last3_temps)==3 and abs(float(t)-np.mean(last3_temps)) < 0.5 and np.std(last3_temps) < 0.01): #Temp Accuarcy Cutoff
                    print(len(last3_temps),np.mean(last3_temps),np.std(last3_temps))
                    if self._vtvh_interrupt == True:
                        break
                    sleep(60) #waits 1 min between temp checks
                    temp_chk=float(self.get_sample_temp())
                    last3_temps.append(temp_chk)
                    while len(last3_temps)>3:
                        last3_temps.pop(0)
                    tempcheck_iters+=1 #count number of checks done 
                    #if temp hasnt stabilized after 30 mins, interrupt the vtvh run
                    if tempcheck_iters>15:
                        if len(last3_temps)==3 and abs(float(t)-np.mean(last3_temps)) < 1.0 and np.std(last3_temps) < 0.05: #secondary criteria after 20 mins
                            print('Warning: Using Secondary Temp Criteria After 15mins')
                            break
                        else:
                            print('VTVH TIMEOUT: Temperature (%s K) Not Reached after 20 mins'%str(t))
                            self.vtvh_interrupt()
                            #TODO: If temp too hot, open needle valve more?
                        #read current, open like 10% more, wait, read temp, do again or break if too open
                    #exit loop when made it to new temp
                        
                #check if interrupt was pressed
                if self._vtvh_interrupt == True:
                    break
                    
                #print that made it to new temp
                print('Temps:', last3_temps)
                print(len(last3_temps),np.mean(last3_temps),np.std(last3_temps))
                print('Next Temp Reached %s K (took %i mins)'%(str(t),tempcheck_iters))

                #log at start of scan
                self.vtvh_logger.generate_vtvh_log(scan_num=scan_num)

                #take a scan 
                print('Taking a Scan - One Lamp Only')
                print('Scan Number %i'%scan_num)
                j1700.initiate_scan_onelamp() ##CHANGE WHEN GET NIR LAMP WORKING
                #Handle waiting for scan and logging during scan
                if scanDelay>300: #if scan is longer than 5 mins
                    wait_left=scanDelay
                    while wait_left > 300:
                        sleep(295)
                        self.vtvh_logger.generate_vtvh_log(scan_num=scan_num) #log every 5 mins
                        sleep(5)
                        wait_left-=300 #track how long left to wait
                    #wait remaining (less than 5 min) amount    
                    sleep(wait_left) 
                else:              
                    sleep(scanDelay) #wait for whole scan time

                #log at end of scan
                self.vtvh_logger.generate_vtvh_log(scan_num=scan_num, after=True)

                #iterate scan number
                scan_num+=1




        #TURN OFF SWITCH HEATER AT END AND IF DIDNT INTERRUPT
        if self._vtvh_interrupt==False and self._switch_status == SWITCH_ENABLED:
            self.disengage_switch_heater()
            print('Waiting for switch heater to cool (5 mins).')
            sleep(300)
        
        #set Cryofree GUI at END
        self.gui.set_cryofree_frame(connected=self._field_connect, vtvh_status=VTVH_INACTIVE)
        self._vtvh_interrupt = False
        print('VTVH Ended')
        self._vtvh_thread = None
    
    def start_vtvh(self, *args):
        if self.serial_m.is_open and self._field_connect:
            if self._vtvh_thread is not None:  # if an action is already being taken
                print('Magnet: VTVH is currently in progress; interrupt or try again afterwards')
            else:  # if there are no background threads taking action
                vhs=self.gui.user_vtvh_field()
                temps=self.gui.user_vtvh_temps()
                st=self.gui.user_scanTime()
                #parse minutes and seconds of scan time
                if ':' in st:
                    mins=st.split(':')[0]
                    secs=st.split(':')[1]
                    print('Scan Time Read as %i mins and %i secs'%(int(mins),int(secs)))
                    st=int(mins)*60+int(secs)
                #set Cryofree GUI
                self.gui.set_cryofree_frame(connected=self._field_connect, vtvh_status=VTVH_ACTIVE)
                #Line below controls what happens when click "Collect VTVH"
                self._vtvh_thread = Thread(target=self._collect_full_vtvh, args=(vhs,temps,st,))
                self._vtvh_thread.start()
        else:
            print('Must be Connected to Start VTVH.')
            
    def start_bg_logging(self, *args):
        if (self.serial_t.is_open or self.serial_m.is_open) and self._bglog_thread == None:
            if self._field_connect:
                self.bglogger.assign_field_log_fxns(get_mag_temp=self.get_magnet_temp, get_mag_field=self.get_current_magnet_field, get_field_set=self.get_field)
            if self._temp_connect:
                self.bglogger.assign_temp_log_fxns(get_vti_temp=self.get_vti_temp, get_sample_temp=self.get_sample_temp, get_pt2_temp=self.get_pt2_temp, get_nv_pressure=self.get_nv_pressure, get_nv_percent=self.get_nv_percent, get_temp_set=self.get_temperature)
            self._bglog_thread=Thread(target=self._bg_logging)
            self._bglog_thread.start()
                
        else:
            print('Not Connected or Already Logging: Cannot start logging')
        
            
    def _bg_logging(self):
        end_now=False
        while (self.serial_t.is_open or self.serial_m.is_open):
            print('Updating Background Log')
            self.bglogger.generate_bg_log()
            wait_time = self.bglogger.bg_log_delay*60 #seconds
            while wait_time>0:
                if (self.serial_t.is_open or self.serial_m.is_open):
                    wait_time-=10
                    sleep(10)
                else:
                    break
        self._bglog_thread=None
        
    def estimate_runtime(self, fields, temps, scanSecs):
        time_sum=0 
        #0 to first field
        time_sum+=abs(0-float(fields[0]))/(0.15*60)
        #time to each of other fields
        for i in range(1,len(fields)):
            time_sum+=abs(float(fields[i-1])-float(fields[i]))/(0.15*60)
        #time for temps
        time_sum+=(len(fields)*len(temps)*0.25)
        time_sum+=(len(fields)*len(temps)*(scanSecs/(60*60)))
        return time_sum #in hours
            
            


if __name__ == '__main__':
    print_to_log('------------------------------New Session Started')
    print(datetime.datetime.now())
    app = Application()
    app.run()
