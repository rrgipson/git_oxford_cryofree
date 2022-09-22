from time import sleep
from threading import Thread
from oxford import SerialPort, default_comport_m, default_comport_t
from gui import *
import spectrometer as j1700
from logger import *

# Appearance settings, delay settings, and default COM port
delay_sensor = 5  # time between updates for sensors

# Temperature controller settings
isobus_temp = '@2' 
isobus_temp_version = 'ITC503 Version  4.01 (c) OXFORD 2011'
min_temp, max_temp = 0, 300
temperature_sensor = 3  # sensor 1, sensor 2, or sensor 3 for auto regulation to the set point - UPDATED FOR CRYOFREE to sample
temperature_return_control = 'C3'  # return instrument to 'C0' (LOCAL & LOCKED) or 'C2' (LOCAL & UNLOCKED) or C3 Remote and Unlocked

# Magnet controller settings - UPDATED FOR CRYOFREE
isobus_magnet = '@1'
isobus_magnet_version = 'IPS    Version  4.01 (c) OXFORD 2011'
magnet_return_control = 'C1'  # return instrument to 'C0' (LOCAL?), 'C1' (REMOTE & UNLOCKED) or 'C2' (REMOTE & LOCKED)
max_field = 7  # maximum strength of magnetic field
switch_wait = 5  # seconds to wait when turning switch heater on/off

