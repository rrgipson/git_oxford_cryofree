;
; AutoHotkey script to initiate a long scan on the JASCO J-730/J-810 spectrophotometers
;
; This should report to stdout whether a scan was successfully initiated, as long as the scan takes more than a few
; seconds. If you have particularly unusual parameters so that a scan is done within a second or two, the stdout
; response is less reliable but the script will still issue a 'click' event to the [Start] button if it can.
;

; Remove any click delays so someone using the mouse has less of a chance to screw things up
SetControlDelay, -1
; Find the window we want by saying it should contain somewhere within the string "Baseline correct"
;SpectrumMeasurement := WinExist("Spectrum Measurement", "Baseline correct")
SpectrumMeasurement := WinExist("Spectrum Measurement")
WinGetTitle, SpectrumTitle, ahk_id %SpectrumMeasurement%  ; Store its title
; Create a `StartButton` variable determining if something labeled "Start" is enabled within %SpectrumMeasurement%
ControlGet, StartButton, Enabled, , Start, ahk_id %SpectrumMeasurement%
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
    ; Also keep an eye out for the popup the J-730 throws, but don't wait forever! Sixty seconds should do it.
    MaxWaitTime := 60
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
        MaxWaitTime -= 1  ; Count down the timer to make sure we don't stall the program in this while loop
    }
    If (MaxWaitTime > 0) and (StopButton)  ; If we haven't timed out and if [Stop] enabled (ie, we're acquiring)
    {
        Success := 1
    }
}
If (Success)
{
    FileAppend, %SpectrumTitle%, *  ; Write the value of `Success` to stdout to be picked up by the Python script
}
