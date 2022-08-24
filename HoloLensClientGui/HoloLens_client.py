import socket
import struct
import abc
import threading
from collections import namedtuple, deque
from enum import Enum
import numpy as np
import cv2
import csv
from pathlib import Path
from utils import *
import time
import os
from tkinter import *
from tkinter import messagebox
from eye_stream_header import EYE_FRAME_STREAM, EYE_STREAM_HEADER_FORMAT
from eye_stream_header_recorder_format import RECORDER_EYE_FRAME_STREAM, recorder_eye_frame_bytes
from transform_eye_frame_to_recorder_eye_frame import transform_eye_frame_to_recorder_eye_frame
import sys

np.warnings.filterwarnings('ignore')

# Definitions
# Protocol Header Format
# see https://docs.python.org/2/library/struct.html#format-characters


VIDEO_STREAM_HEADER_FORMAT = "@qIIII20f"

VIDEO_FRAME_STREAM_HEADER = namedtuple(
    'SensorFrameStreamHeader',
    'Timestamp ImageWidth ImageHeight PixelStride RowStride fx fy ox oy '
    'PVtoWorldtransformM11 PVtoWorldtransformM12 PVtoWorldtransformM13 PVtoWorldtransformM14 '
    'PVtoWorldtransformM21 PVtoWorldtransformM22 PVtoWorldtransformM23 PVtoWorldtransformM24 '
    'PVtoWorldtransformM31 PVtoWorldtransformM32 PVtoWorldtransformM33 PVtoWorldtransformM34 '
    'PVtoWorldtransformM41 PVtoWorldtransformM42 PVtoWorldtransformM43 PVtoWorldtransformM44 '
)

RM_EXTRINSICS_HEADER_FORMAT = "@16f"
RM_EXTRINSICS_HEADER = namedtuple(
    'SensorFrameExtrinsicsHeader',
    'rig2camTransformM11 rig2camTransformM12 rig2camTransformM13 rig2camTransformM14 '
    'rig2camTransformM21 rig2camTransformM22 rig2camTransformM23 rig2camTransformM24 '
    'rig2camTransformM31 rig2camTransformM32 rig2camTransformM33 rig2camTransformM34 '
    'rig2camTransformM41 rig2camTransformM42 rig2camTransformM43 rig2camTransformM44 '
)

RM_STREAM_HEADER_FORMAT = "@qIIII16f"
RM_FRAME_STREAM_HEADER = namedtuple(
    'SensorFrameStreamHeader',
    'Timestamp ImageWidth ImageHeight PixelStride RowStride '
    'rig2worldTransformM11 rig2worldTransformM12 rig2worldTransformM13 rig2worldTransformM14 '
    'rig2worldTransformM21 rig2worldTransformM22 rig2worldTransformM23 rig2worldTransformM24 '
    'rig2worldTransformM31 rig2worldTransformM32 rig2worldTransformM33 rig2worldTransformM34 '
    'rig2worldTransformM41 rig2worldTransformM42 rig2worldTransformM43 rig2worldTransformM44 '
)

# Each port corresponds to a single stream type
# AHAT_STREAM_PORT = 23941

VIDEO_STREAM_PORT = 23940
LONG_THROW_STREAM_PORT = 23941
LEFT_FRONT_STREAM_PORT = 23942
RIGHT_FRONT_STREAM_PORT = 23943
EYE_STREAM_PORT = 23945

HOST = '132.69.202.148'  # 169.254.233.208'   # '169.254.189.82' #'192.168.1.242'
# '192.168.1.92'

HundredsOfNsToMilliseconds = 1e-4
MillisecondsToSeconds = 1e-3


class SensorType(Enum):
    VIDEO = 1
    AHAT = 2
    LONG_THROW_DEPTH = 3
    LF_VLC = 4
    RF_VLC = 5


