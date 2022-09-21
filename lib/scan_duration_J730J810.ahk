;
; AutoHotkey script to time the duration of a long scan on the JASCO J-730/J-810 spectrophotometers
;
; This should report to stdout whether a scan was successfully initiated, as long as the scan takes more than a few
; seconds. If you have particularly unusual parameters so that a scan is done within a second or two, the stdout
; response is less reliable but the script will still issue a 'click' event to the [Start] button if it can.
;

; Store current window
VTVHSoftware := WinExist("Solomon Group VTVH MCD Tool")
; Remove any click delays so someone using the mouse has less of a chance to screw things up
SetControlDelay, -1
; Find the window we want, specifying it should contain the string "Baseline correct" somewhere within
;SpectrumMeasurement := WinExist("Spectrum Measurement", "Baseline correct")
SpectrumMeasurement := WinExist("Spectrum Measurement")
WinActivate, ahk_id %SpectrumMeasurement%
; Create a `StartButton` variable determining if something labeled "Start" is enabled within %SpectrumMeasurement%
ControlGet, StartButton, Enabled, , Start, ahk_id %SpectrumMeasurement%
; Record the start time
StartTime := A_TickCount
Duration := 0
; We also initiate an `Success` flag to monitor whether the acquisition has successfully started
Success := 0
If (SpectrumMeasurement) and (StartButton)  ; If window exists and [Start] enabled
{
    ; Click [Start] and wait one second to see what happens to the [Start]/[Stop] toggle button
    ControlClick, Start, ahk_id %SpectrumMeasurement%, , , , NA
    Sleep, 1000
    ; If the acquisition has begun, [Stop] will be enabled; otherwise, we need to wait for the instrument to change
    ; its wavelength. Alternatively, something broader is amiss.
    ControlGet, StartButton, Enabled, , Start, ahk_id %SpectrumMeasurement%  ; [Start] enabled?
    ControlGet, StopButton, Enabled, , Stop, ahk_id %SpectrumMeasurement%    ; [Stop] enabled?
    ; Also keep an eye out for the popup the J-730 throws, but don't wait forever! Will wait up to 5 min.
    MaxWaitTime := 300
    ; While neither button is enabled, we loop to see what's happening
    While (not StartButton) and (not StopButton) and (MaxWaitTime > 0)
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
    If (MaxWaitTime > 0) and (StopButton)  ; If we haven't timed out and if [Stop] enabled (ie, we're acquiring)
    {
        Success := 1
    }
}
ControlGet, StartButton, Enabled, , Start, ahk_id %SpectrumMeasurement%  ; [Start] enabled?
MaxWaitTime := 3600  ; Maximally allow one hour of acquisition
If (Success) and (not StartButton)  ; If we're currently acquiring, loop till it's over
{
    Gui, +AlwaysOnTop +ToolWindow +HwndInterruptProcess  ; Make a custom MsgBox to allow user to interrupt/cancel
    Gui, Add, Text, , Waiting up to 3600 s (1 h) for scan to finish...
    Gui, Add, Button, gGuiClose, Cancel  ; I hope `gGuiClose` will work so I don't have to write my own close routine
    Gui, Show, , Measuring Scan Duration
    Uninterrupted:= WinExist("ahk_id" InterruptProcess)
    ;MsgBox, %InterruptProcess%, %Uninterrupted%
    While (not StartButton) and (MaxWaitTime > 0) and (Uninterrupted)
    {
        Sleep, 1000
        ControlGet, StartButton, Enabled, , Start, ahk_id %SpectrumMeasurement%  ; [Start] enabled?
        Uninterrupted := WinExist("ahk_id" InterruptProcess)  ; Make sure user hasn't hit 'Cancel'
        MaxWaitTime -= 1
    }
    If (MaxWaitTime > 0) and (StartButton) and (Uninterrupted)  ; If successful and not interrupted
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
;;WinActivate, ahk_id %DurationPopup%
WinShow, ahk_id %VTVHSoftware%
WinActivate, ahk_id %VTVHSoftware%
FileAppend, %Duration%, *  ; Write the value of `Duration` to stdout to be picked up by the Python script
ExitApp, (not Success)  ; Return exitcode `0` to indicate success and `1` to indicate failure

GuiClose:
    Gui, Destroy
    Return
