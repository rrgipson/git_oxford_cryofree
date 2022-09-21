import subprocess

def event(script='scan_duration.ahk'):
    program = 'C:/Program Files/AutoHotkey/AutoHotkey.exe'
    return subprocess.run((program, script), capture_output=True)
