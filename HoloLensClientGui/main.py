import tkinter as tk
from time import gmtime, strftime
from tkinter import *
from tkinter import messagebox
import os
from tkinter import ttk
import threading

import numpy as np

import HoloLens_client
import visualize
import process_all
from pathlib import Path
from utils import load_head_hand_eye_data

def get_selection(furniture_combox, environment_combox, feature_combox, assembler_name, root_path, ip):
    global fullList
    global host
    fullList.clear()
    chosen_furniture = furniture_combox.get()
    chosen_environment = environment_combox.get()
    chosen_extra_feature = feature_combox.get()
    builder_name = assembler_name.get()
    path = root_path.get()
    host = ip.get()
    if chosen_furniture == 'Choose' or chosen_environment == 'Choose' or chosen_extra_feature == 'Choose' or builder_name == 'Choose':
        messagebox.showinfo("Selection", "You didn't choose")
    else:
        fullList.append(path)
        fullList.append(chosen_furniture)
        fullList.append(chosen_environment)
        fullList.append(chosen_extra_feature)
        fullList.append(builder_name)


def start_process(last_path):
    global main_thread
    HoloLens_client.update()
    main_thread = threading.Thread(target=HoloLens_client.main_function, args=((last_path, host)))
    main_thread.start()
    return main_thread


def stop_process(fullList):
    fullList.clear()


def get_avg_delta(timestamps):
    deltas = [(timestamps[i] - timestamps[i-1]) for i in range(1, len(timestamps))]
    return np.mean(deltas)


def visualize_path(updated_path,video_path):
    print(str(video_path.get()))

    if video_path.get() == "video path":
        visualize.visualize(updated_path)
    else:
        visualize.visualize(str(video_path.get()))


def process_button(process_path):

    if process_path.get() == "process path":
        messagebox.showerror("Error", "Fill specific path")
    else:
        process_all.process_all(Path(process_path.get()))


def buildPath(full_feature_list):
    if len(full_feature_list) == 0:
        return
    global updated_full_path
    global path_pv
    global path_AHAT
    available_depth_sensors = ["pv", "Depth Long Throw"]
    os.chdir(full_feature_list[0]) #change to work dir
    os.makedirs(full_feature_list[1], exist_ok=True) #create directory for furniture item if needed
    new_folder_name = ""
    new_path = full_feature_list[0] + "\\" + (full_feature_list[1])

    for name in full_feature_list[2:]:
        new_folder_name += f"{name}_"

    new_folder_name = new_folder_name + strftime("%d%m%Y_%H%M", gmtime()) + "_recDir"

    os.chdir(new_path)
    os.mkdir(new_folder_name)
    updated_full_path = new_path + "\\" + new_folder_name

    for name in available_depth_sensors:
        os.chdir(updated_full_path)
        os.mkdir(name)

    path_pv = updated_full_path + "\\" + available_depth_sensors[0]
    #path_AHAT = updated_path + "\\" + namesList[1]
    path_LT = updated_full_path + "\\" + available_depth_sensors[1]


if __name__ == "__main__":
    global main_thread
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
    updated_full_path = ''
    path = ''
    fullList = []
    root = tk.Tk()

    root.title('HoloLens 2 Stream Recorder GUI')
    technion_logo = PhotoImage(file='new_technion_logo.png')
    root.iconphoto(False, technion_logo)
    root.geometry('720x720')
    background_image = PhotoImage(file='faculty.png')

    Image_display = Label(root, image=background_image)
    Image_display.place(x=25, y=600)

    object_list = ["Drawer", "Table", "Coffee_Table"]
    background_list = ["Table", "Floor"]
    feature_list = ["None", "Gloves", "Bright light", "Dark light"]
    assembler_name_list = ["Paul", "Eviatar", "Roie"]

    furniture_combo_box = ttk.Combobox(root, value=object_list)
    furniture_combo_box.place(x=55, y=185)
    furniture_combo_box.set("Choose")

    environment_combox = ttk.Combobox(root, value=background_list)
    environment_combox.set("Choose")
    environment_combox.place(x=260, y=185)

    extra_feature_combox = ttk.Combobox(root, value=feature_list)
    extra_feature_combox.set("Choose")
    extra_feature_combox.place(x=460, y=185)

    assembler_label = Label(root, text="Who Is The Assembler?", font=last_font)
    assembler_label.place(x=45, y=215)

    assembler_name = ttk.Combobox(root, value=assembler_name_list)
    assembler_name.set("Choose")
    assembler_name.place(x=55, y=260)

    hololens_ip = Label(root, text="insert HoloLens ip:", font=last_font)
    hololens_ip.place(x=55, y=470)
    ip = tk.Entry(root)
    ip.insert(-1, "132.69.202.47")
    ip.place(x=280, y=480)

    hololens_root_path = Label(root, text="path to root directory:", font=last_font)
    hololens_root_path.place(x=55, y=500)
    root_path = tk.Entry(root)
    root_path.insert(-1, "C:\HoloLens")  # TODO: set this according to pc user
    root_path.place(x=280, y=510)

    process_root_path = Label(root, text="Process directory:", font=last_font)
    process_root_path.place(x=55, y=530)
    process_path = tk.Entry(root)
    process_path.insert(-1, "process path")
    process_path.place(x=280, y=540)

    video_root_path = Label(root, text="Chosen video directory:", font=last_font)
    video_root_path.place(x=55, y=560)
    video_path = tk.Entry(root)
    video_path.insert(-1, "video path")
    video_path.place(x=280, y=570)

    furniture = tk.Label(root, text="Pick a Furniture", font=Font_tuple)
    furniture.place(x=45, y=140)

    assembling_environment = tk.Label(root, text="Pick an Environment", font=Font_tuple)
    assembling_environment.place(x=230, y=140)

    feature = tk.Label(root, text="Pick a Feature", font=Font_tuple)
    feature.place(x=449, y=140)

    picture = PhotoImage(file="start.png")
    start_button = tk.Button(root, text="Start",
                             command=lambda: [
                                 get_selection(furniture_combo_box, environment_combox, extra_feature_combox,
                                               assembler_name, root_path, ip),
                                 buildPath(fullList),
                                 start_process(updated_full_path),
                                 HoloLens_client.display(root, duration_text, pv_text, AHAT_text)], image=picture)

    start_button.place(x=515, y=300)

    stop_pic = PhotoImage(file="stop.png")
    stop_button = tk.Button(root, text="Stop", image=stop_pic,
                            command=lambda: [stop_process(fullList),
                                             HoloLens_client.display(root, duration_text, pv_text, AHAT_text),
                                             HoloLens_client.stop_all_threads(), HoloLens_client.counter(root, path_pv)])
    stop_button.place(x=515, y=375)

    vid_pic = PhotoImage(file="new_vid.png")
    Video_Button = tk.Button(root, text="Video", image=vid_pic,
                             command=lambda: [visualize_path(updated_full_path, video_path),
                                              print("updated path is", updated_full_path)])
    Video_Button.place(x=515, y=550)

    process_pic = PhotoImage(file="process.png")
    process_Button = tk.Button(root, text="process", image=process_pic,
                               command=lambda: [process_button(process_path)])
    process_Button.place(x=515, y=510)


    photo = PhotoImage(file="fresh.png")

    Last_record_statistics = Label(root, text="Last record statistics", font=Second_font)
    show = Label(root, image=photo)
    show.place(x=80, y=20)

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
