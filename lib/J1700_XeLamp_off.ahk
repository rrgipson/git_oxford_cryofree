; AutoHotKey script for turning off the Xe Arc Lamp on the J1700 Spectra Measurement Software.

; Remove any click delays so someone using the mouse has less of a chance to screw things up
SetControlDelay, -1
; Activate Spectra Measurement window
WinActivate, Spectra Measurement - J1700/D001461900
; Search Spectra Measurement window for the start button image within the specified X1, Y1, X2, and Y2 window pixel area
; Store the location as FoundX and FoundY
ImageSearch, FoundX, FoundY, 150, 50, 1920, 550, C:\Users\Jasco\Desktop\git_oxford_cryofree\lib\J1700_XeLamp.png
; Click the FoundX and FoundY pixel location on the Spectra Measurement Window 
ControlClick, X%FoundX% Y%FoundY%, Spectra Measurement - J1700/D001461900
; MsgBox % "Xe Lamp Off Button Found at X " . FoundX . " " . "Y " . FoundY . " - Lamp turned off"
FileAppend, Xe Lamp Off Button Found at X= %FoundX% and Y= %FoundY%, *