# super().__init__(host, EYE_STREAM_PORT, EYE_STREAM_HEADER_FORMAT,
#                  EYE_FRAME_STREAM, False)
class FrameReceiverThread(threading.Thread):
    def __init__(self, host, port, header_format, header_data, find_extrinsics):
        super(FrameReceiverThread, self).__init__()
        self.header_size = struct.calcsize(header_format)
        self.header_format = header_format
        self.header_data = header_data
        self.host = host
        self.port = port
        self.latest_frame = None
        self.latest_header = None
        self.extrinsics_header = None
        self.socket = None
        self.find_extrinsics = find_extrinsics
        self.lut = None

    def get_extrinsics_from_socket(self, imgWidth, imgHeight):
        # read the header in chunks
        reply = self.recvall(self.header_size)

        if not reply:
            print('ERROR: Failed to receive data from stream.')
            return

        data = struct.unpack(self.header_format, reply)
        header = self.header_data(*data)

        size_of_float = 4
        lut_bytes = imgHeight * imgWidth * 3 * size_of_float

        lut_data = self.recvall(lut_bytes)

        return header, lut_data

    def get_data_from_socket(self):
        # read the header in chunks
        reply = self.recvall(self.header_size)

        if not reply:
            print('ERROR: Failed to receive data from stream.')
            return

        data = struct.unpack(self.header_format, reply)
        header = self.header_data(*data)

        # read the image in chunks
        image_size_bytes = header.ImageHeight * header.RowStride

        image_data = self.recvall(image_size_bytes)

        return header, image_data

    def recvall(self, size):
        msg = bytes()
        while len(msg) < size:
            try:
                part = self.socket.recv(size - len(msg))
            except:
                break
            if part == '':
                break  # the connection is closed
            msg += part
        return msg

    def start_socket(self):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.connect((self.host, self.port))

        # send_message(self.socket, b'socket connected at ')
        print('INFO: Socket connected to ' + self.host + ' on port ' + str(self.port))

    def start_listen(self):
        t = threading.Thread(target=self.listen)
        t.start()

    @abc.abstractmethod
    def listen(self):
        return

    @abc.abstractmethod
    def get_mat_from_header(self, header):
        return


class EyeReceiverThread(FrameReceiverThread):

    def get_mat_from_header(self, header):
        pass

    def __init__(self, host):
        self.eye_flag = False
        self.prev_timestamp = 0
        super().__init__(host, EYE_STREAM_PORT, EYE_STREAM_HEADER_FORMAT,
                         # TODO: change back to EYE_STREAM_HEADER_FORMAT
                         EYE_FRAME_STREAM, False)

    def get_eye_data_from_socket(self):
        # read the header in chunks
        reply = self.recvall(self.header_size)
        if not reply:
            print('ERROR: Failed to receive data from stream.')
            return

        data = struct.unpack(self.header_format, reply)
        eye_data_struct = self.header_data(*data)
        return eye_data_struct

    def listen(self):
        while True:
            self.latest_header = self.get_eye_data_from_socket()
            if self.latest_header is not None:
                if self.prev_timestamp != self.latest_header.timestamp:
                    self.prev_timestamp = self.latest_header.timestamp
                    self.eye_flag = True
                else:
                    print(f"for some reason we got the same timestamp twice. will not save second timestamp data"
                          f" prev timestamp = {self.prev_timestamp} new timestamp = {self.latest_header.timestamp}")

            else:
                print("for some reason lateset header is none")


class VideoReceiverThread(FrameReceiverThread):
    def __init__(self, host):
        self.pv_flag = False
        self.prev_timestamp = 0
        super().__init__(host, VIDEO_STREAM_PORT, VIDEO_STREAM_HEADER_FORMAT,
                         VIDEO_FRAME_STREAM_HEADER, False)

    def listen(self):
        while True:
            self.latest_header, image_data = self.get_data_from_socket()
            self.pv_flag = True
            self.latest_frame = np.frombuffer(image_data, dtype=np.uint8).reshape((self.latest_header.ImageHeight,
                                                                                   self.latest_header.ImageWidth,
                                                                                   self.latest_header.PixelStride))
            assert (self.prev_timestamp != self.latest_header.Timestamp)
            self.prev_timestamp = self.latest_header.Timestamp

    def get_mat_from_header(self, header):
        pv_to_world_transform = np.array(header[7:24]).reshape((4, 4)).T
        return pv_to_world_transform


