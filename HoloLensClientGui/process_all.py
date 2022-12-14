"""
 Copyright (c) Microsoft. All rights reserved.
 This code is licensed under the MIT License (MIT).
 THIS CODE IS PROVIDED *AS IS* WITHOUT WARRANTY OF
 ANY KIND, EITHER EXPRESS OR IMPLIED, INCLUDING ANY
 IMPLIED WARRANTIES OF FITNESS FOR A PARTICULAR
 PURPOSE, MERCHANTABILITY, OR NON-INFRINGEMENT.
"""
import argparse
from pathlib import Path
from project_hand_eye_to_pv import project_hand_eye_to_pv
from utils import check_framerates, extract_tar_file
from save_pclouds import save_pclouds
from convert_images import convert_images
from glob import glob
import os


def check_if_recording_was_processed(path):
    if "_recDir" in path[-8:]:
        if "eye_hands" not in os.listdir(path):
            return False
        pgm_paths = sorted(list((Path(path) / 'Depth Long Throw').glob('*pgm')))
        ply_paths = sorted(list((Path(path) / 'Depth Long Throw').glob('*ply')))
        print(len(pgm_paths), len(ply_paths))
        if len(ply_paths) == 0:
            return False
    else:
        print("this is not a recording directory")
        return False

    return True


def process_all_recordings_in_path(path):

    if "_recDir" in path[-8:] and not check_if_recording_was_processed(path):
        print(f"calling process_all for {path}")
        print(os.listdir(path))
        try:
            process_all(Path(path), project_hand_eye=True)
        except:
            print("some error occured for this file. probably need to delete this recording")

        return
    for sub_dir in glob(rf"{path}\*\\"):
        print(f"calling process_all_recordings_in_path for path: {sub_dir}, continuing search for recording dir")
        process_all_recordings_in_path(sub_dir)


def process_all(w_path, project_hand_eye=True):
    # Extract all tar
    for tar_fname in w_path.glob("*.tar"):
        print(f"Extracting {tar_fname}")
        tar_output = ''
        tar_output = w_path / Path(tar_fname.stem)
        tar_output.mkdir(exist_ok=True)
        extract_tar_file(tar_fname, tar_output)

    # Process PV if recorded
    if (w_path / "PV.tar").exists():
        # Convert images
        convert_images(w_path)

    # Project
    if (w_path / "PV").exists():

        if project_hand_eye:
            if project_hand_eye_to_pv(w_path) == -1 :
                return -1

# Process depth if recorded
    for sensor_name in ["Depth Long Throw", "Depth AHaT"]:
        if (w_path / "{}".format(sensor_name)).exists():
            # Save point clouds
            save_pclouds(w_path, sensor_name)
    print("")
    check_framerates(w_path)


if __name__ == '__main__':
    w_path = Path(r'C:\HoloLens')
    process_all_recordings_in_path(r'C:\HoloLens')
#     parser = argparse.ArgumentParser(description='Process recorded data.')
#     parser.add_argument("--recording_path", required=True,
#                         help="Path to recording folder")
#     parser.add_argument("--project_hand_eye",
#                         required=False,
#                         action='store_true',
#                         help="Project hand joints (and eye gaze, if recorded) to rgb images")
#
#     args = parser.parse_args()
#
#     w_path = Path(args.recording_path)
#
#     process_all(w_path, args.project_hand_eye)
