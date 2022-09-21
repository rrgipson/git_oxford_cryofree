;MsgBox % Scan duration is currently disabled, sorry! - MCD Crew
SetControlDelay, -1
; Find the window we want. 
SpectrumMeasurement := WinExist("Spectra Measurement - J1700/D001461900")
WinActivate, ahk_id %SpectrumMeasurement%
MsgBox % "Start Button Found at X " . SpectrumMeasurement . " " . "Y " . SpectrumMeasurement . " Window Activated?"
 