class AhatReceiverThread(FrameReceiverThread):

    def __init__(self, host, port, header_format, header_data, find_extrinsics=False):
        super().__init__(host, port, header_format, header_data, find_extrinsics)
        self.ahat_flag = False
        self.prev_timestamp = 0

    def listen(self):
        while True:
            if self.find_extrinsics:
                if not np.any(self.lut):
                    self.extrinsics_header, lut_data = self.get_extrinsics_from_socket(512, 512)
                    self.lut = np.frombuffer(lut_data, dtype=np.float32).reshape((512 * 512, 3))
            else:
                self.latest_header, image_data = self.get_data_from_socket()

                self.latest_frame = np.frombuffer(image_data, dtype=np.uint16).reshape(
                    (self.latest_header.ImageHeight, self.latest_header.ImageWidth))

                self.ahat_flag = True
                assert (self.prev_timestamp != self.latest_header.Timestamp)
                self.prev_timestamp = self.latest_header.Timestamp

    def get_mat_from_header(self, header):
        rig_to_world_transform = np.array(header[5:22]).reshape((4, 4)).T
        return rig_to_world_transform


class LongThrowReceiverThread(FrameReceiverThread):

    def __init__(self, host, port, header_format, header_data, find_extrinsics=False):
        super().__init__(host, port, header_format, header_data, find_extrinsics)
        self.lt_flag = False
        self.prev_timestamp = 0

    def listen(self):
        frame_counter = 0
        while True:
            if self.find_extrinsics:
                if not np.any(self.lut):
                    self.extrinsics_header, lut_data = self.get_extrinsics_from_socket(320, 288)
                    self.lut = np.frombuffer(lut_data, dtype=np.float32).reshape((320 * 288, 3))
            else:
                frame_counter += 1
                if frame_counter % 20 == 0:
                    print(f"got {frame_counter} long throw frames")
                self.latest_header, image_data = self.get_data_from_socket()

                self.latest_frame = np.frombuffer(image_data, dtype=np.uint16).reshape(
                    (self.latest_header.ImageHeight, self.latest_header.ImageWidth))
                self.lt_flag = True
                assert (self.prev_timestamp != self.latest_header.Timestamp)
                self.prev_timestamp = self.latest_header.Timestamp

    def get_mat_from_header(self, header):
        rig_to_world_transform = np.array(header[5:22]).reshape((4, 4)).T
        return rig_to_world_transform


class SpatialCamsReceiverThread(FrameReceiverThread):
    def __init__(self, host, port, header_format, header_data, find_extrinsics=False):
        super().__init__(host, port, header_format, header_data, find_extrinsics)

    def listen(self):
        while True:
            if self.find_extrinsics:
                if not np.any(self.lut):
                    self.extrinsics_header, lut_data = self.get_extrinsics_from_socket(640, 480)
                    self.lut = np.frombuffer(lut_data, dtype=np.float32).reshape((640 * 480, 3))
            else:
                self.latest_header, image_data = self.get_data_from_socket()
                self.latest_frame = np.frombuffer(image_data, dtype=np.uint8).reshape(
                    (self.latest_header.ImageHeight, self.latest_header.ImageWidth))

    def get_mat_from_header(self, header):
        rig_to_world_transform = np.array(header[5:22]).reshape((4, 4)).T
        return rig_to_world_transform


############################################
this_flag = True

Second_font = ("Comic Sans MS", 10, "bold")
end = 2
start = 2
FullList = []


def test(last_path):
    StartWatch()
    global this_flag

    # while this_flag:
    #     print("Your Path is : " + last_path)
    #     time.sleep(0.5)


