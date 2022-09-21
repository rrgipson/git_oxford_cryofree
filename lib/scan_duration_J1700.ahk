SetControlDelay, -1
; Find the window we want. 
SpectrumMeasurement := WinExist("Spectra Measurement - J1700/D001461900")
;WinActivate, ahk_id %SpectrumMeasurement%
WinActivate, Spectra Measurement - J1700/D001461900 ; Is this line or the line above the correct line?
Sleep, 200
; Search Spectra Measurement window for the start button image within the specified X1, Y1, X2, and Y2 window pixel area
; Store the location as FoundX and FoundY variables
ImageSearch, FoundX, FoundY, 140, 50, 240, 150, lib\J1700_startbutton.png
;MsgBox % "Start Button Found at X " . FoundX . " " . "Y " . FoundY . " Woo! "
; Record the start time
StartTime := A_TickCount
Duration := 0
; We also initiate an `Success` flag to monitor whether the acquisition has successfully started
Success := 0

If (SpectrumMeasurement) and (FoundX) and (FoundY)  ; If window exists and [Start] button X and Y pixel locations. 
{
    ; Click [Start] and wait one second to see what happens to the [Start]/[Stop] toggle button
    WinActivate, ahk_id %SpectrumMeasurement%
    ;WinActivate, Spectra Measurement - J1700/D001461900 ; Is this line or the line above the correct line?
    ControlClick, X%FoundX% Y%FoundY%, ahk_id %SpectrumMeasurement%, , , , NA
    ;MsgBox % "Start Button Pressed at X " . FoundX . " " . "Y " . FoundY . " - Scan Initiated"
    ;ControlClick, X%FoundX% Y%FoundY%, Spectra Measurement - J1700/D001461900 ; Is this line or the line above the correct line??
    Sleep, 1000
    WinActivate, ahk_id %SpectrumMeasurement%
    ;WinActivate, Spectra Measurement - J1700/D001461900 ; Is this line or the line above the correct line?
    ; If the acquisition has begun, [Stop] will be enabled; otherwise, we need to wait for the instrument to change
    ; its wavelength. Alternatively, something broader is amiss.
    ; Search Spectra Measurement window for the start button image within the specified X1, Y1, X2, and Y2 window pixel area
    ; Search Spectra Measurement window for the stop button image within the specified X1, Y1, X2, and Y2 window pixel area
    ; Store the location as FoundX and FoundY variables
    ImageSearch, FoundX, FoundY, 140, 50, 240, 150, lib\J1700_startbutton.png        ; [Start] enabled?   
    ImageSearch, FoundStopX, FoundStopY, 140, 50, 240, 150, lib\J1700_stopbutton.png ; [Stop] enabled?
    ;MsgBox % "Stop Button Found at X " . FoundStopX . " " . "Y " . FoundStopY . " - Measuring Scan Time"   
    ; Also keep an eye out for the popup the J-730 throws, but don't wait forever! Will wait up to 5 min.
    MaxWaitTime := 300
    ; While neither button is enabled, we loop to see what's happening
    While (not FoundX) and (not FoundY) and (not FoundStopX) and (not FoundStopX) and (MaxWaitTime > 0)
    {
        ; We start by looking for a popup titled "Spectrum Measurement" containing the string "Start Measurement?"
        StartPopup := WinExist("Spectrum Measurement", "Start Measurement?")
        If (StartPopup)  ; If this popup is found, click 'OK'
        {
            ControlClick, OK, ahk_id %StartPopup%, , , , NA
        }
        ; We wait one second and the check again on the status of the [Start]/[Stop] toggle button
        Sleep, 1000
        ControlGet, StartButton, Enabled, , Start, ahk_id %SpectrumMeasurement%
        ControlGet, StopButton, Enabled, , Stop, ahk_id %SpectrumMeasurement%
        MaxWaitTime -= 1  ; Count down the timer to make sure we don't freeze the program forever in this while loop
    }
    If (MaxWaitTime > 0) and (FoundStopX) and (FoundStopY)  ; If we haven't timed out and if [Stop] enabled (ie, we're acquiring)
    {
        Success := 1
    }
}
WinActivate, ahk_id %SpectrumMeasurement%
;WinActivate, Spectra Measurement - J1700/D001461900 ; Is this line or the line above the correct line?
; Search Spectra Measurement window for the start button image within the specified X1, Y1, X2, and Y2 window pixel area
; Store the location as FoundX and FoundY variables
ImageSearch, FoundX, FoundY, 140, 50, 240, 150, lib\J1700_startbutton.png        ; [Start] enabled?   
;MsgBox % "Looking for Start Button at X " . FoundX . " " . "Y " . Success . " - and flag" 
MaxWaitTime := 3600  ; Maximally allow one hour of acquisition
If (Success) and (not FoundX) and (not FoundY) ; If we're currently acquiring, loop till it's over
{
    Gui, +AlwaysOnTop +ToolWindow +HwndInterruptProcess  ; Make a custom MsgBox to allow user to interrupt/cancel
    Gui, Add, Text, , Waiting up to 3600 s (1 h) for scan to finish...
    Gui, Add, Button, gGuiClose, Cancel  ; I hope `gGuiClose` will work so I don't have to write my own close routine
    Gui, Show, , Measuring Scan Duration
    Uninterrupted:= WinExist("ahk_id" InterruptProcess)
    ;MsgBox, %InterruptProcess%, %Uninterrupted%
    While (not FoundX) and (not FoundY) and (MaxWaitTime > 0) and (Uninterrupted)
    {
        Sleep, 1000
        WinActivate, ahk_id %SpectrumMeasurement%
        ;WinActivate, Spectra Measurement - J1700/D001461900 ; Is this line or the line above the correct line?
        ; Search Spectra Measurement window for the start button image within the specified X1, Y1, X2, and Y2 window pixel area
        ; Store the location as FoundX and FoundY variables
        ImageSearch, FoundX, FoundY, 140, 50, 240, 150, lib\J1700_startbutton.png        ; [Start] enabled?
        ;MsgBox % "Looking for Start Button at X " . FoundX . " " . "Y " . FoundY . " - while scanning"    
        Uninterrupted := WinExist("ahk_id" InterruptProcess)  ; Make sure user hasn't hit 'Cancel'
        MaxWaitTime -= 1
    }
    If (MaxWaitTime > 0) and (FoundX) and (FoundY) and (Uninterrupted)  ; If successful and not interrupted
    {
        WinClose, Measuring Scan Duration
        Duration := A_TickCount - StartTime
        Success := 1
    }
    Else
    {
        Success := 0
    }
}
;MsgBox % "Did duration count correctly, value returned is " . Duration . " " . "Y " . Duration . " Woo 2 !"
;;WinActivate, ahk_id %DurationPopup%
WinShow, ahk_id %VTVHSoftware%
WinActivate, ahk_id %VTVHSoftware%
FileAppend, %Duration%, *  ; Write the value of `Duration` to stdout to be picked up by the Python script
ExitApp, (not Success)  ; Return exitcode `0` to indicate success and `1` to indicate failure

GuiClose:
    Gui, Destroy
    Return





