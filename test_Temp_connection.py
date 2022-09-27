from time import sleep
from threading import Thread
from oxford import SerialPort
import spectrometer as j1700
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
isobus_temp_version = 'ITC503 Version  4.01 (c) OXFORD 2011'
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
version = my_serial.transmit(isobus_temp+'V', 'TempControl: Error receiving version')
if version == isobus_temp_version:  # if version matches expectation
    status = my_serial.transmit(isobus_temp+'X', 'TempControl: Error retrieving status')
    # `status' takes form `XnAnCnSnnHnLn' as in ITC503 manual
    if len(status) != len_x or ''.join([list(status)[i] for i in [0, 2, 4, 6, 9, 11]]) != 'XACSHL':
        print('TempControl: Uninterpretable status', status)
        success = False
    if status[0:2] != 'X0':  # If not `X0', status is not normal so don't initiate control
        print('TempControl: Non-normal status error', status[0:2], 'in', status)
        success = False
    # DEBUG what `An', `Snn', and `Ln' settings are allowed?
else:
    print('TempControl: Version error', '('+str(version)+')')
    success = False


nxt=input("Command to send to magnet (quit to close):")
while nxt !='quit':
    if nxt!= 'scan' and 'X' not in nxt and 'R' not in nxt and 'V' not in nxt:
        yn=input("Are you sure you want to send an action command?(y/n)")
        if yn=='y':
            res=my_serial.transmit(isobus_temp+nxt, error_message='Error Performing Task')
    elif nxt == 'scan':
        j1700.initiate_scan_onelamp()
    else:
        res=my_serial.transmit(isobus_temp+nxt, error_message='Error Reading')
        
    nxt=input("Command to send to iTC (quit to close):")

#set box back to local
my_serial.transmit(isobus_temp+temperature_return_control, error_message='Error Setting to Remote & Unlocked')
my_serial.close()