def Stop():
    # global end
    global this_flag
    this_flag = False
    stopwatch()
    print("stopped")


def update():
    global this_flag

    this_flag = True


def display(root, duration_text, pv_text, AHAT_text):
    global start
    dur_display = Label(root, text="" + duration_text, font=Second_font)
    # dur_display.place(x=110, y=300)
    pv_display = Label(root, text="" + pv_text, font=Second_font)
    # pv_display.place(x=110, y=320)
    AHAT_display = pv_display = Label(root, text="" + AHAT_text, font=Second_font)
    # AHAT_display.place(x=110, y=340)


def counter(root, path):
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
    print(format(fps, ".3f"))
    fps_num_display = format(fps, ".3f")

    dur_time = Label(root, text=temp, font=Second_font)
    dur_time.place(x=110, y=380)
    FpsDisplay = Label(root, text=fps_num_display, font=Second_font)
    FpsDisplay.place(x=110, y=400)
    Ah_display = Label(root, text=fps_num_display, font=Second_font)
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
    print("M", mins)
    sec = sec % 60
    print("s", sec)
    hours = mins // 60
    print("h", hours)

    mins = mins % 60
    print("Last mins", mins)

    print("Time Lapsed = {0}:{1}:{2:.2f}".format(int(hours), int(mins), sec))

    return "{0}:{1}:{2:.2f}".format(int(hours), int(mins), sec)


#############################################

