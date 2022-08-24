import tkinter as tk
from time import gmtime, strftime
from tkinter import *
from tkinter import messagebox
import os
from tkinter import ttk
import FolderScript
import threading
import HoloLens_client
import visualize
import process_all
from pathlib import Path
import time
# import PIL.Image, PIL.ImageTk
from utils import load_head_hand_eye_data

folders_extensions = [('PV', 'bytes'),
                      ('Depth AHaT', '[0-9].pgm'),
                      ('Depth Long Throw', '[0-9].pgm'),
                      ('VLC LF', '[0-9].pgm'),
                      ('VLC RF', '[0-9].pgm'),
                      ('VLC LL', '[0-9].pgm'),
                      ('VLC RR', '[0-9].pgm')]

Font_tuple = ("Comic Sans MS", 15, "bold")
Second_font = ("Comic Sans MS", 10, "bold")
last_font = ("Comic Sans MS", 14, "bold")
path_pv = ''
path_AHAT = ''
path_LT = ''
updated_path = ''
path = ''
fullList = []
root = tk.Tk()
# cv_img = cv2.imread('new.png')
# height, width, temp = cv_img.shape


# cv2.imshow('image',cv_img)


# photo = PIL.ImageTk.PhotoImage(image=PIL.Image.fromarray(cv_img))

root.title('HoloLens 2 Stream Recorder GUI')
img = PhotoImage(file='new_technion_logo.png')
root.iconphoto(False, img)
root.geometry('720x720')
background_image = PhotoImage(file='faculty.png')

Image_display = Label(root, image = background_image)
Image_display.place(x=25, y=600)



lst = ["Clothet", "Drawer", "Table"]
sec_lst = ["Floor", "Table"]
rd_lst = ["Gloves", "Bright light", "Dark light"]
built = ["Eviatar","Paul", "Roie"]

combo_box = ttk.Combobox(root, value=lst)
combo_box.place(x=55, y=185)
combo_box.set("Choose")

sec_combox = ttk.Combobox(root, value=sec_lst)
sec_combox.set("Choose")
sec_combox.place(x=260, y=185)

rd_combox = ttk.Combobox(root, value=rd_lst)
rd_combox.set("Choose")
rd_combox.place(x=460, y=185)

Assembler = Label(root,text = "Who Is The Assembler?", font = last_font)
Assembler.place(x=45,y=215)

# furniture = tk.Label(root, text="Pick a Furniture", font=Font_tuple)
# furniture.place(x=45, y=140)
#

who_built = ttk.Combobox(root, value=built)
who_built.set("Choose")
who_built.place(x=55, y=260)

hololens_ip = Label(root,text = "insert HoloLens ip:", font = last_font)
hololens_ip.place(x=55,y=470)
ip = tk.Entry(root)
ip.insert(-1,"132.69.202.7")
ip.place(x=280,y=480)


hololens_root_path = Label(root,text = "path to root directory:", font = last_font)
hololens_root_path.place(x=55,y=500)
root_path= tk.Entry(root)
root_path.insert(-1,"C:\HoloLens")
root_path.place(x=280,y=510)

process_root_path = Label(root,text = "Process directory:", font = last_font)
process_root_path.place(x=55,y=530)
process_path= tk.Entry(root)
process_path.insert(-1,"process path")
process_path.place(x=280,y=540)

video_root_path = Label(root,text = "Chosen video directory:", font = last_font)
video_root_path.place(x=55,y=560)
video_path= tk.Entry(root)
video_path.insert(-1,"video path")
video_path.place(x=280,y=570)

def getSelection(combo_box, sec_combox, rd_combox, who_built,root_path,ip):
    global fullList
    global host
    fullList.clear()
    value = combo_box.get()
    val2 = sec_combox.get()
    val3 = rd_combox.get()
    builder_name = who_built.get()
    path = root_path.get()
    host = ip.get()
    if value == 'Choose' or val2 == 'Choose' or val3 == 'Choose' or builder_name == 'Choose':
        messagebox.showinfo("Selection", "You didn't choose")
    else:
        fullList.append(path)
        fullList.append(value)
        fullList.append(val2)
        fullList.append(val3)
        fullList.append(builder_name)


def Start_Process(last_path):
    HoloLens_client.update()
    t = threading.Thread(target=HoloLens_client.main_function, args=((last_path,host)))
    t.start()

def stop_process(fullList):
    fullList.clear()

