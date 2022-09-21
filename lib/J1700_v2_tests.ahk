;ControlClick, Start, ahk_id %SpectrumMeasurement%, , , , NA
;ControlClick, X190 Y100, Spectra Measurement - J1700/D001461900

WinActivate, Spectra Measurement - J1700/D001461900
ImageSearch, FoundX, FoundY, 0, 0, 300, 160, J1700_stopbutton.png
;ImageSearch, FoundX, FoundY, 140, 50, 240, 150, J1700_startbutton.png
;ControlClick, X%FoundX% Y%FoundY%, Spectra Measurement - J1700/D001461900
MsgBox % "X " . FoundX . " " . "Y " . FoundY
