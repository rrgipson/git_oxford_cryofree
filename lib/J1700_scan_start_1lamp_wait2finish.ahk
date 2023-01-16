; AutoHotKey script for starting a scan on the J-1700 Spectra Measurement Software.

; Remove any click delays so someone using the mouse has less of a chance to screw things up
SetControlDelay, -1
; Activate Spectra Measurement window
WinActivate, Spectra Measurement - J1700/D001461900
; Search Spectra Measurement window for the start button image within the specified X1, Y1, X2, and Y2 window pixel area
; Store the location as FoundX and FoundY
ImageSearch, FoundX, FoundY, 140, 50, 240, 150, C:\Users\Jasco\Desktop\git_oxford_cryofree\lib\J1700_startbutton.png
; Click the FoundX and FoundY pixel location on the Spectra Measurement Window 
ControlClick, X%FoundX% Y%FoundY%, Spectra Measurement - J1700/D001461900
; MsgBox % "Start Button Found at X " . FoundX . " " . "Y " . FoundY . " - Scan Initiated"
FileAppend, Start Button Found at X= %FoundX% and Y= %FoundY%, *

;Send Enter when prompt asks for both lamps to be lit
Send {Enter}

;Loop until finished with the scan
Loop,
{
   Imagesearch, FoundX, FoundY, 140, 50, 240, 150, C:\Users\Jasco\Desktop\git_oxford_cryofree\lib\J1700_stopbutton.png
   if (ErrorLevel = 1)
       break
   Sleep, 1000
}
MsgBox "Out of Loop"