#send stderr to file - uncomment to write errors to file
#sys.stderr = open('UserLogs/error_log.txt', 'a+')

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
        self.gui.update_temps(setpoint_sensor=temperature_sensor)
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
        version = self.serial_t.transmit(isobus_temp+'V', 'TempControl: Error receiving version')
        if version == isobus_temp_version:  # if version matches expectation
            status = self.serial_t.transmit(isobus_temp+'X', 'TempControl: Error retrieving status')
            # `status' takes form `XnAnCnSnnHnLn' as in ITC503 manual
            if len(status) != 13 or ''.join([list(status)[i] for i in [0, 2, 4, 6, 9, 11]]) != 'XACSHL':
                print('TempControl: Uninterpretable status', status)
                success = False
            if status[0:2] != 'X0':  # If not `X0', status is not normal so don't initiate control
                print('TempControl: Non-normal status error', status[0:2], 'in', status)
                success = False
            # DEBUG what `An', `Snn', and `Ln' settings are allowed?
        else:
            print('TempControl: Version error', '('+str(version)+')')
            success = False
        if success:
            self.serial_t.transmit(isobus_temp+'C3')  # set status to REMOTE & UNLOCKED - CRYOFREE
            self.serial_t.transmit(isobus_temp+'H'+str(temperature_sensor))  # set temperature sensor for set point - CRYOFREE - MIGHT NEED TO DELETE IF NEED TO SET BOTH SENSORS WHENEVER CHANGE SET
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
    
                
    def serial_disconnect(self):
        if self.serial_t.is_open:
            if self._temp_connect:
                self.serial_t.transmit(isobus_temp+temperature_return_control)
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

    def _monitor_temperature(self): 
        """
        Daemon thread function to update the temperature every `_temp_delay' seconds. Does not print each
        message/response to std_out so as to prevent clutter from background monitoring operations.
        """
        while self.serial_t.is_open and self._temp_connect:
            sensor1 = self.serial_t.transmit(isobus_temp + 'R1', 'TempControl: Error reading sensor 1', False)
            if len(sensor1) > 0:
                if sensor1[0] == 'R':
                    sensor1 = sensor1[1:]
                else:
                    sensor1 = '—'
            else:
                sensor1 = '—'
            sensor3 = self.serial_t.transmit(isobus_temp + 'R3', 'TempControl: Error reading sensor 3', False)
            if len(sensor3) > 0:
                if sensor3[0] == 'R':
                    sensor3 = sensor3[1:]
                else:
                    sensor3 = '—'
            else:
                sensor3 = '—'
                
            #CRYOFREE Added NV
            current_nv= self.get_nv_value()
            
            self.gui.update_temps(sensor1=sensor1, sensor3=sensor3, current_nv=current_nv)
            sleep(self._temp_delay)
        # after 'while' loop breaks
        self.gui.update_temps(sensor1='—', sensor3='—', current_nv= '—')
        return

    def set_temperature(self, *args):
        if self.serial_t.is_open and self._temp_connect:
            self.serial_t.transmit(isobus_temp+'A1', 'TempControl: Error setting heater to Auto') #CRYOFREE - CURRENTLY SETS HEATER TO AUTO AND GAS TO MANUAL
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
                    
                self.serial_t.transmit(isobus_temp+'H1', 'TempControl: Error changing to VTI Temp') #Change to VTI Temp sensor
                if temperature <= 10:
                    vti_temp= (0.988*float(temperature)) - 0.063 #based on regression of factor tested temp offsets
                else: 
                    vti_temp= (0.984*float(temperature)) - 0.999

                stop=False
                print("Setting VTI Temp to", vti_temp)
                vti_response = self.serial_t.transmit(isobus_temp + 'T' + format_temp(vti_temp))
                if vti_response[0] == '?':
                    print('TempControl: Instrument confused by VTI Temp Setting', '\a')  # try to beep
                    stop=True
                    
                if not stop:
                    self.serial_t.transmit(isobus_temp+'H3', 'TempControl: Error changing back to Sample Temp') #Change back to Sample Temp sensor
                    print("Setting Sample Temp to", temperature)
                    response = self.serial_t.transmit(isobus_temp + 'T' + format_temp(temperature))
                    if response[0] == '?':
                        print('TempControl: Instrument confused by', self.gui.user_temperature(), '\a')  # try to beep

        self.get_temperature()

    def get_temperature(self): #Gets temp set point
        temperature = '—'
        if self.serial_t.is_open and self._temp_connect:
            response = self.serial_t.transmit(isobus_temp+'R0', 'TempControl: Error reading set point')
            if response[0] == 'R':
                temperature = response[1:]
        self.gui.update_temps(setpoint=temperature)

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
        
        
    ### ROB'S UPDATES FOR THE CRYOFREE SYSTEM
    def get_ramp_rate(self): #gets field set point
        ramp_rate = '—'
        if self.serial_m.is_open and self._field_connect:
            response = self.serial_m.transmit(isobus_magnet + 'R9', 'Magnet: Error reading ramp rate')
            if response[0] == 'R':
                ramp_rate = response[1:]
        print('Magnet Ramp Rate:',ramp_rate, 'T/min')
        return ramp_rate
    
    def get_magnet_temp(self): #gets magnet temperature
        mag_temp = '—'
        if self.serial_m.is_open and self._field_connect:
            response = self.serial_m.transmit(isobus_magnet + 'R10', 'Magnet: Error reading temperature')
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
        return field
    
    def get_sample_temp(self):
        if self.serial_t.is_open and self._temp_connect:
            temp3 = self.serial_t.transmit(isobus_temp + 'R3', 'TempControl: Error reading temp sensor 3', False)
            if len(temp3) > 0:
                if temp3[0] == 'R':
                    temp3 = temp3[1:]
                else:
                    temp3 = None
            else:
                temp3 = None
        return temp3

    def get_vti_temp(self):
        if self.serial_t.is_open and self._temp_connect:
            temp1 = self.serial_t.transmit(isobus_temp + 'R1', 'TempControl: Error reading temp sensor 1', False)
            if len(temp1) > 0:
                if temp1[0] == 'R':
                    temp1 = temp1[1:]
                else:
                    temp1 = None
            else:
                temp1 = None
        return temp1
        
    def get_nv_value(self):
        if self.serial_t.is_open and self._temp_connect:
            val = self.serial_t.transmit(isobus_temp + 'R7', 'TempControl: Error reading Needle Valve', False)
            if len(val) > 0:
                if val[0] == 'R':
                    val = val[1:]
                else:
                    val = None
            else:
                val = None
        return val
    
    def set_nv(self, *args):
        if self.serial_t.is_open and self._temp_connect:
            self.serial_t.transmit(isobus_temp+'A1', 'TempControl: Error setting heater to Auto and NV to Manual') #CRYOFREE - CURRENTLY SETS HEATER TO AUTO AND GAS TO MANUAL
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
                response = self.serial_t.transmit(isobus_temp + 'G' + str(nv_val))
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
        
    def _collect_isotherm(self, field_list, scanTime):      
        #measure scan duration??

        #Check if fields are in correct range
        if any(abs(float(h)) > 7 for h in field_list):
            print('Error in Fields: Must be between -7 and 7 T')
            self.vtvh_interrupt()
        
        #Read the inputted time for scan and use as delay
        scanDelay=int(scanTime)
        if scanDelay > 0:
            print('Each scan takes %i seconds.'%scanDelay)
        else:
            print('Invalid Time Delay for Scan')
            self.vtvh_interrupt()
        
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
        self.vtvh_logger.set_log_file('UserLogs/vtvh_log.csv')
        if self._field_connect:
            self.vtvh_logger.assign_field_log_fxns(get_mag_temp=self.get_magnet_temp, get_mag_field=self.get_current_magnet_field)
        if self._temp_connect:
             self.vtvh_logger.assign_temp_log_fxns() #TODO ADD TEMP GET FUNCTIONS
        
        
        #go to each field and scan
        scan_num=0
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
            
            #go to next field
            self.set_field_and_go(newfield=h)
            #Let field stabilize
            sleep(30)
            
            #check if interrupt was pressed
            if self._vtvh_interrupt == True:
                break
            
            #log at start of scan
            self.vtvh_logger.generate_vtvh_log(scan_num=scan_num)
            
            #take a scan 
            print('Taking a Scan')
            j1700.initiate_scan_onelamp() ##CHANGE WHEN GET NIR LAMP WORKING
            sleep(scanDelay) #for scan waiting
            
            #log at end of scan
            self.vtvh_logger.generate_vtvh_log(scan_num=scan_num)
            
            #iterate scan number
            scan_num+=1

        #Does not return to 0 at end because this is commented out
        #if didn't end at zero and didn't interrupt, go to zero
        #if int(field_list[-1]) != 0 and self._vtvh_interrupt==False:
        #    self.zero_field()

        #TODO TURN OFF SWITCH HEATER AT END AND IF DIDNT INTERRUPT
        if self._vtvh_interrupt==False and self._switch_status == SWITCH_ENABLED:
            self.disengage_switch_heater()
            print('Waiting for switch heater to cool (5 mins).')
            sleep(300)
        
        #Currently leaves switch heater on at end of isotherm
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
                st=self.gui.user_scanTime()
                #set Cryofree GUI
                self.gui.set_cryofree_frame(connected=self._field_connect, vtvh_status=VTVH_ACTIVE)
                self._vtvh_thread = Thread(target=self._collect_isotherm, args=(vhs,st,))
                self._vtvh_thread.start()
        else:
            print('Must be Connected to Start VTVH.')
            
    def start_bg_logging(self, *args):
        if (self.serial_t.is_open or self.serial_m.is_open) and self._bglog_thread == None:
            if self._field_connect:
                self.bglogger.assign_field_log_fxns(get_mag_temp=self.get_magnet_temp, get_mag_field=self.get_current_magnet_field)
            if self._temp_connect:
                self.bglogger.assign_temp_log_fxns(get_vti_temp=self.get_vti_temp, get_sample_temp=self.get_sample_temp, get_nv_pressure=self.get_nv_value)
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
            
            


if __name__ == '__main__':
    print(datetime.datetime.now())
    app = Application()
    app.run()
