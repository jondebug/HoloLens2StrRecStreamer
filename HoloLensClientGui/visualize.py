import cv2
import numpy as np
import os
import vedo
import open3d as o3d
from PIL import Image
from pathlib import Path
import ast
from glob import glob


def visualize_all_recordings_in_path(path):
    if "_recDir" in path[-8:] and "eye_hands" in os.listdir(path):
        for child in os.listdir(path):
            if ".avi" in child:
                return
        print(f"calling process_all for {path}")
        print(os.listdir(path))
        visualize(path)
        return
    for sub_dir in glob(rf"{path}\*\\"):
        print(f"calling visualize_all for path: {sub_dir}, continuing search for recording dir")
        visualize_all_recordings_in_path(sub_dir)

def get_sensor_size(w_path):
    pv_info_path = w_path + "pv.txt"
    has_pv = len(list(pv_info_path)) > 0
    if has_pv:
        print(pv_info_path)
        with open(pv_info_path) as f:
            lis = f.readlines()
            intrinsics_ox, intrinsics_oy, \
            intrinsics_width, intrinsics_height = ast.literal_eval(lis[0])

    return intrinsics_width, intrinsics_height

def load_images_timestamps_from_folder(w_path,flags):
    PV_images = dict()
    AHAT_images = dict()
    Long_Throw_images = dict()
    LF_images = dict()
    RF_images = dict()
    LL_images = dict()
    RR_images = dict()
    eye_hands_images = dict()
    if(flags["PV"] == True):
        for file in os.listdir(w_path+'PV'):
            if(file.endswith(".png")):
                filename = os.path.splitext(os.path.basename(file))[0]
                img = cv2.imread(os.path.join(w_path+'PV', file))
                PV_images[filename] = img
    if (flags["AHaT_depth"] == True):
        for file in os.listdir(w_path + 'Depth AHaT'):
            if (file.endswith(".pgm")):
                filename = os.path.splitext(os.path.basename(file))[0]
                img = cv2.imread(os.path.join(w_path + 'Depth AHaT', file))
                AHAT_images[filename] = img.astype(np.uint8)
    if (flags["long_depth"] == True):
        for file in os.listdir(w_path + 'Depth Long Throw'):
            if (file.endswith(".pgm")  and not file.endswith("_ab.pgm")):
                filename = os.path.splitext(os.path.basename(file))[0]
                img = cv2.imread(os.path.join(w_path + 'Depth Long Throw', file))
                Long_Throw_images[filename] = img.astype(np.uint8)
    if (flags["front_left"] == True):
        for file in os.listdir(w_path+'VLC LF new'):
            if(file.endswith(".pgm")):
                filename = os.path.splitext(os.path.basename(file))[0]
                img = cv2.imread(os.path.join(w_path+'VLC LF new', file))
                LF_images[filename] = img
    if (flags["front_right"] == True):
        for file in os.listdir(w_path+'VLC RF new'):
            if(file.endswith(".pgm")):
                filename = os.path.splitext(os.path.basename(file))[0]
                img = cv2.imread(os.path.join(w_path + 'VLC RF new', file))
                RF_images[filename] = img
    if (flags["right_right"] == True):
        for file in os.listdir(w_path+'VLC RR new'):
            if(file.endswith(".pgm")):
                filename = os.path.splitext(os.path.basename(file))[0]
                img = cv2.imread(os.path.join(w_path + 'VLC RR new', file))
                RR_images[filename] = img
    if (flags["left_left"] == True):
        for file in os.listdir(w_path+'VLC LL new'):
            if(file.endswith(".pgm")):
                filename = os.path.splitext(os.path.basename(file))[0]
                img = cv2.imread(os.path.join(w_path + 'VLC LL new', file))
                LL_images[filename] = img
    if (flags["eye_hands"] == True):
        for file in os.listdir(w_path+'eye_hands'):
            if(file.endswith(".png")):
                filename = os.path.splitext(os.path.basename(file))[0]
                img = cv2.imread(os.path.join(w_path + 'eye_hands', file))
                eye_hands_images[filename] = img
    return PV_images,AHAT_images,Long_Throw_images,LF_images,RF_images,LL_images,RR_images,eye_hands_images