def main_function(path, HOST):
    output_path = Path(path)

    video_receiver = VideoReceiverThread(HOST)
    video_receiver.start_socket()

    # ahat_extr_receiver = AhatReceiverThread(HOST, AHAT_STREAM_PORT, RM_EXTRINSICS_HEADER_FORMAT, RM_EXTRINSICS_HEADER,True)
    # ahat_extr_receiver.start_socket()

    lt_extr_receiver = LongThrowReceiverThread(HOST, LONG_THROW_STREAM_PORT, RM_EXTRINSICS_HEADER_FORMAT,
                                               RM_EXTRINSICS_HEADER, True)
    lt_extr_receiver.start_socket()

    eye_receiver = EyeReceiverThread(HOST)
    eye_receiver.start_socket()
    eye_receiver.start_listen()

    video_receiver.start_listen()
    # ahat_extr_receiver.start_listen()
    lt_extr_receiver.start_listen()
    first_line_flag = True
    ahat_receiver = None
    lt_receiver = None
    prev_timestamp_pv = 0
    prev_timestamp_ahat = 0
    prev_timestamp_lt = 0
    prev_timestamp_eye_gaze = 0
    with open(output_path / 'pv.txt', 'w', newline='') as f1, \
            open(output_path / 'head_hand_eye.csv', 'w', newline='') as f_eye_recorder, \
            open(output_path / 'Depth Long Throw_lut.bin', 'w', newline='') as f5, \
            open(output_path / 'Depth Long Throw_rig2world.txt', 'w', newline='') as f7:

        w1 = csv.writer(f1)
        w4 = csv.writer(f7)
        w_eye_recorder = csv.writer(f_eye_recorder)

        while True:
            if eye_receiver is not None and np.any(eye_receiver.latest_header):
                streamer_eye_data = eye_receiver.latest_header
                curr_eye_timestamp = streamer_eye_data.timestamp
                if prev_timestamp_eye_gaze < curr_eye_timestamp:
                    recorder_format_eye_data = transform_eye_frame_to_recorder_eye_frame(streamer_eye_data)
                    corrected_trues = [str(1) if str(field) == "True" else str(field) for field in
                                       recorder_format_eye_data]
                    corrected_booleans = [str(0) if str(field) == "False" else str(field) for field in corrected_trues]
                    w_eye_recorder.writerow(corrected_booleans)  # change all fields to strings before saving them.
                    prev_timestamp_eye_gaze = curr_eye_timestamp

            if video_receiver is not None and np.any(video_receiver.latest_frame):
                latest_frame = video_receiver.latest_frame
                pv_hdr = video_receiver.latest_header
                curr_pv_timestamp = pv_hdr.Timestamp
                if prev_timestamp_pv < curr_pv_timestamp and video_receiver.pv_flag:
                    cv2.imwrite(str(output_path / "PV" / (str(curr_pv_timestamp) + ".png")), latest_frame)
                    prev_timestamp_pv = curr_pv_timestamp
                    video_receiver.pv_flag = False

                    pv2world_transform = np.array([
                        pv_hdr.PVtoWorldtransformM11, pv_hdr.PVtoWorldtransformM12, pv_hdr.PVtoWorldtransformM13,
                        pv_hdr.PVtoWorldtransformM14,
                        pv_hdr.PVtoWorldtransformM21, pv_hdr.PVtoWorldtransformM22, pv_hdr.PVtoWorldtransformM23,
                        pv_hdr.PVtoWorldtransformM24,
                        pv_hdr.PVtoWorldtransformM31, pv_hdr.PVtoWorldtransformM32, pv_hdr.PVtoWorldtransformM33,
                        pv_hdr.PVtoWorldtransformM34,
                        pv_hdr.PVtoWorldtransformM41, pv_hdr.PVtoWorldtransformM42, pv_hdr.PVtoWorldtransformM43,
                        pv_hdr.PVtoWorldtransformM44]).reshape(4, 4)

                    pv2world_transform = np.transpose(pv2world_transform)
                    if first_line_flag:
                        first_line_flag = False
                        w1.writerow([pv_hdr.ox, pv_hdr.oy, pv_hdr.ImageWidth, pv_hdr.ImageHeight])
                    w1.writerow(
                        [pv_hdr.Timestamp, pv_hdr.fx, pv_hdr.fy, pv2world_transform[0, 0], pv2world_transform[0, 1],
                         pv2world_transform[0, 2], pv2world_transform[0, 3],
                         pv2world_transform[1, 0], pv2world_transform[1, 1], pv2world_transform[1, 2],
                         pv2world_transform[1, 3],
                         pv2world_transform[2, 0], pv2world_transform[2, 1], pv2world_transform[2, 2],
                         pv2world_transform[2, 3],
                         pv2world_transform[3, 0], pv2world_transform[3, 1], pv2world_transform[3, 2],
                         pv2world_transform[3, 3]])
                cv2.imshow('Photo Video Camera Stream', video_receiver.latest_frame)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break

            # if ahat_receiver and np.any(ahat_receiver.latest_frame) and ahat_receiver.ahat_flag:
            #     #
            #     # save_count_ahat += 1
            #     header = ahat_receiver.latest_header
            #     curr_ahat_timestamp = header.Timestamp
            #     # print("c_t: ", curr_ahat_timestamp, "p_t: ", prev_timestamp_ahat)
            #
            #     cv2.imwrite(str(output_path) + r"\Depth AHaT\\" + str(curr_ahat_timestamp) + ".pgm",
            #                 (ahat_receiver.latest_frame).astype(np.uint16))
            #     prev_timestamp_ahat = curr_ahat_timestamp
            #     ahat_receiver.ahat_flag = False
            #
            #     # depth_img = ahat_receiver.latest_frame
            #     depth_hdr = ahat_receiver.latest_header
            #     rig2world_transform = np.array([
            #         depth_hdr.rig2worldTransformM11, depth_hdr.rig2worldTransformM12, depth_hdr.rig2worldTransformM13,
            #         depth_hdr.rig2worldTransformM14,
            #         depth_hdr.rig2worldTransformM21, depth_hdr.rig2worldTransformM22, depth_hdr.rig2worldTransformM23,
            #         depth_hdr.rig2worldTransformM24,
            #         depth_hdr.rig2worldTransformM31, depth_hdr.rig2worldTransformM32, depth_hdr.rig2worldTransformM33,
            #         depth_hdr.rig2worldTransformM34,
            #         depth_hdr.rig2worldTransformM41, depth_hdr.rig2worldTransformM42, depth_hdr.rig2worldTransformM43,
            #         depth_hdr.rig2worldTransformM44]).reshape(4, 4)
            #
            #     rig2world_transform = np.transpose(rig2world_transform)
            #     # change back to ahat timestamp
            #     w2.writerow([curr_ahat_timestamp, rig2world_transform[0, 0], rig2world_transform[0, 1],
            #                  rig2world_transform[0, 2], rig2world_transform[0, 3],
            #                  rig2world_transform[1, 0], rig2world_transform[1, 1], rig2world_transform[1, 2],
            #                  rig2world_transform[1, 3],
            #                  rig2world_transform[2, 0], rig2world_transform[2, 1], rig2world_transform[2, 2],
            #                  rig2world_transform[2, 3],
            #                  rig2world_transform[3, 0], rig2world_transform[3, 1], rig2world_transform[3, 2],
            #                  rig2world_transform[3, 3]])

            # if ahat_extr_receiver and np.any(ahat_extr_receiver.lut):
            #     ahat_extr_receiver.socket.close()
            #     ahat_receiver = AhatReceiverThread(HOST, AHAT_STREAM_PORT, RM_STREAM_HEADER_FORMAT,
            #                                        RM_FRAME_STREAM_HEADER)
            #
            #     ahat_receiver.extrinsics_header = ahat_extr_receiver.extrinsics_header
            #     # ahat_receiver.lut = ahat_extr_receiver.lut
            #     ahat_extr_receiver.lut.tofile(f4)
            #
            #     depth_hdr = ahat_receiver.extrinsics_header
            #     rig2cam_transform = np.array([
            #         depth_hdr.rig2camTransformM11, depth_hdr.rig2camTransformM12, depth_hdr.rig2camTransformM13,
            #         depth_hdr.rig2camTransformM14,
            #         depth_hdr.rig2camTransformM21, depth_hdr.rig2camTransformM22, depth_hdr.rig2camTransformM23,
            #         depth_hdr.rig2camTransformM24,
            #         depth_hdr.rig2camTransformM31, depth_hdr.rig2camTransformM32, depth_hdr.rig2camTransformM33,
            #         depth_hdr.rig2camTransformM34,
            #         depth_hdr.rig2camTransformM41, depth_hdr.rig2camTransformM42, depth_hdr.rig2camTransformM43,
            #         depth_hdr.rig2camTransformM44]).reshape(4, 4)
            #
            #     with open(output_path / 'Depth AHaT_extrinsics.txt', 'w') as f3:
            #         w3 = csv.writer(f3)
            #         w3.writerow([rig2cam_transform[0, 0], rig2cam_transform[0, 1],
            #                      rig2cam_transform[0, 2], rig2cam_transform[0, 3],
            #                      rig2cam_transform[1, 0], rig2cam_transform[1, 1], rig2cam_transform[1, 2],
            #                      rig2cam_transform[1, 3],
            #                      rig2cam_transform[2, 0], rig2cam_transform[2, 1], rig2cam_transform[2, 2],
            #                      rig2cam_transform[2, 3],
            #                      rig2cam_transform[3, 0], rig2cam_transform[3, 1], rig2cam_transform[3, 2],
            #                      rig2cam_transform[3, 3]])
            #
            #     ahat_extr_receiver = None
            #     ahat_receiver.start_socket()
            #     ahat_receiver.start_listen()
            # long throw depth
            if lt_receiver and np.any(lt_receiver.latest_frame) and lt_receiver.lt_flag:
                header = lt_receiver.latest_header
                curr_lt_timestamp = header.Timestamp
                if prev_timestamp_lt < curr_lt_timestamp:
                    cv2.imwrite(str(output_path) + r"\Depth Long Throw\\" + str(curr_lt_timestamp) + ".pgm",
                                (lt_receiver.latest_frame).astype(np.uint16))
                prev_timestamp_lt = curr_lt_timestamp
                lt_receiver.lt_flag = False

                depth_hdr = lt_receiver.latest_header
                rig2world_transform = np.array([
                    depth_hdr.rig2worldTransformM11, depth_hdr.rig2worldTransformM12, depth_hdr.rig2worldTransformM13,
                    depth_hdr.rig2worldTransformM14,
                    depth_hdr.rig2worldTransformM21, depth_hdr.rig2worldTransformM22, depth_hdr.rig2worldTransformM23,
                    depth_hdr.rig2worldTransformM24,
                    depth_hdr.rig2worldTransformM31, depth_hdr.rig2worldTransformM32, depth_hdr.rig2worldTransformM33,
                    depth_hdr.rig2worldTransformM34,
                    depth_hdr.rig2worldTransformM41, depth_hdr.rig2worldTransformM42, depth_hdr.rig2worldTransformM43,
                    depth_hdr.rig2worldTransformM44]).reshape(4, 4)

                rig2world_transform = np.transpose(rig2world_transform)
                w4.writerow(
                    [curr_lt_timestamp, rig2world_transform[0, 0], rig2world_transform[0, 1], rig2world_transform[0, 2],
                     rig2world_transform[0, 3],
                     rig2world_transform[1, 0], rig2world_transform[1, 1], rig2world_transform[1, 2],
                     rig2world_transform[1, 3],
                     rig2world_transform[2, 0], rig2world_transform[2, 1], rig2world_transform[2, 2],
                     rig2world_transform[2, 3],
                     rig2world_transform[3, 0], rig2world_transform[3, 1], rig2world_transform[3, 2],
                     rig2world_transform[3, 3]])

            if lt_extr_receiver and np.any(lt_extr_receiver.lut):
                lt_extr_receiver.socket.close()
                lt_receiver = LongThrowReceiverThread(HOST, LONG_THROW_STREAM_PORT, RM_STREAM_HEADER_FORMAT,
                                                      RM_FRAME_STREAM_HEADER)

                lt_receiver.extrinsics_header = lt_extr_receiver.extrinsics_header
                lt_extr_receiver.lut.tofile(f5)

                depth_hdr = lt_receiver.extrinsics_header
                rig2cam_transform = np.array([
                    depth_hdr.rig2camTransformM11, depth_hdr.rig2camTransformM12, depth_hdr.rig2camTransformM13,
                    depth_hdr.rig2camTransformM14,
                    depth_hdr.rig2camTransformM21, depth_hdr.rig2camTransformM22, depth_hdr.rig2camTransformM23,
                    depth_hdr.rig2camTransformM24,
                    depth_hdr.rig2camTransformM31, depth_hdr.rig2camTransformM32, depth_hdr.rig2camTransformM33,
                    depth_hdr.rig2camTransformM34,
                    depth_hdr.rig2camTransformM41, depth_hdr.rig2camTransformM42, depth_hdr.rig2camTransformM43,
                    depth_hdr.rig2camTransformM44]).reshape(4, 4)

                with open(output_path / 'Depth Long Throw_extrinsics.txt', 'w') as f6:
                    w3 = csv.writer(f6)
                    w3.writerow([rig2cam_transform[0, 0], rig2cam_transform[0, 1],
                                 rig2cam_transform[0, 2], rig2cam_transform[0, 3],
                                 rig2cam_transform[1, 0], rig2cam_transform[1, 1], rig2cam_transform[1, 2],
                                 rig2cam_transform[1, 3],
                                 rig2cam_transform[2, 0], rig2cam_transform[2, 1], rig2cam_transform[2, 2],
                                 rig2cam_transform[2, 3],
                                 rig2cam_transform[3, 0], rig2cam_transform[3, 1], rig2cam_transform[3, 2],
                                 rig2cam_transform[3, 3]])

                lt_extr_receiver = None
                lt_receiver.start_socket()
                lt_receiver.start_listen()


if __name__ == "__main__":
    path = os.path.abspath(__file__)
    output_dir = os.path.join(path, "output_dir")
    main_function(output_dir, HOST)
