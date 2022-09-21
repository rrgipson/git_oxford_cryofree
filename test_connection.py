from time import sleep
from threading import Thread
from oxford import SerialPort, default_comport
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

# Magnet controller settings
isobus_magnet = '@1'
isobus_magnet_version = 'IPS    Version  4.01 (c) OXFORD 2011'
magnet_return_control = 'C1'  # return instrument to 'C0' (LOCAL?), 'C1' (REMOTE & UNLOCKED) or 'C2' (REMOTE & LOCKED)
com_port='COM3'
len_x= 12 #length of the eXamine command @1X

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

# Connect to magnet controller
success = True  # flag to monitor successful communication to temperature controller
version = my_serial.transmit(isobus_magnet+'V', 'Magnet: Error receiving version')
print(isobus_magnet+'V', ' returned ', str(version))
if version == isobus_magnet_version:  # if version matches expectation
    status = my_serial.transmit(isobus_magnet+'X', 'Magnet: Error receiving status')
    # `status' takes form `XnAnCnSnnHnLn' as in ITC503 manual
    if len(status) != len_x or ''.join([list(status)[i] for i in [0, 3, 5, 7, 9]]) != 'XACHM':
        print('Magnet: Uninterpretable status', status)
        success = False
    if status[0:3] != 'X00':  # If not `X00', status is not normal so don't initiate control
        print('Magnet: Non-normal status error', status[0:3], 'in', status)
        success = False
    if status[7:9] in ['H0', 'H2']:  # if switch heater off ('H0' at zero field, 'H2' at nonzero field)
        print('Switch Heater OFF based on X')
    elif status[7:9] == 'H1':
        print('Switch Heater ON based on X')
    else:  # if 'H5' (fault) or 'H8' (missing), don't proceed
        print('Magnet: Switch heater fault or missing', status[7:9], 'in', status)
        success = False
    # DEBUG what `Xmn', `Mmn', and `Pmn' settings are allowed?
else:
    print('Magnet: Version error')
    success = False
if success:
    mag_temp=my_serial.transmit(isobus_magnet+'R10', error_message='Error Reading Temp')  # Read Magnet Temp
    print('Magnet Temperature= ', mag_temp[1:], ' K')


nxt=input("Command to send to magnet (quit to close):")
while nxt !='quit':
    if nxt!= 'scan' and 'X' not in nxt and 'R' not in nxt and 'V' not in nxt:
        yn=input("Are you sure you want to send an action command?(y/n)")
        if yn=='y':
            mag_temp=my_serial.transmit(isobus_magnet+nxt, error_message='Error Performing Task')
    elif nxt == 'scan':
        j1700.initiate_scan_onelamp()
    else:
        mag_temp=my_serial.transmit(isobus_magnet+nxt, error_message='Error Reading')
        
    nxt=input("Command to send to magnet (quit to close):")

#set box back to local
my_serial.transmit(isobus_magnet+'C0', error_message='Error Setting to Local')
my_serial.close()
