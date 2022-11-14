from time import sleep
from threading import Thread
from oxford import SerialPort
from gui import *

test_gui = GUI()



test_gui.mainloop()
sleep(1)
test_gui.warning_popup('title','message')