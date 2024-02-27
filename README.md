# git_oxford_cryofree
Code for running the Solomon Lab MCD.

## The Setup Used for Writing and Testing Code
- This code runs an Oxford Instruments SpectromagPT cryofree instrument with an iTC and iPS
- The iTC and iPS are connected via separate serial connections. 2 separate serial ports are used (see oxford.py global vars)
- The iTC (temp controller) is set to read the new SCPI commands
- The iPS (magnet controller) is set to read legacy commands
- You will also need to install AutoHotKey if you want to use the code to collect spectra via the J-1700 Jasco software (https://www.autohotkey.com/)

## The Code Components
1. main_new.py is the one to run as it is the working desing. I changed over from main.py when switching the magnet from legacy to SCPI commands.
2. oxford.py handles serial communication with the box (implementing pyserial).  
3. spectrometer.py handles communication with the J1700 and Jasco software via the autohotkey scripts found in lib
    - Note that there are 2 scripts- the "one lamp" one just had an extra "Enter" keypress to close the popup that tells you there is only 1 lamp on
4. gui.py handles the setup and changes made to the gui (activating/deactivating fields) during running.
5. logger.py contains a class that handles all of the logging activities (writing data from background/VTVH to csv files as well as printed text and errors, stderr is overwritten).
    - the background_log.csv file is in the main folder and the VTVH and error logs are in UserLogs/
    - Background log is updated when connection is established and every 2 hours after
    - VTVH logging happens at the beginning and end of every scan
    - Error logging just prints all messages to a file (that is time stamped) including ones from stderr for later reference
6. scpi_iTC just stores as strings some of the base SCPI commands for the temp controller
7. All the other python files in the main folder are tests for various parts. test_connection, test_temp_connection, and test_temp_newCmds allow you to communicate with the box without the GUI

## Controlling the Instrument with the program (From the SOP)
- To access the program, run (double click on) main_new.py. This should open a black window with text and the GUI window.
- To access the log file of VTVH scans (scan number, fields, temps), open the folder /UserLogs/ and look for the csv file labeled something like vtvh_log.csv. Feel free to move this file to somewhere you will remember it if you need it. (Also be aware that you may have previous users VTVH runs also in the file above your run - check the date in the first column to be sure it's yours).
- Note on Messages/Freezing: A lot of things print out to the black screen during usage but stderr is written to the /UserLogs/error_log.txt to save them for the crew to check later. Check this if you think something is wrong (there may be a message telling you that you have to wait 5 minutes for the switch heater or something). \textit{Troubleshooting:} If you think that the code is actually frozen, try clicking "VTVH Interrupt" if you're running VTVH (or the interrupt relevant to what you're doing). If that doesn't work, either contact someone in the crew or if that isn't possible, click "Disconnect" under the 2 COMs message and then contact the crew.
- Note on Color Scheme: Black boxes with red text are editable by the user. White boxes with black text are unable to be edited (this might be because these are just taking readings or you aren't connected). 

### Running VTVH from the Program
- Find the VTVH Section on the lower left of the program interface.
- Input (comma separated numbers) the fields and temperatures you want to scan. The fields should be in Tesla and the temps should be in Kelvin (but you don't need to include units in your input). The run will scan every temperature at each field.
- Open the Jasco software for running scans on the J1700. (And do all the prerequisite warm up procedures involved with the instrument.)
- Time how long it takes to run a scan with your desired parameters (just use your phone or something). Add a few extra seconds to this time before inputting it just to be safe.
- Input the time that the scan took in seconds into the third box in the VTVH Section. 
- Optional: Select the folder that the Jasco software is autosaving to using the Browse button. This will make a note of which file each scan corresponds to in the VTVH log file and will save the VTVH log file to this location so everything is together.  
- Click Collect VTVH to start the run.
- Look for messages on the black screen (it will tell you if you've inputted any temps or fields incorrectly). It will also make you wait 5 minutes for the Switch Heater to Warm Up (the switch heater will be turned on automatically if it isn't already). 
- Make sure the Jasco Scanning Software window is open (not minimized but it can be behind the program). Scans will not be collected if it is minimized or not open.
- The program will print messages to the black screen when each field and temperature is reached, when a scan is taken, and when the run is finished.
- If you need to stop during the run for any reason, use the "VTVH Interrupt" button.

### Changing the Temperature
- Type in your desired set point for the sample temperature in the "Sample Temp Setpoint" Box in the middle of the program screen. Proper format is a number followed by K (for Kelvin) with no spaces. 
- Click "Write Set Point" and the correct temperatures will be set for the VTI and Sample (Regressions for offset were created based on factory test results for our instrument)
- If you are unsure what the current set point is, click "Read Set Point" and whatever is in the black box will be replaced by the current set point.
    
### Changing the Field}
- Click "Engage Switch Heater" in the upper right of the program. (If the button says "Disengage" that means the switch heater is already on.)
- Wait 5 minutes for the switch heater to warm up (the code will probably force you to do this).
- Type in your desired set point for the field in the "Field Set Point" Box in the middle of the program screen. Proper format is just a number no spaces. This value should be in Tesla. 
- Click "Write Set Point".
- If you are unsure what the current set point is, click "Read Set Point" and whatever is in the black box will be replaced by the current set point.
- To go to the Set Point, click "Go to Set" above the black box.
- If you need to stop the field change before it reaches the set point, click "Sweeping... Interrupt". This will pause the field wherever it is.
- To go to zero field, either change the setpoint to 0 and follow the same steps or just click "Go to Zero".
