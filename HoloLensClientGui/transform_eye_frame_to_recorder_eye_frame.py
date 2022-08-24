from collections import namedtuple, deque
from eye_stream_header import EYE_FRAME_STREAM
from eye_stream_header_recorder_format import RECORDER_EYE_FRAME_STREAM, recorder_eye_frame_bytes, RECORDER_EYE_STREAM_FORMAT, recorder_eye_frame_num_fields
import struct
from pathlib import Path
import csv

def transform_eye_frame_to_recorder_eye_frame(streamer_eye_frame:EYE_FRAME_STREAM):
    disk_space_allocation = bytearray([0 for i in range(3448)]) #recorder_eye_frame_num_fields)])
    formatted_disk_space_allocation = struct.unpack(RECORDER_EYE_STREAM_FORMAT, disk_space_allocation)
    recorder_eye_frame = RECORDER_EYE_FRAME_STREAM(*formatted_disk_space_allocation)
    recorder_dict = recorder_eye_frame._asdict()
    streamer_dict = streamer_eye_frame._asdict()

    for name in recorder_eye_frame._fields:
        recorder_dict[name] = streamer_dict[name]
        if streamer_dict[name] == True:
            streamer_dict[name] = 1
        if streamer_dict[name] == False:
            streamer_dict[name] = 0

    return RECORDER_EYE_FRAME_STREAM(*recorder_dict.values())

#
# #
# streamer_eye_frame = EYE_FRAME_STREAM(*[i+2**60 for i in range(878)])
# disk_space_allocation = bytearray([0 for i in range(3448)])#recorder_eye_frame_num_fields)])
# formatted_disk_space_allocation = struct.unpack(RECORDER_EYE_STREAM_FORMAT, disk_space_allocation)
# recorder_eye_frame = RECORDER_EYE_FRAME_STREAM(*formatted_disk_space_allocation)
# recorder_dict = recorder_eye_frame._asdict()
# streamer_dict = streamer_eye_frame._asdict()
#
# for name in recorder_eye_frame._fields:
#     recorder_dict[name] = streamer_dict[name]
# named_data = RECORDER_EYE_FRAME_STREAM(*recorder_dict.values())
# print(named_data)
#
# path = r"C:\Users\jonathan_pc\Desktop\HoloLens2DataAcquisition\streamer_repurposed"
# output_path = Path(path)
#
# with open(output_path / 'test_eye_data_printer.csv', 'w', newline='')as test_f:
#     test_recorder = csv.writer(test_f)
#     string_data = [str(field) for field in named_data]
#     print(string_data)
#     test_recorder.writerow(string_data)
#     test_recorder.writerow(string_data)
#     test_recorder.writerow(string_data)
#
#
