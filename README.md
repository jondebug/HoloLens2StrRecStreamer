# HoloLens2StrRecStreamer
1. get hololens ip address.

to compile the hololens app:
  1. open StreamRecorder.sln
  2. select release mode to compile in release mode
  3. select remote machine to make sure the executable file is created on teh device.
  4. under configuration properties -> Debugging -> Machine Name enter hololense ip adress.
  5. compile.
  6. StreamRecorder application should appear on your hololens device
  
  
 once the hololens app is comiled and on the device:
  1. run the HoloensClientGui/main.py script to start the desktop app.
  2. enter relevent information including ip address
  3. select start recording.
  4. run the recording app on the hololens, it will automatically connect to the 
