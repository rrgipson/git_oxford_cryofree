from time import sleep
from threading import Thread
from oxford import SerialPort
import spectrometer as j1700
from scpi_iTC import *
##In OXFORD.PY
'''
Updated baudrate to 115200
Switched all \r\n end characters to \r
Does the Q2 command work? Line 138- removed and changed strip commands
Changed number of stopbits to 1
'''

# Appearance settings, delay settings, and default COM port
delay_sensor = 5  # time between updates for sensors

# Temperature controller settings
isobus_temp = '@2'
isobus_temp_version = '81'
min_temp, max_temp = 0, 300
temperature_sensor = 1  # sensor 1, sensor 2, or sensor 3 for auto regulation to the set point
temperature_return_control = 'C3'  # return instrument to 'C0' (LOCAL & LOCKED) or 'C2' (LOCAL & UNLOCKED) or C3 Remote and Unlocked
com_port='COM4'
len_x= 13 #length of the eXamine command @2X

"""
Attempts to connect to the Oxford instrument through the requested COM port. Sends several messages to both the
temperature control and magnet control:
    ???'Q2' asks for a \n at the end of each message (helps Windows find the end of each communication) - disabled now
    'V' to check that the version matches the one expected
    'C1' to switch control to REMOTE & UNLOCKED 
    'X' to inspect the current state of the system
Based on the current state of the system, prepares the system in a specific state.
"""
# Try to open communication to the COM port, and switch 'Connect' button to 'Disconnect' if successful
my_serial=SerialPort()
my_serial.port = com_port
if my_serial.is_open:  # if the port is somehow already open, close it
    my_serial.close()
if not my_serial.open():  # if open() returns False, then opening has failed
    print("Failed to connect!")
print('is_open: ', my_serial.is_open)

# Connect to temperature controller
success = True  # flag to monitor successful communication to temperature controller
version = my_serial.transmit(isobus_temp+READ_VERSION, 'TempControl: Error receiving version')
if version.split(':')[-1] == isobus_temp_version:  # if version matches expectation
    status = my_serial.transmit(isobus_temp+READ_ALARMS, 'TempControl: Error retrieving alarms')
    # Check if any alarms have been triggered
    if status.split(':')[-1] == '':
        pass
    elif status.split(':')[-1] == 'DB8.T1\tOpen Circuit;':
        print('-'*10)
        print('Sample Probe Unplugged! (If not, other error present.)')
        print('-'*10)
    else:
        success = False
else:
    print('TempControl: Version error', '('+str(version)+')')
    success = False
if success:
    nxt=input("Command to send to iTC (quit to close):")
    while nxt !='quit':
        res=my_serial.transmit(isobus_temp+nxt, error_message='Error Reading')
        if res.split(':')[-1] == 'INVALID':
            print('Correctly Interpreted an Error')
        nxt=input("Command to send to iTC (quit to close):")

my_serial.close()
