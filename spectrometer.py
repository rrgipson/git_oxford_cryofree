"""Various functions to deploy AutoHotkey scripts to interact with the spectrophotometer through the JASCO software"""
import subprocess
from logger import print


"""AutoHotkey Settings for JASCO Spectrophotometer Control: These settings direct the program to the AutoHotkey
executable file and the AutoHotkey script that facilitates initialization of a scan on the JASCO spectropolarimeter."""
autohotkey_exe = 'C:\\Program Files\\AutoHotkey\\AutoHotkeyU64.exe' ## Edited by Jeff for J1700
script_scan_start = 'lib/J1700_scan_start.ahk' ## Edited by Jeff for J1700
script_scan_duration = 'lib/scan_duration_J1700.ahk' ## Edited by Jeff for J1700 8/5/21
default_user_folder = '~/Data'

def initiate_scan():
    print('Jasco scan event')
    autohotkey_event = subprocess.run((autohotkey_exe, script_scan_start)) ## Edited by Jeff for J1700

def measure_duration():
    print('Jasco scan event: measuring duration')
    autohotkey_event = subprocess.run((autohotkey_exe, script_scan_duration), capture_output=True)
    duration = autohotkey_event.stdout
    if isinstance(duration, bytes):
        duration = duration.decode('utf-8').strip('\r\n')
    try:
        duration = float(duration)
    except ValueError:
        duration = 0
    return duration

def initiate_scan_onelamp():
    print('Jasco scan event')
    #just added an additional enter press in order to close the popup asking for both lamps to be lit
    autohotkey_event = subprocess.run((autohotkey_exe, 'lib/J1700_scan_start_1lamp.ahk'), capture_output=True) ## Edited by Rob
    print(autohotkey_event.stdout.decode('utf-8').replace('\n',''))
    #print(autohotkey_event.stderr.decode('utf-8').replace('\r\n',''))
    
def turn_off_xe_lamp():
    print('Turning Off J-1700 Xe-Arc Lamp')
    autohotkey_event = subprocess.run((autohotkey_exe, 'lib/J1700_XeLamp_off.ahk'), capture_output=True) ## Edited by Rob
    print(autohotkey_event.stdout.decode('utf-8').replace('\n',''))
    
def turn_off_wx_lamp():
    print('Turning Off J-1700 Tungsten Halogen NIR Lamp')
    autohotkey_event = subprocess.run((autohotkey_exe, 'lib/J1700_WXLamp_off.ahk'), capture_output=True) ## Edited by Rob
    print(autohotkey_event.stdout.decode('utf-8').replace('\n',''))

def test_new_scan():
    print('Jasco scan event - testing new stop/timing procedure')
    #just added an additional enter press in order to close the popup asking for both lamps to be lit
    #also now waits for stop button to disappear 
    autohotkey_event = subprocess.run((autohotkey_exe, 'lib/J1700_scan_start_1lamp_wait2finish.ahk'), capture_output=True) ## Edited by Rob
    scan_status = autohotkey_event.stdout.decode('utf-8').replace('\n','')
    print(scan_status)
    if 'Error' in scan_status:
        return False
    else:
        return True
    