def visualize(w_path):
    print(os.path.join(w_path, "PV"))
    flags = {
        "PV": Path(os.path.join(w_path,"PV")).exists(),
        "long_depth": Path(os.path.join(w_path,"Depth Long Throw")).exists(),
        "AHaT_depth": Path(os.path.join(w_path, "Depth AHaT")).exists(),
        "front_left": Path(os.path.join(w_path, "VLC LF new")).exists(),
        "front_right": Path(os.path.join(w_path, "VLC RF new")).exists(),
        "right_right": Path(os.path.join(w_path, "VLC RR new")).exists(),
        "left_left": Path(os.path.join(w_path, "VLC LL new")).exists(),
        "eye_hands" : Path(os.path.join(w_path, "eye_hands")).exists()
    }
    print(flags)
    original_path = str(w_path)
    recording_name = (original_path.split("\\")[-3] + "_" + original_path.split("\\")[-2])[:-7]
    print(f"creating video {recording_name}")
    w_path = str(w_path)+"\\"
    PV_images,AHAT_images,LT_images,LF_images,RF_images,LL_images,RR_images,eye_hands_images = load_images_timestamps_from_folder(str(w_path),flags)
    all_images = {**PV_images,**AHAT_images,**LT_images,**LF_images,**RF_images,**LL_images,**RR_images,**eye_hands_images}

    pv_img_flag = False
    lf_img = False
    rr_img = False
    ll_img = False
    rf_img = False
    eh_img = False
    lt_img =False
    ahat_img = False



    pv_width,pv_height = get_sensor_size(w_path)
    ahat_width,ahat_height = 512,512
    lt_width,lt_height = 320,288
    if(flags["AHaT_depth"] == True):
        output_image = np.zeros((max(pv_height, ahat_height), pv_width + ahat_width, 3))
    elif(flags["long_depth"] == True):
        output_image = np.zeros((max(pv_height, lt_height), pv_width + lt_width, 3))
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    video = cv2.VideoWriter(original_path + str(f'/{recording_name}.avi'), fourcc, 15, (output_image.shape[1],output_image.shape[0]))

    for timestamp in sorted(all_images.keys()):
        timestamp = str(timestamp)
        if(all_images.get(timestamp) is not None):
            if(flags["PV"] == True):
                temp = PV_images.get(timestamp)
                if(temp is not None):
                   # pv_image = PV_images[timestamp]
                   pv_image = temp
                   pv_img_flag = True

            if (all_images.get(timestamp) is not None):
                if (flags["AHaT_depth"] == True):
                    temp = AHAT_images.get(timestamp)
                    if (temp is not None):
                       ahat_image = cv2.normalize(temp, dst=None, alpha=0, beta=255, norm_type=cv2.NORM_MINMAX)
                       ahat_img = True

            if (all_images.get(timestamp) is not None):
                if (flags["long_depth"] == True):
                    temp = LT_images.get(timestamp)
                    if (temp is not None):
                       LT_image = cv2.normalize(temp, dst=None, alpha=0, beta=255, norm_type=cv2.NORM_MINMAX, dtype=cv2.CV_8U)
                       lt_img = True
            if (flags["front_left"] == True):
                if(LF_images.get(timestamp) is not None):
                    LF_image = LF_images[timestamp]
                    LF_image = cv2.resize(LF_image, (428, LF_image.shape[0]))
                    LF_image_rotate = cv2.rotate(LF_image, cv2.ROTATE_90_CLOCKWISE)
                    lf_img = True

            if (flags["front_right"] == True):
                if(RF_images.get(timestamp) is not None):
                    RF_image = RF_images[timestamp]
                    RF_image = cv2.resize(RF_image, (428, RF_image.shape[0]))
                    RF_image_rotate = cv2.rotate(RF_image,cv2.ROTATE_90_COUNTERCLOCKWISE)
                    rf_img = True
            if (flags["right_right"] == True):
                if(RR_images.get(timestamp) is not None):
                    RR_image = RR_images[timestamp]
                    RR_image = cv2.resize(RR_image, (428, RR_image.shape[0]))
                    RR_image = cv2.rotate(RR_image, cv2.ROTATE_90_CLOCKWISE)
                    rr_img = True
            if (flags["left_left"] == True):
                if(LL_images.get(timestamp) is not None):
                    LL_image = LL_images[timestamp]
                    LL_image = cv2.resize(LL_image, (428, LL_image.shape[0]))
                    LL_image = cv2.rotate(LL_image, cv2.ROTATE_90_COUNTERCLOCKWISE)
                    ll_img = True
            if (flags["eye_hands"] == True):
                temp = eye_hands_images.get(timestamp)
                if (temp is not None):
                    eye_hand_image = eye_hands_images[timestamp]
                    eh_img = True

            all_flags = int(pv_img_flag) + int(lf_img) + int(rf_img) + int(ll_img) + int(rr_img) + int(eh_img)
            if(flags["PV"] and ((flags["AHaT_depth"] and pv_img_flag and ahat_img) or flags["long_depth"] and pv_img_flag and lt_img)):
                if (flags["eye_hands"] == True):
                    rgb_img = eye_hand_image
                else:
                    rgb_img = pv_image
                if (flags["AHaT_depth"] == True):
                    output_image = np.zeros((max(pv_height, ahat_height), pv_width + ahat_width, 3)).astype(np.uint8)
                    output_image[:, :, :] = (0, 0, 0)
                    output_image[:pv_height, :pv_width, :3] = rgb_img
                    output_image[:ahat_height, pv_width:pv_width + ahat_width, :3] = ahat_image
                elif (flags["long_depth"] == True):
                    output_image = np.zeros((max(pv_height, lt_height), pv_width + lt_width, 3)).astype(np.uint8)
                    output_image[:, :, :] = (0, 0, 0)
                    output_image[:pv_height, :pv_width, :3] = rgb_img
                    output_image[:lt_height, pv_width:pv_width + lt_width, :3] = LT_image
            # elif (flags["PV"] and flags["long_depth"] and pv_img and lt_img):
            #     output_image = np.zeros((max(pv_height, lt_height), pv_width + lt_width, 3)).astype(np.uint8)
            #     output_image[:, :, :] = (255, 255, 255)
            #     output_image[:pv_height, :pv_width, :3] = pv_image
            #     output_image[:lt_height, pv_width:pv_width + lt_width, :3] = LT_image

                #numpy_horizontal_concat1 = np.concatenate((pv_image, ahat_image), axis=1)
                #numpy_horizontal_concat2 = np.concatenate((eye_hand_image, LL_image, RR_image), axis=1)
                #numpy_vertical_concat = np.concatenate((numpy_horizontal_concat1, numpy_horizontal_concat2), axis=0)
                video.write(output_image)
               # cv2.imshow('Hololens2 stream visualizer', numpy_horizontal_concat1)
                #cv2.imshow("frame",output_image)
                #if cv2.waitKey(20) & 0xFF == ord('q'):
                #    break
    video.release()

if __name__ == "__main__":
    visualize_all_recordings_in_path(r'C:\HoloLens')
    #TODO: check if video name change works.
    exit(0)
    visualize(r'C:\HoloLens')
