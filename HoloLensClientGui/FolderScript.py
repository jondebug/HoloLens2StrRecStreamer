import fnmatch
import os
import time
from tkinter import *
from tkinter import messagebox
import tkinter as tk
#TODO: maybe delete this file completely

update_flag = True

Second_font = ("Comic Sans MS", 10, "bold")
end = 2
start = 2
FullList = []


def test(last_path):
    StartWatch()
    global update_flag

    # while this_flag:
    #     print("Your Path is : " + last_path)
    #     time.sleep(0.5)

def Stop():
    # global end
    global update_flag
    this_flag = False
    stopwatch()
    print("stopped")



def update():
    global update_flag

    this_flag=True

def display(root,duration_text,pv_text,AHAT_text):
    global start
    dur_display = Label(root, text="" + duration_text, font=Second_font)
    # dur_display.place(x=110, y=300)
    pv_display = Label(root, text="" + pv_text, font=Second_font)
    # pv_display.place(x=110, y=320)
    AHAT_display = pv_display = Label(root, text="" + AHAT_text, font=Second_font)
    # AHAT_display.place(x=110, y=340)


def counter(root,path):
        amount = len(os.listdir(path))
        s = stopwatch()
        sum = stop - start
        print(sum)
        temp = time_convert(sum)
        # total_time = time_convert(sum)
        # print("Total time: ")
        # print(total_time) # none here
        print("The FPS IS:")
        fps = amount / sum
        print(format(fps,".3f"))
        fps_num_display = format(fps,".3f")

        dur_time = Label(root, text=temp, font=Second_font)
        dur_time.place(x=110, y=380)
        FpsDisplay = Label(root,text = fps_num_display,font=Second_font)
        FpsDisplay.place(x=110, y=400)
        Ah_display = Label (root, text =fps_num_display,font=Second_font)
        Ah_display.place(x=110, y=420)

def StartWatch():
    global start
    global total_time
    start = time.time()
    return start
def stopwatch():
    global stop
    stop = time.time()
    return stop

def time_convert(sec):

  mins = sec // 60
  print("M" , mins)
  sec = sec % 60
  print("s", sec)
  hours = mins // 60
  print("h", hours)

  mins = mins % 60
  print("Last mins",mins)

  print("Time Lapsed = {0}:{1}:{2:.2f}".format(int(hours),int(mins),sec))

  return "{0}:{1}:{2:.2f}".format(int(hours),int(mins),sec)