def check_framerates(capture_path):
    HundredsOfNsToMilliseconds = 1e-4
    MillisecondsToSeconds = 1e-3

    def get_avg_delta(timestamps):
        deltas = [(timestamps[i] - timestamps[i-1]) for i in range(1, len(timestamps))]
        return np.mean(deltas)

    for (img_folder, img_ext) in folders_extensions:
        base_folder = capture_path / img_folder
        paths = base_folder.glob('*%s' % img_ext)
        timestamps = [int(path.stem) for path in paths]
        if len(timestamps):
            avg_delta = get_avg_delta(timestamps) * HundredsOfNsToMilliseconds
            print('Average {} delta: {:.3f}ms, fps: {:.3f}'.format(
                img_folder, avg_delta, 1/(avg_delta * MillisecondsToSeconds)))

    head_hat_stream_path = capture_path.glob('*eye.csv')
    try:
        head_hat_stream_path = next(head_hat_stream_path)
        timestamps = load_head_hand_eye_data(str(head_hat_stream_path))[0]
        hh_avg_delta = get_avg_delta(timestamps) * HundredsOfNsToMilliseconds
        print('Average hand/head delta: {:.3f}ms, fps: {:.3f}'.format(
            hh_avg_delta, 1/(hh_avg_delta * MillisecondsToSeconds)))
    except StopIteration:
        pass


def visualize_path(updated_path,video_path):
    print(str(video_path.get()))
    if(video_path.get()=="video path"):
        visualize.visualize(updated_path)
    else:
        visualize.visualize(str(video_path.get()))

def process_button(process_path):
    if(process_path.get()=="process path"):
        messagebox.showerror("Error", "Fill specific path")
    else:
        process_all.process_all(Path(process_path.get()))


furniture = tk.Label(root, text="Pick a Furniture", font=Font_tuple)
furniture.place(x=45, y=140)

envi = tk.Label(root, text="Pick an Environment", font=Font_tuple)
envi.place(x=230, y=140)

feature = tk.Label(root, text="Pick a Feature", font=Font_tuple)
feature.place(x=449, y=140)

picture = PhotoImage(file="start.png")
start_button = tk.Button(root, text="Start",
                         command=lambda: [getSelection(combo_box, sec_combox, rd_combox, who_built,root_path,ip),
                                          buildingPath(fullList),
                                          Start_Process(updated_path),
                                          HoloLens_client.display(root, duration_text, pv_text, AHAT_text)], image=picture)

start_button.place(x=515, y=300)

stop_pic = PhotoImage(file="stop.png")
stop_button = tk.Button(root, text="Stop", image=stop_pic,
                        command=lambda: [ stop_process(fullList),HoloLens_client.display(root, duration_text, pv_text, AHAT_text),
                                         HoloLens_client.Stop(),HoloLens_client.counter(root, path_pv)])
stop_button.place(x=515, y=375)

vid_pic = PhotoImage(file="new_vid.png")
Video_Button = tk.Button(root, text="Video", image=vid_pic, command=lambda: [visualize_path(updated_path,video_path),print("updated path is",updated_path)])
Video_Button.place(x=515, y=550)

process_pic = PhotoImage(file="process.png")
process_Button = tk.Button(root, text="process", image=process_pic, command=lambda: [process_button(process_path)])
process_Button.place(x=515, y=510)


def buildingPath(FullList):
    global updated_path
    global path_pv
    global path_AHAT
    namesList = ["pv", "Depth Long Throw"]
    os.chdir(FullList[0])
    os.makedirs(FullList[1],exist_ok=True)
    new_Folder = ""
    new_Path = FullList[0] + "\\" + (FullList[1])

    for name in FullList[2:]:
        new_Folder += "%s" % (name) + "_"

    Last_Path = new_Folder + strftime("%d%m%Y_%H%M", gmtime())

    os.chdir(new_Path)
    os.mkdir(Last_Path)
    updated_path = new_Path + "\\" + Last_Path

    for names in namesList:
        os.chdir(updated_path)
        os.mkdir(names)

    path_pv = updated_path + "\\" + namesList[0]
    #path_AHAT = updated_path + "\\" + namesList[1]
    path_LT = updated_path + "\\" + namesList[1]
photo = PhotoImage(file="fresh.png")
show = Label(root, image=photo)
show.place(x=80, y=20)

Last_record_statistics = Label(root, text="Last record statistics", font=Second_font)
Last_record_statistics.place(x=55, y=360)

Duration = Label(root, text="Duration:", font=Second_font)
Duration.place(x=55, y=380)

duration_text = 'None'
# dur_display = Label(root,text=":"+duration_text,font=Second_font)
# dur_display.place(x=110,y=300)

PV_FPS = Label(root, text="PV FPS:", font=Second_font)
PV_FPS.place(x=55, y=400)

pv_text = "None"
# pv_display = Label(root,text=":"+pv_text,font=Second_font)
# pv_display.place(x=110,y=320)

AHAT_FPS = Label(root, text="AHAT FPS:", font=Second_font)
AHAT_FPS.place(x=55, y=420)

AHAT_text = "None"
# AHAT_display = pv_display = Label(root,text=":"+AHAT_text,font=Second_font)
# AHAT_display.place(x=110,y=340)

root.mainloop()
